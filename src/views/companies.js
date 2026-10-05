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
import { shortDate, thesisStatus } from "../core/format.js";
import { href } from "../core/router.js";
import { resolve } from "../core/data.js";
import * as filters from "../core/filters.js";
import { panel, tickerLink } from "./table.js";
import { filterBar, filteredEmpty } from "./filterbar.js";

const SORTS = [
  ["recent", "Latest activity"],
  ["support", "Policy tailwinds"],
  ["pressure", "Policy headwinds"],
];
const ARROW = { tailwind: "▲", headwind: "▼", mixed: "◆" };

function label(sector, labels) {
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
    shortDate(p.date),
    "LLM reading",
  ]
    .filter(Boolean)
    .join(" · ");
}

function statusPill(status) {
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

function card(c, labels, windowDays) {
  const sectorName = label(c.sector, labels);
  return el(
    "article",
    { class: "company-card", id: `company-${c.ticker}` },
    el(
      "header",
      { class: "company-head" },
      tickerLink(c.ticker, "holdings"),
      el("span", { class: "company-name" }, c.name || ""),
      statusPill(c.thesis_status),
      c.challenges?.length
        ? el("span", { class: "tag tag-risk", title: c.challenges[0].headline }, "thesis challenged")
        : null,
    ),
    el("p", { class: "company-sector" }, sectorName),
    el(
      "div",
      { class: "company-cols" },
      el(
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
      ),
      el(
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
      ),
    ),
  );
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
            quiet.map((c, i) => [i ? ", " : "", tickerLink(c.ticker, "holdings")]),
          ),
        )
      : null,
  );

  if (route?.focus) {
    document.getElementById(`company-${route.focus}`)?.scrollIntoView({ block: "start" });
  }
}
