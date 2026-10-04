const LABELS = ["Very conservative", "Conservative", "Balanced", "Dynamic", "Aggressive"];
const COLORS = ["#10b981", "#84cc16", "#eab308", "#f97316", "#ef4444"];

// Semicircle gauge from 1 to 5, with an optional target marker (the user's stated tolerance)
export default function RiskGauge({ score, target }) {
  const angle = (v) => Math.PI * (1 - (Math.min(Math.max(v, 1), 5) - 1) / 4);
  const pt = (v, r) => [60 + r * Math.cos(angle(v)), 60 - r * Math.sin(angle(v))];
  const arc = (from, to) => {
    const [x1, y1] = pt(from, 48), [x2, y2] = pt(to, 48);
    return `M${x1} ${y1} A48 48 0 0 1 ${x2} ${y2}`;
  };
  const [nx, ny] = pt(score || 1, 38);
  const [tx1, ty1] = pt(target || 1, 40), [tx2, ty2] = pt(target || 1, 57);

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 120 68" className="w-full max-w-[220px]">
        {COLORS.map((c, i) => (
          <path key={c} d={arc(1 + i * 0.8 + 0.04, 1 + (i + 1) * 0.8 - 0.04)} stroke={c} strokeWidth="10" fill="none" />
        ))}
        {target && <line x1={tx1} y1={ty1} x2={tx2} y2={ty2} stroke="#0b1530" strokeWidth="2" strokeDasharray="2 1.5" />}
        {score > 0 && (
          <>
            <line x1="60" y1="60" x2={nx} y2={ny} stroke="#0b1530" strokeWidth="3" strokeLinecap="round" />
            <circle cx="60" cy="60" r="4.5" fill="#0b1530" />
          </>
        )}
      </svg>
      <div className="-mt-1 text-center">
        <div className="text-3xl font-bold tabular-nums">{score ? score.toFixed(1) : "—"}<span className="text-base font-medium text-slate-400"> / 5</span></div>
        <div className="text-sm font-medium text-slate-600">{score ? LABELS[Math.round(score) - 1] : "No holdings yet"}</div>
        {target && (
          <div className="mt-1 text-xs text-slate-500">
            Your tolerance: <strong>{target}/5</strong> ({LABELS[target - 1].toLowerCase()})
          </div>
        )}
      </div>
    </div>
  );
}
