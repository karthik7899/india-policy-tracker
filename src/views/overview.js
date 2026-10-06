// Overview — what changed, and what the reader should look at first.
//
// Two charts, each answering a question a table made the reader compute:
// which sectors are growing, and how much of the book has an intact thesis.

import { el, mount } from "../core/dom.js";
import { num, pct, thesisStatus, LLM_MARK } from "../core/format.js";
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

/**
 * The track-record line (analysis/track_record.py): how many picks old enough
 * to judge beat the Nifty 50 since the day they were made. Exits count — the
 * summary says how many — because dropping them is what flattered the old
 * target-based hit rate.
 */
/** A difference of two returns: percentage points, not percent. */
function pts(v) {
  return pct(v).replace("%", " pts");
}

export function trackSummary(record) {
  const s = record?.summary || {};
  const minAge = record?.min_age_days ?? 30;
  if (!record?.decisions?.length) return "";
  if (!s.n) {
    return `No pick is ${minAge} days old yet (${s.too_recent || 0} younger).`;
  }
  const signed = (v) => `${v > 0 ? "+" : ""}${Number(v).toFixed(1)}`;
  return [
    `${s.beat_nifty} of ${s.n}${s.stocks && s.stocks !== s.n ? ` (${s.stocks} stocks)` : ""} beat the Nifty 50`,
    `median ${signed(s.median_vs_nifty_pct)} pts`,
    s.exited ? `${s.exited} since exited, still counted` : "",
    s.with_index ? `${s.beat_index} of ${s.with_index} ahead of their sector index` : "",
    s.index_unmeasured ? `sector index unavailable for ${s.index_unmeasured}` : "",
  ]
    .filter(Boolean)
    .join(" \u00b7 ");
}

const CHANGE_GROUPS = [
  ["watchlist", "Watchlist"],
  ["thesis", "Thesis"],
  ["events", "Company events"],
  ["policy", "New policy"],
  ["warnings", "New or escalated alerts"],
];

/**
 * The non-empty groups of what changed since the last run
 * (analysis/changes.py), in reading order, each with its full count — the
 * payload keeps at most eight items per group, so "12 new" must come from
 * the count rather than the list.
 */
export function changeGroups(changes) {
  if (!changes || changes.first_run) return [];
  return CHANGE_GROUPS.map(([key, label]) => ({
    key,
    label,
    count: changes.counts?.[key] || 0,
    items: changes.items?.[key] || [],
  })).filter((g) => g.count);
}

/** Sectors by policy balance, net tailwind first, sectors with nothing left out. */
export function policyRows(balance, labels = {}) {
  return Object.entries(balance || {})
    .map(([sector, b]) => ({
      sector,
      label: labels[sector]?.label || sector.replace(/_/g, " "),
      tailwind: b.tailwind || 0,
      headwind: b.headwind || 0,
      mixed: b.mixed || 0,
      net: b.net ?? (b.tailwind || 0) - (b.headwind || 0),
    }))
    .filter((r) => r.tailwind || r.headwind || r.mixed)
    .sort((a, c) => c.net - a.net || c.tailwind - a.tailwind);
}

