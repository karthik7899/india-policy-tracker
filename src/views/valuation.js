// Valuation — one view, four lenses.
//
// Absorbs Sector Valuation, Margin of Safety, Buffett Valuation and Scoring
// Engine. They were four tabs asking one question ("what is this worth, and
// against what?"), which meant answering it required visiting four places and
// holding the numbers in your head.
//
// buffett_valuation is 59 KB and now lives in a sidecar, so it is fetched only
// when its lens is opened — most visits never pay for it.

import { el, mount, emptyState } from "../core/dom.js";
import { num, pct, plain } from "../core/format.js";
import { resolve } from "../core/data.js";
import { href } from "../core/router.js";
import * as charts from "../charts/charts.js";
import { dataTable, panel, chartFrame, tickerLink } from "./table.js";

/**
 * Each sector's P/E against the median of all sectors.
 *
 * sector_valuation carries median_pe per sector and no comparison figure, so
 * the baseline is derived here — the cross-sector median, which is the only
 * peer group this payload actually describes. Naming it "vs all sectors"
 * rather than "vs peers" matters: a sector's true industry peer group is a
 * different thing, and claiming this is that would overstate it.
 */
function sectorPremium(rows) {
  const withPE = (rows || [])
    .map((r) => ({ ...r, _pe: num(r.median_pe) }))
    .filter((r) => r._pe !== null && r._pe > 0);
  if (withPE.length < 2) return [];
  const sorted = [...withPE].map((r) => r._pe).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const median =
    sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  return withPE
    .map((r) => ({ ...r, _v: ((r._pe - median) / median) * 100 }))
    .sort((a, c) => c._v - a._v);
}

const LENSES = [
  ["sector", "Sector P/E"],
  ["graham", "Margin of safety"],
  ["buffett", "Owner earnings"],
  ["scoring", "Score"],
];

function lensNav(active, route) {
  return el(
    "nav",
    { class: "lens-nav" },
    LENSES.map(([key, label]) =>
      el(
        "a",
        {
          class: `lens${key === active ? " lens-active" : ""}`,
          href: href("valuation", { ...route.params, lens: key }),
        },
        label,
      ),
    ),
  );
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const lens = route?.params?.lens || "sector";

  const head = el(
    "header",
    { class: "view-head" },
    el("h2", { class: "view-title" }, "Valuation"),
    el("p", { class: "view-sub" }, "What it is worth, and against what."),
  );

  let body;

  if (lens === "sector") {
    const rows = sectorPremium(b.sector_valuation);

    body = panel(
      "Sector P/E against the all-sector median",
      "Blue above the median, red below, gray at parity \u2014 the sign is the " +
        "whole question, and a one-hue ramp would hide it. Compared against the " +
        "median of all sectors, not each sector\u2019s true industry peer group, " +
        "which this payload does not carry.",
      rows.length ? chartFrame("chart-val", Math.max(220, rows.length * 24)) : null,
      dataTable(
        rows,
        [
          { key: "sector", label: "Sector", render: (r) => r.label || String(r.sector || "").replace(/_/g, " ") },
          { key: "median_pe", label: "Median P/E", numeric: true, render: (r) => plain(r.median_pe, 1) },
          { key: "_v", label: "vs all sectors", numeric: true, render: (r) => pct(r._v) },
          { key: "stock_count", label: "Holdings", numeric: true },
        ],
        { empty: "No sector valuation this run." },
      ),
    );
  } else if (lens === "graham") {
    // margin_of_safety carries price and intrinsic value but no margin — it
    // is derived here rather than assumed to exist. A row missing either
    // input gets null, not zero: unknown and "no margin" are different.
    const rows = (b.margin_of_safety || []).map((r) => {
      const price = num(r.price);
      const value = num(r.graham_intrinsic_value);
      return {
        ...r,
        _margin: price && value ? ((value - price) / price) * 100 : null,
      };
    });
    body = panel(
      "Margin of safety",
      "Graham intrinsic value against price. A holding is only here when both " +
        "inputs were readable — an unreadable one is absent, not zero.",
      dataTable(
        rows,
        [
          { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings") },
          { key: "price", label: "Price", numeric: true },
          { key: "graham_intrinsic_value", label: "Intrinsic", numeric: true, render: (r) => plain(r.graham_intrinsic_value) },
          { key: "_margin", label: "Margin", numeric: true, render: (r) => pct(r._margin) },
          { key: "is_bargain", label: "Bargain", render: (r) => (r.is_bargain ? "yes" : "—") },
        ],
        { focus: route?.focus, empty: "No holding cleared the margin screen." },
      ),
    );
  } else if (lens === "buffett") {
    const rows = await resolve(b, "buffett_valuation");
    body = panel(
      "Owner earnings",
      "Fetched on demand — this is 59 KB and most visits never open it.",
      Array.isArray(rows)
        ? dataTable(
            rows,
            [
              { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings") },
              { key: "owner_earnings", label: "Owner earnings", numeric: true, render: (r) => plain(r.owner_earnings) },
              { key: "moat_status", label: "Moat" },
            ],
            { focus: route?.focus, empty: "No owner-earnings rows." },
          )
        : emptyState("Owner earnings unavailable.", "The sidecar could not be loaded."),
    );
  } else {
    const rows = (payload?.watchlist ? Object.values(payload.watchlist).flat() : [])
      .filter((s) => s && s.score)
      .map((s) => ({ ...s, _score: num(s.score.overall_score) }))
      .sort((a, c) => (c._score ?? -99) - (a._score ?? -99));

    body = panel(
      "Score",
      "Never a single opaque total: the reasons and risks that produced it are " +
        "the row, not a tooltip.",
      dataTable(
        rows,
        [
          { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings") },
          { key: "_score", label: "Score", numeric: true },
          { key: "confidence", label: "Data", render: (r) => r.score?.confidence ?? "—" },
          {
            key: "reasons",
            label: "For",
            render: (r) => el("span", { class: "cell-good" }, (r.score?.reasons || []).slice(0, 2).join("; ") || "—"),
          },
          {
            key: "risks",
            label: "Against",
            render: (r) => el("span", { class: "cell-bad" }, (r.score?.risks || []).slice(0, 2).join("; ") || "—"),
          },
        ],
        { focus: route?.focus, empty: "Nothing scored." },
      ),
    );
  }

  mount(container, head, lensNav(lens, route || { params: {} }), body);

  if (lens === "sector") {
    const rows = sectorPremium(b.sector_valuation);
    if (rows.length) {
      charts.divergingBar(document.getElementById("chart-val"), {
        labels: rows.map((r) => r.label || String(r.sector || "").replace(/_/g, " ")),
        values: rows.map((r) => Number(r._v.toFixed(1))),
        suffix: "%",
      });
    }
  }
}
