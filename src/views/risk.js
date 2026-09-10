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
import * as charts from "../charts/charts.js";
import { statusColour } from "../charts/palette.js";
import { dataTable, panel, chartFrame, tickerLink } from "./table.js";

const ORDER = { Broken: 0, Weakening: 1, Intact: 2 };

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

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const health = Object.values(b.thesis_health || {}).filter(Boolean);
  health.sort(
    (a, c) =>
      (ORDER[a.status] ?? 9) - (ORDER[c.status] ?? 9) ||
      String(a.ticker).localeCompare(String(c.ticker)),
  );

  const counts = { Broken: 0, Weakening: 0, Intact: 0 };
  for (const h of health) if (h.status in counts) counts[h.status] += 1;

  const warnings = b.early_warnings || [];
  const ongoing = b.warning_summary || [];

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

    panel(
      "Thesis health",
      "A thesis moves off Intact only when this cycle's evidence contradicts " +
        "the original catalyst — not on price noise.",
      chartFrame("chart-risk-band", 90),
      dataTable(
        health,
        [
          { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings") },
          { key: "status", label: "Status", render: (r) => statusPill(r.status) },
          { key: "reasons", label: "Why", render: (r) => (r.reasons || []).join("; ") || "—" },
        ],
        { focus: route?.focus, empty: "No thesis grades this run." },
      ),
    ),

    panel(
      "New and escalated",
      "Only warnings that appeared for the first time or got worse. The rest " +
        "are standing conditions, collapsed below.",
      dataTable(
        warnings,
        [
          { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings") },
          { key: "severity", label: "Severity" },
          { key: "status", label: "Change" },
          { key: "signal", label: "Signal" },
        ],
        { focus: route?.focus, empty: "Nothing new or escalated." },
      ),
    ),

    panel(
      "Standing conditions",
      "Unchanged since last run, grouped. \"46 holdings carry valuation flags\" " +
        "is a portfolio characteristic, not 46 decisions.",
      dataTable(
        ongoing,
        [
          { key: "category", label: "Category" },
          { key: "severity", label: "Severity" },
          { key: "count", label: "Holdings", numeric: true },
          { key: "tickers", label: "Which", render: (r) => (r.tickers || []).join(", ") },
        ],
        { empty: "No standing conditions." },
      ),
    ),
  );

  charts.statusBand(document.getElementById("chart-risk-band"), {
    segments: [
      { label: "Broken", value: counts.Broken, status: "critical" },
      { label: "Weakening", value: counts.Weakening, status: "serious" },
      { label: "Intact", value: counts.Intact, status: "good" },
    ],
  });
}

export { statusColour };