function changesPanel(changes) {
  if (!changes) return null;
  if (changes.first_run) {
    return panel("Since the last run", "Nothing to compare against yet; this fills in from the next run.");
  }
  const groups = changeGroups(changes);
  if (!groups.length) return panel("Since the last run", "Nothing new since the last run.");
  return panel(
    "Since the last run",
    "Only what is new: everything else on this page is standing state.",
    el(
      "div",
      { class: "changes-grid" },
      groups.map((g) =>
        el(
          "section",
          {},
          el("h4", {}, `${g.label} (${g.count})`),
          el(
            "ul",
            { class: "evidence" },
            g.items.map((i) =>
              el(
                "li",
                {},
                i.ticker ? [tickerLink(i.ticker, "companies"), " "] : null,
                i.link
                  ? el("a", { href: i.link, target: "_blank", rel: "noopener noreferrer" }, i.text)
                  : i.text,
                i.detail ? el("span", { class: "evidence-meta" }, i.detail) : null,
              ),
            ),
          ),
          g.count > g.items.length
            ? el("p", { class: "section-note" }, `+ ${g.count - g.items.length} more`)
            : null,
        ),
      ),
    ),
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
  const policy = policyRows(b.policy_balance, payload?.sectors);
  const record = b.track_record || {};
  const minAge = record.min_age_days ?? 30;
  const judged = (record.decisions || [])
    .filter((r) => typeof r.vs_nifty_pct === "number" && r.days >= minAge)
    .sort((a, c) => c.vs_nifty_pct - a.vs_nifty_pct);

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

    changesPanel(b.changes),

    policy.length
      ? panel(
          "Policy by sector",
          "Policy measures read in the last 30 days, by which way they cut for each " +
            "sector (\u25b2 tailwind, \u25bc headwind; a proposal counts half). Open a " +
            `sector to see the companies and the measures behind the count. ${LLM_MARK}`,
          dataTable(
            policy,
            [
              {
                key: "label",
                label: "Sector",
                render: (r) =>
                  el(
                    "a",
                    { href: href("companies", { sector: r.sector, sort: r.net < 0 ? "pressure" : "support" }) },
                    r.label,
                  ),
              },
              { key: "tailwind", label: "\u25b2 Tailwind", numeric: true },
              { key: "headwind", label: "\u25bc Headwind", numeric: true },
              { key: "net", label: "Net", numeric: true, render: (r) => `${r.net > 0 ? "+" : ""}${r.net}` },
            ],
            { view: "overview", route, empty: "" },
          ),
        )
      : null,

    panel(
      "Thesis health",
      "Where each holding stands against the catalyst that put it on the " +
        "list. A thesis is Broken only when this cycle's evidence contradicts " +
        "it — not when the price fell.",
      chartFrame("chart-thesis", 90),
    ),

    panel(
      "Sector growth",
      "Median trailing-year revenue growth across the holdings in each " +
        "sector, fastest first. Only holdings whose growth figure was " +
        "readable count toward a median, so a sector standing on one holding " +
        "ranks beside one standing on five — hover for the number behind it.",
      chartFrame("chart-growth", Math.max(220, growth.length * 22)),
    ),

    record.decisions?.length
      ? panel(
          "Track record",
          `${trackSummary(record)}. Each rotation pick from the day it was made ` +
            "to today, against the Nifty 50 over the same days — equal-weighted, " +
            "adjusted closes. Weeks of data, so no Sharpe ratio.",
          judged.length ? chartFrame("chart-track", Math.max(180, judged.length * 18 + 60)) : null,
          dataTable(
            judged,
            [
              { key: "ticker", label: "Pick", render: (r) => tickerLink(r.ticker, "holdings") },
              { key: "date", label: "Since" },
              { key: "return_pct", label: "Return", render: (r) => pct(r.return_pct) },
              { key: "nifty_pct", label: "Nifty 50", render: (r) => pct(r.nifty_pct) },
              { key: "vs_nifty_pct", label: "vs Nifty", render: (r) => pts(r.vs_nifty_pct) },
              {
                key: "vs_index_pct",
                label: "vs sector index",
                render: (r) =>
                  typeof r.vs_index_pct === "number"
                    ? `${pts(r.vs_index_pct)} (${r.index})`
                    : r.index_unmeasured
                      ? "unavailable"
                      : "\u2014",
              },
              { key: "still_held", label: "Held", render: (r) => (r.still_held ? "yes" : "exited") },
            ],
            { focus: route?.focus, view: "overview", route, empty: "No pick is old enough to judge yet." },
          ),
        )
      : null,

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

  if (judged.length) {
    charts.rankedBar(document.getElementById("chart-track"), {
      labels: judged.map((r) => r.ticker),
      values: judged.map((r) => Number(r.vs_nifty_pct.toFixed(1))),
      suffix: " pts",
      horizontal: true,
      axisLabel: "Return minus the Nifty 50 since the pick (percentage points)",
    });
  }

  charts.rankedBar(document.getElementById("chart-growth"), {
    labels: growth.map((s) => s.label || String(s.sector || "").replace(/_/g, " ")),
    values: growth.map((s) => Number(s._g.toFixed(1))),
    suffix: "%",
    horizontal: true,
    axisLabel: "Median trailing-year revenue growth (%)",
    // What the median stands on. The payload already flags a thin sector;
    // without this the chart ranks a one-holding median beside a five-holding
    // one and gives the reader no way to tell.
    meta: growth.map((s) => {
      const n = num(s.stock_count);
      if (n === null) return null;
      return `median of ${n} holding${n === 1 ? "" : "s"}${s.low_confidence ? " — thin" : ""}`;
    }),
  });
}

export { pct };
