// Risk — thesis health, warnings, and the standing conditions behind them.
//
// Absorbs Thesis & Signals, Early Warning and Caution List. The split between
// them was never about subject, only about severity, and it meant a holding
// whose thesis had broken AND which carried a critical warning appeared as two
// unrelated rows in two tabs.
//
// Ordering follows analysis/thesis.thesis_health_sorted: Broken, then
// Weakening, then Intact, then ticker. The ticker tiebreak matters — without
// it, which holdings survive a truncation depends on dict insertion order.

import { el, mount } from "../core/dom.js";
import { thesisStatus } from "../core/format.js";
import * as filters from "../core/filters.js";
import * as charts from "../charts/charts.js";
import { statusColour } from "../charts/palette.js";
import { dataTable, panel, chartFrame, tickerLink } from "./table.js";
import { filterBar, filteredEmpty } from "./filterbar.js";

const ORDER = { Broken: 0, Weakening: 1, Intact: 2 };

// Short ticker lists stay inline: a disclosure costs a click, and hiding three
// tickers behind one is worse than showing them. The cut-off is where the list
// stops being readable at a glance rather than a round number.
const INLINE_TICKERS = 5;

const SEGMENTS = [
  { key: "Broken", label: "Broken", status: "critical" },
  { key: "Weakening", label: "Weakening", status: "serious" },
  { key: "Intact", label: "Intact", status: "good" },
];

/**
 * A native disclosure. No JS state, no new dependency, keyboard-operable and
 * announced by screen readers for free — and closed by default, which is the
 * point: this page was 6,832px tall and most of that was detail nobody had
 * asked to see yet.
 *
 * `summary` must carry the count, not just a verb. "Show" tells a reader
 * nothing about whether opening it is worth the scroll; "67 holdings" does.
 */
function disclosure(summaryText, body) {
  return el(
    "details",
    { class: "disclose" },
    el("summary", { class: "disclose-summary" }, summaryText),
    body,
  );
}

function statusPill(status) {
  // Icon + label, never colour alone: on the light surface two of the four
  // status steps are sub-3:1 by design, and the pairing is the mitigation.
  const mark = { Broken: "✕", Weakening: "!", Intact: "✓" }[status] || "?";
  return el(
    "span",
    { class: `pill pill-${thesisStatus(status)}` },
    el("span", { class: "pill-mark", "aria-hidden": "true" }, mark),
    status || "Unknown",
  );
}

/**
 * The watchlist entry for each ticker, keyed upper-case.
 *
 * A thesis_health row carries ticker, name, sector, status and reasons — but
 * no `screener`. So a liquidity filter applied to these rows directly would
 * match nothing and silently empty the view, which is precisely the failure
 * this dashboard is careful about elsewhere. Joining the watchlist entry back
 * in is what makes one filter mean the same thing in every view.
 */
function holdingIndex(watchlist) {
  const out = {};
  for (const [sector, stocks] of Object.entries(watchlist || {})) {
    for (const s of stocks || []) {
      if (s?.ticker) out[String(s.ticker).toUpperCase()] = { ...s, sector };
    }
  }
  return out;
}

