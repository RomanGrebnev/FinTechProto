"""Builds the Mistral prompt and turns the response into a validated Analysis."""

import json
import logging

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from .config import MISTRAL_API_KEY, MISTRAL_MODEL
from .models import User
from .portfolio import FUND_TYPES
from .schemas import Analysis, PortfolioOut

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Wealthpilot, an investment research assistant for French retail investors.
You produce personalised investment advice on behalf of Wealthpilot SAS, a registered conseiller en
investissements financiers (CIF) giving non-independent advice. You never execute trades. Present your
output as personalised advice based on the information the investor provided.

Context to keep in mind:
- The investor is French. Where relevant, mention French wrappers (PEA, assurance-vie, compte-titres)
  and PEA eligibility (EU-listed equities and PEA-eligible ETFs).
- Prefer broad, low-cost, diversified instruments (UCITS ETFs) when suggesting new positions.
- Match suggestions to the investor's risk tolerance (1 = very conservative, 5 = aggressive) and horizon.
- Be specific: name tickers (Yahoo Finance format, e.g. CW8.PA, MC.PA) and give concrete percentages.

Suitability rules (mandatory):
- Never recommend a product whose risk exceeds the investor's risk tolerance or their maximum acceptable
  loss (max_acceptable_loss_pct): a plausible drawdown of the product must not exceed that loss.
- If investment_knowledge is "none", recommend only diversified UCITS ETFs or bond funds.
- Take investment_experience_years and investment_knowledge into account; avoid complex products for
  basic knowledge or little experience.
- The "summary" must include a suitability statement explaining why this advice is suitable for this
  investor's knowledge, experience, loss capacity, risk tolerance and horizon.

