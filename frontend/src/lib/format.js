export const eur = (n, digits = 0) =>
  n == null ? "—" : new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n);

export const money = (n, currency = "EUR", digits = 2) =>
  n == null ? "—" : new Intl.NumberFormat("fr-FR", { style: "currency", currency, maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n);

export const pct = (n, digits = 1, sign = true) =>
  n == null ? "—" : `${sign && n > 0 ? "+" : ""}${n.toFixed(digits).replace(".", ",")} %`;

export const tone = (n) => (n == null ? "text-slate-500" : n >= 0 ? "text-emerald-600" : "text-rose-600");
