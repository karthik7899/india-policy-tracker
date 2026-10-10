// Company — everything known about one holding, on one page.
//
// Before this page one company was spread over five views. The Holdings
// drawer had its prices and coverage but not its thesis grade (Syrma, graded
// Broken, showed no sign of it there); Risk had the grade but not the news;
// Companies had the news and policy; Network had its partners. Every ticker
// in the dashboard now opens this page, so what a click shows no longer
// depends on where it was made.
//
// Assembled from the same section builders the other views use, so a fix to
// how coverage or signals render reaches both places.

import { el, mount } from "../core/dom.js";
import { resolve, loadCoverage, loadGraph, loadProposals } from "../core/data.js";
import { href } from "../core/router.js";
import { panel } from "./table.js";
import {
  factsList,
  holdingSignals,
  signalsSection,
  newsSections,
  thesisSection,
  upsideText,
} from "./holdings.js";
import { priceLine, activitySection, policySection, statusPill, label } from "./companies.js";
import { pickBook, positionOf } from "../core/portfolio.js";
import { eventsFor, scorecardFor, kindLabel } from "../core/calendar.js";
import { pct } from "../core/format.js";

const EDGE_LABEL = {
  partner: "partner",
  supplier_customer: "supplier or customer",
  competitor: "competitor",
  anchor_demand: "demand anchor",
  input_cost: "input cost",
};

/** The holding with this ticker, its sector attached; null when not held. */
export function findHolding(watchlist, ticker) {
  const key = String(ticker || "").toUpperCase();
  if (!key) return null;
  for (const [sector, stocks] of Object.entries(watchlist || {})) {
    if (sector === "macro_indicators" || !Array.isArray(stocks)) continue;
    const stock = stocks.find((s) => s && String(s.ticker || "").toUpperCase() === key);
    if (stock) return { ...stock, sector };
  }
  return null;
}

/**
 * The graph edges that name this holding directly, and those that reach it
 * through its sector. Kept apart: "Vivo is Dixon's partner" and "Apple's
 * demand moves every electronics maker" are different strengths of link.
 */
export function companyEdges(edges, ticker, sector) {
  const key = String(ticker || "").toUpperCase();
  const own = [];
  const viaSector = [];
  for (const e of edges || []) {
    const src = String(e.src || "").toUpperCase();
    const dst = String(e.dst || "").toUpperCase();
    if (src === key || dst === key) {
      own.push({ ...e, other: src === key ? e.dst : e.src });
    } else if (sector && String(e.dst || "") === sector) {
      viaSector.push(e);
    }
  }
  return { own, viaSector };
}

/** Read-throughs whose chain ends at this holding. */
export function readThroughsFor(rows, ticker) {
  const key = String(ticker || "").toUpperCase();
  return (rows || []).filter((r) =>
    (r.tickers || []).some((t) => String(t).toUpperCase() === key),
  );
}

/** Holdings whose ticker or name starts like the one asked for. */
export function nearMisses(watchlist, ticker, limit = 5) {
  const q = String(ticker || "").toLowerCase();
  if (!q) return [];
  const out = [];
  for (const [sector, stocks] of Object.entries(watchlist || {})) {
    if (sector === "macro_indicators" || !Array.isArray(stocks)) continue;
    for (const s of stocks) {
      const t = String(s?.ticker || "").toLowerCase();
      const n = String(s?.name || "").toLowerCase();
      if (t.startsWith(q.slice(0, 3)) || n.startsWith(q.slice(0, 3))) out.push(s);
    }
  }
  return out.slice(0, limit);
}

function healthBlock(health) {
  if (!health?.status) return null;
  return el(
    "div",
    { class: "drawer-section" },
    el("h4", {}, "Thesis grade"),
    el("p", {}, statusPill(health.status)),
    health.reasons?.length
      ? el("ul", { class: "evidence" }, health.reasons.map((r) => el("li", {}, r)))
      : el("p", { class: "evidence-meta" }, "Nothing in the evidence counts against it."),
    // Context is shown but does not grade: ownership and valuation flags
    // describe the price, not whether the business case still holds.
    health.context?.length
      ? el(
          "p",
          { class: "evidence-meta" },
          `Context, not graded: ${health.context.join("; ")}`,
        )
      : null,
  );
}