Reply with a single JSON object, no markdown, exactly matching this schema:
{
  "summary": "2-3 sentence overall assessment of the portfolio vs the investor's profile",
  "recommendations": [   // exactly 3 items
    {"action": "buy" | "sell" | "hold" | "rebalance",
     "ticker": "Yahoo ticker",
     "title": "short imperative headline, max 8 words",
     "rationale": "2-4 sentences explaining why, referencing the investor's data"}
  ],
  "rebalancing": {
    "summary": "1-3 sentences describing the suggested rebalancing",
    "target_allocation": [ {"label": "asset or asset class", "percent": number} ]  // sums to 100
  },
  "risk_flag": {"severity": "low" | "medium" | "high", "title": "short headline", "detail": "1-3 sentences"}
}"""

GOAL_LABELS = {
    "retirement": "retirement", "home": "buying a home", "education": "education",
    "wealth_growth": "long-term wealth growth", "emergency_fund": "emergency fund", "other": "other",
}


def build_user_message(user: User, portfolio: PortfolioOut) -> str:
    p = user.profile
    data = {
        "investor_profile": {
            "age": p.age,
            "annual_income_eur": p.annual_income,
            "savings_goal": GOAL_LABELS.get(p.savings_goal, p.savings_goal),
            "monthly_investment_eur": p.monthly_investment,
            "risk_tolerance_1_to_5": p.risk_tolerance,
            "investment_horizon_years": p.horizon_years,
            "investment_knowledge": p.investment_knowledge,
            "investment_experience_years": p.investment_experience_years,
            "max_acceptable_loss_pct": p.max_acceptable_loss_pct,
        },
        "portfolio": {
            "currency": portfolio.currency,
            "total_value": portfolio.total_value,
            "total_unrealised_pnl_pct": portfolio.total_pnl_pct,
            "measured_risk_score_1_to_5": portfolio.risk_score,
            "annualised_volatility_pct": portfolio.volatility,
            "holdings": [
                {
                    "ticker": h.ticker, "name": h.name, "type": h.instrument_type, "quantity": h.quantity,
                    "avg_buy_price": h.avg_buy_price, "current_price": h.current_price,
                    "price_currency": h.currency, "value_eur": h.value,
                    "weight_pct": h.weight, "unrealised_pnl_pct": h.pnl_pct,
                }
                for h in portfolio.holdings
            ],
        },
    }
    return "Analyse this investor and portfolio:\n" + json.dumps(data, indent=2)


def mistral_analysis(user: User, portfolio: PortfolioOut) -> Analysis:
    body = {
        "model": MISTRAL_MODEL,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(user, portfolio)},
        ],
    }
    try:
        r = httpx.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {MISTRAL_API_KEY}"},
            json=body, timeout=60,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        analysis = Analysis.model_validate_json(content)
    except httpx.HTTPError as e:
        log.error("Mistral request failed: %s", e)
        raise HTTPException(502, "The AI advisor is unavailable right now. Please try again.")
    except (ValidationError, KeyError, ValueError) as e:
        log.error("Mistral returned an unexpected payload: %s", e)
        raise HTTPException(502, "The AI advisor returned an unexpected answer. Please try again.")
    analysis.recommendations = analysis.recommendations[:3]
    return analysis


def demo_analysis(user: User, portfolio: PortfolioOut) -> Analysis:
    """Rule-based stand-in used when MISTRAL_API_KEY is not set, so the app is usable offline."""
    p = user.profile
    holdings = sorted(portfolio.holdings, key=lambda h: h.weight, reverse=True)
    recs = []
    stocks = [h for h in holdings if h.instrument_type not in FUND_TYPES]
    if stocks:
        top = stocks[0]
        if top.weight > 25:
            recs.append({"action": "rebalance", "ticker": top.ticker,
                         "title": f"Trim {top.ticker} below 20% of portfolio",
                         "rationale": f"{top.ticker} is {top.weight:.0f}% of your portfolio. A single position this large "
                                      "means one company's news can move your whole savings. Consider redirecting part "
                                      "of it to diversified funds."})
    if holdings:
        worst = min(holdings, key=lambda h: h.pnl_pct)
        if worst.pnl_pct < -10 and all(r["ticker"] != worst.ticker for r in recs):
            recs.append({"action": "hold", "ticker": worst.ticker,
                         "title": f"Review the thesis on {worst.ticker}",
                         "rationale": f"{worst.ticker} is down {abs(worst.pnl_pct):.0f}% from your average buy price. "
                                      "Check whether the reasons you bought it still hold before averaging down or selling."})
    gap = portfolio.risk_score - p.risk_tolerance
    recs.append({"action": "buy", "ticker": "CW8.PA",
                 "title": "Invest monthly in a PEA-eligible MSCI World ETF",
                 "rationale": f"With a {p.horizon_years}-year horizon, a monthly €{p.monthly_investment:.0f} into a broad, "
                              "PEA-eligible world equity ETF spreads risk across ~1,300 companies at low cost and "
                              "benefits from PEA tax treatment after 5 years."})
    bond_reason = (f"Your portfolio's measured risk ({portfolio.risk_score}/5) is above your stated tolerance "
                   f"({p.risk_tolerance}/5)." if gap > 0.5 else
                   "A bond allocation adds a source of return that does not move with equity markets.")
    recs.append({"action": "buy", "ticker": "IEAG.AS",
                 "title": "Add a euro aggregate bond ETF",
                 "rationale": bond_reason + f" Directing part of your €{p.monthly_investment:.0f} monthly contribution "
                              "to euro bonds would cushion drawdowns. Note: bond ETFs are not PEA-eligible; "
                              "hold them in a compte-titres or assurance-vie."})
    if holdings:
        best = max(holdings, key=lambda h: h.pnl_pct)
        recs.append({"action": "hold", "ticker": best.ticker,
                     "title": f"Keep {best.ticker} but stop adding",
                     "rationale": f"{best.ticker} is up {best.pnl_pct:.0f}% on your buy price and is {best.weight:.0f}% of "
                                  "the portfolio. Holding avoids crystallising capital gains tax (30% flat tax outside "
                                  "a PEA); new money is better spent on under-weighted assets."})

    equity = round(max(20, min(90, 20 + p.risk_tolerance * 12 + min(p.horizon_years, 20) / 2)))
    return Analysis.model_validate({
        "summary": f"Your portfolio is worth €{portfolio.total_value:,.0f} with a measured risk of "
                   f"{portfolio.risk_score}/5 ({portfolio.risk_label.lower()}), against a stated tolerance of "
                   f"{p.risk_tolerance}/5. This is a demo analysis — set MISTRAL_API_KEY for AI-generated advice.",
        "recommendations": recs[:3],
        "rebalancing": {
            "summary": f"For a risk tolerance of {p.risk_tolerance}/5 over {p.horizon_years} years, a reference "
                       f"allocation is roughly {equity}% equities and {100 - equity}% bonds and cash.",
            "target_allocation": [
                {"label": "Global equities (ETF)", "percent": round(equity * 0.7)},
                {"label": "European equities", "percent": equity - round(equity * 0.7)},
                {"label": "Euro bonds", "percent": round((100 - equity) * 0.7)},
                {"label": "Cash / money market", "percent": 100 - equity - round((100 - equity) * 0.7)},
            ],
        },
        "risk_flag": _demo_risk_flag(portfolio, p.risk_tolerance, stocks),
    })


def _demo_risk_flag(portfolio: PortfolioOut, tolerance: int, stocks) -> dict:
    gap = portfolio.risk_score - tolerance
    base = f"Measured portfolio risk is {portfolio.risk_score}/5 versus your stated tolerance of {tolerance}/5."
    if gap > 0.5:
        return {"severity": "high" if gap > 1 else "medium", "title": "Risk above your tolerance",
                "detail": base + " A sharp market fall could hit harder than you are comfortable with."}
    if stocks and stocks[0].weight > 25:
        return {"severity": "medium", "title": f"Concentrated in {stocks[0].ticker}",
                "detail": f"{stocks[0].ticker} alone is {stocks[0].weight:.0f}% of your portfolio. " + base}
    if gap < -1:
        return {"severity": "low", "title": "More cautious than your profile",
                "detail": base + f" Over a long horizon this may limit growth towards your goal."}
    return {"severity": "low", "title": "Risk in line with your profile", "detail": base}


def analyse(user: User, portfolio: PortfolioOut) -> tuple[Analysis, str]:
    if MISTRAL_API_KEY:
        return mistral_analysis(user, portfolio), "mistral"
    return demo_analysis(user, portfolio), "demo"
