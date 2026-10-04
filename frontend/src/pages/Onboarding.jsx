import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Logo from "../components/Logo";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { eur } from "../lib/format";

const GOALS = [
  { value: "retirement", label: "Retirement", hint: "Build a pension top-up" },
  { value: "home", label: "Buy a home", hint: "Save for a deposit" },
  { value: "education", label: "Education", hint: "Children's studies" },
  { value: "wealth_growth", label: "Grow my wealth", hint: "Long-term capital growth" },
  { value: "emergency_fund", label: "Safety net", hint: "Precautionary savings" },
  { value: "other", label: "Something else", hint: "A personal project" },
];

const RISK = [
  { value: 1, label: "Very cautious", hint: "I can't accept losing money, even temporarily." },
  { value: 2, label: "Cautious", hint: "Small dips are OK if returns are steady." },
  { value: 3, label: "Balanced", hint: "I accept ups and downs for better long-term growth." },
  { value: 4, label: "Dynamic", hint: "I can live with a 20–30% drop in a bad year." },
  { value: 5, label: "Adventurous", hint: "I'm chasing growth and can stomach large swings." },
];

const STEPS = [
  { key: "age", title: "How old are you?", hint: "Your age helps us gauge how much time your money has to grow." },
  { key: "annual_income", title: "What is your annual net income?", hint: "An estimate is fine. It's used to size suggestions, never shared." },
  { key: "savings_goal", title: "What are you investing for?", hint: "Pick the goal that matters most right now." },
  { key: "monthly_investment", title: "How much can you invest each month?", hint: "Regular contributions are the most reliable way to build wealth." },
  { key: "risk_tolerance", title: "How do you feel about risk?", hint: "Imagine your portfolio falls sharply in a market crash." },
  { key: "horizon_years", title: "When will you need this money?", hint: "Your investment horizon — the longer, the more volatility you can absorb." },
];

export default function Onboarding() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState(
    user.profile || { age: "", annual_income: "", savings_goal: "", monthly_investment: "", risk_tolerance: 0, horizon_years: 10 }
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const s = STEPS[step];
  const value = form[s.key];
  const set = (v) => setForm((f) => ({ ...f, [s.key]: v }));

  const valid = {
    age: value >= 18 && value <= 100,
    annual_income: value !== "" && value >= 0,
    savings_goal: !!value,
    monthly_investment: value !== "" && value >= 0,
    risk_tolerance: value >= 1,
    horizon_years: value >= 1,
  }[s.key];

  const next = async (e) => {
    e?.preventDefault();
    if (!valid) return;
    if (step < STEPS.length - 1) return setStep(step + 1);
    setBusy(true);
    setError("");
    try {
      await api("/profile", {
        method: "PUT",
        body: { ...form, age: +form.age, annual_income: +form.annual_income, monthly_investment: +form.monthly_investment },
      });
      await refresh();
      navigate("/portfolio", { replace: true });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const numberInput = (suffix, props) => (
    <div className="relative">
      <input autoFocus type="number" inputMode="numeric" className="input pr-14 text-2xl font-semibold" value={value}
        onChange={(e) => set(e.target.value === "" ? "" : Number(e.target.value))} {...props} />
      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">{suffix}</span>
    </div>
  );

  return (
    <div className="mx-auto flex min-h-dvh max-w-lg flex-col px-5 py-6">
      <div className="flex items-center justify-between">
        <Logo />
        <span className="text-sm text-slate-500">{step + 1} / {STEPS.length}</span>
      </div>
      <div className="mt-4 h-1.5 rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
      </div>

      <form onSubmit={next} className="mt-10 flex flex-1 flex-col">
        <h1 className="text-2xl font-bold leading-tight">{s.title}</h1>
        <p className="mt-2 text-slate-500">{s.hint}</p>

        <div className="mt-8">
          {s.key === "age" && numberInput("years", { min: 18, max: 100, placeholder: "35" })}
          {s.key === "annual_income" && numberInput("€ / yr", { min: 0, step: 1000, placeholder: "45000" })}
          {s.key === "monthly_investment" && numberInput("€ / mo", { min: 0, step: 50, placeholder: "300" })}

          {s.key === "savings_goal" && (
            <div className="grid grid-cols-2 gap-3">
              {GOALS.map((g) => (
                <button type="button" key={g.value} onClick={() => set(g.value)}
                  className={`rounded-2xl p-4 text-left ring-1 transition ${value === g.value ? "bg-ink text-white ring-ink" : "bg-white ring-slate-200 hover:ring-slate-400"}`}>
                  <div className="font-semibold">{g.label}</div>
                  <div className={`mt-0.5 text-xs ${value === g.value ? "text-slate-300" : "text-slate-500"}`}>{g.hint}</div>
                </button>
              ))}
            </div>
          )}

          {s.key === "risk_tolerance" && (
            <div className="space-y-2.5">
              {RISK.map((r) => (
                <button type="button" key={r.value} onClick={() => set(r.value)}
                  className={`flex w-full items-center gap-4 rounded-2xl p-4 text-left ring-1 transition ${value === r.value ? "bg-ink text-white ring-ink" : "bg-white ring-slate-200 hover:ring-slate-400"}`}>
                  <span className={`grid size-9 shrink-0 place-items-center rounded-full text-sm font-bold ${value === r.value ? "bg-brand text-ink" : "bg-slate-100"}`}>{r.value}</span>
                  <span>
                    <span className="block font-semibold">{r.label}</span>
                    <span className={`block text-sm ${value === r.value ? "text-slate-300" : "text-slate-500"}`}>{r.hint}</span>
                  </span>
                </button>
              ))}
            </div>
          )}

          {s.key === "horizon_years" && (
            <div>
              <div className="text-center text-5xl font-bold tabular-nums">{value}<span className="text-xl font-medium text-slate-400"> {value === 1 ? "year" : "years"}</span></div>
              <input type="range" min="1" max="40" value={value} onChange={(e) => set(Number(e.target.value))} className="mt-8 w-full accent-ink" />
              <div className="mt-1 flex justify-between text-xs text-slate-400"><span>1 yr</span><span>40 yrs</span></div>
            </div>
          )}

          {s.key === "monthly_investment" && value > 0 && (
            <p className="mt-3 text-sm text-slate-500">That's {eur(value * 12)} a year.</p>
          )}
        </div>

        {error && <p className="mt-6 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}

        <div className="mt-auto flex gap-3 pt-10">
          {step > 0 && <button type="button" onClick={() => setStep(step - 1)} className="btn-ghost flex-1">Back</button>}
          <button disabled={!valid || busy} className="btn-primary flex-[2]">
            {step === STEPS.length - 1 ? (busy ? "Saving…" : "Finish") : "Continue"}
          </button>
        </div>
      </form>
    </div>
  );
}
