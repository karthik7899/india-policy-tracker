// System — whether this run is worth trusting.
//
// The pipeline partially fails all the time: a blocked exchange, a
// rate-limited Screener, a delisted symbol. Coverage numbers are how a reader
// tells "nothing happened" from "we could not look", and those look identical
// everywhere else in the product.

import { Panel, DataTable } from "../components/ui.jsx";

export function System({ payload }) {
  const b = payload?.briefing || {};
  const holdings = Object.values(payload?.watchlist || {}).flat().filter((s) => s?.ticker);

  const rows = [
    { field: "Live price", got: holdings.filter((s) => s.price).length, of: holdings.length },
    {
      field: "Screener fundamentals",
      got: holdings.filter((s) => s.screener && Object.keys(s.screener).length).length,
      of: holdings.length,
    },
    {
      field: "Delivery percentage",
      got: holdings.filter((s) => s.screener?.deliv_pct !== undefined && s.screener?.deliv_pct !== null).length,
      of: holdings.length,
    },
    { field: "News coverage", got: Object.keys(b.coverage_count || {}).length, of: holdings.length },
  ];

  const sidecarKeys = Object.entries(b)
    .filter(([, v]) => v && typeof v === "object" && v.sidecar)
    .map(([k]) => k);

  return (
    <>
      <header class="view-head">
        <h2 class="view-title">Run health</h2>
        <p class="view-sub">Generated {payload?.last_updated || "—"}</p>
      </header>
      <Panel
        title="Coverage"
        note="A field missing for most holdings means the source refused us, not that the answer is zero. The two are different and only this view separates them."
      >
        <DataTable
          rows={rows}
          tickerKey="field"
          empty="No watchlist loaded."
          columns={[
            { key: "field", label: "Field" },
            { key: "got", label: "Holdings", numeric: true, render: (r) => `${r.got} / ${r.of}` },
            { key: "share", label: "Coverage", numeric: true, render: (r) => (r.of ? `${Math.round((100 * r.got) / r.of)}%` : "—") },
          ]}
        />
      </Panel>
      <Panel title="Payload" note="Sidecars are fetched on demand rather than shipped with the page.">
        <ul class="plain-list">
          <li>Briefing keys: {Object.keys(b).length}</li>
          <li>Sidecar keys: {sidecarKeys.join(", ") || "none"}</li>
        </ul>
      </Panel>
    </>
  );
}
