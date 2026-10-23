// How a read-through says how it travels and how binding its news is.
//
// The words come from the pipeline (strength_note, from
// analysis/event_engine.STRENGTH_SAYS) so the email and the dashboard agree;
// these pin the dashboard's half, including rows written before the fields.

import { test } from "node:test";
import assert from "node:assert/strict";

import { strengthLabel, transmissionLabel } from "../../src/core/format.js";
import { readThroughMeta } from "../../src/views/company.js";

test("a transmission reads as words", () => {
  assert.equal(transmissionLabel("competitive_threat"), "competitive threat");
  assert.equal(transmissionLabel("input_shock"), "input shock");
  assert.equal(transmissionLabel(undefined), "");
});

test("a binding trigger says nothing more; a soft or rumoured one says so", () => {
  assert.equal(strengthLabel({ strength: "hard" }), "");
  assert.equal(strengthLabel({}), "");
  assert.equal(strengthLabel(null), "");
  const note = "not yet binding: an MoU, a lowest bid or an intention";
  assert.equal(strengthLabel({ strength: "soft", strength_note: note }), note);
  // The grade without the words still says what it is.
  assert.equal(strengthLabel({ strength: "soft" }), "not yet binding");
  assert.equal(strengthLabel({ strength: "reported" }), "reported, not confirmed");
});

test("the company page puts how it travels before the chain", () => {
  assert.equal(
    readThroughMeta({
      transmission: "input_shock",
      strength: "reported",
      strength_note: "reported, not confirmed",
      chain: ["copper scarcer", "copper is an input to DIACABS"],
    }),
    "input shock · reported, not confirmed: copper scarcer → copper is an input to DIACABS",
  );
  assert.equal(
    readThroughMeta({ transmission: "demand_pull", strength: "hard", chain: ["a", "b"] }),
    "demand pull: a → b",
  );
  // A row from before these fields existed still shows its chain.
  assert.equal(readThroughMeta({ chain: ["a", "b"] }), "a → b");
});

test("a row standing for several reports says how many more", async () => {
  const { moreReports } = await import("../../src/core/format.js");
  assert.equal(moreReports({ reports: 2 }), " (+1 more report)");
  assert.equal(moreReports({ reports: 4 }), " (+3 more reports)");
  assert.equal(moreReports({ reports: 1 }), "");
  assert.equal(moreReports({}), "");
  assert.equal(moreReports(null), "");
});
