// Overview — what changed, and what the reader should look at first.
//
// Two charts, each answering a question a table made the reader compute:
// which sectors are growing, and how much of the book has an intact thesis.

import { el, mount } from "../core/dom.js";
import { num, pct, thesisStatus } from "../core/format.js";
import { href } from "../core/router.js";
import * as charts from "../charts/charts.js";
import { dataTable, panel, chartFrame, tickerLink } from "./table.js";

/** A headline number. The form heuristic's answer to a one-bar bar chart. */
function statTile(label, value, detail, tone) {
  return el(
    "div",
    { class: `stat-tile${tone ? ` tone-${tone}` : ""}` },
    el("div", { class: "stat-label" }, label),
    el("div", { class: "stat-value" }, value),
    detail ? el("div", { class: "stat-detail" }, detail) : null,
  );
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const health = Object.values(b.thesis_health || {});
  const counts = { Broken: 0, Weakening: 0, Intact: 0 };
  for (const h of health) if (h?.status in counts) counts[h.status] += 1;

  const growth = (b.sector_growth || [])
    .map((s) => ({ ...s, _g: num(s.median_ttm_growth_pct) }))
    .filter((s) => s._g !== null)
    .sort((a, b2) => b2._g - a._g);

  const warnings = b.early_warnings || [];

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Overview"),
      el("p", { class: "view-sub" }, `Updated ${payload?.last_updated || "—"}`),
    ),

    el(
      "div",
      { class: "stat-row" },
      statTile("Holdings", String(health.length || "—"), "with a graded thesis"),
      statTile(
        "Thesis broken",
        String(counts.Broken),
        "evidence contradicts the catalyst",
        counts.Broken ? "critical" : null,
      ),
      statTile(
        "Actionable warnings",
        String(warnings.length),
        "new or escalated this run",
        warnings.length ? "serious" : null,
      ),
      statTile(
        "Sectors ranked",
        String(growth.length),
        growth.length ? `fastest ${growth[0].label ?? growth[0].sector ?? ""}` : "",
      ),
    ),

    panel(
      "Thesis health",
      "Part-to-whole, so one stacked bar. Status colours are reserved and " +
        "every segment is named — on a light surface these hues are not " +
        "allowed to carry the meaning alone.",
      chartFrame("chart-thesis", 90),
    ),

    panel(
      "Sector growth",
      "Magnitude low to high, so a single-hue ordinal ramp rather than a " +
        "colour per sector: the ranking is the message, not sector identity.",
      chartFrame("chart-growth", Math.max(220, growth.length * 22)),
    ),

    panel(
      "Needs attention",
      warnings.length ? null : "Nothing new or escalated this run.",
      dataTable(
        warnings.slice(0, 12),
        [
          { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "risk") },
          { key: "severity", label: "Severity" },
          { key: "signal", label: "Signal" },
        ],
        { focus: route?.focus, empty: "No actionable warnings." },
      ),
      el(
        "a",
        { class: "more-link", href: href("risk") },
        "All risk signals →",
      ),
    ),
  );

  // Charts after mount: the canvases must be in the document to size.
  charts.statusBand(document.getElementById("chart-thesis"), {
    segments: [
      { label: "Broken", value: counts.Broken, status: thesisStatus("Broken") },
      { label: "Weakening", value: counts.Weakening, status: thesisStatus("Weakening") },
      { label: "Intact", value: counts.Intact, status: thesisStatus("Intact") },
    ],
  });

  charts.rankedBar(document.getElementById("chart-growth"), {
    labels: growth.map((s) => s.label || String(s.sector || "").replace(/_/g, " ")),
    values: growth.map((s) => Number(s._g.toFixed(1))),
    suffix: "%",
    horizontal: true,
  });
}

export { pct };
