// Filter state, and the predicates that apply it.
//
// Filters live in the URL query string rather than in a module variable, for
// the same reason `focus` does: a filtered view survives a reload, it can be
// pasted to someone else, and two views reading the same param cannot disagree
// about what is selected. It also means the back button steps through filter
// changes, which a dashboard holding this in memory never gets.
//
// Everything here is pure and takes its context explicitly — no payload
// import, no DOM — so the rules below are testable on their own. The views
// hold the DOM; this file holds the meaning.

import { num } from "./format.js";

/** Params this module owns. Views merge their own (lens, stream) around them. */
export const FILTER_KEYS = ["q", "sector", "thesis", "band", "days"];

export const THESIS_OPTIONS = ["Broken", "Weakening", "Intact"];

/** Liquidity bands, weakest first. Mirrors format.BANDS. */
export const BAND_OPTIONS = ["illiquid", "thin", "adequate", "liquid"];

export const DAY_OPTIONS = [
  [7, "Last 7 days"],
  [30, "Last 30 days"],
  [90, "Last 90 days"],
];

/** Read the filters out of a route. Absent params are the empty filter. */
export function read(route) {
  const p = (route && route.params) || {};
  return {
    q: String(p.q || "").trim(),
    sector: String(p.sector || ""),
    thesis: String(p.thesis || ""),
    band: String(p.band || ""),
    days: p.days ? num(p.days) : null,
  };
}

/** How many filters are doing something. Drives the "clear" affordance. */
export function activeCount(filters) {
  const f = filters || {};
  return [f.q, f.sector, f.thesis, f.band, f.days].filter(Boolean).length;
}

/** Route params with every filter removed, preserving focus, lens and stream. */
export function cleared(params) {
  const out = { ...(params || {}) };
  for (const key of FILTER_KEYS) delete out[key];
  return out;
}

function haystack(...parts) {
  return parts
    .filter((v) => v !== null && v !== undefined)
    .join(" ")
    .toLowerCase();
}

/**
 * Does one holding survive the filters?
 *
 * `thesisByTicker` is passed in rather than looked up, because the grades live
 * in briefing.thesis_health while the holdings live in payload.watchlist, and
 * a predicate that reached across both would be untestable without a payload.
 *
 * Unknown is NOT a match. A holding with no thesis grade is excluded by a
 * thesis filter and one with no band is excluded by a band filter — asking for
 * "Broken" and being shown ungraded rows would be the same absent-vs-empty
 * collapse this product refuses everywhere else.
 */
export function matchesHolding(stock, filters, context = {}) {
  if (!stock) return false;
  const f = filters || {};
  const { thesisByTicker = {} } = context;

  if (f.sector && stock.sector !== f.sector) return false;

  if (f.band) {
    const band = String(stock.screener?.liquidity_band || "").toLowerCase();
    if (band !== f.band) return false;
  }

  if (f.thesis) {
    const grade = thesisByTicker[String(stock.ticker || "").toUpperCase()];
    if (!grade || grade.status !== f.thesis) return false;
  }

  if (f.q) {
    const needle = f.q.toLowerCase();
    if (!haystack(stock.ticker, stock.name, stock.sector).includes(needle)) return false;
  }

  return true;
}

/** The surviving holdings, order untouched. */
export function applyHoldings(rows, filters, context = {}) {
  if (!Array.isArray(rows)) return [];
  if (!activeCount(filters)) return rows;
  return rows.filter((row) => matchesHolding(row, filters, context));
}

/**
 * Days between an item's date and now, or null when the date is unreadable.
 *
 * Unreadable is not "old": an item whose date we cannot parse must not be
 * silently dropped by a date window, so `withinDays` keeps it.
 */
export function ageInDays(value, now = Date.now()) {
  if (!value) return null;
  const t = new Date(value).getTime();
  if (Number.isNaN(t)) return null;
  return (now - t) / 86400000;
}

export function withinDays(value, days, now = Date.now()) {
  if (!days) return true;
  const age = ageInDays(value, now);
  if (age === null) return true; // undated, not expired
  return age <= days && age >= -1; // -1 tolerates a source stamping tomorrow
}

/**
 * Does one flow item survive the filters?
 *
 * Flow rows are already normalised to {when, what, who, source}, so the search
 * runs over the same text the reader can see. Sector, thesis and band do not
 * apply to a news item and are ignored rather than silently excluding
 * everything — a filter that means nothing here should not empty the view.
 */
export function matchesItem(item, filters, context = {}) {
  if (!item) return false;
  const f = filters || {};
  const { now = Date.now() } = context;

  if (f.days && !withinDays(item.when, f.days, now)) return false;

  if (f.q) {
    const needle = f.q.toLowerCase();
    if (!haystack(item.what, item.who, item.source).includes(needle)) return false;
  }

  return true;
}

export function applyItems(rows, filters, context = {}) {
  if (!Array.isArray(rows)) return [];
  const f = filters || {};
  if (!f.q && !f.days) return rows;
  return rows.filter((row) => matchesItem(row, f, context));
}

/**
 * Thesis grades keyed by upper-case ticker.
 *
 * thesis_health is already keyed by ticker, but the casing comes from whatever
 * the pipeline wrote, and `focus` upper-cases. Normalising once here keeps
 * every caller from having to remember that.
 */
export function thesisIndex(briefing) {
  const out = {};
  for (const [ticker, grade] of Object.entries(briefing?.thesis_health || {})) {
    if (grade) out[String(ticker).toUpperCase()] = grade;
  }
  return out;
}
