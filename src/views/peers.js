// Peer Comparisons — holdings against the pipeline's discovered competitors.
// Values remain source fields: no synthetic peer score or cross-sector ranking.

import { el, mount } from "../core/dom.js";
import { resolve } from "../core/data.js";
import { href } from "../core/router.js";
import { dataTable, panel, tickerLink } from "./table.js";

const number = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(String(value).replace(/[,%+₹\s]/g, ""));
  return Number.isFinite(n) ? n : null;
};

const label = (sectors, key) => sectors?.[key]?.label || sectors?.[key]?.name || String(key || "").replace(/_/g, " ");

export function buildPeerRows(watchlist, peerData, marketShare, selectedSector = "all") {
  const sectors = Object.keys(watchlist || {}).filter((s) => s !== "macro_indicators");
  const chosen = selectedSector === "all" ? sectors : sectors.filter((s) => s === selectedSector);
  const shareByTicker = new Map();
  for (const [sector, items] of Object.entries(marketShare || {})) {
    for (const item of items || []) {
      const key = String(item.ticker || "").toUpperCase();
      if (key && (!shareByTicker.has(key) || sector === item.sector)) shareByTicker.set(key, item);
    }
  }

  const rows = [];
  for (const sector of chosen) {
    for (const stock of watchlist?.[sector] || []) {
      if (!stock?.ticker) continue;
      const s = stock.screener || {};
      const share = shareByTicker.get(String(stock.ticker).toUpperCase());
      rows.push({
        ticker: String(stock.ticker).toUpperCase(),
        name: stock.name || stock.ticker,
        sector,
        role: "Watchlist",
        via: "—",
        salesGrowth: number(s.revenue_yoy_pct ?? s.qoq_sales_growth ?? stock.revenue_growth),
        profitGrowth: number(stock.profit_growth ?? stock.earnings_growth),
        pe: number(s.pe_ratio),
        roce: number(s.roce),
        marketShare: number(share?.share_pct),
        shareChange: number(share?.change_pp),
        marketCap: number(s.market_cap),
      });
    }
    for (const peer of peerData?.[sector] || []) {
      if (!peer?.ticker) continue;
      const share = shareByTicker.get(String(peer.ticker).toUpperCase());
      rows.push({
        ticker: String(peer.ticker).toUpperCase(),
        name: peer.name || peer.ticker,
        sector,
        role: "Peer",
        via: peer.via_ticker || "—",
        salesGrowth: number(peer.sales_var_pct),
        profitGrowth: number(peer.profit_var_pct),
        pe: number(peer.pe_ratio),
        roce: number(peer.roce),
        marketShare: number(share?.share_pct ?? peer.industry_share_pct),
        shareChange: number(share?.change_pp),
        marketCap: number(peer.market_cap),
      });
    }
  }
  return rows.sort((a, b) => a.sector.localeCompare(b.sector) || a.role.localeCompare(b.role) || a.ticker.localeCompare(b.ticker));
}

function fmt(value, suffix = "") {
  return value === null || value === undefined ? "—" : `${value > 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const params = route?.params || {};
  const [peerData, marketShare] = await Promise.all([
    resolve(b, "peer_competitors"),
    resolve(b, "market_share"),
  ]);
  const sectors = Object.keys(payload?.watchlist || {}).filter((s) => s !== "macro_indicators");
  const selected = sectors.includes(params.sector) ? params.sector : "all";
  const rows = buildPeerRows(payload?.watchlist || {}, peerData || {}, marketShare || {}, selected);
  const peerCount = rows.filter((r) => r.role === "Peer").length;
  const heldCount = rows.filter((r) => r.role === "Watchlist").length;

  mount(
    container,
    el("header", { class: "view-head" },
      el("h2", { class: "view-title" }, "Peer Comparisons"),
      el("p", { class: "view-sub" }, `${label(payload?.sectors, selected === "all" ? "" : selected)} · ${heldCount} watchlist companies and ${peerCount} discovered peers · latest available quarterly fields`),
    ),
    el("nav", { class: "lens-nav" },
      el("a", { class: `lens${selected === "all" ? " lens-active" : ""}`, href: href("peers") }, "All sectors"),
      sectors.map((sector) => el("a", { class: `lens${selected === sector ? " lens-active" : ""}`, href: href("peers", { sector }) }, label(payload?.sectors, sector))),
    ),
    panel(
      "Operating and valuation comparison",
      "Watchlist companies and discovered peers are shown together. Growth and ROCE are not always from the same reporting period across providers; use the source fields and company filings before drawing conclusions. Missing values are left blank, not treated as zero.",
      rows.length ? dataTable(rows, [
        { key: "ticker", label: "Company", render: (row) => tickerLink(row.ticker) },
        { key: "role", label: "Universe" },
        { key: "via", label: "Compared with" },
        { key: "salesGrowth", label: "Sales growth", numeric: true, render: (row) => fmt(row.salesGrowth, "%") },
        { key: "profitGrowth", label: "Profit growth", numeric: true, render: (row) => fmt(row.profitGrowth, "%") },
        { key: "pe", label: "P/E", numeric: true, render: (row) => fmt(row.pe) },
        { key: "roce", label: "ROCE", numeric: true, render: (row) => fmt(row.roce, "%") },
        { key: "marketShare", label: "Market share", numeric: true, render: (row) => fmt(row.marketShare, "%") },
        { key: "shareChange", label: "Share change", numeric: true, render: (row) => fmt(row.shareChange, "pp") },
      ], { tickerKey: "ticker", focus: route?.focus, view: "peers", route, empty: "No peer rows for this sector." })
        : el("p", { class: "company-empty" }, "No peer comparison data is available for this sector."),
    ),
    panel(
      "Coverage note",
      "The peer universe is the scraper's current discovered-competitor set, not an exhaustive listed-company universe. Market-share values are displayed only where the market-share sidecar has a matching ticker; otherwise the industry-share field from the peer feed is used. No peer is labelled a buy or sell.",
      el("a", { class: "more-link", href: href("companies") }, "Open company activity →"),
    ),
  );
}
