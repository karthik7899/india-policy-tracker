// Holdings — the book, and the liquidity question about it.
//
// Absorbs the old "Holdings by Sector" and "Stocks Screener" tabs, which
// showed the same rows with different columns and no way to get from one to
// the other.
//
// The chart is delivery against turnover, and it is a SCATTER on purpose. The
// question is whether a name that looks liquid on turnover actually settles,
// and that is a relationship between two measures — the form a two-y-axis bar
// chart gets wrong, which is why the skill calls dual axes the single most
// misread chart.
//
// The filter row scopes the scatter, the count in the subtitle and the table
// together. That is the point of putting it above all three rather than inside
// one panel: there is no arrangement of controls that leaves the chart
// describing seventy holdings while the table describes nine.

import { el, mount } from "../core/dom.js";
import { num, crore, pct, bandIndex, BANDS } from "../core/format.js";
import { resolveTicker, loadCoverage } from "../core/data.js";
import * as filters from "../core/filters.js";
import * as charts from "../charts/charts.js";
import { dataTable, panel, chartFrame, tickerLink } from "./table.js";
import { filterBar, filteredEmpty } from "./filterbar.js";

function flatten(watchlist) {
  const out = [];
  for (const [sector, stocks] of Object.entries(watchlist || {})) {
    for (const s of stocks || []) {
      if (s && typeof s === "object" && s.ticker) out.push({ ...s, sector });
    }
  }
  return out;
}

