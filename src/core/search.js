// What the header search box can find, and how a query ranks it.
//
// Each view has its own filter box, which narrows the view already open.
// There was no way to type a company's name anywhere and arrive at it: you
// had to know which view held what you wanted, open it, then filter. This
// is that missing way. Pure functions, so the ranking is tested without a DOM.

import { href } from "./router.js";

const norm = (s) => String(s || "").toLowerCase().replace(/\s+/g, " ").trim();

/** Every holding and every sector, as search entries. */
export function buildIndex(payload) {
  const entries = [];
  const labels = payload?.sectors || {};
  for (const [sector, stocks] of Object.entries(payload?.watchlist || {})) {
    if (sector === "macro_indicators" || !Array.isArray(stocks)) continue;
    const sectorLabel = labels[sector]?.label || sector.replace(/_/g, " ");
    const held = stocks.filter((s) => s && s.ticker);
    entries.push({
      kind: "sector",
      key: sector,
      title: sectorLabel,
      hint: `sector · ${held.length} holding${held.length === 1 ? "" : "s"}`,
      href: href("companies", { sector }),
      terms: [norm(sectorLabel), norm(sector.replace(/_/g, " "))],
    });
    for (const s of held) {
      const ticker = String(s.ticker).toUpperCase();
      entries.push({
        kind: "company",
        key: ticker,
        title: `${ticker} — ${s.name || ticker}`,
        hint: sectorLabel,
        href: href("company", { focus: ticker }),
        terms: [norm(ticker), norm(s.name)],
      });
    }
  }
  return entries;
}

/**
 * Score one entry for a query. The ticker typed exactly wins; then a ticker
 * or a word of the name that starts with the query; then the query anywhere.
 * 0 means no match.
 */
export function score(entry, query) {
  const q = norm(query);
  if (!q) return 0;
  const [first, ...rest] = entry.terms;
  const company = entry.kind === "company";
  if (first === q) return company ? 100 : 90;
  if (first.startsWith(q)) return company ? 80 : 70;
  for (const term of [first, ...rest]) {
    if (term.split(/[\s.&()-]+/).some((w) => w && w.startsWith(q))) return company ? 60 : 55;
  }
  if ([first, ...rest].some((t) => t.includes(q))) return 30;
  return 0;
}

/** The best matches, best first; ties keep index order (sector, then its holdings). */
export function search(index, query, limit = 8) {
  return (index || [])
    .map((entry, i) => ({ entry, i, s: score(entry, query) }))
    .filter((r) => r.s > 0)
    .sort((a, b) => b.s - a.s || a.i - b.i)
    .slice(0, limit)
    .map((r) => r.entry);
}
