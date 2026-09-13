// The table every list view is built from.
//
// Six of the old sixteen tabs were the same table with different columns, each
// written out longhand. One builder means sorting, empty states, the focus
// link and escaping behave identically everywhere instead of nearly.

import { el, mount, emptyState } from "../core/dom.js";
import { href } from "../core/router.js";
import { num } from "../core/format.js";

/** Values that mean "we could not read this", as opposed to a real value. */
function isMissing(value) {
  if (value === null || value === undefined) return true;
  if (typeof value === "number") return !Number.isFinite(value);
  const s = String(value).trim();
  return s === "" || ["N/A", "NA", "-", "—", "NONE"].includes(s.toUpperCase());
}

/**
 * Compare two rows on one key, ascending.
 *
 * Numeric when both sides read as numbers — the pipeline stores "1,840.00" and
 * "+23.0%" as strings, so a plain string compare would order 9 above 100.
 * Falls back to locale text compare, which is what a sector or a name wants.
 */
function compare(av, bv) {
  const an = num(av);
  const bn = num(bv);
  if (an !== null && bn !== null) return an - bn;
  return String(av ?? "").localeCompare(String(bv ?? ""), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

/**
 * Sort rows, keeping unreadable values at the bottom in BOTH directions.
 *
 * This is the whole reason sorting is centralised. "N/A" sorted as zero puts
 * the rows we know least about at the top of an ascending sort and calls them
 * the cheapest, or the least risky — inventing a fact out of a gap. Missing
 * rows are pushed last before the direction is applied, so reversing the sort
 * never promotes them.
 */
export function sortRows(rows, key, dir = "desc", getValue = null) {
  if (!key) return rows;
  // Half the sortable columns read through screener.*, so the value a column
  // sorts on is not always row[key]. The accessor keeps that knowledge in the
  // column definition instead of flattening every row to suit the sorter.
  const read = getValue || ((row) => row[key]);
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const av = read(a);
    const bv = read(b);
    const am = isMissing(av);
    const bm = isMissing(bv);
    if (am && bm) return 0;
    if (am) return 1;
    if (bm) return -1;
    return sign * compare(av, bv);
  });
}

/** The direction a header click should produce next. */
export function nextDir(column, currentKey, currentDir) {
  if (column !== currentKey) return "desc";
  return currentDir === "desc" ? "asc" : "desc";
}

function sortHeader(column, { view, params, sortKey, sortDir }) {
  const isActive = column.key === sortKey;
  // aria-sort carries the state to a screen reader; the arrow is decorative
  // and hidden from it so the state is not announced twice.
  const label = [
    el("span", {}, column.label),
    el(
      "span",
      { class: "sort-mark", "aria-hidden": "true" },
      isActive ? (sortDir === "asc" ? "▲" : "▼") : "↕",
    ),
  ];

  return el(
    "th",
    {
      class: `th-interactive${column.numeric ? " num" : ""}${isActive ? " th-sorted" : ""}`,
      scope: "col",
      "aria-sort": isActive ? (sortDir === "asc" ? "ascending" : "descending") : "none",
    },
    el(
      "a",
      {
        class: "th-sort",
        href: href(view, {
          ...params,
          sort: column.key,
          dir: nextDir(column.key, sortKey, sortDir),
        }),
      },
      label,
    ),
  );
}

/**
 * @param {Array} rows
 * @param {Array} columns  {key, label, render?, numeric?, sortable?}
 * @param {object} opts    {focus, tickerKey, empty, sort, view, route}
 *
 * Sorting is interactive when `view` and `route` are given — the state lives in
 * the URL like every other piece of view state, so a sorted table is a link
 * someone can send. `opts.sort` remains as the default ordering for a view
 * that has an opinion (risk sorts by severity, not alphabetically).
 */
export function dataTable(rows, columns, opts = {}) {
  const { focus = null, tickerKey = "ticker", empty = "Nothing to show." } = opts;
  if (!Array.isArray(rows) || !rows.length) {
    return empty instanceof Node ? empty : emptyState(empty);
  }

  const interactive = Boolean(opts.view && opts.route);
  const params = (opts.route && opts.route.params) || {};
  const sortKey = (interactive && params.sort) || opts.sort?.key || null;
  const sortDir = (interactive && params.dir) || opts.sort?.dir || "desc";

  const sortColumn = columns.find((c) => c.key === sortKey);
  const sorted = sortKey
    ? sortRows(rows, sortKey, sortDir, sortColumn?.sortValue || null)
    : rows;

  const head = el(
    "thead",
    {},
    el(
      "tr",
      {},
      columns.map((c) =>
        interactive && c.sortable !== false
          ? sortHeader(c, { view: opts.view, params, sortKey, sortDir })
          : el("th", { class: c.numeric ? "num" : "", scope: "col" }, c.label),
      ),
    ),
  );

  const body = el(
    "tbody",
    {},
    sorted.map((row) => {
      const ticker = row[tickerKey];
      const isFocus = focus && ticker && String(ticker).toUpperCase() === focus;
      return el(
        "tr",
        { class: isFocus ? "row-focus" : "", dataset: ticker ? { ticker } : {} },
        columns.map((c) => {
          const content = c.render ? c.render(row) : row[c.key];
          return el(
            "td",
            { class: c.numeric ? "num" : "" },
            content instanceof Node ? content : content ?? "—",
          );
        }),
      );
    }),
  );

  return el("div", { class: "table-wrap" }, el("table", { class: "data-table" }, head, body));
}

/**
 * A ticker rendered as a link that focuses it.
 *
 * This is the cross-view thread: the same element in any table, carrying the
 * focus into whichever view the reader is already in. Previously a ticker was
 * inert text in six different tables and following one meant a manual search.
 *
 * `params` carries the current filters through, so following a company out of
 * a filtered table does not silently drop the filter on arrival.
 */
export function tickerLink(ticker, view, params = {}) {
  if (!ticker) return "—";
  return el(
    "a",
    { class: "ticker-link", href: href(view, { ...params, focus: ticker }) },
    String(ticker).toUpperCase(),
  );
}

/** A titled panel, optionally with a chart canvas above the table. */
export function panel(title, note, ...children) {
  return el(
    "section",
    { class: "panel" },
    title ? el("h3", { class: "section-title" }, title) : null,
    note ? el("p", { class: "section-note" }, note) : null,
    ...children,
  );
}

/** A canvas sized by CSS, with its table fallback rendered underneath. */
export function chartFrame(id, height = 260) {
  return el(
    "div",
    { class: "chart-frame", style: `height:${height}px` },
    el("canvas", { id }),
  );
}

export { mount };
