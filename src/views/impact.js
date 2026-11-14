// Company Impact — a review queue ordered by the dimensions the reader chose.
// This is a transparent ordering of existing scraper fields, not a new
// composite investment score or a buy/sell recommendation.

import { el, mount } from "../core/dom.js";
import { resolve } from "../core/data.js";
import { href } from "../core/router.js";
import { dataTable, panel, tickerLink } from "./table.js";

const SEVERITY = { critical: 3, high: 2, medium: 1, low: 0 };

function numeric(value) {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(String(value).replace(/[,%+₹\s]/g, ""));
  return Number.isFinite(n) ? n : null;
}

function priceMove(prices, weeks = 4) {
  if (!Array.isArray(prices) || prices.length < 2) return null;
  const last = prices[prices.length - 1];
  const base = prices[Math.max(0, prices.length - 1 - weeks)];
  const start = numeric(Array.isArray(base) ? base[1] : null);
  const end = numeric(Array.isArray(last) ? last[1] : null);
  return start > 0 && end !== null ? ((end / start) - 1) * 100 : null;
}

function bestWarning(rows) {
  return [...(rows || [])].sort((a, b) =>
    (SEVERITY[String(b.severity || "").toLowerCase()] ?? -1) -
    (SEVERITY[String(a.severity || "").toLowerCase()] ?? -1),
  )[0] || null;
}

export function buildImpactRows(payload, digest = {}) {
  const warnings = payload?.briefing?.early_warnings || [];
  const warningByTicker = new Map();
  for (const warning of warnings) {
    const key = String(warning?.ticker || "").toUpperCase();
    if (!key) continue;
    const previous = warningByTicker.get(key);
    if (!previous || (SEVERITY[String(warning.severity || "").toLowerCase()] ?? -1) >
      (SEVERITY[String(previous.severity || "").toLowerCase()] ?? -1)) {
      warningByTicker.set(key, warning);
    }
  }

  const digestByTicker = new Map(
    (digest?.companies || []).map((company) => [String(company.ticker || "").toUpperCase(), company]),
  );
  const rows = [];
  for (const [sector, stocks] of Object.entries(payload?.watchlist || {})) {
    if (sector === "macro_indicators" || !Array.isArray(stocks)) continue;
    for (const stock of stocks) {
      if (!stock?.ticker) continue;
      const ticker = String(stock.ticker).toUpperCase();
      const screener = stock.screener || {};
      const score = stock.score || {};
      const company = digestByTicker.get(ticker) || {};
      const warning = warningByTicker.get(ticker) || null;
      const policies = company.policies || [];
      const tailwinds = policies.filter((p) => p.direction === "tailwind");
      const headwinds = policies.filter((p) => p.direction === "headwind");
      const change4w = priceMove(company.prices);
      const growth = numeric(screener.revenue_ttm_growth_pct ?? screener.revenue_yoy_pct ?? stock.revenue_growth ?? stock.growth_pct);
      const roce = numeric(screener.roce);
      rows.push({
        ticker,
        name: stock.name || company.name || ticker,
        sector,
        price: stock.price ?? screener.current_price ?? null,
        warning,
        severityRank: SEVERITY[String(warning?.severity || "").toLowerCase()] ?? -1,
        change4w,
        growth,
        roce,
        fundamentalScore: numeric(score.fundamental_score),
        fiiChange: numeric(screener.fii_change),
        diiChange: numeric(screener.dii_change),
        promoterChange: numeric(screener.promoter_change),
        policyCount: policies.length,
        tailwindCount: tailwinds.length,
        headwindCount: headwinds.length,
        activityCount: Number(company.activity_count) || 0,
        mtf: screener.mtf_pct ?? screener.mtf ?? stock.mtf_pct ?? stock.mtf ?? null,
        signal: warning?.signal || warning?.category || "",
        warningConfidence: warning?.confidence || "",
        thesisStatus: company.thesis_status || "",
      });
    }
  }
  return rows.sort((a, b) =>
    b.severityRank - a.severityRank ||
    (Math.abs(b.change4w ?? 0) - Math.abs(a.change4w ?? 0)) ||
    (b.growth ?? -Infinity) - (a.growth ?? -Infinity) ||
    (b.roce ?? -Infinity) - (a.roce ?? -Infinity) ||
    a.ticker.localeCompare(b.ticker),
  );
}

