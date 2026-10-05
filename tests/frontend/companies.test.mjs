// The Companies view's ordering and policy wording, without a DOM.

import { test } from "node:test";
import assert from "node:assert/strict";

import { companyRows, policyMeta } from "../../src/views/companies.js";

const DIGEST = {
  companies: [
    { ticker: "A", name: "Alpha", sector: "fmcg", activity_count: 2, policy_count: 1, policies: [{ direction: "headwind" }] },
    { ticker: "B", name: "Beta", sector: "fmcg", activity_count: 1, policy_count: 2, policies: [{ direction: "tailwind" }, { direction: "tailwind" }] },
    { ticker: "Q", name: "Quiet", sector: "it", activity_count: 0, policy_count: 0, policies: [] },
  ],
};

test("recent keeps the digest's order and sets quiet holdings apart", () => {
  const { busy, quiet } = companyRows(DIGEST);
  assert.deepEqual(busy.map((c) => c.ticker), ["A", "B"]);
  assert.deepEqual(quiet.map((c) => c.ticker), ["Q"]);
});

test("support and pressure order by tailwinds and headwinds", () => {
  assert.deepEqual(companyRows(DIGEST, {}, "support").busy.map((c) => c.ticker), ["B", "A"]);
  assert.deepEqual(companyRows(DIGEST, {}, "pressure").busy.map((c) => c.ticker), ["A", "B"]);
});

test("filters apply before grouping", () => {
  assert.deepEqual(companyRows(DIGEST, { q: "beta" }).busy.map((c) => c.ticker), ["B"]);
  assert.equal(companyRows(DIGEST, { sector: "it" }).busy.length, 0);
});

test("a policy line says whose measure, how far along, and who read it", () => {
  assert.equal(
    policyMeta({ names_company: true, state: "Gujarat", status: "in_force", date: "" }),
    "names this company · Gujarat government · in force · LLM reading",
  );
  assert.match(policyMeta({ status: "proposed", date: "" }), /^central · proposed/);
});
