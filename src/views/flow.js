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
import { shortDate } from "../core/format.js";
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

/** Normalise the differing shapes into one row. */
function normalise(item, streamLabel) {
  return {
    when: item.date || item.published || "",
    what: item.filing || item.headline || item.title || item.signal || "",
    who: item.company || item.ticker || item.name || (item.actors || [])[0] || "",
    source: item.source || streamLabel,
    link: item.link || item.url || "",
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
      for (const item of b[key] || []) all.push(normalise(item, label));
    }
    // Interleaved by date rather than concatenated: concatenation is exactly
    // what let one source consume every slot in the filings section.
    all.sort((a, c) => String(c.when).localeCompare(String(a.when)));
  } else {
    const entry = STREAMS.find(([k]) => k === stream);
    all = (b[entry?.[2]] || []).map((i) => normalise(i, entry?.[1]));
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
            render: (r) =>
              r.link
                ? el("a", { href: r.link, target: "_blank", rel: "noopener noreferrer" }, r.what)
                : r.what,
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
