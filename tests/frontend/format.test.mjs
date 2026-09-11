// Tests for the pure logic the views depend on.
//
// These replace app.test.js and formatGrowthBadge.test.js, which tested the
// same two formatters by reading app.js off disk and eval'ing it in a vm —
// the only way to reach a function inside a 3,706-line script with no module
// boundaries. Real exports make that unnecessary.
//
// The coercion cases matter more than they look. The pipeline stores numbers
// as display strings ("482.95", "+23.0%", "1,840.00") because that is the wire
// format models/stock.py renders back to, so every view coerces before it
// compares. Getting "N/A" wrong here means a sort puts unreadable rows at the
// top as if they were zero.

import { test } from "node:test";
import assert from "node:assert/strict";

import { num, pct, crore, plain, bandIndex, thesisStatus } from "../../src/core/format.js";
import { parse, href } from "../../src/core/router.js";

// --- numeric coercion, mirroring utils.to_float ---------------------------

test("num accepts every format the pipeline actually produces", () => {
  assert.equal(num(10), 10);
  assert.equal(num(12.5), 12.5);
  assert.equal(num("482.95"), 482.95);
  assert.equal(num("1,840.00"), 1840);
  assert.equal(num("+23.0%"), 23);
  assert.equal(num("-9.2%"), -9.2);
  assert.equal(num(" 42 "), 42);
});

test("num returns null for unreadable values, never zero", () => {
  // The distinction the whole product turns on: "we could not read it" is not
  // "it is zero". A sort or a chart that treats them the same invents data.
  for (const v of [null, undefined, "", "   ", "N/A", "NA", "-", "—", "NONE", "n/a", "invalid"]) {
    assert.equal(num(v), null, `expected null for ${JSON.stringify(v)}`);
  }
});

test("num rejects booleans rather than coercing them to 1/0", () => {
  assert.equal(num(true), null);
  assert.equal(num(false), null);
});

test("num rejects non-finite numbers", () => {
  assert.equal(num(Infinity), null);
  assert.equal(num(NaN), null);
});

// --- display ---------------------------------------------------------------

test("pct always carries its sign, because the sign is the information", () => {
  assert.equal(pct(23), "+23.0%");
  assert.equal(pct(-9.2), "-9.2%");
  assert.equal(pct(0), "0.0%");
  assert.equal(pct(null), "—");
});

test("crore scales to the magnitude a reader needs", () => {
  assert.equal(crore(0.42), "₹0.42 Cr");
  assert.equal(crore(1262), "₹1.3k Cr");
  assert.equal(crore(null), "—");
});

test("plain shows an em dash rather than NaN for unreadable input", () => {
  assert.equal(plain("N/A"), "—");
  assert.equal(plain(3.14159), "3.14");
});

// --- band and status mapping ----------------------------------------------

test("liquidity bands are ordered, and trade-to-trade is off the scale", () => {
  assert.equal(bandIndex("illiquid"), 0);
  assert.equal(bandIndex("liquid"), 3);
  // Delivery is compulsory in the trade-to-trade segment, so its figure is a
  // surveillance rule rather than evidence. Placing it on the same ordinal
  // axis as a real delivery percentage would manufacture a bullish signal.
  assert.equal(bandIndex("trade-to-trade"), -1);
  assert.equal(bandIndex(undefined), -1);
});

test("weakening is serious, not warning", () => {
  // A thesis whose evidence has turned is a stronger signal than a data
  // quality nag, and the two must not share a colour.
  assert.equal(thesisStatus("Broken"), "critical");
  assert.equal(thesisStatus("Weakening"), "serious");
  assert.equal(thesisStatus("Intact"), "good");
  assert.equal(thesisStatus("nonsense"), "warning");
});

// --- routing: the mechanism behind following an entity across views -------

test("parse reads the view, focus and params out of a hash", () => {
  assert.deepEqual(parse("#/holdings?focus=hal"), {
    view: "holdings",
    focus: "HAL",
    params: { focus: "hal" },
  });
});

test("parse defaults to overview for an empty or bare hash", () => {
  assert.equal(parse("").view, "overview");
  assert.equal(parse("#").view, "overview");
  assert.equal(parse("#/").view, "overview");
});

test("focus is upper-cased so a link is case-insensitive", () => {
  assert.equal(parse("#/holdings?focus=hal").focus, "HAL");
  assert.equal(parse("#/holdings").focus, null);
});

test("href drops empty params rather than emitting focus=", () => {
  assert.equal(href("risk"), "#/risk");
  assert.equal(href("risk", { focus: null, lens: "" }), "#/risk");
  assert.equal(href("holdings", { focus: "HAL" }), "#/holdings?focus=HAL");
});

test("a route round-trips through href and parse", () => {
  const round = parse(href("valuation", { lens: "buffett", focus: "BEL" }));
  assert.equal(round.view, "valuation");
  assert.equal(round.params.lens, "buffett");
  assert.equal(round.focus, "BEL");
});
