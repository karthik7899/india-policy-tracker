// The policy direction tag on sector news: shown only when the LLM reader
// gave a direction for this sector, and always with the measure's status.

import { test } from "node:test";
import assert from "node:assert/strict";

import { policyTag } from "../../src/views/holdings.js";

test("policyTag names the direction and the status", () => {
  assert.equal(policyTag({ direction: "headwind", status: "proposed" }), "▼ policy headwind (proposed)");
  assert.equal(policyTag({ direction: "tailwind", status: "in_force" }), "▲ policy tailwind (in force)");
});

test("policyTag is empty when there is no direction for this sector", () => {
  assert.equal(policyTag({ direction: null, status: "in_force" }), "");
  assert.equal(policyTag(undefined), "");
});

import { policyDetail, partnershipDetail } from "../../src/views/flow.js";

test("a policy row says how binding it is", () => {
  const row = { effects: [{ sector: "semiconductors", direction: "tailwind" }], state: "Gujarat" };
  assert.equal(
    policyDetail({ ...row, status: "in_force", strength: "hard" }, { semiconductors: { label: "Semiconductors" } }),
    "▲ Semiconductors · Hard policy, in force · Gujarat government · ✦",
  );
  // A draft is not dressed up: its strength and its status say the same.
  assert.equal(policyDetail({ ...row, status: "proposed", strength: "proposed" }), "▲ Semiconductors · proposed · Gujarat government · ✦");
});

test("a government's MoU is a soft partnership, with whose government", () => {
  const labels = { clean_energy: { label: "Clean Energy" } };
  assert.equal(
    partnershipDetail({ strength: "soft", government: "Maharashtra", sectors: ["clean_energy"], certainty: "announced" }, labels),
    "Soft partnership · Maharashtra government · Clean Energy · announced",
  );
  assert.equal(partnershipDetail({ strength: "soft", government: "Centre", sectors: [] }), "Soft partnership · Centre");
  // "Government" says only that one was named; it adds nothing to print.
  assert.equal(partnershipDetail({ strength: "soft", government: "Government" }), "Soft partnership");
});
