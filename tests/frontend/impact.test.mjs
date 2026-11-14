import { test } from "node:test";
import assert from "node:assert/strict";

import { buildImpactRows } from "../../src/views/impact.js";

test("impact queue prioritises business warnings before market movement and fundamentals", () => {
  const payload = {
    briefing: {
      early_warnings: [
        { ticker: "B", severity: "High", signal: "Margin compression" },
        { ticker: "C", severity: "Medium", signal: "Share loss" },
      ],
    },
    watchlist: {
      aerospace_defence: [
        { ticker: "A", name: "Alpha", screener: { revenue_ttm_growth_pct: 80, roce: 40 } },
        { ticker: "B", name: "Beta", screener: { revenue_ttm_growth_pct: 5, roce: 4 } },
        { ticker: "C", name: "Gamma", screener: { revenue_ttm_growth_pct: 20, roce: 15 } },
      ],
    },
  };
  const digest = {
    companies: [
      { ticker: "A", prices: [["2026-10-12", 100], ["2026-11-09", 150]] },
      { ticker: "B", prices: [["2026-10-12", 100], ["2026-11-09", 101]] },
      { ticker: "C", prices: [["2026-10-12", 100], ["2026-11-09", 120]] },
    ],
  };
  const rows = buildImpactRows(payload, digest);
  assert.deepEqual(rows.map((row) => row.ticker), ["B", "C", "A"]);
  assert.equal(rows[0].severityRank, 2);
  assert.equal(rows[2].change4w, 50);
});

test("impact rows preserve missing data and include institutional deltas", () => {
  const payload = {
    briefing: { early_warnings: [] },
    watchlist: {
      banking_financials: [{
        ticker: "ABC",
        screener: { fii_change: -0.5, dii_change: 0.8, promoter_change: 0 },
      }],
      macro_indicators: [{ ticker: "INDEX" }],
    },
  };
  const rows = buildImpactRows(payload, {});
  assert.equal(rows.length, 1);
  assert.equal(rows[0].change4w, null);
  assert.equal(rows[0].growth, null);
  assert.equal(rows[0].fiiChange, -0.5);
  assert.equal(rows[0].diiChange, 0.8);
  assert.equal(rows[0].promoterChange, 0);
});
