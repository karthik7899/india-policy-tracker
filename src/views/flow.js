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
import { shortDate, crore, sizeLabel } from "../core/format.js";
import { href } from "../core/router.js";
import * as filters from "../core/filters.js";
import { dataTable, panel } from "./table.js";
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
];

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
  if (item.reader === "llm") parts.push("LLM only \u00b7 unverified");
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
  return [
    effects,
    String(item.status || "").replace(/_/g, " "),
    item.state ? `${item.state} government` : "",
    "LLM reading",
  ]
    .filter(Boolean)
    .join(" \u00b7 ");
}

/** Normalise the differing shapes into one row. */
function normalise(item, streamLabel, labels) {
  return {
    when: item.date || item.published || "",
    what: item.filing || item.headline || item.title || item.signal || "",
    who: item.company || item.ticker || item.name || (item.actors || [])[0] || "",
    source: item.source || streamLabel,
    link: item.link || item.url || "",
    detail: item.event_type ? eventDetail(item) : item.effects ? policyDetail(item, labels) : "",
  };
}

const CAP = 80;

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const stream = route?.params?.stream || "all";
  const params = (route && route.params) || {};
  const active = filters.read(route);

  let all = [];
  if (stream === "all") {
    for (const [, label, key] of STREAMS) {
      if (!key) continue;
      for (const item of b[key] || []) all.push(normalise(item, label, payload?.sectors));
    }
    // Interleaved by date rather than concatenated: concatenation is exactly
    // what let one source consume every slot in the filings section.
    all.sort((a, c) => String(c.when).localeCompare(String(a.when)));
  } else {
    const entry = STREAMS.find(([k]) => k === stream);
    all = (b[entry?.[2]] || []).map((i) => normalise(i, entry?.[1], payload?.sectors));
  }

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
        anyFilter
          ? `${matched.length} of ${all.length} items`
          : `${all.length} items`,
      ),
    ),

    filterBar({
      view: "flow",
      route,
      filters: active,
      fields: ["q", "days"],
      summary: matched.length > CAP ? `showing the newest ${CAP}` : "",
    }),

    streamNav(stream, route || { params: {} }),
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
            : "Nothing in this stream.",
        },
      ),
    ),
  );
}
