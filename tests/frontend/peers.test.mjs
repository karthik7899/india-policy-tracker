import { test } from "node:test";
import assert from "node:assert/strict";

import { buildPeerRows } from "../../src/views/peers.js";

test("peer comparison joins watchlist and discovered competitors by sector", () => {
  const watchlist = {
    aerospace_defence: [{ ticker: "BEL", name: "Bharat Electronics", screener: { revenue_yoy_pct: 20, pe_ratio: 45, roce: 30 } }],
    macro_indicators: [{ ticker: "INDEX" }],
  };
  const peers = {
    aerospace_defence: [{ ticker: "HAL", name: "Hindustan Aeronautics", via_ticker: "BEL", sales_var_pct: 15, profit_var_pct: 10, pe_ratio: 33, roce: 32, industry_share_pct: 39 }],
  };
  const marketShare = { aerospace_defence: [{ ticker: "BEL", share_pct: 63.9, change_pp: -0.1 }] };
  const rows = buildPeerRows(watchlist, peers, marketShare, "aerospace_defence");
  assert.equal(rows.length, 2);
  assert.equal(rows.find((r) => r.ticker === "BEL").marketShare, 63.9);
  assert.equal(rows.find((r) => r.ticker === "HAL").via, "BEL");
  assert.equal(rows.find((r) => r.ticker === "HAL").marketShare, 39);
});

test("peer comparisons preserve unavailable metrics and allow sector filtering", () => {
  const watchlist = {
    clean_energy: [{ ticker: "ABC" }],
    fmcg: [{ ticker: "XYZ" }],
  };
  const rows = buildPeerRows(watchlist, {}, {}, "clean_energy");
  assert.equal(rows.length, 1);
  assert.equal(rows[0].ticker, "ABC");
  assert.equal(rows[0].pe, null);
  assert.equal(rows[0].marketShare, null);
});
