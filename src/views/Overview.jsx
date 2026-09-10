// Overview — what changed, and what to look at first.

import { num, thesisStatus } from "../core/format.js";
import { href } from "../core/router.js";
import { Panel, StatTile, DataTable, TickerLink } from "../components/ui.jsx";
import { Chart } from "../components/Chart.jsx";

export function Overview({ payload, route }) {
  const b = payload?.briefing || {};
  const health = Object.values(b.thesis_health || {});
  const counts = { Broken: 0, Weakening: 0, Intact: 0 };
  for (const h of health) if (h?.status in counts) counts[h.status] += 1;

  const growth = (b.sector_growth || [])
    .map((s) => ({ ...s, _g: num(s.median_ttm_growth_pct) }))
    .filter((s) => s._g !== null)
    .sort((a, c) => c._g - a._g);

  const warnings = b.early_warnings || [];

  return (
    <>
      <header class="view-head">
        <h2 class="view-title">Overview</h2>
        <p class="view-sub">Updated {payload?.last_updated || "—"}</p>
      </header>

      <div class="stat-row">
        <StatTile label="Holdings" value={String(health.length || "—")} detail="with a graded thesis" />
        <StatTile
          label="Thesis broken"
          value={String(counts.Broken)}
          detail="evidence contradicts the catalyst"
          tone={counts.Broken ? "critical" : null}
        />
        <StatTile
          label="Actionable warnings"
          value={String(warnings.length)}
          detail="new or escalated this run"
          tone={warnings.length ? "serious" : null}
        />
        <StatTile
          label="Sectors ranked"
          value={String(growth.length)}
          detail={growth.length ? `fastest ${growth[0].label ?? growth[0].sector ?? ""}` : ""}
        />
      </div>

      <Panel
        title="Thesis health"
        note="Part-to-whole, so one stacked bar. Status colours are reserved and every segment is named — on a light surface these hues are not allowed to carry the meaning alone."
      >
        <Chart
          kind="statusBand"
          height={90}
          caption={`${counts.Broken} broken, ${counts.Weakening} weakening, ${counts.Intact} intact`}
          spec={{
            segments: [
              { label: "Broken", value: counts.Broken, status: thesisStatus("Broken") },
              { label: "Weakening", value: counts.Weakening, status: thesisStatus("Weakening") },
              { label: "Intact", value: counts.Intact, status: thesisStatus("Intact") },
            ],
          }}
        />
      </Panel>

      <Panel
        title="Sector growth"
        note="Magnitude low to high, so a single-hue ordinal ramp rather than a colour per sector: the ranking is the message, not sector identity."
      >
        <Chart
          kind="rankedBar"
          height={Math.max(220, growth.length * 24)}
          caption={`Median trailing-twelve-month sales growth for ${growth.length} sectors, fastest first`}
          spec={{
            labels: growth.map((s) => s.label || String(s.sector || "").replace(/_/g, " ")),
            values: growth.map((s) => Number(s._g.toFixed(1))),
            suffix: "%",
            horizontal: true,
          }}
        />
      </Panel>

      <Panel title="Needs attention" note={warnings.length ? null : "Nothing new or escalated this run."}>
        <DataTable
          rows={warnings.slice(0, 12)}
          focus={route?.focus}
          empty="No actionable warnings."
          columns={[
            { key: "ticker", label: "Stock", render: (r) => <TickerLink ticker={r.ticker} view="risk" /> },
            { key: "severity", label: "Severity" },
            { key: "signal", label: "Signal" },
          ]}
        />
        <a class="more-link" href={href("risk")}>All risk signals →</a>
      </Panel>
    </>
  );
}
