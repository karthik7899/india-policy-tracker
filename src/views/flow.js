// Flow — everything that arrived, filtered by where it came from.
//
// Absorbs five tabs: Policy Logs, News & Agreements, Product Launches,
// Corporate Filings and Institutional Activity. They were five renderings of
// the same shape — dated item, source, link — separated by which scraper
// produced them, which is a fact about our pipeline rather than about the
// reader's question.
//
// One list with a source filter answers "what happened today" in one place,
// and still answers "what did the exchanges publish" for anyone who wants it.

import { el, mount } from "../core/dom.js";
import { shortDate, crore, sizeLabel, LLM_MARK } from "../core/format.js";
import { href } from "../core/router.js";
import { resolve } from "../core/data.js";
import * as filters from "../core/filters.js";
import { dataTable, panel, pillTag, convictionToggle } from "./table.js";
import { catalystPill, HIGH } from "../core/catalyst.js";
import { filterBar, filteredEmpty } from "./filterbar.js";

const STREAMS = [
  ["all", "Everything", null],
  ["filings", "Filings", "corporate_filings"],
  ["agreements", "Agreements", "corporate_agreements"],
  ["launches", "Launches", "product_launches"],
  ["institutional", "Institutional", "institutional_activity"],
  ["events", "Market events", "market_events"],
  ["global", "Global", "global_market_news"],
  ["policy", "Policy", "policy_impacts"],
  ["partnerships", "Gov't partnerships", "policy_partnerships"],
];

// How binding a policy row is (analysis/policy_impact.py): a measure approved
// or in force, a draft, or a government's MoU or pact with a company.
export const STRENGTH_LABEL = { hard: "Hard policy", proposed: "Proposed", soft: "Soft partnership" };

function streamNav(active, route) {
  return el(
    "nav",
    { class: "lens-nav" },
    STREAMS.map(([key, label]) =>
      el(
        "a",
        {
          class: `lens${key === active ? " lens-active" : ""}`,
          href: href("flow", { ...route.params, stream: key }),
        },
        label,
      ),
    ),
  );
}

/**
 * What a classified event adds beyond its headline: who was on the other side
 * of a tie-up, and how big the deal was against the holding it happened to.
 *
 * Both are omitted rather than shown as blanks when unknown. An event with no
 * `amount_cr` is one whose size the guards would not attribute to a single
 * company — a sector budget, a joint venture's capital, an MoU — and printing
 * nothing is the honest rendering of "not known"; a dash would read as zero.
 */
export function eventDetail(item) {
  const parts = [];
  const others = item.counterparties || [];
  if (others.length) parts.push(`with ${others.join(", ")}`);
  if (typeof item.amount_cr === "number") parts.push(crore(item.amount_cr));
  for (const [ticker, m] of Object.entries(item.materiality || {})) {
    const label = sizeLabel(m && m.pct_of_revenue, m && m.band);
    if (label) parts.push(`${label.replace("of revenue", `of ${ticker} revenue`)}`);
  }
  if (item.certainty && item.certainty !== "completed") parts.push(item.certainty);
  // Which readers found it (analysis/llm_reader.reconcile). Unverified is
  // spelled out: an LLM-only event is shown but grades nothing, and a reader
  // who cannot tell that from the row would weigh it like the others.
  // How much to believe it (analysis/event_evidence.py). Only stated for
  // events about a holding — that is where the check is made.
  if ((item.actors || []).length) {
    if (item.confirmation) parts.push(`confirmed by ${item.confirmation.source} filing`);
    else if ((item.reports || 1) >= 2) parts.push(`${item.reports} outlets`);
    else parts.push("single report");
  }
  if (item.reader === "llm") parts.push(`${LLM_MARK} only \u00b7 unverified`);
  else if (item.corroborated === true) parts.push("corroborated");
  else if (item.llm_reading) parts.push(`LLM read it as ${String(item.llm_reading.event_type).replace(/_/g, " ")}`);
  return parts.join(" \u00b7 ");
}

const ARROW = { tailwind: "\u25b2", headwind: "\u25bc", mixed: "\u25c6" };

