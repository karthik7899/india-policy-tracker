// Tests for the filter predicates and the sort comparator.
//
// Both are pure on purpose. The filter rules decide which rows a reader is
// shown and the sort decides which survive a truncation, so they are the two
// places where a quiet mistake changes what the dashboard appears to say
// rather than merely how it looks.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  read,
  activeCount,
  cleared,
  matchesHolding,
  applyHoldings,
  matchesItem,
  applyItems,
  withinDays,
  ageInDays,
  thesisIndex,
} from "../../src/core/filters.js";
import { sortRows, nextDir } from "../../src/views/table.js";

const HAL = {
  ticker: "HAL",
  name: "Hindustan Aeronautics",
  sector: "aerospace_defence",
  screener: { liquidity_band: "liquid" },
};
const SUZLON = {
  ticker: "SUZLON",
  name: "Suzlon Energy",
  sector: "clean_energy",
  screener: { liquidity_band: "thin" },
};
const UNGRADED = { ticker: "ASMTEC", name: "ASM Technologies", sector: "semiconductors", screener: {} };

const GRADES = { HAL: { status: "Broken" }, SUZLON: { status: "Intact" } };

// --- reading state off the route ------------------------------------------

test("read pulls every filter out of the route params", () => {
  const f = read({ params: { q: " hal ", sector: "clean_energy", thesis: "Broken", days: "30" } });
  assert.equal(f.q, "hal"); // trimmed, so a stray space is not a filter
  assert.equal(f.sector, "clean_energy");
  assert.equal(f.thesis, "Broken");
  assert.equal(f.days, 30);
});

test("read of an empty route is the empty filter", () => {
  const f = read({});
  assert.equal(activeCount(f), 0);
  assert.equal(f.days, null);
});

test("a junk days param is not a filter", () => {
  // num() returns null rather than NaN, so this must not become a window that
  // silently excludes everything.
  assert.equal(read({ params: { days: "banana" } }).days, null);
});

test("cleared drops the filters and keeps the rest of the route", () => {
  const out = cleared({ q: "hal", sector: "x", focus: "BEL", lens: "buffett", stream: "filings" });
  assert.deepEqual(out, { focus: "BEL", lens: "buffett", stream: "filings" });
});

// --- holdings --------------------------------------------------------------

test("no filters means every row survives, by identity", () => {
  const rows = [HAL, SUZLON];
  assert.equal(applyHoldings(rows, read({})), rows);
});

test("search matches ticker, name and sector, case-insensitively", () => {
  for (const q of ["hal", "HAL", "hindustan", "aerospace"]) {
    assert.ok(matchesHolding(HAL, { q }), `expected a match for ${q}`);
  }
  assert.equal(matchesHolding(HAL, { q: "suzlon" }), false);
});

test("an ungraded holding is excluded by a thesis filter, not treated as Intact", () => {
  // The distinction this whole product turns on. Asking for Intact and being
  // handed rows we never graded would be inventing a grade.
  const ctx = { thesisByTicker: GRADES };
  assert.equal(matchesHolding(UNGRADED, { thesis: "Intact" }, ctx), false);
  assert.equal(matchesHolding(UNGRADED, { thesis: "Broken" }, ctx), false);
  assert.ok(matchesHolding(SUZLON, { thesis: "Intact" }, ctx));
});

test("a holding with no band is excluded by a band filter", () => {
  assert.equal(matchesHolding(UNGRADED, { band: "liquid" }), false);
  assert.ok(matchesHolding(HAL, { band: "liquid" }));
});

test("filters compose as AND, not OR", () => {
  const ctx = { thesisByTicker: GRADES };
  const rows = [HAL, SUZLON, UNGRADED];
  assert.deepEqual(
    applyHoldings(rows, { sector: "aerospace_defence", thesis: "Broken" }, ctx).map((r) => r.ticker),
    ["HAL"],
  );
  assert.deepEqual(
    applyHoldings(rows, { sector: "aerospace_defence", thesis: "Intact" }, ctx).map((r) => r.ticker),
    [],
  );
});

// --- dates -----------------------------------------------------------------

const NOW = Date.parse("2026-09-13T00:00:00Z");

test("ageInDays is null for an unreadable date, never zero", () => {
  assert.equal(ageInDays("not a date", NOW), null);
  assert.equal(ageInDays("", NOW), null);
  assert.equal(ageInDays("2026-09-06T00:00:00Z", NOW), 7);
});

