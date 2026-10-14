// A holding's data completeness, field by field (src/core/completeness.js).

import { test } from "node:test";
import assert from "node:assert/strict";

import { completeness, describeCompleteness, fieldStates, FIELDS, STATES } from "../../src/core/completeness.js";

const full = () => ({
  ticker: "HAL",
  price: "4210.50",
  screener: {
    market_cap: 281000,
    pe_ratio: 38.2,
    roce: 31.2,
    roe: 24,
    q_sales: 7044,
    q_opm: 22,
    q_eps: 18.4,
    revenue_ttm_growth_pct: 12.1,
    promoter_pct: 71.6,
    advt_cr: 512,
    deliv_pct: 48,
    week52_low: 3046,
    ttm_eps: 80.2,
  },
});

test("a holding with every field is whole and says nothing more", () => {
  const c = completeness(full());
  assert.equal(c.pct, 100);
  assert.equal(c.fresh.length, FIELDS.length);
  assert.deepEqual([c.missing, c.kept, c.notApplicable], [[], [], []]);
});

test("a failed Screener fetch reads as Screener's fields, missing", () => {
  // As SCHNEIDER, PAGEIND and RELAXO read on 14 Oct.
  const s = full();
  for (const k of ["market_cap", "pe_ratio", "roce", "roe", "q_sales", "q_opm", "q_eps", "revenue_ttm_growth_pct"]) {
    delete s.screener[k];
  }
  const c = completeness(s);
  assert.equal(c.pct, 38);
  assert.deepEqual(
    c.missing.map((f) => f.key),
    ["market_cap", "pe_ratio", "roce", "roe", "q_sales", "q_opm", "q_eps", "revenue_ttm_growth_pct"],
  );
  assert.equal(c.missing[0].source, "Screener");
  assert.match(describeCompleteness(c), /^Missing: Market cap \(Screener\), P\/E \(Screener\)/);
});

test("a lender's financing margin is its quarterly margin", () => {
  const s = full();
  delete s.screener.q_opm;
  s.screener.q_fin_margin = 14;
  assert.equal(completeness(s).pct, 100);
  s._stale_fields = { q_fin_margin: "2026-10-12" };
  assert.deepEqual(
    completeness(s).kept.map((f) => [f.key, f.since]),
    [["q_opm", "2026-10-12"]],
  );
});

test("a value kept from an earlier run counts, and says from when", () => {
  const s = full();
  s._stale_fields = { roce: "2026-10-12", price: "2026-10-13" };
  const c = completeness(s);
  assert.equal(c.pct, 100);
  assert.deepEqual(
    c.kept.map((f) => [f.key, f.since]),
    [
      ["price", "2026-10-13"],
      ["roce", "2026-10-12"],
    ],
  );
  assert.equal(
    describeCompleteness(c),
    "LKG cached: Price (Yahoo, fetched 2026-10-13), ROCE (Screener, fetched 2026-10-12). Live: 11 fields",
  );
});

test("nothing to report is not missing", () => {
  // ITC has no promoter group; a loss-making company has no P/E.
  const s = full();
  delete s.screener.promoter_pct;
  s.screener.fii_pct = 40.1;
  delete s.screener.pe_ratio;
  s.screener.ttm_eps = -3.2;
  delete s.screener.deliv_pct;
  const c = completeness(s);
  assert.deepEqual(
    c.notApplicable.map((f) => [f.key, f.why]),
    [
      ["pe_ratio", "a loss over the last four quarters"],
      ["promoter_pct", "no promoter group"],
    ],
  );
  // Delivery is missing; the others are out of the count, not against it.
  assert.deepEqual(c.missing.map((f) => f.key), ["deliv_pct"]);
  assert.equal(c.pct, Math.round((100 * 10) / 11));
  assert.equal(
    describeCompleteness(c),
    "Missing: Delivery % (NSE). Live: 10 fields. Not applicable: P/E, a loss over the last four quarters; Promoter holding, no promoter group",
  );
});

test("an empty or absent holding does not throw", () => {
  assert.equal(completeness({}).missing.length, FIELDS.length);
  assert.equal(completeness(null).pct, 0);
});

test("the inspector names three states: live, LKG cached with source and date, missing", () => {
  const s = full();
  s._stale_fields = { roce: "2026-10-12" };
  delete s.screener.deliv_pct;
  const groups = fieldStates(completeness(s), (d) => `day ${d}`);
  assert.deepEqual(
    groups.map((g) => [g.state, g.label, g.role, g.fields.length]),
    [
      ["live", "Live", "good", 11],
      ["kept", "LKG cached", "warning", 1],
      ["missing", "Missing", "serious", 1],
    ],
  );
  assert.equal(groups[1].fields[0].text, "ROCE (Screener, fetched day 2026-10-12)");
  assert.equal(groups[2].fields[0].text, "Delivery % (NSE)");
  assert.equal(groups[0].fields[0].text, "Price (Yahoo)");
  assert.match(STATES.kept.means, /^Last known good/);
});

test("a lender's kept financing margin is a cached quarterly margin", () => {
  const s = full();
  delete s.screener.q_opm;
  s.screener.q_fin_margin = 14;
  s._stale_fields = { q_fin_margin: "2026-10-12" };
  const [, kept] = fieldStates(completeness(s));
  assert.deepEqual(kept.fields.map((f) => f.text), ["Quarterly margin (Screener, fetched 2026-10-12)"]);
});