function signed(value, suffix = "%") {
  if (value === null || value === undefined) return "Not available";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}

function institutionalLine(row) {
  const parts = [
    row.fiiChange === null ? "" : `FII ${signed(row.fiiChange, "pp")}`,
    row.diiChange === null ? "" : `DII ${signed(row.diiChange, "pp")}`,
    row.promoterChange === null ? "" : `Promoter ${signed(row.promoterChange, "pp")}`,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "No holding-change data";
}

export async function render(container, { payload, route }) {
  const digest = await resolve(payload?.briefing || {}, "company_digest");
  const rows = buildImpactRows(payload, digest);
  const highRisk = rows.filter((row) => row.severityRank >= 2).length;
  const mtfCount = rows.filter((row) => row.mtf !== null && row.mtf !== undefined && row.mtf !== "").length;

  mount(
    container,
    el("header", { class: "view-head" },
      el("h2", { class: "view-title" }, "Company Impact"),
      el("p", { class: "view-sub" },
        `As of ${payload?.last_updated || "latest pipeline run"} · ${rows.length} companies ranked for review · ${highRisk} high / critical warnings`,
      ),
    ),
    el("div", { class: "stat-row" },
      el("div", { class: "stat-tile" }, el("div", { class: "stat-label" }, "High / critical business risks"), el("div", { class: "stat-value" }, String(highRisk)), el("div", { class: "stat-detail" }, "Existing early-warning engine")),
      el("div", { class: "stat-tile" }, el("div", { class: "stat-label" }, "Companies with 4-week price history"), el("div", { class: "stat-value" }, String(rows.filter((r) => r.change4w !== null).length)), el("div", { class: "stat-detail" }, "Computed from company digest")),
      el("div", { class: "stat-tile" }, el("div", { class: "stat-label" }, "Institutional changes"), el("div", { class: "stat-value" }, String(rows.filter((r) => r.fiiChange !== null || r.diiChange !== null).length)), el("div", { class: "stat-detail" }, "FII / DII / promoter holding deltas")),
      el("div", { class: "stat-tile" }, el("div", { class: "stat-label" }, "MTF coverage"), el("div", { class: "stat-value" }, mtfCount ? String(mtfCount) : "Not tracked"), el("div", { class: "stat-detail" }, mtfCount ? "Rows with an explicit MTF field" : "No MTF field in the current payload")),
    ),
    panel(
      "Impact-ranked review queue",
      "Priority order: business impact (warning severity), market reaction (absolute 4-week move), market opportunity (revenue growth), then financial strength (ROCE). Each column remains visible; this is a review order, not a blended score or investment recommendation.",
      rows.length ? dataTable(rows, [
        { key: "ticker", label: "Company", render: (row) => tickerLink(row.ticker) },
        { key: "warning", label: "Business impact", render: (row) => row.warning ? `${row.warning.severity}: ${row.signal}` : "No active warning" },
        { key: "change4w", label: "Market reaction", numeric: true, render: (row) => signed(row.change4w) },
        { key: "growth", label: "Revenue growth", numeric: true, render: (row) => signed(row.growth) },
        { key: "roce", label: "ROCE", numeric: true, render: (row) => signed(row.roce) },
        { key: "institutional", label: "FII / DII / promoter", sortable: false, render: institutionalLine },
        { key: "policyCount", label: "Policy", numeric: true, render: (row) => `+${row.tailwindCount} / −${row.headwindCount}` },
      ], { tickerKey: "ticker", focus: route?.focus, view: "impact", route, empty: "No companies are available." })
        : el("p", { class: "company-empty" }, "No company rows are available in the current watchlist."),
    ),
    panel(
      "How to read the queue",
      "Business impact is sourced from the existing early-warning engine. Market reaction is calculated from the latest and four-weeks-prior weekly prices in the company digest. Opportunity uses the best available revenue-growth field. Financial strength uses reported ROCE. Missing values are shown as unavailable rather than treated as zero. MTF is shown only when an explicit MTF field exists in the source payload.",
      el("a", { class: "more-link", href: href("risk") }, "Inspect all risk signals →"),
      el("a", { class: "more-link", href: href("companies") }, "Open company activity and policy detail →"),
    ),
  );
}
