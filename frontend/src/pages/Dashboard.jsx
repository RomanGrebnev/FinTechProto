import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ActionBadge from "../components/ActionBadge";
import Disclaimer from "../components/Disclaimer";
import RiskGauge from "../components/RiskGauge";
import Spinner from "../components/Spinner";
import { api } from "../lib/api";
import { eur, pct, tone } from "../lib/format";
import useAnalysis from "../lib/useAnalysis";

const PALETTE = ["#0b1530", "#10b981", "#6366f1", "#f59e0b", "#ec4899", "#06b6d4", "#84cc16", "#f43f5e", "#a855f7", "#64748b"];

function Allocation({ holdings }) {
  const sorted = [...holdings].sort((a, b) => b.weight - a.weight);
  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full">
        {sorted.map((h, i) => (
          <div key={h.id} style={{ width: `${h.weight}%`, background: PALETTE[i % PALETTE.length] }} title={`${h.ticker} ${h.weight}%`} />
        ))}
      </div>
      <ul className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        {sorted.map((h, i) => (
          <li key={h.id} className="flex items-center gap-2">
            <span className="size-2.5 shrink-0 rounded-full" style={{ background: PALETTE[i % PALETTE.length] }} />
            <span className="truncate font-medium">{h.ticker}</span>
            <span className="ml-auto tabular-nums text-slate-500">{h.weight.toFixed(0)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function MarketStrip({ market }) {
  if (!market) return <Spinner label="Loading markets…" />;
  return (
    <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-1 md:mx-0 md:grid md:grid-cols-4 md:px-0">
      {market.map((m) => (
        <div key={m.symbol} className="card min-w-[140px] p-4">
          <div className="text-xs font-medium text-slate-500">{m.name}</div>
          <div className="mt-1 font-semibold tabular-nums">
            {m.price == null ? "—" : m.price.toLocaleString("fr-FR", { maximumFractionDigits: m.symbol.endsWith("=X") ? 4 : 0 })}
          </div>
          <div className={`text-sm font-medium tabular-nums ${tone(m.change_pct)}`}>{pct(m.change_pct, 2)}</div>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState(null);
  const [market, setMarket] = useState(null);
  const [error, setError] = useState("");
  const { analysis, generating, error: aiError, generate } = useAnalysis();

  useEffect(() => {
    api("/portfolio").then(setPortfolio).catch((e) => setError(e.message));
    api("/market").then(setMarket).catch(() => setMarket([]));
  }, []);

  if (error) return <p className="text-rose-700">{error}</p>;
  if (!portfolio) return <Spinner label="Fetching live prices…" />;
  const empty = portfolio.holdings.length === 0;

  return (
    <div className="space-y-5">
      <section className="rounded-3xl bg-ink p-6 text-white">
        <div className="text-sm text-slate-400">Portfolio value</div>
        <div className="mt-1 text-4xl font-bold tracking-tight tabular-nums">{eur(portfolio.total_value)}</div>
        {!empty && (
          <div className={`mt-1 text-sm font-medium tabular-nums ${portfolio.total_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
            {portfolio.total_pnl >= 0 ? "▲" : "▼"} {eur(Math.abs(portfolio.total_pnl))} ({pct(portfolio.total_pnl_pct)}) unrealised
          </div>
        )}
        <div className="mt-4 flex gap-6 text-sm text-slate-400">
          <span><strong className="text-white">{portfolio.holdings.length}</strong> holdings</span>
          <span>Invested <strong className="text-white tabular-nums">{eur(portfolio.total_cost)}</strong></span>
        </div>
      </section>

      {empty ? (
        <div className="card text-center">
          <p className="text-slate-600">Add your holdings to get a risk score and AI recommendations.</p>
          <Link to="/portfolio" className="btn-primary mt-4">Add holdings</Link>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          <section className="card">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Risk score</h2>
              <Link to="/onboarding" className="text-xs font-medium text-slate-500 hover:text-ink">Edit profile</Link>
            </div>
            <div className="mt-4"><RiskGauge score={portfolio.risk_score} target={portfolio.target_risk} /></div>
            <p className="mt-4 text-center text-xs text-slate-500">
              {portfolio.volatility != null ? `Based on 1-year annualised volatility of ${portfolio.volatility.toString().replace(".", ",")} %.` : "Not enough price history to measure volatility."}
            </p>
          </section>
          <section className="card">
            <h2 className="font-semibold">Allocation</h2>
            <div className="mt-4"><Allocation holdings={portfolio.holdings} /></div>
          </section>
        </div>
      )}

      {!empty && (
        <section className="card">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">AI recommendations</h2>
              {analysis && <p className="text-xs text-slate-500">Generated {new Date(analysis.created_at + (analysis.created_at.endsWith("Z") || analysis.created_at.includes("+") ? "" : "Z")).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}{analysis.source === "demo" && " · demo mode"}</p>}
            </div>
            <button onClick={generate} disabled={generating} className="btn-primary px-3 py-2 text-xs">
              {generating ? "Analysing…" : analysis ? "Refresh" : "Analyse my portfolio"}
            </button>
          </div>
          {analysis?.outdated && (
            <p role="alert" className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800 ring-1 ring-amber-200">Your profile changed. Refresh this analysis before acting on it.</p>
          )}
          {aiError && <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{aiError}</p>}
          {analysis === undefined || generating ? (
            <div className="py-6"><Spinner label={generating ? "Mistral is analysing your portfolio…" : "Loading…"} /></div>
          ) : analysis ? (
            <>
              <ul className="mt-4 divide-y divide-slate-100">
                {analysis.analysis.recommendations.map((r, i) => (
                  <li key={i} className="flex items-start gap-3 py-3">
                    {!analysis.outdated && <ActionBadge action={r.action} />}
                    <div className="min-w-0">
                      <div className="text-sm font-semibold">{r.title}</div>
                      <div className="text-xs text-slate-500">{r.ticker}</div>
                    </div>
                  </li>
                ))}
              </ul>
              <Link to="/recommendations" className="mt-2 block text-sm font-semibold text-ink hover:underline">See full analysis →</Link>
            </>
          ) : (
            <p className="mt-4 text-sm text-slate-500">No analysis yet. Generate one to get 3 personalised recommendations.</p>
          )}
          <Disclaimer className="mt-4" text={analysis?.disclaimer} />
        </section>
      )}

      <section>
        <h2 className="mb-3 font-semibold">Market context</h2>
        <MarketStrip market={market} />
      </section>
    </div>
  );
}
