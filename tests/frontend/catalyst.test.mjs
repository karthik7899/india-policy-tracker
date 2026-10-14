// How settled a catalyst is, as a pill (src/core/catalyst.js).

import { test } from "node:test";
import assert from "node:assert/strict";

import { catalystPill, isHighConviction } from "../../src/core/catalyst.js";
import { normalise } from "../../src/views/flow.js";

const kind = (item) => catalystPill(item)?.kind ?? null;

test("a policy row says how binding it is", () => {
  assert.equal(kind({ effects: [], strength: "hard", status: "approved" }), "hard");
  assert.equal(kind({ effects: [], strength: "proposed", status: "proposed" }), "proposed");
  assert.equal(catalystPill({ effects: [], strength: "hard" }).label, "Hard policy");
  // A government's MoU: no measure yet.
  assert.equal(kind({ strength: "soft", government: "Gujarat" }), "soft");
});

test("a policy saved before strength was is read from its status", () => {
  // The company digest's rows, until the next run adds strength to them.
  assert.equal(kind({ measure: "", status: "in_force" }), "hard");
  assert.equal(kind({ measure: "", status: "approved" }), "hard");
  assert.equal(kind({ measure: "", status: "proposed" }), "proposed");
  // A status alone does not make a row a policy.
  assert.equal(kind({ status: "counted", event_type: "tie_up" }), null);
});

test("an order win is confirmed, or an L-1 bid, or not yet settled", () => {
  const win = { event_type: "order_win", certainty: "completed", headline: "Suzlon wins 200 MW order" };
  assert.equal(kind(win), "win");
  assert.equal(catalystPill(win).label, "Confirmed win");
  const l1 = { event_type: "order_win", certainty: "announced", phrase: "emerges l1", headline: "RVNL emerges L1 bidder" };
  assert.equal(kind(l1), "l1");
  assert.equal(catalystPill(l1).label, "L-1 (announced)");
  assert.equal(kind({ event_type: "order_win", certainty: "announced", headline: "Lowest bidder for metro line" }), "l1");
  assert.equal(kind({ event_type: "order_win", certainty: "announced", headline: "BEL set to win order" }), "announced");
  assert.equal(kind({ event_type: "order_win", certainty: "reported", headline: "BEL likely to win order" }), "reported");
  // A company's activity row: kind "order", its text and certainty.
  assert.equal(kind({ kind: "order", text: "HAL bags Rs 2,000 crore order", certainty: "completed" }), "win");
  assert.equal(kind({ kind: "order", text: "IRCON emerges L-1 for rail project" }), "l1");
  // Stage unknown (a row from before the digest recorded it): no pill.
  assert.equal(kind({ kind: "order", text: "HAL bags Rs 2,000 crore order" }), null);
});

test("other events and plain news carry no pill", () => {
  assert.equal(kind({ event_type: "tie_up", certainty: "completed" }), null);
  assert.equal(kind({ kind: "news", text: "HAL shares rise" }), null);
  assert.equal(kind(null), null);
});

test("high conviction is a hard policy or a confirmed win, nothing else", () => {
  assert.equal(isHighConviction({ effects: [], strength: "hard" }), true);
  assert.equal(isHighConviction({ event_type: "order_win", certainty: "completed", headline: "wins order" }), true);
  assert.equal(isHighConviction({ effects: [], strength: "proposed" }), false);
  assert.equal(isHighConviction({ strength: "soft" }), false);
  assert.equal(isHighConviction({ event_type: "order_win", certainty: "announced", headline: "emerges L1" }), false);
  assert.equal(isHighConviction({ kind: "news" }), false);
});

test("a Flow row carries its catalyst's pill", () => {
  const row = normalise(
    { headline: "Suzlon wins 200 MW order", event_type: "order_win", certainty: "completed", actors: ["SUZLON"], date: "2026-10-14" },
    "Market events",
    {},
  );
  assert.equal(row.pill.kind, "win");
  assert.equal(normalise({ title: "A launch", date: "2026-10-14" }, "Launches", {}).pill, null);
});
