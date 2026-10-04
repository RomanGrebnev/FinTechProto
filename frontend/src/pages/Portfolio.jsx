import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Spinner from "../components/Spinner";
import { api } from "../lib/api";
import { eur, money, pct, tone } from "../lib/format";

const EMPTY = { ticker: "", quantity: "", avg_buy_price: "" };

function HoldingForm({ initial, onSaved, onCancel }) {
  const [form, setForm] = useState(initial || EMPTY);
  const [lookup, setLookup] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const check = async () => {
    const t = form.ticker.trim();
    if (!t) return setLookup(null);
    setLookup({ loading: true });
    try {
      setLookup(await api(`/portfolio/lookup/${encodeURIComponent(t)}`));
    } catch (err) {
      setLookup({ error: err.message });
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = { ticker: form.ticker.trim(), quantity: +form.quantity, avg_buy_price: +form.avg_buy_price };
      const data = initial
        ? await api(`/portfolio/holdings/${initial.id}`, { method: "PUT", body })
        : await api("/portfolio/holdings", { method: "POST", body });
      onSaved(data);
      setForm(EMPTY);
      setLookup(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="card space-y-4">
      <h2 className="font-semibold">{initial ? `Edit ${initial.ticker}` : "Add a holding"}</h2>
      <div>
        <label className="label" htmlFor="ticker">Ticker</label>
        <input id="ticker" required className="input uppercase placeholder:normal-case" placeholder="e.g. MC.PA, CW8.PA, AAPL" value={form.ticker}
          onChange={set("ticker")} onBlur={check} autoCapitalize="characters" autoCorrect="off" />
        <p className="mt-1 min-h-4 text-xs">
          {lookup?.loading && <span className="text-slate-500">Looking up…</span>}
          {lookup?.error && <span className="text-amber-700">{lookup.error}. You can still add it; its value will use your buy price.</span>}
          {lookup?.price != null && (
            <span className="text-emerald-700">✓ {lookup.name || lookup.ticker} · {money(lookup.price, lookup.currency)}</span>
          )}
          {!lookup && <span className="text-slate-400">Yahoo Finance symbols — Paris listings end in .PA</span>}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label" htmlFor="qty">Quantity</label>
          <input id="qty" required type="number" step="any" min="0" inputMode="decimal" className="input" value={form.quantity} onChange={set("quantity")} />
        </div>
        <div>
          <label className="label" htmlFor="price">Avg. buy price{lookup?.currency ? ` (${lookup.currency})` : ""}</label>
          <input id="price" required type="number" step="any" min="0" inputMode="decimal" className="input" value={form.avg_buy_price} onChange={set("avg_buy_price")} />
        </div>
      </div>
      {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
      <div className="flex gap-3">
        {onCancel && <button type="button" onClick={onCancel} className="btn-ghost flex-1">Cancel</button>}
        <button disabled={busy} className="btn-primary flex-[2]">{busy ? "Saving…" : initial ? "Save changes" : "Add holding"}</button>
      </div>
    </form>
  );
}

export default function Portfolio() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(null);

  useEffect(() => {
    api("/portfolio").then(setData).catch((e) => setError(e.message));
  }, []);

  const remove = async (h) => {
    if (!confirm(`Remove ${h.ticker} from your portfolio?`)) return;
    setData(await api(`/portfolio/holdings/${h.id}`, { method: "DELETE" }));
  };

  if (error) return <p className="text-rose-700">{error}</p>;
  if (!data) return <Spinner label="Fetching live prices…" />;

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Portfolio</h1>
          <p className="text-sm text-slate-500">Enter your holdings manually. Prices update from Yahoo Finance.</p>
        </div>
        {data.holdings.length > 0 && (
          <div className="text-right">
            <div className="text-xl font-bold tabular-nums">{eur(data.total_value)}</div>
            <div className={`text-sm font-medium tabular-nums ${tone(data.total_pnl)}`}>{eur(data.total_pnl)} ({pct(data.total_pnl_pct)})</div>
          </div>
        )}
      </div>

      <div className="grid gap-5 md:grid-cols-[1fr_340px] md:items-start">
        <div className="space-y-3">
          {data.holdings.length === 0 && (
            <div className="card text-center text-slate-500">No holdings yet. Add your first position to get an analysis.</div>
          )}
          {data.holdings.map((h) => (
            <div key={h.id} className="card p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{h.ticker}</span>
                    {h.instrument_type === "ETF" && <span className="rounded bg-slate-100 px-1.5 text-[10px] font-semibold text-slate-600">ETF</span>}
                    {!h.price_available && <span className="rounded bg-amber-100 px-1.5 text-[10px] font-semibold text-amber-800">NO PRICE</span>}
                  </div>
                  <div className="truncate text-sm text-slate-500">{h.name || "Unknown instrument"}</div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="font-semibold tabular-nums">{eur(h.value)}</div>
                  <div className={`text-sm tabular-nums ${tone(h.pnl)}`}>{pct(h.pnl_pct)}</div>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-3 text-xs text-slate-500">
                <span className="tabular-nums">
                  {h.quantity} × {money(h.avg_buy_price, h.currency)} → {h.price_available ? money(h.current_price, "EUR") : "—"} · {pct(h.weight, 1, false)}
                </span>
                <span className="flex gap-3">
                  <button onClick={() => setEditing(h)} className="font-medium text-ink hover:underline">Edit</button>
                  <button onClick={() => remove(h)} className="font-medium text-rose-600 hover:underline">Remove</button>
                </span>
              </div>
            </div>
          ))}
          {data.holdings.length > 0 && (
            <p className="text-xs text-slate-400">Values in EUR. Buy prices are in each instrument's trading currency and converted at today's rate.</p>
          )}
        </div>

        <div className="space-y-3 md:sticky md:top-20">
          {editing ? (
            <HoldingForm key={editing.id} initial={editing} onCancel={() => setEditing(null)} onSaved={(d) => { setData(d); setEditing(null); }} />
          ) : (
            <HoldingForm onSaved={setData} />
          )}
          {data.holdings.length > 0 && (
            <Link to="/dashboard" className="btn-ghost w-full ring-1 ring-slate-200">View dashboard →</Link>
          )}
        </div>
      </div>
    </div>
  );
}
