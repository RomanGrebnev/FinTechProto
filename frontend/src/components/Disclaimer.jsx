const ORIAS = import.meta.env.VITE_CIF_ORIAS_NUMBER || "00000000";

export const DISCLAIMER =
  `Wealthpilot SAS is a conseiller en investissements financiers (CIF) registered with ORIAS under no. ${ORIAS}. This is non-independent investment advice, based on the information you provided in your profile and portfolio. See our Terms of Service (Terms, section 2) for details.`;

export default function Disclaimer({ text = DISCLAIMER, className = "" }) {
  return (
    <p role="note" className={`flex gap-2 rounded-xl bg-amber-50 px-4 py-3 text-xs leading-relaxed text-amber-900 ring-1 ring-amber-200 ${className}`}>
      <svg viewBox="0 0 20 20" className="mt-0.5 size-4 shrink-0 fill-amber-500" aria-hidden>
        <path d="M10 1.5a8.5 8.5 0 100 17 8.5 8.5 0 000-17zM9 6h2v6H9V6zm0 7.5h2v2H9v-2z" />
      </svg>
      <span><strong className="font-semibold">Regulatory status.</strong> {text}</span>
    </p>
  );
}