function partnersSection(links, proposals, ticker) {
  const { own, viaSector } = links;
  if (!own.length && !viaSector.length && !proposals.length) return null;
  return panel(
    "Partners and links",
    "From the entity graph. A partner's trouble reaches the holding as a read-through; its own good news does not.",
    own.length
      ? el(
          "ul",
          { class: "evidence" },
          own.map((e) =>
            el(
              "li",
              {},
              el("span", { class: "tag" }, EDGE_LABEL[e.type] || e.type),
              " ",
              String(e.other || ""),
              e.evidence && String(e.evidence).toLowerCase() !== "curated"
                ? el("span", { class: "evidence-meta" }, `“${String(e.evidence).slice(0, 120)}”`)
                : null,
            ),
          ),
        )
      : null,
    viaSector.length
      ? el(
          "p",
          { class: "evidence-meta" },
          `${viaSector.length} sector-wide link(s): `,
          viaSector
            .slice(0, 6)
            .map((e) => `${e.src} (${EDGE_LABEL[e.type] || e.type})`)
            .join(", "),
          viaSector.length > 6 ? "…" : "",
        )
      : null,
    proposals.length
      ? el(
          "p",
          { class: "evidence-meta" },
          `${proposals.length} proposed partner(s) awaiting review: `,
          proposals.map((p) => p.counterparty).join(", "),
        )
      : null,
    el("p", {}, el("a", { href: href("network", { focus: ticker }) }, "See it on the Network view →")),
  );
}

function readThroughSection(rows) {
  if (!rows.length) return null;
  return panel(
    `Read-throughs (${rows.length})`,
    "Second-order: news about someone else that may reach this holding. A hypothesis with its reasoning, not evidence.",
    el(
      "ul",
      { class: "evidence" },
      rows.map((r) =>
        el(
          "li",
          {},
          el("span", { class: `tag tag-${r.direction === "risk" ? "risk" : "opp"}` }, r.direction || ""),
          " ",
          r.trigger || "",
          el("span", { class: "evidence-meta" }, (r.chain || []).join(" → ")),
        ),
      ),
    ),
  );
}

export async function render(container, { payload, route }) {
  const ticker = route?.focus;
  const stock = findHolding(payload?.watchlist, ticker);
  if (!stock) {
    const near = nearMisses(payload?.watchlist, ticker);
    mount(
      container,
      el("header", { class: "view-head" }, el("h2", { class: "view-title" }, "Company")),
      panel(
        null,
        ticker ? `${ticker} is not on the watchlist.` : "No company chosen.",
        near.length
          ? el(
              "p",
              {},
              "Did you mean: ",
              near.map((s, i) => [
                i ? ", " : "",
                el("a", { href: href("company", { focus: s.ticker }) }, s.ticker),
              ]),
            )
          : el("p", {}, el("a", { href: href("companies") }, "Browse every holding →")),
      ),
    );
    return;
  }

  const key = String(stock.ticker).toUpperCase();
  const b = payload?.briefing || {};
  const labels = payload?.sectors || {};
  const sectorName = label(stock.sector, labels);
  const [digest, coverage, edges, proposals, portfolio, calendar, results] = await Promise.all([
    resolve(b, "company_digest"),
    loadCoverage(key),
    loadGraph(),
    loadProposals(),
    resolve(b, "portfolio"),
    resolve(b, "event_calendar"),
    resolve(b, "results"),
  ]);
  const card = (digest?.companies || []).find((c) => String(c.ticker).toUpperCase() === key);
  const health = b.thesis_health?.[key];
  const check = b.thesis_check?.holdings?.[key];
  const windowDays = digest?.window_days || 30;

  if (typeof document !== "undefined") document.title = `${key} · India Policy Tracker`;

  mount(
    container,
    el(
      "header",
      { class: "view-head company-page-head" },
      el(
        "p",
        { class: "crumbs" },
        el("a", { href: href("companies") }, "Companies"),
        " › ",
        el("a", { href: href("companies", { sector: stock.sector }) }, sectorName),
      ),
      el(
        "h2",
        { class: "view-title" },
        el("span", { class: "company-page-ticker" }, key),
        " ",
        stock.name || "",
        " ",
        statusPill(health?.status || card?.thesis_status),
      ),
      el(
        "p",
        { class: "view-sub" },
        el("a", { href: href("ask", { focus: key }) }, `Ask about ${key} \u2192`),
        " \u00b7 ",
        [
          stock.price ? `Price ${stock.price}` : "",
          stock.target ? `target ${stock.target}` : "",
          stock.growth_pct ? `upside ${upsideText(stock)}` : "",
          stock.rating || "",
        ]
          .filter(Boolean)
          .join(" · "),
      ),
    ),
    el(
      "div",
      { class: "company-page" },
      el(
        "div",
        { class: "company-page-main" },
        panel(
          "Why you own it",
          null,
          thesisSection(stock.catalyst, check),
          healthBlock(health),
        ),
        card
          ? panel(
              `News and policy, last ${windowDays} days`,
              null,
              el(
                "div",
                { class: "company-cols" },
                activitySection(card, windowDays),
                policySection(card, sectorName, windowDays),
              ),
            )
          : null,
        panel("Everything written about it", null, newsSections(stock, payload, coverage)),
      ),
      el(
        "aside",
        { class: "company-page-side" },
        panel("Numbers", null, card ? priceLine(card) : null, factsList(stock)),
        positionSection(pickBook(portfolio), key),
        datesSection(eventsFor(calendar, key), scorecardFor(results, key)),
        (() => {
          const signals = holdingSignals(payload, key);
          return signals.length ? panel(null, null, signalsSection(signals)) : null;
        })(),
        readThroughSection(readThroughsFor(b.read_throughs, key)),
        partnersSection(
          companyEdges(edges, key, stock.sector),
          (proposals || []).filter(
            (p) => p.status === "pending" && String(p.holding).toUpperCase() === key,
          ),
          key,
        ),
      ),
    ),
  );
}

