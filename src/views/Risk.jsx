// Risk — thesis health, warnings, and the standing conditions behind them.
//
// Ordering follows analysis/thesis.thesis_health_sorted: Broken, Weakening,
// Intact, then ticker. The ticker tiebreak matters — without it, which rows
// survive a truncation depends on dict insertion order.

import { thesisStatus } from "../core/format.js";
import { Panel, DataTable, TickerLink, StatusPill } from "../components/ui.jsx";
import { Chart } from "../components/Chart.jsx";

const ORDER = { Broken: 0, Weakening: 1, Intact: 2 };

export function Risk({ payload, route }) {
  const b = payload?.briefing || {};
  const health = Object.values(b.thesis_health || {}).filter(Boolean);
  health.sort(
    (a, c) =>
      (ORDER[a.status] ?? 9) - (ORDER[c.status] ?? 9) ||
      String(a.ticker).localeCompare(String(c.ticker)),
  );

  const counts = { Broken: 0, Weakening: 0, Intact: 0 };
  for (const h of health) if (h.status in counts) counts[h.status] += 1;

  return (
    <>
      <header class="view-head">
        <h2 class="view-title">Risk</h2>
        <p class="view-sub">
          {counts.Broken} broken · {counts.Weakening} weakening · {counts.Intact} intact
        </p>
      </header>

      <Panel
        title="Thesis health"
        note="A thesis moves off Intact only when this cycle's evidence contradicts the original catalyst — not on price noise."
      >
        <Chart
          kind="statusBand"
          height={90}
          caption={`${counts.Broken} broken, ${counts.Weakening} weakening, ${counts.Intact} intact`}
          spec={{
            segments: [
              { label: "Broken", value: counts.Broken, status: "critical" },
              { label: "Weakening", value: counts.Weakening, status: "serious" },
              { label: "Intact", value: counts.Intact, status: "good" },
            ],
          }}
        />
        <DataTable
          rows={health}
          focus={route?.focus}
          empty="No thesis grades this run."
          columns={[
            { key: "ticker", label: "Stock", render: (r) => <TickerLink ticker={r.ticker} /> },
            { key: "status", label: "Status", render: (r) => <StatusPill status={r.status} role={thesisStatus(r.status)} /> },
            { key: "reasons", label: "Why", render: (r) => (r.reasons || []).join("; ") || "—" },
          ]}
        />
      </Panel>

      <Panel
        title="New and escalated"
        note="Only warnings that appeared for the first time or got worse. The rest are standing conditions, collapsed below."
      >
        <DataTable
          rows={b.early_warnings || []}
          focus={route?.focus}
          empty="Nothing new or escalated."
          columns={[
            { key: "ticker", label: "Stock", render: (r) => <TickerLink ticker={r.ticker} /> },
            { key: "severity", label: "Severity" },
            { key: "status", label: "Change" },
            { key: "signal", label: "Signal" },
          ]}
        />
      </Panel>

      <Panel
        title="Standing conditions"
        note={'Unchanged since last run, grouped. "46 holdings carry valuation flags" is a portfolio characteristic, not 46 decisions.'}
      >
        <DataTable
          rows={b.warning_summary || []}
          empty="No standing conditions."
          columns={[
            { key: "category", label: "Category" },
            { key: "severity", label: "Severity" },
            { key: "count", label: "Holdings", numeric: true },
            { key: "tickers", label: "Which", render: (r) => (r.tickers || []).join(", ") },
          ]}
        />
      </Panel>
    </>
  );
}
