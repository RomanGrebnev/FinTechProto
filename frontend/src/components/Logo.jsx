export default function Logo({ light }) {
  return (
    <span className={`flex items-center gap-2 text-lg font-bold tracking-tight ${light ? "text-white" : "text-ink"}`}>
      <svg viewBox="0 0 32 32" className="size-7">
        <rect width="32" height="32" rx="8" fill={light ? "#1b2a52" : "#0b1530"} />
        <path d="M8 21l5-6 4 3 7-9" stroke="#34d399" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      Wealthpilot
    </span>
  );
}
