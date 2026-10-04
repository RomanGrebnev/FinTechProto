export default function Spinner({ full, label }) {
  const el = (
    <div className="flex items-center gap-3 text-sm text-slate-500">
      <span className="size-5 animate-spin rounded-full border-2 border-slate-300 border-t-ink" />
      {label}
    </div>
  );
  return full ? <div className="grid min-h-dvh place-items-center">{el}</div> : el;
}