/** Counts per sector, most-damaged first, so the chart's top row is the answer. */
function groupBySector(health, holdings) {
  const groups = new Map();
  for (const h of health) {
    const sector =
      h.sector || holdings[String(h.ticker).toUpperCase()]?.sector || "unassigned";
    if (!groups.has(sector)) {
      groups.set(sector, { label: sector.replace(/_/g, " "), counts: {}, _broken: 0, _n: 0 });
    }
    const g = groups.get(sector);
    g.counts[h.status] = (g.counts[h.status] || 0) + 1;
    g._n += 1;
    if (h.status === "Broken") g._broken += 1;
  }
  return [...groups.values()].sort((a, b) => b._broken - a._broken || b._n - a._n);
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const params = (route && route.params) || {};
  const active = filters.read(route);
  const holdings = holdingIndex(payload?.watchlist);
  const sectors = Object.keys(payload?.watchlist || {}).sort();

  const allHealth = Object.values(b.thesis_health || {}).filter(Boolean);

  // The filters describe holdings, so each graded ticker is matched as the
  // holding it is — its watchlist entry, which carries the screener block the
  // grade itself does not.
  const asHolding = (h) => {
    const held = holdings[String(h.ticker).toUpperCase()] || {};
    return {
      ticker: h.ticker,
      name: h.name || held.name,
      sector: h.sector || held.sector,
      screener: held.screener || {},
    };
  };
  const thesisByTicker = filters.thesisIndex(b);
  const health = filters.activeCount(active)
    ? allHealth.filter((h) => filters.matchesHolding(asHolding(h), active, { thesisByTicker }))
    : allHealth;

  health.sort(
    (a, c) =>
      (ORDER[a.status] ?? 9) - (ORDER[c.status] ?? 9) ||
      String(a.ticker).localeCompare(String(c.ticker)),
  );

  const counts = { Broken: 0, Weakening: 0, Intact: 0 };
  for (const h of health) if (h.status in counts) counts[h.status] += 1;

  const groups = groupBySector(health, holdings);
  const filtered = filters.activeCount(active) > 0;

  // Warnings are per-ticker too, so the same slice applies to them.
  const keep = new Set(health.map((h) => String(h.ticker).toUpperCase()));
  const scope = (list) =>
    filtered
      ? (list || []).filter((r) => !r.ticker || keep.has(String(r.ticker).toUpperCase()))
      : list || [];

  const warnings = scope(b.early_warnings);
  const ongoing = b.warning_summary || [];

  // Tiered by severity, most severe open. The sort already runs Broken ->
  // Weakening -> Intact, so this partitions the same order rather than
  // re-sorting it: a ticker a reader had in view stays where it was.
  //
  // Why tier at all: this panel was 2,959px of the page on its own, and a
  // reader arriving at Risk wants the contradicted theses first. Broken is
  // that set. The two tiers below it are real but secondary, and each summary
  // carries its count so the choice to open is an informed one.
  const byStatus = (s) => health.filter((h) => h.status === s);
  const broken = byStatus("Broken");
  const weakening = byStatus("Weakening");
  const intact = byStatus("Intact");

  const gradeColumns = [
    { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings", params) },
    {
      key: "status",
      label: "Status",
      sortValue: (r) => ORDER[r.status] ?? 9,
      render: (r) => statusPill(r.status),
    },
    {
      key: "reasons",
      label: "Why",
      sortable: false,
      render: (r) => (r.reasons || []).join("; ") || "—",
    },
  ];

  // One shape for all three tiers, so sorting and focus behave identically
  // whichever one a reader is in.
  const gradeTable = (rows, { empty }) =>
    dataTable(rows, gradeColumns, { focus: route?.focus, view: "risk", route, empty });

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Risk"),
      el(
        "p",
        { class: "view-sub" },
        `${counts.Broken} broken · ${counts.Weakening} weakening · ${counts.Intact} intact`,
      ),
    ),

    filterBar({
      view: "risk",
      route,
      filters: active,
      fields: ["q", "sector", "thesis", "band"],
      sectors,
      summary: filtered ? `${health.length} of ${allHealth.length} graded` : "",
    }),

    // Both charts first, then the long table. They summarise the same rows, so
    // separating them with seventy rows of detail would mean scrolling past the
    // answer to find the other half of it.
    panel(
      "Thesis health",
      "A thesis moves off Intact only when this cycle's evidence contradicts " +
        "the original catalyst — not on price noise.",
      chartFrame("chart-risk-band", 90),
    ),

    groups.length > 1
      ? panel(
          "Where the damage is",
          "The band above says how much of the book has turned; it cannot say " +
            "where. Nine broken theses inside one sector is a sector call, and " +
            "nine spread across nine sectors is not — these are absolute counts " +
            "so a three-holding sector cannot look as weighty as a fifteen.",
          chartFrame("chart-risk-sector", Math.max(180, groups.length * 30 + 60)),
        )
      : null,

    panel(
      "Broken theses",
      broken.length
        ? "This cycle's evidence contradicts the catalyst that put the holding " +
          "on the list. Weakening and intact grades are below, collapsed."
        : null,
      gradeTable(broken, {
        empty: filtered ? filteredEmpty("risk", params, "holdings") : "Nothing broken this run.",
      }),

      weakening.length
        ? disclosure(
            `${weakening.length} weakening — evidence softening, not yet contradicting`,
            gradeTable(weakening, { empty: "None weakening." }),
          )
        : null,

      // Intact holdings are graded but carry no reasons — by construction, not
      // by omission: a thesis stays Intact precisely when nothing contradicted
      // it, so there is nothing to write in the Why column. Eleven rows of em
      // dash is not a finding. Kept behind the disclosure rather than dropped,
      // because "graded and fine" is different from "not graded", and a reader
      // checking whether a holding was assessed at all must be able to see it.
      intact.length
        ? disclosure(
            `${intact.length} intact — graded, nothing contradicted the catalyst`,
            gradeTable(intact, { empty: "None intact." }),
          )
        : null,
    ),

    panel(
      "New and escalated",
      "Only warnings that appeared for the first time or got worse. The rest " +
        "are standing conditions, collapsed below.",
      dataTable(
        warnings,
        [
          { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings", params) },
          { key: "severity", label: "Severity" },
          { key: "status", label: "Change" },
          { key: "signal", label: "Signal", sortable: false },
        ],
        {
          focus: route?.focus,
          view: "risk",
          route,
          empty: "Nothing new or escalated.",
        },
      ),
    ),

    panel(
      "Standing conditions",
      "Unchanged since last run, grouped: a portfolio characteristic rather " +
        "than a list of decisions. Warnings outnumber holdings wherever one " +
        "holding carries the same condition more than once, and a warning " +
        "that names no holding counts as a warning with nothing in Which. " +
        "Not scoped by the filters above — these are counted across the " +
        "whole book.",
      dataTable(
        ongoing,
        [
          { key: "category", label: "Category" },
          { key: "severity", label: "Severity" },
          // Two numbers, because they are two different things and the panel
          // had been showing one under the other's name. summarize_ongoing
          // increments `count` once per WARNING, while `tickers` is deduped
          // per holding and drops any warning it could not attribute — so a
          // column labelled "Holdings" was reporting warnings. They agree for
          // 18 of 22 rows, which is why it went unnoticed; where they differ
          // the gap is the finding. Corporate Move is 53 warnings across 20
          // holdings, and Input Cost Shock is 3 warnings attributed to none.
          {
            key: "tickers",
            label: "Holdings",
            numeric: true,
            sortValue: (r) => (r.tickers || []).length,
            render: (r) => String((r.tickers || []).length),
          },
          { key: "count", label: "Warnings", numeric: true },
          {
            key: "which",
            label: "Which",
            sortable: false,
            // Behind a disclosure rather than inline. These cells carried 345
            // tickers between them across 22 rows — one of them 67 — which is
            // a wall of capital letters no one reads and which made this panel
            // as tall as the whole graded table. The count column already
            // answers "how many"; this answers "which", on request.
            render: (r) => {
              const list = r.tickers || [];
              if (!list.length) return "—";
              if (list.length <= INLINE_TICKERS) return list.join(", ");
              return disclosure(`${list.length} holdings`, el("span", {}, list.join(", ")));
            },
          },
        ],
        { empty: "No standing conditions." },
      ),
    ),
  );

  charts.statusBand(document.getElementById("chart-risk-band"), {
    segments: SEGMENTS.map((s) => ({ label: s.label, value: counts[s.key], status: s.status })),
  });

  if (groups.length > 1) {
    charts.statusByGroup(document.getElementById("chart-risk-sector"), {
      groups,
      statuses: SEGMENTS,
    });
  }
}

export { statusColour };
