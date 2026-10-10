// The calendar helpers: weeks, the window ahead, and one holding's dates.

import { test } from "node:test";
import assert from "node:assert/strict";

import { weekOf, byWeek, within, eventsFor, scorecardFor, kindLabel } from "../../src/core/calendar.js";

const CAL = {
  as_of: "2026-10-10",
  upcoming: [
    { ticker: "HAL", date: "2026-10-31", kind: "results", title: "Board meeting: Financial Results" },
    { ticker: "ITC", date: "2026-10-12", kind: "dividend", title: "Ex-date: Dividend" },
    { ticker: "BEL", date: "2026-10-17", kind: "board", title: "Board meeting" },
  ],
  macro: [{ date: "2026-10-14", kind: "macro", title: "RBI policy decision" }],
};

test("a date belongs to the week starting the Monday before it", () => {
  assert.equal(weekOf("2026-10-10"), "2026-10-05"); // a Saturday
  assert.equal(weekOf("2026-10-12"), "2026-10-12"); // a Monday
  assert.equal(weekOf("2026-10-18"), "2026-10-12"); // a Sunday
});

test("events are grouped by week with market dates merged in, earliest first", () => {
  const weeks = byWeek(CAL.upcoming, CAL.macro);
  assert.deepEqual(
    weeks.map((w) => [w.week, w.events.map((e) => e.ticker || e.title)]),
    [
      ["2026-10-12", ["ITC", "RBI policy decision", "BEL"]],
      ["2026-10-26", ["HAL"]],
    ],
  );
});

test("the week ahead counts from the calendar's own date", () => {
  assert.deepEqual(
    within(CAL, 7).map((e) => e.date),
    ["2026-10-12", "2026-10-14", "2026-10-17"],
  );
  assert.deepEqual(within(CAL, 1), []);
  assert.deepEqual(within(null, 7), []);
});

test("one holding's dates and latest result", () => {
  assert.deepEqual(eventsFor(CAL, "hal").map((e) => e.date), ["2026-10-31"]);
  const results = { scorecards: [{ ticker: "HAL", quarter: "Sep 2026" }] };
  assert.equal(scorecardFor(results, "hal").quarter, "Sep 2026");
  assert.equal(scorecardFor(results, "BEL"), null);
  assert.equal(scorecardFor(null, "HAL"), null);
});

test("kinds read as words", () => {
  assert.equal(kindLabel("fund_raising"), "Fund raising");
  assert.equal(kindLabel("results"), "Results");
  assert.equal(kindLabel("something_new"), "something new");
});
