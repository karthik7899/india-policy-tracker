// Value formatting, in one place.
//
// The pipeline stores numbers as display strings ("482.95", "+23.0%",
// "1,840.00") because that is the legacy wire format models/stock.py renders
// back to. So every view has to coerce before it compares, and doing that
// ad-hoc is what to_float was created to end on the Python side. This is the
// same idea for the browser: one tolerant coercion, one set of formatters.

/** Tolerant numeric coercion. Mirrors utils.to_float — same accepted forms. */
export function num(value) {
  if (value === null || value === undefined || typeof value === "boolean") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  const cleaned = String(value).trim().replace(/[%+,]/g, "");
  if (!cleaned) return null;
  if (["N/A", "NA", "-", "—", "NONE"].includes(cleaned.toUpperCase())) return null;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

/** Rupees in crore, with the magnitude the reader actually needs. */
export function crore(value) {
  const n = num(value);
  if (n === null) return "—";
  if (Math.abs(n) >= 1000) return `₹${(n / 1000).toFixed(1)}k Cr`;
  if (Math.abs(n) >= 1) return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: 0 })} Cr`;
  return `₹${n.toFixed(2)} Cr`;
}

/** A signed percentage, always with its sign — the sign is the information. */
export function pct(value, decimals = 1) {
  const n = num(value);
  if (n === null) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(decimals)}%`;
}

export function plain(value, decimals = 2) {
  const n = num(value);
  return n === null ? "—" : n.toFixed(decimals);
}

/** A date the way the rest of the product writes them. */
export function shortDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

/**
 * Thesis status -> a status role.
 *
 * Named rather than inlined so the mapping is stated once. "Weakening" is
 * `serious`, not `warning`: a thesis whose evidence has turned is a stronger
 * signal than a data-quality nag, and the two must not share a colour.
 */
export function thesisStatus(status) {
  return { Broken: "critical", Weakening: "serious", Intact: "good" }[status] ?? "warning";
}

/**
 * Liquidity/delivery band -> its position on the ordinal scale.
 *
 * trade-to-trade is deliberately OUTSIDE the scale. Delivery is compulsory in
 * that segment, so its ~100% is a surveillance rule rather than evidence of
 * accumulation, and placing it on the same axis as a real delivery figure
 * would manufacture a bullish signal out of a trading restriction.
 */
export const BANDS = ["illiquid", "thin", "adequate", "liquid"];

export function bandIndex(band) {
  return BANDS.indexOf(String(band || "").toLowerCase());
}
