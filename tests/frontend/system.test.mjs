// Run health's channel counts, for keys in the payload and keys moved to
// their own file (dashboard/sidecars.py).

import { test } from "node:test";
import assert from "node:assert/strict";

import { channelRows } from "../../src/views/system.js";

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
