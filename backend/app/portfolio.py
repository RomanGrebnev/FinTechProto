from .config import BASE_CURRENCY
from .models import User
from .prices import annual_volatility, fx_rate, get_quotes
from .schemas import HoldingOut, PortfolioOut

# Annualised volatility thresholds for risk scores 1..5, loosely following the PRIIPs SRI bands
_VOL_BANDS = [0.0, 0.03, 0.07, 0.12, 0.20, 0.30]
FUND_TYPES = {"ETF", "MUTUALFUND"}
RISK_LABELS = {1: "Very conservative", 2: "Conservative", 3: "Balanced", 4: "Dynamic", 5: "Aggressive"}


def volatility_to_score(vol: float) -> float:
    for i in range(1, len(_VOL_BANDS)):
        lo, hi = _VOL_BANDS[i - 1], _VOL_BANDS[i]
        if vol < hi:
            return round(max(1.0, i - 1 + (vol - lo) / (hi - lo)), 1)
    return 5.0


def build_portfolio(user: User) -> PortfolioOut:
    quotes = get_quotes([h.ticker for h in user.holdings])
    rows = []
    for h in user.holdings:
        q = quotes.get(h.ticker.upper())
        rate = fx_rate(q.currency) if q else None
        if q and rate:
            price = q.price * rate
            # avg_buy_price is entered in the instrument's own currency
            cost = h.avg_buy_price * h.quantity * rate
        else:
            price, cost = None, h.avg_buy_price * h.quantity
        value = (price if price is not None else h.avg_buy_price) * h.quantity
        rows.append((h, q, price, value, cost))

    total_value = sum(r[3] for r in rows)
    total_cost = sum(r[4] for r in rows)
    holdings = []
    weights: dict[str, float] = {}
    for h, q, price, value, cost in rows:
        weight = value / total_value if total_value else 0.0
        weights[h.ticker.upper()] = weights.get(h.ticker.upper(), 0) + weight
        holdings.append(HoldingOut(
            id=h.id, ticker=h.ticker.upper(), name=q.name if q else None, instrument_type=q.instrument_type if q else None,
            quantity=h.quantity, avg_buy_price=h.avg_buy_price,
            current_price=round(price, 4) if price is not None else None,
            currency=q.currency if q else BASE_CURRENCY,
            value=round(value, 2), cost_basis=round(cost, 2),
            pnl=round(value - cost, 2), pnl_pct=round((value / cost - 1) * 100, 2) if cost else 0.0,
            weight=round(weight * 100, 2), price_available=price is not None,
        ))

    vol = annual_volatility(weights, quotes) if weights else None
    score = volatility_to_score(vol) if vol is not None else (3.0 if holdings else 0.0)
    # Concentration bumps risk: a single stock above 40% of the portfolio
    stock_weights = [h.weight for h in holdings if h.instrument_type not in FUND_TYPES]
    if stock_weights and max(stock_weights) > 40:
        score = min(5.0, score + 0.5)

    return PortfolioOut(
        holdings=holdings,
        total_value=round(total_value, 2), total_cost=round(total_cost, 2),
        total_pnl=round(total_value - total_cost, 2),
        total_pnl_pct=round((total_value / total_cost - 1) * 100, 2) if total_cost else 0.0,
        currency=BASE_CURRENCY,
        risk_score=round(score, 1),
        risk_label=RISK_LABELS[max(1, min(5, int(score + 0.5)))] if holdings else "No holdings",
        volatility=round(vol * 100, 1) if vol is not None else None,
        target_risk=user.profile.risk_tolerance if user.profile else None,
    )
