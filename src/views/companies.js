// Companies — every holding on one page: what it did lately, and which
// policies cut its way.
//
// The other views are organised by kind of data (flow by feed, risk by
// grade, holdings by liquidity), which is right for those questions and
// wrong for "what has Suzlon done lately, and is policy behind it?" — that
// answer was spread over the agreements, filings and launches streams, the
// sector blocks and the policy list. The digest (analysis/company_digest.py)
// regroups the same data by company; this renders it as one card each.
//
// Loaded from its sidecar only when this view opens, so the payload every
// visitor downloads does not grow.

import { el, mount, disclosure } from "../core/dom.js";
import { shortDate, thesisStatus, LLM_MARK } from "../core/format.js";
import { href } from "../core/router.js";
import { resolve } from "../core/data.js";
import * as filters from "../core/filters.js";
import { panel, tickerLink } from "./table.js";
import { sparkline, seriesChange } from "../core/sparkline.js";
import { filterBar, filteredEmpty } from "./filterbar.js";

const SORTS = [
  ["recent", "Latest activity"],
  ["support", "Policy tailwinds"],
  ["pressure", "Policy headwinds"],
];
const ARROW = { tailwind: "▲", headwind: "▼", mixed: "◆" };

export function label(sector, labels) {
  return labels?.[sector]?.label || String(sector || "").replace(/_/g, " ");
}

const count = (c, dir) => (c.policies || []).filter((p) => p.direction === dir).length;

/**
 * The cards to show, filtered and ordered. Pure, so the ordering rules are
 * testable without a DOM:
 *   recent    newest activity first (the digest's own order)
 *   support   most tailwinds touching the company first
 *   pressure  most headwinds first — the ones to read before the rest
 * A company with nothing in the window is "quiet" and listed apart.
 */
export function companyRows(digest, active = {}, sort = "recent", thesisByTicker = {}) {
  const all = (digest?.companies || []).filter((c) =>
    filters.matchesHolding(c, active, { thesisByTicker }),
  );
  const busy = all.filter((c) => c.activity_count || c.policy_count);
  const quiet = all.filter((c) => !c.activity_count && !c.policy_count);
  if (sort === "support") {
    busy.sort((a, b) => count(b, "tailwind") - count(a, "tailwind"));
  } else if (sort === "pressure") {
    busy.sort((a, b) => count(b, "headwind") - count(a, "headwind"));
  }
  return { busy, quiet, total: all.length };
}

/** One policy's meta line: whose measure, how far along, when, and who read it. */
export function policyMeta(p) {
  return [
    p.names_company ? "names this company" : "",
    p.state ? `${p.state} government` : "central",
    String(p.status || "").replace(/_/g, " "),
    p.outlets > 1 ? `${p.outlets} outlets` : "",
    shortDate(p.date),
    LLM_MARK,
  ]
    .filter(Boolean)
    .join(" · ");
}

export function statusPill(status) {
  if (!status) return null;
  const mark = { Broken: "✕", Weakening: "!", Intact: "✓" }[status] || "?";
  return el(
    "span",
    { class: `pill pill-${thesisStatus(status)}` },
    el("span", { class: "pill-mark", "aria-hidden": "true" }, mark),
    status,
  );
}

function link(url, text) {
  return url ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, text) : text;
}

/** Markers for the price line: the card's own news and policies. */
export function markers(c) {
  return [
    ...(c.activity || []).map((a) => ({ date: a.date, kind: "activity", label: a.text })),
    ...(c.policies || [])
      .filter((p) => p.direction)
      .map((p) => ({ date: p.date, kind: p.direction, label: p.headline })),
  ];
}

export function priceLine(c) {
  const svg = sparkline(c.prices, markers(c));
  if (!svg) return null;
  const change = seriesChange(c.prices);
  return el(
    "div",
    { class: "company-spark" },
    el("div", { html: svg }),
    el(
      "span",
      { class: "evidence-meta" },
      `${c.prices.length} weeks ${change >= 0 ? "+" : ""}${change.toFixed(1)}% \u00b7 ` +
        "dots: news (blue), policy \u25b2 green / \u25bc red \u2014 hover for the headline",
    ),
  );
}

/** The holding's own news in the window, and the namesakes set aside from it. */
export function activitySection(c, windowDays) {
  return el(
    "section",
    {},
    el("h4", {}, `Recent activity${c.activity_count > (c.activity || []).length ? ` (${c.activity_count})` : ""}`),
    c.activity?.length
      ? el(
          "ul",
          { class: "evidence" },
          c.activity.map((a) =>
            el(
              "li",
              {},
              el("span", { class: `tag${a.kind === "adverse" ? " tag-risk" : ""}` }, a.kind),
              link(a.link, a.text),
              el(
                "span",
                { class: "evidence-meta" },
                [shortDate(a.date), a.source].filter(Boolean).join(" · "),
              ),
            ),
          ),
        )
      : el("p", { class: "company-empty" }, `No news attributed to it in ${windowDays} days.`),
    // Headlines the thesis check read as being about a namesake (a
    // foreign parent, a person): kept for inspection, not shown as news.
    c.namesakes?.length
      ? disclosure(
          `${c.namesakes.length} set aside \u2014 likely about another company or person ${LLM_MARK}`,
          el(
            "ul",
            { class: "evidence" },
            c.namesakes.map((a) => el("li", {}, link(a.link, a.text))),
          ),
        )
      : null,
  );
}

