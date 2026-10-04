import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Logo from "../components/Logo";
import { useAuth } from "../lib/auth";

export default function AuthPage({ mode }) {
  const isSignup = mode === "signup";
  const { authenticate } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const me = await authenticate(mode, email, password);
      navigate(me.profile ? "/dashboard" : "/onboarding", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-dvh flex-col bg-ink md:items-center md:justify-center">
      <div className="px-6 pb-10 pt-12 md:w-full md:max-w-md md:px-0 md:pt-0">
        <Logo light />
        <h1 className="mt-8 text-3xl font-bold leading-tight text-white">
          {isSignup ? "Invest with a clear plan." : "Welcome back."}
        </h1>
        <p className="mt-2 text-slate-400">
          {isSignup ? "Personalised, AI-assisted insight on your portfolio — in minutes." : "Log in to see your portfolio insights."}
        </p>
      </div>
      <form onSubmit={submit} className="flex-1 space-y-4 rounded-t-3xl bg-white px-6 py-8 md:w-full md:max-w-md md:flex-none md:rounded-3xl md:p-8">
        <div>
          <label className="label" htmlFor="email">Email</label>
          <input id="email" type="email" required autoComplete="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="password">Password</label>
          <input id="password" type="password" required minLength={8} autoComplete={isSignup ? "new-password" : "current-password"}
            className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
          {isSignup && <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p>}
        </div>
        {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
        <button disabled={busy} className="btn-primary w-full">{busy ? "Please wait…" : isSignup ? "Create account" : "Log in"}</button>
        <p className="text-center text-sm text-slate-600">
          {isSignup ? "Already have an account? " : "New to Wealthpilot? "}
          <Link to={isSignup ? "/login" : "/signup"} className="font-semibold text-ink underline">
            {isSignup ? "Log in" : "Create an account"}
          </Link>
        </p>
        {!isSignup && (
          <button type="button" onClick={() => { setEmail("demo@wealthpilot.fr"); setPassword("demo1234"); }}
            className="w-full text-center text-xs text-slate-500 hover:text-ink">
            Use demo account <span className="text-slate-400">(demo@wealthpilot.fr / demo1234)</span>
          </button>
        )}
      </form>
    </div>
  );
}
