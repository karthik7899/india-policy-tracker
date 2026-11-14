// The shared research adapter keeps the existing payload contract intact.

import { test } from "node:test";
import assert from "node:assert/strict";

import { buildResearchContext, RESEARCH_SIDECARS } from "../../src/core/research.js";

test("company index flattens sectors without mutating the source rows", () => {
  const alpha = { ticker: "abc", name: "Alpha" };
  const payload = {
    last_updated: "2026-11-13 10:00:00",
    sectors: { semiconductors_equipment: { label: "Semiconductors" } },
    watchlist: {
      semiconductors_equipment: [alpha, { name: "No ticker" }, null],
      clean_energy: [{ ticker: "XYZ", name: "Xylo" }],
    },
    briefing: {},
  };
  const context = buildResearchContext(payload);

  assert.equal(context.asOf, payload.last_updated);
  assert.deepEqual(context.companies.map((c) => c.ticker), ["ABC", "XYZ"]);
  assert.equal(context.companies[0].sectorLabel, "Semiconductors");
  assert.equal(context.companiesByTicker.get("ABC").name, "Alpha");
  assert.deepEqual(context.companiesBySector.clean_energy.map((c) => c.ticker), ["XYZ"]);
  assert.equal(alpha.ticker, "abc");
});

test("sector news and briefing fields preserve absent versus empty", () => {
  const context = buildResearchContext({
    watchlist: { fmcg: [], banking_financials: [] },
    briefing: { fmcg: [], policy_balance: {}, emerging_competitors: [] },
  });

  assert.deepEqual(context.newsBySector.fmcg, []);
  assert.equal(context.newsBySector.banking_financials, null);
  assert.deepEqual(context.insights.policyBalance, {});
  assert.deepEqual(context.insights.emergingCompetitors, []);
  assert.equal(context.insights.readThroughs, null);
});

test("sidecar values are passed through without changing their shape", () => {
  const empty = [];
  const context = buildResearchContext({ briefing: {} }, { event_calendar: empty, results: null });
  assert.equal(context.sidecars.event_calendar, empty);
  assert.equal(context.sidecars.results, null);
  assert.ok(RESEARCH_SIDECARS.includes("event_calendar"));
  assert.ok(RESEARCH_SIDECARS.includes("institutional_activity"));
});
