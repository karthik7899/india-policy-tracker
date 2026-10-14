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

import { earningsBadge, resultsBadge, daysBetween, todayISO } from "../../src/core/calendar.js";

test("results due within ten days read as T-minus days", () => {
  const calendar = { next_results: { BHEL: "2026-10-14", PERSISTENT: "2026-10-15", HDFCBANK: "2026-10-24", OLD: "2026-10-01" } };
  const asOf = "2026-10-14";
  assert.deepEqual(earningsBadge(calendar, "bhel", { asOf }), { date: "2026-10-14", days: 0, text: "Earnings: today" });
  assert.equal(earningsBadge(calendar, "PERSISTENT", { asOf }).text, "Earnings: T-1d");
  assert.equal(earningsBadge(calendar, "HDFCBANK", { asOf }).text, "Earnings: T-10d");
  assert.equal(earningsBadge(calendar, "HDFCBANK", { asOf: "2026-10-13" }), null);
  // A date already past, on a calendar a day stale, shows nothing.
  assert.equal(earningsBadge(calendar, "OLD", { asOf }), null);
  assert.equal(earningsBadge(null, "BHEL", { asOf }), null);
});

test("the latest results state the figures and never a beat or a miss", () => {
  const results = {
    scorecards: [
      { ticker: "BHEL", detected: "2026-10-15", quarter: "Sep 2026", sales_yoy_pct: 21.4, sales_qoq_pct: 8, opm_change_pp: -3, summary: "Sales ₹8,000 Cr, +21.4% on a year ago" },
      { ticker: "NEW", detected: "2026-10-15", quarter: "Sep 2026", sales_qoq_pct: -4.2 },
    ],
  };
  const badge = resultsBadge(results, "BHEL", { asOf: "2026-10-16" });
  assert.equal(badge.text, "Sep 2026: sales ▲21.4% YoY · margin ▼3.0 pts QoQ");
  assert.equal(badge.title, "Sales ₹8,000 Cr, +21.4% on a year ago");
  assert.ok(!/beat|miss/i.test(badge.text));
  // No year-ago figure yet: the quarter before, said so.
  assert.equal(resultsBadge(results, "NEW", { asOf: "2026-10-16" }).text, "Sep 2026: sales ▼4.2% QoQ");
  // Old news after 45 days.
  assert.equal(resultsBadge(results, "BHEL", { asOf: "2026-12-15" }), null);
  assert.equal(resultsBadge(results, "TCS", { asOf: "2026-10-16" }), null);
});

test("a lender's results say revenue, its top line", () => {
  const results = {
    scorecards: [
      { ticker: "SBIN", detected: "2026-10-15", quarter: "Sep 2026", sales_qoq_pct: 3.6, opm_change_pp: -1, margin_basis: "financing" },
    ],
  };
  assert.equal(resultsBadge(results, "SBIN", { asOf: "2026-10-16" }).text, "Sep 2026: revenue ▲3.6% QoQ · margin ▼1.0 pts QoQ");
});

test("days are counted between calendar dates", () => {
  assert.equal(daysBetween("2026-10-14", "2026-10-24"), 10);
  assert.equal(daysBetween("2026-10-14", "2026-10-13"), -1);
  assert.equal(daysBetween("x", "2026-10-13"), null);
  assert.equal(todayISO(new Date(2026, 9, 4)), "2026-10-04");
});
