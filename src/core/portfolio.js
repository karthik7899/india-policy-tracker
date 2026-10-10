// The book, for the Portfolio view and the company page.
//
// Everything is computed by the pipeline (analysis/portfolio.py) and arrives
// in data/portfolio.json; what lives here is choosing a book, saying where
// each limit stands, and writing the order list out for a trading desk.

/** The book with this id, or the first one measured without an error. */
export function pickBook(data, id) {
  const books = (data && Array.isArray(data.books) ? data.books : []).filter(Boolean);
  if (!books.length) return null;
  return (
    books.find((b) => id && String(b.id) === String(id)) ||
    books.find((b) => !b.error) ||
    books[0]
  );
}

/** One holding's row in the book, or null when the book does not hold it. */
export function positionOf(book, ticker) {
  const key = String(ticker || "").toUpperCase();
  return (book?.positions || []).find((p) => String(p.ticker).toUpperCase() === key) || null;
}

/** The orders the book would send, split into the trades that had to happen
 * and the ones that only settle the cash those trades left. */
export function orderGroups(orders) {
  const rows = orders?.rows || [];
  const settles = (o) => /^(reinvests|raises cash)/.test(String(o.reason || ""));
  return { main: rows.filter((o) => !settles(o)), settle: rows.filter(settles) };
}

const LIMITS = [
  ["max_stock_pct", "Largest position", "% of NAV"],
  ["max_sector_pct", "Largest sector", "% of NAV"],
  ["max_group_pct", "Largest business group", "% of NAV"],
  ["max_days_to_exit", "Slowest exit", "days"],
  ["max_ownership_pct", "Largest share of a company", "%"],
  ["max_beta", "Beta", ""],
  ["max_tracking_error_pct", "Tracking error", "% a year"],
];

/**
 * Each limit the book sets, with the figure it is measured against today and
 * the name that sets that figure. `value` is null when nothing could be
 * measured, which is not the same as being within the limit.
 */
export function limitStatus(book) {
  const set = book?.limits || {};
  const positions = book?.positions || [];
  const top = (rows, key) =>
    rows.reduce((best, r) => (typeof r[key] === "number" && (!best || r[key] > best[key]) ? r : best), null);
  const largest = top(positions, "weight_pct");
  const slowest = top(positions, "days_to_exit");
  const owned = top(positions, "ownership_pct");
  const sector = (book?.exposure?.sectors || [])[0];
  const group = top(book?.exposure?.groups || [], "weight_pct");
  const risk = book?.risk || {};
  const now = {
    max_stock_pct: largest && [largest.weight_pct, largest.ticker],
    max_sector_pct: sector && [sector.weight_pct, sector.sector],
    max_group_pct: group && [group.weight_pct, group.group],
    max_days_to_exit: slowest && [slowest.days_to_exit, slowest.ticker],
    max_ownership_pct: owned && [owned.ownership_pct, owned.ticker],
    max_beta: typeof risk.beta === "number" && [risk.beta, ""],
    max_tracking_error_pct: typeof risk.tracking_error_pct === "number" && [risk.tracking_error_pct, ""],
  };
  return LIMITS.filter(([key]) => typeof set[key] === "number").map(([key, label, unit]) => {
    const [value, subject] = now[key] || [null, ""];
    return {
      key,
      label,
      unit,
      limit: set[key],
      value,
      subject,
      ok: value === null ? null : value <= set[key],
    };
  });
}

/** A CSV cell: quoted when it must be, and never read as a formula. */
function cell(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "";
  let s = String(value);
  // A spreadsheet runs a cell that opens with one of these as a formula.
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

const CSV_COLUMNS = [
  ["side", "side"],
  ["symbol", "ticker"],
  ["exchange", null],
  ["name", "name"],
  ["quantity", "quantity"],
  ["reference_price", "price"],
  ["value_cr", "value_cr"],
  ["weight_now_pct", "weight_now_pct"],
  ["target_pct", "target_pct"],
  ["days_to_trade", "days_to_trade"],
  ["reason", "reason"],
];

/** The order list as CSV: one row per order, NSE symbols, whole shares. */
export function ordersCsv(book) {
  const rows = book?.orders?.rows || [];
  const lines = [CSV_COLUMNS.map(([h]) => h).join(",")];
  for (const o of rows) {
    lines.push(CSV_COLUMNS.map(([, k]) => cell(k === null ? "NSE" : o[k])).join(","));
  }
  return lines.join("\r\n") + "\r\n";
}

/** A filename for the order list: the book and the day it was computed. */
export function csvName(book, asOf) {
  const id = String(book?.id || "book").replace(/[^A-Za-z0-9_-]/g, "") || "book";
  const day = String(asOf || "").replace(/[^0-9-]/g, "");
  return `orders-${id}${day ? `-${day}` : ""}.csv`;
}
