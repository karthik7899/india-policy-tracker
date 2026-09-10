// Holdings — the book, and the liquidity question about it.
//
// The chart is delivery against turnover, and it is a SCATTER on purpose: the
// question is whether a name that looks liquid actually settles, which is a
// relationship between two measures. A two-y-axis bar is the form that gets
// this wrong, and it is the most misread chart there is.

import { num, crore, pct } from "../core/format.js";
import { useTickerSidecar, useCoverage } from "../hooks.js";
import { statusColour } from "../charts/palette.js";
import { Panel, DataTable, TickerLink, Async } from "../components/ui.jsx";
import { Chart } from "../components/Chart.jsx";

function flatten(watchlist) {
  const out = [];
  for (const [sector, stocks] of Object.entries(watchlist || {})) {
    for (const s of stocks || []) if (s?.ticker) out.push({ ...s, sector });
  }
  return out;
}

function Drawer({ stock, briefing }) {
  const topics = useTickerSidecar(briefing, "stock_topics", stock.ticker);
  const coverage = useCoverage(stock.ticker);
  const sc = stock.screener || {};

  const facts = [
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

  return (
    <div class="drawer">
      <h3 class="drawer-title">{stock.name || stock.ticker}</h3>
      <dl class="drawer-facts">
        {facts.map(([k, v]) => (
          <>
            <dt key={`${k}-t`}>{k}</dt>
            <dd key={`${k}-d`}>{String(v)}</dd>
          </>
        ))}
      </dl>
      <div class="drawer-section">
        <h4>Topics</h4>
        <Async state={topics} empty="No topics for this holding.">
          {(items) => (
            <ul>
              {items.slice(0, 5).map((t, i) => (
                <li key={i}>{t.topic || t.title || String(t)}</li>
              ))}
            </ul>
          )}
        </Async>
      </div>
      <div class="drawer-section">
        <h4>Coverage</h4>
        <Async state={coverage} empty="No news attributed to this holding.">
          {(items) => (
            <ul>
              {items.slice(0, 6).map((c, i) => (
                <li key={i}>{c.headline || c.title || ""}</li>
              ))}
            </ul>
          )}
        </Async>
      </div>
    </div>
  );
}

export function Holdings({ payload, route }) {
  const all = flatten(payload?.watchlist);
  const sector = route?.params?.sector || null;
  const rows = sector ? all.filter((s) => s.sector === sector) : all;
  const focused = route?.focus ? all.find((s) => String(s.ticker).toUpperCase() === route.focus) : null;

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

  return (
    <>
      <header class="view-head">
        <h2 class="view-title">Holdings</h2>
        <p class="view-sub">
          {sector
            ? `${rows.length} in ${sector.replace(/_/g, " ")}`
            : `${rows.length} holdings across ${Object.keys(payload?.watchlist || {}).length} sectors`}
        </p>
      </header>

      {points.length > 0 && (
        <Panel
          title="Delivery against turnover"
          note="Turnover counts every share that changed hands; delivery counts the ones that settled. A name far right and low traded heavily and delivered little — deep by turnover, few real buyers."
        >
          <Chart
            kind="scatter"
            height={300}
            caption={`Delivery percentage against daily traded value for ${points.length} holdings`}
            spec={{
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
            }}
          />
        </Panel>
      )}

      <Panel title={sector ? "In this sector" : "All holdings"}>
        <DataTable
          rows={rows}
          focus={route?.focus}
          empty="No holdings match."
          columns={[
            { key: "ticker", label: "Stock", render: (r) => <TickerLink ticker={r.ticker} /> },
            { key: "name", label: "Name" },
            { key: "sector", label: "Sector", render: (r) => String(r.sector).replace(/_/g, " ") },
            { key: "price", label: "Price", numeric: true },
            { key: "growth_pct", label: "Upside", numeric: true, render: (r) => pct(r.growth_pct) },
            { key: "advt", label: "Turnover", numeric: true, render: (r) => crore(r.screener?.advt_cr) },
            {
              key: "deliv",
              label: "Delivery",
              numeric: true,
              render: (r) => {
                const d = num(r.screener?.deliv_pct);
                if (d === null) return "—";
                const band = r.screener?.delivery_band;
                // Direct label, always — the relief rule from palette validation.
                return (
                  <span class={`band-${band || "unknown"}`}>
                    {d.toFixed(0)}%{band === "churn" ? " churn" : ""}
                  </span>
                );
              },
            },
          ]}
        />
      </Panel>

      {focused && <Drawer stock={focused} briefing={payload.briefing} />}
    </>
  );
}
