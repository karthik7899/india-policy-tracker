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
    "names this company · Gujarat government · in force · ✦",
  );
  assert.match(policyMeta({ status: "proposed", date: "" }), /^central · proposed/);
});

import { changeGroups, policyRows } from "../../src/views/overview.js";
import { upsideText } from "../../src/views/holdings.js";

test("change groups keep reading order, full counts, and skip empty or first runs", () => {
  const groups = changeGroups({
    counts: { watchlist: 0, thesis: 12, events: 1, policy: 0, warnings: 0 },
    items: { thesis: [{ text: "a" }], events: [{ text: "b" }] },
  });
  assert.deepEqual(groups.map((g) => [g.key, g.count]), [["thesis", 12], ["events", 1]]);
  assert.deepEqual(changeGroups({ first_run: true, counts: { thesis: 3 } }), []);
});

test("policy rows sort by net and drop sectors with nothing", () => {
  const rows = policyRows(
    { fmcg: { tailwind: 0, headwind: 2, net: -2 }, clean_energy: { tailwind: 3, headwind: 0.5, net: 2.5 }, it: {} },
    { clean_energy: { label: "Clean Energy" } },
  );
  assert.deepEqual(rows.map((r) => [r.label, r.net]), [["Clean Energy", 2.5], ["fmcg", -2]]);
});

test("a capped upside reads as a bound, an ordinary one as a figure", () => {
  assert.equal(upsideText({ growth_pct: "-50.0%", upside_capped: "floor" }), "≤ -50.0% (capped)");
  assert.equal(upsideText({ growth_pct: "+60.0%", upside_capped: "cap" }), "≥ +60.0% (capped)");
  assert.equal(upsideText({ growth_pct: "+12.3%" }), "+12.3%");
});

import { sparkline, seriesChange } from "../../src/core/sparkline.js";
import { markers } from "../../src/views/companies.js";

const PRICES = [["2026-08-01", 100], ["2026-08-08", 110], ["2026-08-15", 105], ["2026-08-22", 120]];

test("the price line draws one dot per week and kind, escaped", () => {
  const svg = sparkline(PRICES, [
    { date: "2026-08-09", kind: "activity", label: "Order <win>" },
    { date: "2026-08-10", kind: "activity", label: "Second story" },
    { date: "2026-08-10", kind: "tailwind", label: "PLI approved" },
    { date: "2026-07-01", kind: "activity", label: "before the line" },
    { date: "2026-08-12", kind: "nonsense", label: "ignored" },
  ]);
  assert.equal((svg.match(/<circle/g) || []).length, 2);
  assert.match(svg, /Order &lt;win&gt;/);
  assert.match(svg, /Second story/);
  assert.doesNotMatch(svg, /before the line/);
  assert.match(svg, /aria-label="Weekly closes 2026-08-01 to 2026-08-22, \+20.0%"/);
});

test("too few prices draw nothing", () => {
  assert.equal(sparkline([["2026-08-01", 100]]), "");
  assert.equal(seriesChange([]), null);
  assert.equal(seriesChange(PRICES), 20);
});

test("card markers are its news and its directed policies", () => {
  const m = markers({
    activity: [{ date: "2026-08-09", text: "Order" }],
    policies: [{ date: "2026-08-10", direction: "headwind", headline: "Duty cut" }, { date: "2026-08-11", headline: "Names it" }],
  });
  assert.deepEqual(m.map((x) => x.kind), ["activity", "headwind"]);
});
