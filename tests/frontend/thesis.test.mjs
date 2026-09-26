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
