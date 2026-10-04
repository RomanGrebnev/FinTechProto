import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import Logo from "./Logo";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "M3 12l9-8 9 8M5 10v10h5v-6h4v6h5V10" },
  { to: "/portfolio", label: "Portfolio", icon: "M4 20V10m6 10V4m6 16v-7m4 7H2" },
  { to: "/recommendations", label: "Advice", icon: "M12 3l2.5 5.5L20 9l-4 4 1 6-5-3-5 3 1-6-4-4 5.5-.5L12 3z" },
];

const Icon = ({ d }) => (
  <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="min-h-dvh pb-24 md:pb-10">
      <header className="sticky top-0 z-20 bg-ink/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Logo light />
          <nav className="hidden gap-1 md:flex">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to}
                className={({ isActive }) => `rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-white/10 text-white" : "text-slate-300 hover:text-white"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-slate-400 sm:inline">{user?.email}</span>
            <button onClick={logout} className="rounded-lg px-2 py-1 text-slate-300 hover:text-white">Log out</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-5 md:py-8">
        <Outlet />
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden">
        <div className="grid grid-cols-3">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to}
              className={({ isActive }) => `flex flex-col items-center gap-1 py-2.5 text-xs font-medium ${isActive ? "text-ink" : "text-slate-400"}`}>
              <Icon d={n.icon} />
              {n.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
