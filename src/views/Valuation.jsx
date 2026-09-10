// Valuation — one view, four lenses.

import { num, pct, plain } from "../core/format.js";
import { href } from "../core/router.js";
import { useSidecar } from "../hooks.js";
import { Panel, DataTable, TickerLink, Async } from "../components/ui.jsx";
import { Chart } from "../components/Chart.jsx";

/**
 * Each sector's P/E against the median of all sectors.
 *
 * sector_valuation carries median_pe and no comparison figure, so the baseline
 * is derived here. Named "vs all sectors" rather than "vs peers" deliberately:
 * a sector's true industry peer group is a different thing, and this payload
 * does not carry it.
 */
function sectorPremium(rows) {
  const withPE = (rows || []).map((r) => ({ ...r, _pe: num(r.median_pe) })).filter((r) => r._pe > 0);
  if (withPE.length < 2) return [];
  const sorted = withPE.map((r) => r._pe).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  return withPE.map((r) => ({ ...r, _v: ((r._pe - median) / median) * 100 })).sort((a, c) => c._v - a._v);
}

const LENSES = [
  ["sector", "Sector P/E"],
  ["graham", "Margin of safety"],
  ["buffett", "Owner earnings"],
  ["scoring", "Score"],
];

function BuffettLens({ briefing, focus }) {
  const state = useSidecar(briefing, "buffett_valuation");
  return (
    <Panel title="Owner earnings" note="Fetched on demand — 59 KB that most visits never open.">
      <Async state={state} empty="No owner-earnings rows.">
        {(rows) => (
          <DataTable
            rows={rows}
            focus={focus}
            columns={[
              { key: "ticker", label: "Stock", render: (r) => <TickerLink ticker={r.ticker} /> },
              { key: "owner_earnings", label: "Owner earnings", numeric: true, render: (r) => plain(r.owner_earnings) },
              { key: "moat_status", label: "Moat" },
            ]}
          />
        )}
      </Async>
    </Panel>
  );
}

export function Valuation({ payload, route }) {
  const b = payload?.briefing || {};
  const lens = route?.params?.lens || "sector";
  const params = route?.params || {};

  let body = null;

  if (lens === "sector") {
    const rows = sectorPremium(b.sector_valuation);
    body = (
      <Panel
        title="Sector P/E against the all-sector median"
        note="Blue above the median, red below, gray at parity — the sign is the whole question, and a one-hue ramp would hide it. Compared against the median of all sectors, not each sector's true industry peer group, which this payload does not carry."
      >
        {rows.length > 0 && (
          <Chart
            kind="divergingBar"
            height={Math.max(220, rows.length * 24)}
            caption={`Each sector's median P/E as a percentage above or below the all-sector median`}
            spec={{
              labels: rows.map((r) => r.label || String(r.sector || "").replace(/_/g, " ")),
              values: rows.map((r) => Number(r._v.toFixed(1))),
              suffix: "%",
            }}
          />
        )}
        <DataTable
          rows={rows}
          empty="No sector valuation this run."
          columns={[
            { key: "sector", label: "Sector", render: (r) => r.label || String(r.sector || "").replace(/_/g, " ") },
            { key: "median_pe", label: "Median P/E", numeric: true, render: (r) => plain(r.median_pe, 1) },
            { key: "_v", label: "vs all sectors", numeric: true, render: (r) => pct(r._v) },
            { key: "stock_count", label: "Holdings", numeric: true },
          ]}
        />
      </Panel>
    );
  } else if (lens === "graham") {
    // margin_of_safety carries price and intrinsic value but no margin, so it
    // is derived. Null when either input is unreadable — not zero.
    const rows = (b.margin_of_safety || []).map((r) => {
      const price = num(r.price);
      const value = num(r.graham_intrinsic_value);
      return { ...r, _margin: price && value ? ((value - price) / price) * 100 : null };
    });
    body = (
      <Panel
        title="Margin of safety"
        note="Graham intrinsic value against price. A holding is here only when both inputs were readable — an unreadable one is absent, not zero."
      >
        <DataTable
          rows={rows}
          focus={route?.focus}
          empty="No holding cleared the margin screen."
          columns={[
            { key: "ticker", label: "Stock", render: (r) => <TickerLink ticker={r.ticker} /> },
            { key: "price", label: "Price", numeric: true },
            { key: "graham_intrinsic_value", label: "Intrinsic", numeric: true, render: (r) => plain(r.graham_intrinsic_value) },
            { key: "_margin", label: "Margin", numeric: true, render: (r) => pct(r._margin) },
            { key: "is_bargain", label: "Bargain", render: (r) => (r.is_bargain ? "yes" : "—") },
          ]}
        />
      </Panel>
    );
  } else if (lens === "buffett") {
    body = <BuffettLens briefing={b} focus={route?.focus} />;
  } else {
    const rows = Object.values(payload?.watchlist || {})
      .flat()
      .filter((s) => s?.score)
      .map((s) => ({ ...s, _score: num(s.score.overall_score) }))
      .sort((a, c) => (c._score ?? -99) - (a._score ?? -99));
    body = (
      <Panel
        title="Score"
        note="Never a single opaque total: the reasons and risks that produced it are the row, not a tooltip."
      >
        <DataTable
          rows={rows}
          focus={route?.focus}
          empty="Nothing scored."
          columns={[
            { key: "ticker", label: "Stock", render: (r) => <TickerLink ticker={r.ticker} /> },
            { key: "_score", label: "Score", numeric: true },
            { key: "confidence", label: "Data", render: (r) => r.score?.confidence ?? "—" },
            { key: "reasons", label: "For", render: (r) => <span class="cell-good">{(r.score?.reasons || []).slice(0, 2).join("; ") || "—"}</span> },
            { key: "risks", label: "Against", render: (r) => <span class="cell-bad">{(r.score?.risks || []).slice(0, 2).join("; ") || "—"}</span> },
          ]}
        />
      </Panel>
    );
  }

  return (
    <>
      <header class="view-head">
        <h2 class="view-title">Valuation</h2>
        <p class="view-sub">What it is worth, and against what.</p>
      </header>
      <nav class="lens-nav">
        {LENSES.map(([key, label]) => (
          <a key={key} class={`lens${key === lens ? " lens-active" : ""}`} href={href("valuation", { ...params, lens: key })}>
            {label}
          </a>
        ))}
      </nav>
      {body}
    </>
  );
}
