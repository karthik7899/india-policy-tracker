// The table every list view is built from.
//
// Six of the old sixteen tabs were the same table with different columns, each
// written out longhand. One builder means sorting, empty states, the focus
// link and escaping behave identically everywhere instead of nearly.

import { el, mount, emptyState } from "../core/dom.js";
import { href } from "../core/router.js";
import { num } from "../core/format.js";

/**
 * @param {Array} rows
 * @param {Array} columns  {key, label, render?, numeric?, width?}
 * @param {object} opts    {focus, tickerKey, empty, sort}
 */
export function dataTable(rows, columns, opts = {}) {
  const { focus = null, tickerKey = "ticker", empty = "Nothing to show." } = opts;
  if (!Array.isArray(rows) || !rows.length) return emptyState(empty);

  let sorted = rows;
  if (opts.sort) {
    const { key, dir = "desc" } = opts.sort;
    sorted = [...rows].sort((a, b) => {
      const av = num(a[key]);
      const bv = num(b[key]);
      if (av === null && bv === null) return 0;
      if (av === null) return 1; // unknowns last, never sorted as zero
      if (bv === null) return -1;
      return dir === "desc" ? bv - av : av - bv;
    });
  }

  const head = el(
    "thead",
    {},
    el(
      "tr",
      {},
      columns.map((c) =>
        el("th", { class: c.numeric ? "num" : "", scope: "col" }, c.label),
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
 */
export function tickerLink(ticker, view) {
  if (!ticker) return "—";
  return el(
    "a",
    { class: "ticker-link", href: href(view, { focus: ticker }) },
    String(ticker).toUpperCase(),
  );
}

/** A titled panel, optionally with a chart canvas above the table. */
export function panel(title, note, ...children) {
  return el(
    "section",
    { class: "panel" },
    el("h3", { class: "section-title" }, title),
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
