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
