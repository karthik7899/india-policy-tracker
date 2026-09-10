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

import { el, mount } from "../core/dom.js";
import { num, crore, pct, bandIndex, BANDS } from "../core/format.js";
import { resolveTicker, loadCoverage } from "../core/data.js";
import * as charts from "../charts/charts.js";
import { statusColour } from "../charts/palette.js";
import { dataTable, panel, chartFrame, tickerLink } from "./table.js";

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
  const all = flatten(payload?.watchlist);
  const sectorFilter = route?.params?.sector || null;
  const rows = sectorFilter ? all.filter((s) => s.sector === sectorFilter) : all;

  // One series, so the all-pairs colour cap does not apply. Points are marked
  // by delivery band using the reserved status roles, and the band name is in
  // every tooltip — colour never carries it alone.
  const points = rows
    .map((s) => {
      const sc = s.screener || {};
      const x = num(sc.advt_cr);
      const y = num(sc.deliv_pct);
      return x !== null && y !== null
        ? { x: Number(x.toFixed(1)), y: Number(y.toFixed(1)), label: s.ticker, band: sc.delivery_band }
        : null;
    })
    .filter(Boolean);

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Holdings"),
      el(
        "p",
        { class: "view-sub" },
        sectorFilter
          ? `${rows.length} in ${sectorFilter.replace(/_/g, " ")}`
          : `${rows.length} holdings across ${Object.keys(payload?.watchlist || {}).length} sectors`,
      ),
    ),

    points.length
      ? panel(
          "Delivery against turnover",
          "Turnover counts every share that changed hands; delivery counts the " +
            "ones that settled. A name high on the x-axis and low on the y traded " +
            "heavily and delivered little — deep by turnover, few real buyers.",
          chartFrame("chart-delivery", 300),
        )
      : null,

    panel(
      sectorFilter ? "In this sector" : "All holdings",
      null,
      dataTable(
        rows,
        [
          { key: "ticker", label: "Stock", render: (r) => tickerLink(r.ticker, "holdings") },
          { key: "name", label: "Name" },
          { key: "sector", label: "Sector", render: (r) => String(r.sector).replace(/_/g, " ") },
          { key: "price", label: "Price", numeric: true },
          { key: "growth_pct", label: "Upside", numeric: true, render: (r) => pct(r.growth_pct) },
          {
            key: "advt",
            label: "Turnover",
            numeric: true,
            render: (r) => crore(r.screener?.advt_cr),
          },
          {
            key: "deliv",
            label: "Delivery",
            numeric: true,
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
        { focus: route?.focus, empty: "No holdings match." },
      ),
    ),

    el("div", { id: "holding-drawer" }),
  );

  if (points.length) {
    charts.scatter(document.getElementById("chart-delivery"), {
      points,
      xLabel: "₹ Cr traded/day",
      yLabel: "% delivered",
      marker: (p) =>
        statusColour(
          p.band === "churn"
            ? "critical"
            : p.band === "trade-to-trade"
              ? "warning"
              : p.band === "delivery-led"
                ? "good"
                : "serious",
        ),
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