/** The policies touching the holding or its sector, with their direction. */
export function policySection(c, sectorName, windowDays) {
  return el(
    "section",
    {},
    el("h4", {}, "Policy"),
    c.policies?.length
      ? el(
          "ul",
          { class: "evidence" },
          c.policies.map((p) =>
            el(
              "li",
              {},
              p.direction
                ? el(
                    "span",
                    { class: `tag ${p.direction === "headwind" ? "tag-risk" : p.direction === "tailwind" ? "tag-opp" : ""}` },
                    `${ARROW[p.direction] || ""} ${p.direction}`,
                  )
                : null,
              link(p.link, p.headline),
              el("span", { class: "evidence-meta" }, policyMeta(p)),
            ),
          ),
        )
      : el("p", { class: "company-empty" }, `No policy touching ${sectorName} in ${windowDays} days.`),
  );
}

function card(c, labels, windowDays) {
  const sectorName = label(c.sector, labels);
  return el(
    "article",
    { class: "company-card", id: `company-${c.ticker}` },
    el(
      "header",
      { class: "company-head" },
      tickerLink(c.ticker),
      el("span", { class: "company-name" }, c.name || ""),
      statusPill(c.thesis_status),
      c.challenges?.length
        ? el("span", { class: "tag tag-risk", title: c.challenges[0].headline }, "thesis challenged")
        : null,
    ),
    el("p", { class: "company-sector" }, sectorName),
    // Folded on a phone, open elsewhere. Fifty-odd full cards made this
    // view 29,500px tall on a phone; folded, each is its latest headline and
    // two counts, and opening one shows the rest.
    el(
      "details",
      { class: "company-more", open: compactCards() ? null : "" },
      el("summary", { class: "company-more-summary" }, cardSummary(c)),
      priceLine(c),
      el(
        "div",
        { class: "company-cols" },
        activitySection(c, windowDays),
        policySection(c, sectorName, windowDays),
      ),
    ),
  );
}

/** A card's one-line account, shown when it is folded. */
export function cardSummary(c) {
  const latest = (c.activity || [])[0];
  const news = c.activity_count || 0;
  const policies = c.policy_count || 0;
  return [
    latest ? latest.text : "No news in the window",
    `${news} news \u00b7 ${policies} polic${policies === 1 ? "y" : "ies"}`,
  ].join(" \u2014 ");
}

function compactCards() {
  return typeof window !== "undefined" && Boolean(window.matchMedia?.("(max-width: 640px)").matches);
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const params = (route && route.params) || {};
  const active = filters.read(route);
  const sort = SORTS.some(([k]) => k === params.sort) ? params.sort : "recent";
  const digest = await resolve(b, "company_digest");
  const labels = payload?.sectors || {};
  const sectors = Object.keys(payload?.watchlist || {})
    .filter((s) => s !== "macro_indicators")
    .sort();

  if (!digest?.companies) {
    mount(
      container,
      el("header", { class: "view-head" }, el("h2", { class: "view-title" }, "Companies")),
      panel(null, "The company digest has not been built yet; it appears after the next daily run."),
    );
    return;
  }

  const { busy, quiet } = companyRows(digest, active, sort, filters.thesisIndex(b));
  const windowDays = digest.window_days || 30;
  const anyFilter = filters.activeCount(active) > 0;

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Companies"),
      el(
        "p",
        { class: "view-sub" },
        `Each holding's news and the policies touching it, last ${windowDays} days · ${busy.length} with something new, ${quiet.length} quiet`,
      ),
    ),
    filterBar({
      view: "companies",
      route,
      filters: active,
      fields: ["q", "sector", "thesis"],
      sectors,
      summary: anyFilter ? `${busy.length + quiet.length} of ${digest.companies.length} holdings` : "",
    }),
    el(
      "nav",
      { class: "lens-nav" },
      SORTS.map(([key, text]) =>
        el(
          "a",
          { class: `lens${key === sort ? " lens-active" : ""}`, href: href("companies", { ...params, sort: key }) },
          text,
        ),
      ),
    ),
    busy.length
      ? el("div", { class: "company-grid" }, busy.map((c) => card(c, labels, windowDays)))
      : panel(null, null, anyFilter ? filteredEmpty("companies", params, "holdings") : "Nothing new for any holding."),
    quiet.length
      ? disclosure(
          `${quiet.length} quiet — no attributed news or policy in ${windowDays} days`,
          el(
            "p",
            { class: "company-quiet" },
            quiet.map((c, i) => [i ? ", " : "", tickerLink(c.ticker)]),
          ),
        )
      : null,
  );

  if (route?.focus) {
    document.getElementById(`company-${route.focus}`)?.scrollIntoView({ block: "start" });
  }
}
