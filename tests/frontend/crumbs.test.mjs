// The trail above every view, from the route alone (src/core/crumbs.js).

import { test } from "node:test";
import assert from "node:assert/strict";

import { crumbsFor } from "../../src/core/crumbs.js";
import { parse } from "../../src/core/router.js";

const views = {
  overview: { label: "Overview" },
  companies: { label: "Companies" },
  holdings: { label: "Holdings" },
  company: { label: "Company", hidden: true },
};
const watchlist = {
  aerospace_defence: [{ ticker: "HAL" }],
  macro_indicators: [{ ticker: "NIFTY" }],
};
const labels = { aerospace_defence: { label: "Aerospace & Defence" } };
const trail = (hash) => crumbsFor(parse(hash), { views, watchlist, labels });

test("a company page is traced through its sector", () => {
  assert.deepEqual(trail("#/company?focus=hal"), [
    { text: "Companies", href: "#/companies" },
    { text: "Aerospace & Defence", href: "#/companies?sector=aerospace_defence" },
    { text: "HAL" },
  ]);
  // The old email link form lands on the same trail.
  assert.deepEqual(trail("#stock/HAL/news"), trail("#/company?focus=HAL"));
  // A ticker not on the watchlist still says where the reader is.
  assert.deepEqual(trail("#/company?focus=XYZ"), [{ text: "Companies", href: "#/companies" }, { text: "XYZ" }]);
});

test("a view at its top level has no trail", () => {
  assert.deepEqual(trail("#/companies"), []);
  assert.deepEqual(trail(""), []);
  // Other filters live in the filter bar, not the trail.
  assert.deepEqual(trail("#/companies?q=solar&thesis=Broken"), []);
});

test("a sector filter and a focus are steps, the last one the page", () => {
  assert.deepEqual(trail("#/companies?sector=aerospace_defence"), [
    { text: "Companies", href: "#/companies" },
    { text: "Aerospace & Defence" },
  ]);
  assert.deepEqual(trail("#/holdings?sector=aerospace_defence&focus=HAL"), [
    { text: "Holdings", href: "#/holdings" },
    { text: "Aerospace & Defence", href: "#/holdings?sector=aerospace_defence" },
    { text: "HAL" },
  ]);
  // An unknown view traces as the Overview it renders.
  assert.deepEqual(trail("#/nowhere?focus=HAL"), [{ text: "Overview", href: "#/overview" }, { text: "HAL" }]);
});
