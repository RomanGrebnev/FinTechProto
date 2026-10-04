const STYLES = {
  buy: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  sell: "bg-rose-50 text-rose-700 ring-rose-200",
  hold: "bg-sky-50 text-sky-700 ring-sky-200",
  rebalance: "bg-violet-50 text-violet-700 ring-violet-200",
};

export default function ActionBadge({ action }) {
  return (
    <span className={`w-[76px] shrink-0 rounded-md px-2 py-0.5 text-center text-[11px] font-semibold uppercase tracking-wide ring-1 ${STYLES[action] || STYLES.hold}`}>
      {action}
    </span>
  );
}

export const SEVERITY = {
  low: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  medium: "bg-amber-50 text-amber-900 ring-amber-200",
  high: "bg-rose-50 text-rose-800 ring-rose-200",
};