/**
 * The holding as a position in the book (analysis/portfolio.py): its size,
 * how long it would take to sell, any limit it breaks, and any order the
 * rebalance would send. Nothing when the book does not hold it.
 */
export function positionSection(book, ticker) {
  if (!book || book.error) return null;
  const p = positionOf(book, ticker);
  const order = (book.orders?.rows || []).find((o) => o.ticker === ticker);
  if (!p && !order) return null;
  const breaches = (book.breaches || []).filter((b) => b.subject === ticker);
  const n = (v, d = 2, s = "") => (typeof v === "number" ? `${v.toFixed(d)}${s}` : "—");
  const facts = p
    ? [
        ["Weight", `${n(p.weight_pct, 2, "%")} of the book (target ${n(p.target_pct, 2, "%")})`],
        ["Value", `₹${n(p.value_cr, 2)} Cr · ${p.quantity.toLocaleString("en-IN")} shares`],
        typeof p.pnl_pct === "number" ? ["P&L", `${pct(p.pnl_pct, 2)} on cost`] : null,
        typeof p.days_to_exit === "number"
          ? ["To sell", `${n(p.days_to_exit, 1)} days at 20% of daily value traded`]
          : ["To sell", "no traded value on record"],
        typeof p.ownership_pct === "number" ? ["Owned", `${n(p.ownership_pct, 2, "%")} of the company`] : null,
        typeof p.beta === "number" ? ["Beta", `${n(p.beta, 2)} to the ${book.benchmark?.label || "benchmark"}`] : null,
      ].filter(Boolean)
    : [];
  return panel(
    "In the portfolio",
    book.kind === "model" ? `${book.name} — a model, not real holdings.` : book.name,
    facts.length
      ? el("dl", { class: "portfolio-stats" }, facts.map(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]))
      : el("p", { class: "company-empty" }, "Not held yet."),
    breaches.length
      ? el("ul", { class: "portfolio-breaches" }, breaches.map((b) => el("li", {}, b.message)))
      : null,
    order
      ? el(
          "p",
          { class: "portfolio-line" },
          el("strong", { class: order.side === "SELL" ? "order-sell" : "order-buy" }, order.side),
          ` ${order.quantity.toLocaleString("en-IN")} shares (₹${n(order.value_cr, 2)} Cr): ${order.reason}.`,
        )
      : null,
    el("p", { class: "evidence-meta" }, el("a", { href: href("portfolio", { book: book.id }) }, "The whole book \u2192")),
  );
}

/**
 * What the holding has coming up, and what its latest results said
 * (analysis/event_calendar.py). Nothing when there is neither.
 */
export function datesSection(events, card) {
  if (!(events || []).length && !card) return null;
  return panel(
    "Dates and results",
    null,
    (events || []).length
      ? el(
          "ul",
          { class: "evidence" },
          events.slice(0, 5).map((e) =>
            el(
              "li",
              {},
              el("strong", {}, e.date),
              ` ${kindLabel(e.kind)}: `,
              e.link ? el("a", { href: e.link, target: "_blank", rel: "noopener noreferrer" }, e.title) : e.title,
              e.detail ? el("span", { class: "evidence-meta" }, e.detail) : null,
            ),
          ),
        )
      : el("p", { class: "company-empty" }, "No date announced in the next 45 days."),
    card
      ? el(
          "p",
          { class: "portfolio-line" },
          el("strong", {}, `${card.quarter || "Latest"} quarter: `),
          card.summary || "",
          el(
            "span",
            { class: "evidence-meta" },
            `Seen ${card.detected}; set against a year earlier, with no consensus to call it a beat or a miss.`,
          ),
        )
      : null,
    el("p", { class: "evidence-meta" }, el("a", { href: href("calendar") }, "The whole calendar \u2192")),
  );
}