test("an undated item is kept by a date window rather than silently dropped", () => {
  // Undated is not expired. Dropping it would hide a real item behind a
  // control the reader thinks only narrows by time.
  assert.ok(withinDays("", 7, NOW));
  assert.ok(withinDays(null, 30, NOW));
});

test("a date window keeps what is inside it and drops what is older", () => {
  assert.ok(withinDays("2026-09-10T00:00:00Z", 7, NOW));
  assert.equal(withinDays("2026-08-01T00:00:00Z", 7, NOW), false);
  assert.ok(withinDays("2026-08-01T00:00:00Z", 90, NOW));
});

test("no window means no date filtering at all", () => {
  assert.ok(withinDays("1999-01-01T00:00:00Z", null, NOW));
});

// --- flow items ------------------------------------------------------------

const ITEMS = [
  { when: "2026-09-12T00:00:00Z", what: "Order win at BEL", who: "BEL", source: "NSE" },
  { when: "2026-06-01T00:00:00Z", what: "Old filing", who: "HAL", source: "BSE" },
  { when: "", what: "Undated note", who: "", source: "news" },
];

test("sector and thesis do not empty the flow view", () => {
  // They describe holdings and mean nothing for a news item, so they are
  // ignored here rather than matching nothing.
  assert.equal(applyItems(ITEMS, { sector: "clean_energy", thesis: "Broken" }).length, 3);
});

test("flow search covers what, who and source", () => {
  assert.equal(applyItems(ITEMS, { q: "bel" }).length, 1);
  assert.equal(applyItems(ITEMS, { q: "bse" }).length, 1);
  assert.equal(applyItems(ITEMS, { q: "nothing here" }).length, 0);
});

test("a flow date window keeps undated rows", () => {
  const kept = applyItems(ITEMS, { days: 30 }, { now: NOW }).map((i) => i.what);
  assert.deepEqual(kept, ["Order win at BEL", "Undated note"]);
});

test("matchesItem ANDs search with the date window", () => {
  assert.equal(matchesItem(ITEMS[1], { q: "hal", days: 30 }, { now: NOW }), false);
  assert.ok(matchesItem(ITEMS[1], { q: "hal", days: 365 }, { now: NOW }));
});

// --- thesis index ----------------------------------------------------------

test("thesisIndex upper-cases its keys so focus links resolve", () => {
  const idx = thesisIndex({ thesis_health: { hal: { status: "Broken" }, BEL: { status: "Intact" } } });
  assert.equal(idx.HAL.status, "Broken");
  assert.equal(idx.BEL.status, "Intact");
});

// --- sorting ---------------------------------------------------------------

const ROWS = [
  { ticker: "A", pe: "12.5" },
  { ticker: "B", pe: "N/A" },
  { ticker: "C", pe: "9" },
  { ticker: "D", pe: "100" },
];

test("sorting is numeric even though the pipeline stores display strings", () => {
  // A string sort puts "9" above "100", which is how a screener starts lying.
  assert.deepEqual(
    sortRows(ROWS, "pe", "desc").map((r) => r.ticker),
    ["D", "A", "C", "B"],
  );
});

test("unreadable values sort last in BOTH directions", () => {
  // The one rule that matters here. Sorted as zero, "N/A" would head an
  // ascending sort and read as the cheapest row on the screen.
  assert.equal(sortRows(ROWS, "pe", "desc").at(-1).ticker, "B");
  assert.equal(sortRows(ROWS, "pe", "asc").at(-1).ticker, "B");
});

test("sortRows does not mutate its input", () => {
  const before = ROWS.map((r) => r.ticker);
  sortRows(ROWS, "pe", "asc");
  assert.deepEqual(ROWS.map((r) => r.ticker), before);
});

test("an accessor reads columns that live under screener", () => {
  const nested = [
    { ticker: "A", screener: { advt_cr: 5 } },
    { ticker: "B", screener: {} },
    { ticker: "C", screener: { advt_cr: 50 } },
  ];
  assert.deepEqual(
    sortRows(nested, "advt_cr", "desc", (r) => r.screener?.advt_cr).map((r) => r.ticker),
    ["C", "A", "B"],
  );
});

test("clicking a new column starts descending; clicking the same one toggles", () => {
  assert.equal(nextDir("pe", null, "desc"), "desc");
  assert.equal(nextDir("pe", "ticker", "asc"), "desc");
  assert.equal(nextDir("pe", "pe", "desc"), "asc");
  assert.equal(nextDir("pe", "pe", "asc"), "desc");
});
