import { test } from "node:test";
import assert from "node:assert/strict";

import { catalystRows, priorityWarnings } from "../../src/views/intelligence.js";

test("decision queue ranks severity first and evidence confidence second", () => {
  const rows = priorityWarnings([
    { ticker: "C", severity: "Medium", confidence: "High" },
    { ticker: "B", severity: "High", confidence: "Low" },
    { ticker: "A", severity: "High", confidence: "High" },
    { ticker: "D", severity: "Low", confidence: "High" },
  ]);
  assert.deepEqual(rows.map((item) => item.ticker), ["A", "B", "C", "D"]);
});

test("catalysts rank confirmed policy before proposals and undated items", () => {
  const rows = catalystRows(
    [
      { headline: "Draft policy", strength: "proposed", status: "proposed", effects: [], date: "2026-11-13" },
      { headline: "Approved policy", strength: "hard", status: "approved", effects: [], date: "2026-11-12" },
    ],
    [
      { headline: "General market tie-up", event_type: "tie_up", certainty: "completed", date: "2026-11-14" },
    ],
  );
  assert.deepEqual(rows.map((item) => item.headline), [
    "Approved policy", "Draft policy", "General market tie-up",
  ]);
});
