// Run health's channel counts, for keys in the payload and keys moved to
// their own file (dashboard/sidecars.py), and the AI readers' report
// (analysis/reader_runtime.py).

import { test } from "node:test";
import assert from "node:assert/strict";

import { channelRows, readerRows, setAsideRows } from "../../src/views/system.js";

const row = (rows, label) => rows.find((r) => r.label === label);

test("a split key is counted from its manifest, not its two keys", () => {
  const rows = channelRows({
    market_events: { sidecar: "data/market_events.json", count: 40 },
    peer_competitors: { sidecar: "data/peer_competitors.json", count: 0 },
    read_throughs: [{}, {}],
  });
  assert.equal(row(rows, "Market events").state, "40");
  // Ran and found nothing, which this channel should never do.
  assert.equal(row(rows, "Competitor radar").state, "nothing");
  assert.equal(row(rows, "Read-throughs").state, "2");
  // Absent is "did not run", whatever the other keys are.
  assert.equal(row(rows, "Industry share").state, "did not run");
});

test("each AI reader shows its models, what it read and what failed it", () => {
  const briefing = {
    ai_readers: {
      readers: {
        check: {
          calls: 0,
          seconds: 0,
          answered: {},
          failed: {},
          counts: { pending: 3 },
          skipped: "every model failed",
        },
        events: {
          calls: 2,
          seconds: 41.5,
          answered: { "gemini-flash-lite-latest": 2 },
          failed: { "gemini-3.8-flash": { count: 1, reason: "Gemini unavailable (503)" } },
          counts: { read: 80, cached: 400, pending: 0 },
        },
        tagger: { calls: 1, seconds: 2, answered: { m: 1 }, failed: {} },
      },
      set_aside: { "gemini-3.8-flash": "Gemini unavailable (503)" },
    },
  };
  const rows = readerRows(briefing);
  // The order a run calls them in, then any reader the view has no name for.
  assert.deepEqual(
    rows.map((r) => r.label),
    ["Event reader", "Second reading", "tagger"],
  );
  const [events, check] = rows;
  assert.equal(events.answered, "gemini-flash-lite-latest ×2");
  assert.equal(events.result, "80 read · 400 cached · 0 pending");
  assert.equal(events.failed, "gemini-3.8-flash ×1: Gemini unavailable (503)");
  assert.equal(events._failed, 1);
  // Called no model: why, not an empty "answered by".
  assert.equal(check.answered, "—");
  assert.equal(check.result, "3 pending — skipped: every model failed");
  assert.equal(check.failed, "none");
  assert.deepEqual(setAsideRows(briefing), [
    { model: "gemini-3.8-flash", why: "Gemini unavailable (503)" },
  ]);
});

test("a payload from before the report has no reader rows", () => {
  assert.deepEqual(readerRows({}), []);
  assert.deepEqual(readerRows(null), []);
  assert.deepEqual(setAsideRows({ ai_readers: { readers: {} } }), []);
});
