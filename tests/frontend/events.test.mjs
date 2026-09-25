// Tests for how a classified event's size and counterparty are rendered.
//
// The rule under test is the one the Python side keeps: an unmeasured size is
// ABSENT, and absent renders as nothing. A dash or a zero would read as
// "sized, and small" — the exact confusion analysis/materiality.py exists to
// prevent, reintroduced one layer later.

import { test } from "node:test";
import assert from "node:assert/strict";

import { sizeLabel } from "../../src/core/format.js";
import { eventDetail } from "../../src/views/flow.js";

test("sizeLabel states the share and the band", () => {
  assert.equal(sizeLabel(3.76, "minor"), "3.8% of revenue · minor");
  assert.equal(sizeLabel(64.94, "transformative"), "65% of revenue · transformative");
});

test("sizeLabel renders nothing for an unmeasured size", () => {
  assert.equal(sizeLabel(null, "unknown"), "");
  assert.equal(sizeLabel(undefined), "");
});

test("an order win shows its amount and its share of the holding's revenue", () => {
  const detail = eventDetail({
    event_type: "order_win",
    certainty: "completed",
    amount_cr: 1081,
    materiality: { BEL: { pct_of_revenue: 3.76, band: "minor" } },
  });
  assert.match(detail, /3\.8% of BEL revenue · minor/);
  assert.match(detail, /₹/);
  // Completed is the default state and says nothing, so it is not printed.
  assert.doesNotMatch(detail, /completed/);
});

test("a tie-up names its counterparty and keeps its certainty visible", () => {
  assert.equal(
    eventDetail({
      event_type: "tie_up",
      certainty: "announced",
      counterparties: ["Kaga Electronics"],
    }),
    "with Kaga Electronics · announced",
  );
});

test("an event with nothing measured renders no detail at all", () => {
  // Not "₹— Cr", not "0% of revenue": the JV guard declined to size this,
  // and that is "not known", which is shown as silence.
  assert.equal(
    eventDetail({ event_type: "tie_up", certainty: "completed", counterparties: [] }),
    "",
  );
});

test("an event only the LLM found says so", () => {
  assert.match(
    eventDetail({ event_type: "acquisition", certainty: "completed", reader: "llm" }),
    /LLM only · unverified/,
  );
});

test("agreement and disagreement between readers are both visible", () => {
  assert.equal(eventDetail({ event_type: "order_win", corroborated: true }), "corroborated");
  assert.equal(
    eventDetail({
      event_type: "tie_up",
      corroborated: false,
      llm_reading: { event_type: "order_win", actors: [] },
    }),
    "LLM read it as order win",
  );
});

test("an event about a holding states its evidence", () => {
  const base = { event_type: "order_win", actors: ["SUZLON"] };
  assert.match(eventDetail({ ...base, confirmation: { source: "NSE" } }), /confirmed by NSE filing/);
  assert.match(eventDetail({ ...base, reports: 3 }), /3 outlets/);
  assert.match(eventDetail({ ...base, reports: 1 }), /single report/);
});
