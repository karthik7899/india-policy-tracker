// The thesis check in the dashboard: the drawer's summary line and the Flow
// view's policy rows. Both keep "not checked" apart from "nothing found".

import { test } from "node:test";
import assert from "node:assert/strict";

import { thesisSummary } from "../../src/views/holdings.js";
import { policyDetail } from "../../src/views/flow.js";

test("a placeholder thesis says there is nothing to check", () => {
  const s = thesisSummary(
    "Auto-discovered via media radar. Catalyst: Policy tailwinds in the fmcg segment.",
    undefined,
  );
  assert.match(s, /No written thesis/);
});

test("a written thesis with no headlines says so, not 'no challenges'", () => {
  assert.equal(thesisSummary("Debt-free wind leader.", undefined), "No attributed headlines to check this cycle.");
});

test("the summary counts what was read, unread, challenged and supported", () => {
  const s = thesisSummary("Debt-free wind leader.", {
    read: 5,
    unread: 2,
    challenged: [{}],
    supported: [{}, {}],
  });
  assert.equal(s, "5 headline(s) read against it · 2 not yet read · 1 challenge(s) · 2 support(s)");
});

test("a policy row names its sectors, status and state, and says who read it", () => {
  const s = policyDetail({
    effects: [
      { sector: "clean_energy", direction: "tailwind" },
      { sector: "fmcg", direction: "headwind" },
    ],
    status: "in_force",
    state: "Gujarat",
  });
  assert.equal(s, "▲ Clean Energy, ▼ Fmcg · in force · Gujarat government · LLM reading");
});

test("a central measure carries no state", () => {
  const s = policyDetail({ effects: [{ sector: "clean_energy", direction: "mixed" }], status: "proposed" });
  assert.equal(s, "◆ Clean Energy · proposed · LLM reading");
});

import { trackSummary } from "../../src/views/overview.js";

test("the track summary counts beats, exits and index comparisons", () => {
  const s = trackSummary({
    min_age_days: 30,
    decisions: [{}],
    summary: { n: 4, beat_nifty: 2, median_vs_nifty_pct: 5, exited: 1, with_index: 1, beat_index: 0 },
  });
  assert.equal(
    s,
    "2 of 4 beat the Nifty 50 · median +5.0 pts · 1 since exited, still counted · 0 of 1 ahead of their sector index",
  );
});

test("a young ledger says it is too early rather than showing zeros", () => {
  assert.equal(
    trackSummary({ min_age_days: 30, decisions: [{}], summary: { n: 0, too_recent: 5 } }),
    "No pick is 30 days old yet (5 younger).",
  );
  assert.equal(trackSummary({ decisions: [] }), "");
});

test("the track summary names repeat picks and missing sector indices", () => {
  const s = trackSummary({
    decisions: [{}],
    summary: { n: 27, stocks: 26, beat_nifty: 22, median_vs_nifty_pct: 12.4, index_unmeasured: 14 },
  });
  assert.equal(
    s,
    "22 of 27 (26 stocks) beat the Nifty 50 \u00b7 median +12.4 pts \u00b7 sector index unavailable for 14",
  );
});
