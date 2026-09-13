// The filter row.
//
// Composition follows the dataviz interaction rules: one row, left-aligned,
// directly above the content it scopes — never inside a chart card and never
// per-chart. Whatever is below it, chart and stat and table alike, describes
// the same slice, so two numbers on one screen can never disagree.
//
// These are ordinary form controls rather than chart marks, deliberately. A
// bespoke dropdown would lose the keyboard behaviour, the mobile pickers and
// the screen-reader semantics that a native <select> has for free.

import { el } from "../core/dom.js";
import * as router from "../core/router.js";
import { activeCount, cleared, BAND_OPTIONS, DAY_OPTIONS, THESIS_OPTIONS } from "../core/filters.js";

const SEARCH_ID = "filter-q";

// Re-rendering the view replaces the DOM, so the input the reader is typing
// into is destroyed on every keystroke. We record where the caret was and put
// it back after the new bar is mounted; without this, search accepts exactly
// one character and then blurs.
let pendingFocus = null;

function navigate(view, params, patch, { replace = false } = {}) {
  const next = { ...params, ...patch };
  for (const [key, value] of Object.entries(next)) {
    if (value === "" || value === null || value === undefined) delete next[key];
  }
  router.go(view, next, { replace });
}

function select(id, label, value, options, onPick) {
  return el(
    "label",
    { class: "filter-field" },
    el("span", { class: "filter-label" }, label),
    el(
      "select",
      {
        id,
        class: "filter-control",
        onchange: (e) => onPick(e.target.value),
      },
      options.map(([optValue, optLabel]) =>
        el(
          "option",
          { value: optValue, selected: String(optValue) === String(value || "") },
          optLabel,
        ),
      ),
    ),
  );
}

/**
 * @param {object} opts
 *   view      route view these filters write back to
 *   route     the current route
 *   filters   the parsed filter state
 *   fields    which controls to show — views ask only for what applies to them
 *   sectors   sector keys present in the data
 *   summary   "23 of 70 holdings", rendered beside the clear button
 */
export function filterBar({ view, route, filters, fields, sectors = [], summary = "" }) {
  const params = (route && route.params) || {};
  const show = new Set(fields || ["q", "sector", "thesis", "band"]);
  const active = activeCount(filters);

  const controls = [];

  if (show.has("q")) {
    controls.push(
      el(
        "label",
        { class: "filter-field filter-field-search" },
        el("span", { class: "filter-label" }, "Search"),
        el("input", {
          id: SEARCH_ID,
          class: "filter-control",
          type: "search",
          value: filters.q || "",
          placeholder: "ticker or name",
          autocomplete: "off",
          oninput: (e) => {
            const input = e.target;
            pendingFocus = { start: input.selectionStart, end: input.selectionEnd };
            // replace:true — one history entry for the whole word, not one per
            // keystroke.
            navigate(view, params, { q: input.value }, { replace: true });
          },
        }),
      ),
    );
  }

  if (show.has("sector") && sectors.length) {
    controls.push(
      select(
        "filter-sector",
        "Sector",
        filters.sector,
        [["", "All sectors"], ...sectors.map((s) => [s, String(s).replace(/_/g, " ")])],
        (value) => navigate(view, params, { sector: value }),
      ),
    );
  }

  if (show.has("thesis")) {
    controls.push(
      select(
        "filter-thesis",
        "Thesis",
        filters.thesis,
        [["", "Any thesis"], ...THESIS_OPTIONS.map((t) => [t, t])],
        (value) => navigate(view, params, { thesis: value }),
      ),
    );
  }

  if (show.has("band")) {
    controls.push(
      select(
        "filter-band",
        "Liquidity",
        filters.band,
        [["", "Any liquidity"], ...BAND_OPTIONS.map((b) => [b, b])],
        (value) => navigate(view, params, { band: value }),
      ),
    );
  }

  if (show.has("days")) {
    // Date range first among the range controls, and presets rather than a
    // calendar — nobody fights a date grid to say "last 30 days".
    controls.push(
      select(
        "filter-days",
        "Period",
        filters.days ? String(filters.days) : "",
        [["", "All time"], ...DAY_OPTIONS.map(([d, label]) => [String(d), label])],
        (value) => navigate(view, params, { days: value }),
      ),
    );
  }

  return el(
    "div",
    { class: "filter-bar", role: "search" },
    el("div", { class: "filter-fields" }, controls),
    el(
      "div",
      { class: "filter-status" },
      summary ? el("span", { class: "filter-summary" }, summary) : null,
      active
        ? el(
            "a",
            {
              class: "filter-clear",
              href: router.href(view, cleared(params)),
            },
            `Clear ${active} filter${active > 1 ? "s" : ""}`,
          )
        : null,
    ),
  );
}

/**
 * Put the caret back after a re-render. Called once per route render, from
 * main.js, so the whole restore lives at a single explicit hook rather than
 * being re-derived by every view.
 */
export function restoreFocus() {
  if (!pendingFocus) return;
  const input = document.getElementById(SEARCH_ID);
  const at = pendingFocus;
  pendingFocus = null;
  if (!input) return;
  input.focus();
  try {
    input.setSelectionRange(at.start, at.end);
  } catch {
    // Some input types refuse setSelectionRange; focus alone is enough.
  }
}

/** An empty state that names the filters as the cause and offers a way out. */
export function filteredEmpty(view, params, noun = "rows") {
  return el(
    "div",
    { class: "empty-state" },
    el("p", { class: "empty-state-msg" }, `No ${noun} match these filters.`),
    el(
      "a",
      { class: "filter-clear", href: router.href(view, cleared(params)) },
      "Clear filters",
    ),
  );
}
