// The order-book slot on the company page (src/views/holdings.js): the order
// book where a source gives one, else what stands in for it, labelled so.

import { test } from "node:test";
import assert from "node:assert/strict";

import { orderBookRow, visibilityProxy } from "../../src/views/holdings.js";
import { partnerCount } from "../../src/views/company.js";

const hal = { ticker: "HAL", screener: { working_capital_days: -110, debtor_days: 72.4, roce: 32 } };

test("with no order book, the slot is a visibility proxy and says so", () => {
  const [label, value] = orderBookRow(hal, { partners: 2 });
  assert.equal(label, "Visibility proxy");
  assert.equal(value.text, "Working capital -110 days · debtors 72 days · 2 partners on record");
  assert.match(value.title, /^No order book is reported/);
});

test("an order book, where a source gives one, takes the slot", () => {
  const stock = { screener: { ...hal.screener, order_book: 94000 } };
  assert.equal(orderBookRow(stock)[0], "Order book");
});

test("the proxy shows what there is, and nothing when there is nothing", () => {
  assert.equal(visibilityProxy({ screener: { debtor_days: 40 } }).text, "Debtors 40 days");
  assert.equal(visibilityProxy({ screener: {} }, { partners: 1 }).text, "1 partner on record");
  // A lender: no working-capital rows, no partners.
  assert.equal(visibilityProxy({ screener: { roce: 7 } }), null);
  assert.equal(orderBookRow({ screener: { order_book: "N/A" } }), null);
});

test("partners are counted either side of the edge, any case, partners only", () => {
  const edges = [
    { src: "Ananth Technologies", dst: "BEL", type: "partner" },
    { src: "bel", dst: "Safran", type: "partner" },
    { src: "BEL", dst: "aerospace_defence", type: "competitor" },
    { src: "Airbus", dst: "HAL", type: "partner" },
  ];
  assert.equal(partnerCount(edges, "BEL"), 2);
  assert.equal(partnerCount(edges, "hal"), 1);
  assert.equal(partnerCount(null, "BEL"), 0);
});
