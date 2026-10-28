// Value formatting, in one place.
//
// The pipeline stores numbers as display strings ("482.95", "+23.0%",
// "1,840.00") because that is the legacy wire format models/stock.py renders
// back to. So every view has to coerce before it compares, and doing that
// ad-hoc is what to_float was created to end on the Python side. This is the
// same idea for the browser: one tolerant coercion, one set of formatters.

import { calendarDay, dayShaped } from "./calendar.js";

/** Tolerant numeric coercion. Mirrors utils.to_float — same accepted forms. */
/**
 * Marks a reading made by the LLM (Gemini) rather than taken from a source
 * or computed. One glyph, explained once in the page footer, instead of the
 * words "LLM reading" repeated on every line it applies to.
 */
export const LLM_MARK = "\u2726";

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

/**
 * An event's size against the company it happened to: "3.8% of revenue ·
 * minor". Unsigned — a share of revenue has no direction — and the band is
 * spelled out because 3.8% means nothing until you know where the lines are.
 */
export function sizeLabel(pctOfRevenue, band) {
  const n = num(pctOfRevenue);
  if (n === null) return "";
  const figure = n >= 10 ? n.toFixed(0) : n.toFixed(1);
  return `${figure}% of revenue${band ? ` \u00b7 ${band}` : ""}`;
}

/**
 * How a read-through reaches the holding: "demand pull", "competitive
 * threat" or "input shock" (analysis/read_through.TRANSMISSIONS). Empty for a
 * row written before rows carried it.
 */
export function transmissionLabel(transmission) {
  return String(transmission || "").replace(/_/g, " ");
}

/**
 * What a read-through's trigger falls short of \u2014 "not yet binding: an MoU, a
 * lowest bid or an intention", "reported, not confirmed" \u2014 or "" when it is
 * binding. The words travel with the row (strength_note) so the email and the
 * dashboard say the same thing; the fallback covers a row with the grade and
 * not the words.
 */
/**
 * " (+1 more headline)" when other headlines told the same story: one
 * read-through row stands for them (analysis/read_through._dedupe).
 */
export function moreHeadlines(row) {
  const more = Number(row?.headline_count || 1) - 1;
  if (!Number.isFinite(more) || more < 1) return "";
  return ` (+${more} more headline${more > 1 ? "s" : ""})`;
}

export function strengthLabel(row) {
  const strength = row?.strength;
  if (!strength || strength === "hard") return "";
  if (row.strength_note) return String(row.strength_note);
  return strength === "soft" ? "not yet binding" : "reported, not confirmed";
}

/**
 * A brokerage's call, the reasons its story gives for it, each quoted, and the
 * words of the thesis they bear on (analysis/brokerage_reasons.py): "JM
 * Financial: upgrades stock \u2014 \u201cstrong order inflows\u201d \u2192 thesis:
 * \u201crecord order book\u201d \u00b7 from the article". Shown beside the support
 * or challenge it explains; "" for no call.
 */
export function callLine(call) {
  if (!call?.call) return "";
  const reasons = (call.reasons || []).map((r) => `\u201c${r}\u201d`).join("; ");
  return [
    `${call.brokerage || "A brokerage"}: ${call.call}`,
    reasons ? ` \u2014 ${reasons}` : " \u2014 the story gives no reason",
    call.claim ? ` \u2192 thesis: \u201c${call.claim}\u201d` : "",
    ` \u00b7 from the ${call.source === "article" ? "article" : "summary"} \u00b7 ${LLM_MARK}`,
  ].join("");
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

const SHORT = { day: "2-digit", month: "short", year: "numeric" };

/**
 * A date the way the rest of the product writes them.
 *
 * A date with no time ("2026-10-15", as results dates, filings and kept-value
 * stamps are) is written from its own fields, the same in every timezone.
 * Parsed as an instant it was midnight UTC, which a reader west of Greenwich
 * saw as 14 Oct beside a badge saying "Earnings: today". A timestamp is
 * still shown in the reader's own time.
 */
export function shortDate(value) {
  if (!value) return "";
  const day = calendarDay(value);
  if (day) {
    const [y, m, d] = day;
    return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-IN", { ...SHORT, timeZone: "UTC" });
  }
  if (dayShaped(value)) return String(value); // "2026-02-30" is no day at all
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString("en-IN", SHORT);
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