/** The drawer: everything known about one holding, fetched on open. */
async function drawer(stock, payload) {
  const sc = stock.screener || {};
  const topics = await resolveTicker(payload.briefing, "stock_topics", stock.ticker);
  const coverage = await loadCoverage(stock.ticker);

  const rows = [
    ["Price", stock.price ?? "—"],
    ["Target", stock.target ?? "—"],
    ["Upside", pct(stock.growth_pct)],
    ["P/E", sc.pe_ratio ?? "—"],
    ["ROCE", sc.roce !== undefined ? `${sc.roce}%` : "—"],
    ["Turnover", sc.advt_cr ? `${crore(sc.advt_cr)}/day (${sc.liquidity_band ?? "unknown"})` : "—"],
    [
      "Delivery",
      sc.deliv_pct !== undefined && sc.deliv_pct !== null
        ? `${sc.deliv_pct}% of last session (${sc.delivery_band ?? "unknown"})`
        : "—",
    ],
  ];

  return el(
    "div",
    { class: "drawer" },
    el("h3", { class: "drawer-title" }, `${stock.name || stock.ticker}`),
    el(
      "dl",
      { class: "drawer-facts" },
      rows.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, String(v))]),
    ),
    topics?.length
      ? el(
          "div",
          { class: "drawer-section" },
          el("h4", {}, "Topics"),
          el("ul", {}, topics.slice(0, 5).map((t) => el("li", {}, t.topic || t.title || String(t)))),
        )
      : null,
    coverage?.length
      ? el(
          "div",
          { class: "drawer-section" },
          el("h4", {}, `Coverage (${coverage.length})`),
          el(
            "ul",
            {},
            coverage.slice(0, 6).map((c) => el("li", {}, c.headline || c.title || "")),
          ),
        )
      : null,
  );
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const all = flatten(payload?.watchlist);
  const active = filters.read(route);
  const thesisByTicker = filters.thesisIndex(b);
  const rows = filters.applyHoldings(all, active, { thesisByTicker });
  const params = (route && route.params) || {};
  const sectors = Object.keys(payload?.watchlist || {}).sort();

  // Grouped by delivery band, one dataset each, so the legend names every
  // colour on screen. These are the reserved STATUS roles rather than
  // categorical hues, which is correct — a band is an ordered judgement about
  // a holding, not an identity — and status colour never travels without its
  // label.
  //
  // trade-to-trade is `warning` and not `good` on purpose: delivery is
  // compulsory in that segment, so a high figure there is a surveillance rule
  // rather than evidence of real buyers, and colouring it like delivery-led
  // would manufacture a bullish signal out of a trading restriction.
  const BAND_SERIES = [
    { band: "delivery-led", label: "Delivery-led", status: "good" },
    { band: "mixed", label: "Mixed", status: "serious" },
    { band: "churn", label: "Churn", status: "critical" },
    { band: "trade-to-trade", label: "Trade-to-trade", status: "warning" },
    { band: null, label: "Band not reported", status: "unknown" },
  ];

  const plotted = rows
    .map((s) => {
      const sc = s.screener || {};
      const x = num(sc.advt_cr);
      const y = num(sc.deliv_pct);
      return x !== null && y !== null
        ? { x: Number(x.toFixed(1)), y: Number(y.toFixed(1)), label: s.ticker, band: sc.delivery_band }
        : null;
    })
    .filter(Boolean);

  const known = new Set(BAND_SERIES.map((s) => s.band).filter(Boolean));
  const series = BAND_SERIES.map((s) => ({
    label: s.label,
    status: s.status,
    points: plotted.filter((p) =>
      s.band === null ? !p.band || !known.has(p.band) : p.band === s.band,
    ),
  }));

  const filtered = filters.activeCount(active) > 0;

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Holdings"),
      el(
        "p",
        { class: "view-sub" },
        filtered
          ? `${rows.length} of ${all.length} holdings`
          : `${all.length} holdings across ${sectors.length} sectors`,
      ),
    ),

    filterBar({
      view: "holdings",
      route,
      filters: active,
      fields: ["q", "sector", "thesis", "band"],
      sectors,
      summary: plotted.length ? `${plotted.length} plotted` : "",
    }),

    plotted.length
      ? panel(
          "Delivery against turnover",
          "Turnover counts every share that changed hands; delivery counts the " +
            "ones that settled. A name high on the x-axis and low on the y traded " +
            "heavily and delivered little — deep by turnover, few real buyers. " +
            "Holdings missing either figure are absent from the plot rather than " +
            "drawn at zero, so the count above may be lower than the table's.",
          chartFrame("chart-delivery", 330),
        )
      : null,

    panel(
      filtered ? "Matching holdings" : "All holdings",
      null,
      dataTable(
        rows,
        [
          {
            key: "ticker",
            label: "Stock",
            render: (r) => tickerLink(r.ticker, "holdings", params),
          },
          { key: "name", label: "Name" },
          { key: "sector", label: "Sector", render: (r) => String(r.sector).replace(/_/g, " ") },
          { key: "price", label: "Price", numeric: true },
          { key: "growth_pct", label: "Upside", numeric: true, render: (r) => pct(r.growth_pct) },
          {
            key: "advt_cr",
            label: "Turnover",
            numeric: true,
            sortValue: (r) => r.screener?.advt_cr,
            render: (r) => crore(r.screener?.advt_cr),
          },
          {
            key: "deliv_pct",
            label: "Delivery",
            numeric: true,
            sortValue: (r) => r.screener?.deliv_pct,
            render: (r) => {
              const d = num(r.screener?.deliv_pct);
              if (d === null) return "—";
              const band = r.screener?.delivery_band;
              // Direct label, always. The relief rule from the palette
              // validation: a mark whose hue is sub-3:1 must carry text.
              return el(
                "span",
                { class: `band-${band || "unknown"}` },
                `${d.toFixed(0)}%${band === "churn" ? " churn" : ""}`,
              );
            },
          },
        ],
        {
          focus: route?.focus,
          view: "holdings",
          route,
          empty: filtered ? filteredEmpty("holdings", params, "holdings") : "No holdings loaded.",
        },
      ),
    ),

    el("div", { id: "holding-drawer" }),
  );

  if (plotted.length) {
    charts.scatter(document.getElementById("chart-delivery"), {
      series,
      xLabel: "₹ Cr traded/day",
      yLabel: "% delivered",
    });
  }

  if (route?.focus) {
    const stock = all.find((s) => String(s.ticker).toUpperCase() === route.focus);
    if (stock) {
      const host = document.getElementById("holding-drawer");
      mount(host, await drawer(stock, payload));
      host.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }
}

export { BANDS, bandIndex };