function sectorName(key, labels) {
  if (labels?.[key]?.label) return labels[key].label;
  return String(key || "")
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/**
 * A policy row (analysis/policy_impact.py): which of our sectors the measure
 * helps or hurts, how far along it is, and whose measure it is. Always
 * labelled as the LLM's reading — it is scored, not reviewed.
 */
export function policyDetail(item, labels = {}) {
  const effects = (item.effects || [])
    .map((e) => `${ARROW[e.direction] || ""} ${sectorName(e.sector, labels)}`.trim())
    .join(", ");
  const status = String(item.status || "").replace(/_/g, " ");
  const strength = STRENGTH_LABEL[item.strength];
  return [
    effects,
    // "Hard policy, in force"; a row from before strength was recorded keeps
    // its bare status.
    strength && strength.toLowerCase() !== status ? `${strength}, ${status}` : status,
    item.state ? `${item.state} government` : "",
    item.outlets > 1 ? `${item.outlets} outlets` : "",
    LLM_MARK,
  ]
    .filter(Boolean)
    .join(" \u00b7 ");
}

/**
 * A government's MoU or pact with a company: no measure yet, so not a policy
 * row. The sectors and holdings are the tie-up event's own.
 */
export function partnershipDetail(item, labels = {}) {
  return [
    STRENGTH_LABEL.soft,
    item.government && item.government !== "Government" ? `${item.government}${item.government === "Centre" ? "" : " government"}` : "",
    (item.sectors || []).map((s) => sectorName(s, labels)).join(", "),
    item.certainty && item.certainty !== "completed" ? item.certainty : "",
  ]
    .filter(Boolean)
    .join(" \u00b7 ");
}

/** Normalise the differing shapes into one row. */
export function normalise(item, streamLabel, labels) {
  return {
    // How settled it is: a policy's strength, an order win's stage.
    pill: catalystPill(item),
    when: item.date || item.published || "",
    what: item.filing || item.headline || item.title || item.signal || "",
    who: item.company || item.ticker || item.name || (item.actors || item.tickers || [])[0] || "",
    source: item.source || streamLabel,
    link: item.link || item.url || "",
    detail: item.event_type
      ? eventDetail(item)
      : item.effects
        ? policyDetail(item, labels)
        : item.strength === "soft"
          ? partnershipDetail(item, labels)
          : "",
  };
}

const CAP = 80;

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const stream = route?.params?.stream || "all";
  const params = (route && route.params) || {};
  const active = filters.read(route);

  // Each feed is its own file (dashboard/sidecars.py), fetched when this view
  // opens; "Everything" fetches them together.
  const wanted = STREAMS.filter(([key, , field]) => field && (stream === "all" || key === stream));
  const feeds = await Promise.all(wanted.map(([, , field]) => resolve(b, field)));
  let all = [];
  wanted.forEach(([, label], i) => {
    for (const item of feeds[i] || []) all.push(normalise(item, label, payload?.sectors));
  });
  if (stream === "all") {
    // Interleaved by date rather than concatenated: concatenation is exactly
    // what let one source consume every slot in the filings section.
    all.sort((a, c) => String(c.when).localeCompare(String(a.when)));
  }

  // Hard policies and confirmed wins only, when asked: what has happened,
  // without the drafts, MoUs, L-1 bids and reports around it.
  const conviction = params.conviction === "high";
  if (conviction) all = all.filter((r) => r.pill && HIGH.has(r.pill.kind));

  // Filter BEFORE the cap, not after. Capping first would search only the
  // newest eighty items and report "no matches" for something that is
  // genuinely in the stream, a step behind where the reader is looking.
  const matched = filters.applyItems(all, active);
  const rows = matched.slice(0, CAP);
  const anyFilter = filters.activeCount(active) > 0;

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Flow"),
      el(
        "p",
        { class: "view-sub" },
        (anyFilter ? `${matched.length} of ${all.length} items` : `${all.length} items`) +
          (conviction ? " \u00b7 hard policies and confirmed wins only" : ""),
      ),
    ),

    filterBar({
      view: "flow",
      route,
      filters: active,
      fields: ["q", "days"],
      summary: matched.length > CAP ? `showing the newest ${CAP}` : "",
    }),

    el(
      "div",
      { class: "flow-controls" },
      streamNav(stream, route || { params: {} }),
      convictionToggle("flow", params, conviction),
    ),
    panel(
      null,
      null,
      dataTable(
        rows,
        [
          { key: "when", label: "Date", render: (r) => shortDate(r.when) },
          { key: "who", label: "Company" },
          {
            key: "what",
            label: "What",
            sortable: false,
            render: (r) => [
              pillTag(r.pill),
              r.link
                ? el("a", { href: r.link, target: "_blank", rel: "noopener noreferrer" }, r.what)
                : r.what,
              r.detail ? el("span", { class: "evidence-meta flow-detail" }, r.detail) : null,
            ],
          },
          { key: "source", label: "Source" },
        ],
        {
          tickerKey: "who",
          focus: route?.focus,
          view: "flow",
          route,
          empty: anyFilter
            ? filteredEmpty("flow", params, "items")
            : conviction
              ? "No hard policy or confirmed win in this stream."
              : "Nothing in this stream.",
        },
      ),
    ),
  );
}
