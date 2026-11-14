import { test } from "node:test";
import assert from "node:assert/strict";

import { NAV_GROUPS, groupForView, navigationViews } from "../../src/core/navigation.js";

test("every existing primary view appears once in the workstation navigation", () => {
  const entries = navigationViews();
  const views = entries.map((entry) => entry.view);
  assert.equal(new Set(views).size, views.length);
  assert.deepEqual(views, [
    "overview", "flow", "calendar", "companies", "network",
    "portfolio", "holdings", "review", "valuation", "risk", "ask", "system",
  ]);
});

test("route groups are stable and unknown routes fall back to Daily Intelligence", () => {
  assert.equal(groupForView("overview").id, "daily");
  assert.equal(groupForView("companies").id, "companies");
  assert.equal(groupForView("holdings").id, "portfolio");
  assert.equal(groupForView("valuation").id, "advanced");
  assert.equal(groupForView("not-a-view").id, NAV_GROUPS[0].id);
});
