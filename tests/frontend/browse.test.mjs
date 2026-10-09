// Getting to a company: the header search, the company page's helpers, and
// the old link form the email kept using.

import { test } from "node:test";
import assert from "node:assert/strict";

import { parse } from "../../src/core/router.js";
import { buildIndex, search } from "../../src/core/search.js";
import {
  findHolding,
  companyEdges,
  readThroughsFor,
  nearMisses,
} from "../../src/views/company.js";
import { cardSummary } from "../../src/views/companies.js";

const PAYLOAD = {
  sectors: {
    aerospace_defence: { label: "Aerospace & Defence" },
    manufacturing_electronics: { label: "Manufacturing & Electronics" },
  },
  watchlist: {
    aerospace_defence: [
      { ticker: "HAL", name: "Hindustan Aeronautics" },
      { ticker: "BEL", name: "Bharat Electronics" },
    ],
    manufacturing_electronics: [
      { ticker: "KAYNES", name: "Kaynes Technology" },
      { ticker: "SYRMA", name: "Syrma SGS Tech." },
    ],
    macro_indicators: [{ ticker: "NIFTY", name: "Nifty 50" }],
  },
};

test("the old #stock/TICKER/news links open the company page", () => {
  // Every "Coverage (n)" link in the email used this form and, after the
  // dashboard rewrite, landed on the Overview.
  assert.deepEqual(parse("#stock/dixon/news"), {
    view: "company",
    focus: "DIXON",
    params: { focus: "DIXON" },
  });
  assert.equal(parse("#stock/T1/snapshot").focus, "T1");
  assert.equal(parse("#/company?focus=syrma").focus, "SYRMA");
});

test("search finds a company by ticker, by a word of its name, and a sector", () => {
  const index = buildIndex(PAYLOAD);
  assert.equal(search(index, "syrma")[0].href, "#/company?focus=SYRMA");
  assert.equal(search(index, "kayn")[0].key, "KAYNES");
  // A word inside the name, not only its start.
  assert.equal(search(index, "aeronautics")[0].key, "HAL");
  assert.equal(search(index, "defence")[0].href, "#/companies?sector=aerospace_defence");
  assert.deepEqual(search(index, ""), []);
  assert.deepEqual(search(index, "zzz"), []);
});

test("an exact ticker outranks a name that merely starts the same", () => {
  const index = buildIndex({
    watchlist: { it: [{ ticker: "BELL", name: "Bell Corp" }, { ticker: "BEL", name: "Bharat Electronics" }] },
  });
  assert.equal(search(index, "bel")[0].key, "BEL");
});

test("macro indicators are not companies to search for or open", () => {
  const index = buildIndex(PAYLOAD);
  assert.ok(!index.some((e) => e.key === "NIFTY"));
  assert.equal(findHolding(PAYLOAD.watchlist, "NIFTY"), null);
  assert.equal(findHolding(PAYLOAD.watchlist, "syrma").sector, "manufacturing_electronics");
});

test("a company's own links are kept apart from its sector's", () => {
  const edges = [
    { src: "Elemaster", dst: "SYRMA", type: "partner" },
    { src: "SYRMA", dst: "Amber", type: "competitor" },
    { src: "Apple", dst: "manufacturing_electronics", type: "anchor_demand" },
    { src: "Vivo", dst: "DIXON", type: "partner" },
  ];
  const { own, viaSector } = companyEdges(edges, "SYRMA", "manufacturing_electronics");
  assert.deepEqual(own.map((e) => e.other), ["Elemaster", "Amber"]);
  assert.deepEqual(viaSector.map((e) => e.src), ["Apple"]);
});

test("read-throughs are the ones whose chain ends at this holding", () => {
  const rows = [
    { trigger: "chip shortage", tickers: ["SYRMA", "DIXON"] },
    { trigger: "steel duty", tickers: ["BHEL"] },
  ];
  assert.deepEqual(readThroughsFor(rows, "syrma").map((r) => r.trigger), ["chip shortage"]);
});

test("a mistyped ticker suggests the holdings it was probably meant to be", () => {
  assert.deepEqual(nearMisses(PAYLOAD.watchlist, "SYRM").map((s) => s.ticker), ["SYRMA"]);
  assert.deepEqual(nearMisses(PAYLOAD.watchlist, ""), []);
});

test("a folded company card says its latest headline and its counts", () => {
  assert.equal(
    cardSummary({ activity: [{ text: "Syrma opens Jodhpur plant" }], activity_count: 3, policy_count: 1 }),
    "Syrma opens Jodhpur plant — 3 news · 1 policy",
  );
  assert.equal(cardSummary({}), "No news in the window — 0 news · 0 policies");
});
