// The Portfolio view's model: choosing a book, where each limit stands, and
// the order list written out for a desk.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  pickBook,
  positionOf,
  orderGroups,
  limitStatus,
  ordersCsv,
  csvName,
} from "../../src/core/portfolio.js";

const BOOK = {
  id: "model",
  name: "Model book",
  limits: { max_stock_pct: 8, max_days_to_exit: 5, max_ownership_pct: 1, max_group_pct: 15 },
  positions: [
    { ticker: "HAL", weight_pct: 1.4, days_to_exit: 0.1, ownership_pct: 0.002 },
    { ticker: "SPELS", weight_pct: 1.39, days_to_exit: 138.9, ownership_pct: 1.27 },
    { ticker: "ASMTEC", weight_pct: 1.38 },
  ],
  exposure: {
    sectors: [{ sector: "clean_energy", weight_pct: 6.94 }],
    groups: [{ group: "Government of India", weight_pct: 12.5 }],
  },
  risk: { beta: 0.98 },
  orders: {
    rows: [
      { side: "SELL", ticker: "SPELS", name: "SPEL Semiconductor", quantity: 564218, price: 118.65, value_cr: 6.69, reason: "over its cap (5 days to exit)" },
      { side: "BUY", ticker: "HAL", name: "Hindustan Aeronautics, Ltd", quantity: 52, price: 4677.3, value_cr: 0.24, reason: "reinvests the proceeds of the sales" },
      { side: "BUY", ticker: "X", name: '=HYPERLINK("http://evil")', quantity: 1, price: 1, value_cr: 0, reason: "new to the targets" },
    ],
  },
};

test("a book is chosen by id, else the first that was measured", () => {
  const data = { books: [{ id: "bad", error: "no positions" }, BOOK, { id: "other" }] };
  assert.equal(pickBook(data, "other").id, "other");
  assert.equal(pickBook(data, "missing").id, "model");
  assert.equal(pickBook(data).id, "model");
  assert.equal(pickBook({ books: [] }), null);
  assert.equal(pickBook(null), null);
});

test("a position is found by ticker, any case", () => {
  assert.equal(positionOf(BOOK, "spels").ticker, "SPELS");
  assert.equal(positionOf(BOOK, "TCS"), null);
});

test("orders that settle cash are kept apart from the ones that had to happen", () => {
  const { main, settle } = orderGroups(BOOK.orders);
  assert.deepEqual(main.map((o) => o.ticker), ["SPELS", "X"]);
  assert.deepEqual(settle.map((o) => o.ticker), ["HAL"]);
});

test("each limit is shown against the figure and the name that set it", () => {
  const rows = Object.fromEntries(limitStatus(BOOK).map((r) => [r.key, r]));
  assert.deepEqual(Object.keys(rows), ["max_stock_pct", "max_group_pct", "max_days_to_exit", "max_ownership_pct"]);
  assert.equal(rows.max_stock_pct.subject, "HAL");
  assert.equal(rows.max_stock_pct.ok, true);
  assert.equal(rows.max_days_to_exit.subject, "SPELS");
  assert.equal(rows.max_days_to_exit.ok, false);
  assert.equal(rows.max_ownership_pct.ok, false);
  assert.equal(rows.max_group_pct.subject, "Government of India");
  // Nothing measured is not the same as within the limit.
  const blank = limitStatus({ limits: { max_days_to_exit: 5 }, positions: [{ ticker: "A" }] });
  assert.equal(blank[0].ok, null);
  assert.equal(blank[0].value, null);
});

test("the order list is CSV a spreadsheet will not run", () => {
  const csv = ordersCsv(BOOK);
  const lines = csv.trimEnd().split("\r\n");
  assert.equal(
    lines[0],
    "side,symbol,exchange,name,quantity,reference_price,value_cr,weight_now_pct,target_pct,days_to_trade,reason",
  );
  assert.ok(lines[1].startsWith("SELL,SPELS,NSE,SPEL Semiconductor,564218,118.65,6.69,"));
  // A comma is quoted; a cell that opens like a formula is defused.
  assert.ok(lines[2].includes('"Hindustan Aeronautics, Ltd"'));
  assert.ok(lines[3].includes(`"'=HYPERLINK(""http://evil"")"`));
  assert.equal(ordersCsv({}), "side,symbol,exchange,name,quantity,reference_price,value_cr,weight_now_pct,target_pct,days_to_trade,reason\r\n");
});

test("the file is named for the book and the day", () => {
  assert.equal(csvName(BOOK, "2026-10-10"), "orders-model-2026-10-10.csv");
  assert.equal(csvName({ id: "../x y" }, ""), "orders-xy.csv");
});
