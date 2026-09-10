// Flow — everything that arrived, filtered by where it came from.
//
// Five tabs were the same dated-item list separated by which scraper produced
// them, which is a fact about our pipeline rather than the reader's question.

import { shortDate } from "../core/format.js";
import { href } from "../core/router.js";
import { Panel, DataTable } from "../components/ui.jsx";

const STREAMS = [
  ["all", "Everything", null],
  ["filings", "Filings", "corporate_filings"],
  ["agreements", "Agreements", "corporate_agreements"],
  ["launches", "Launches", "product_launches"],
  ["institutional", "Institutional", "institutional_activity"],
  ["events", "Market events", "market_events"],
  ["global", "Global", "global_market_news"],
];

function normalise(item, streamLabel) {
  return {
    when: item.date || item.published || "",
    what: item.filing || item.headline || item.title || item.signal || "",
    who: item.company || item.ticker || item.name || (item.actors || [])[0] || "",
    source: item.source || streamLabel,
    link: item.link || item.url || "",
  };
}

export function Flow({ payload, route }) {
  const b = payload?.briefing || {};
  const stream = route?.params?.stream || "all";
  const params = route?.params || {};

  let rows = [];
  if (stream === "all") {
    for (const [, label, key] of STREAMS) {
      if (key) for (const item of b[key] || []) rows.push(normalise(item, label));
    }
    // Sorted by date rather than concatenated: concatenation is exactly what
    // let one source consume every slot in the filings section.
    rows.sort((a, c) => String(c.when).localeCompare(String(a.when)));
    rows = rows.slice(0, 80);
  } else {
    const entry = STREAMS.find(([k]) => k === stream);
    rows = (b[entry?.[2]] || []).map((i) => normalise(i, entry?.[1]));
  }

  return (
    <>
      <header class="view-head">
        <h2 class="view-title">Flow</h2>
        <p class="view-sub">{rows.length} items</p>
      </header>
      <nav class="lens-nav">
        {STREAMS.map(([key, label]) => (
          <a key={key} class={`lens${key === stream ? " lens-active" : ""}`} href={href("flow", { ...params, stream: key })}>
            {label}
          </a>
        ))}
      </nav>
      <Panel>
        <DataTable
          rows={rows}
          tickerKey="who"
          focus={route?.focus}
          empty="Nothing in this stream."
          columns={[
            { key: "when", label: "Date", render: (r) => shortDate(r.when) },
            { key: "who", label: "Company" },
            {
              key: "what",
              label: "What",
              render: (r) =>
                r.link ? (
                  <a href={r.link} target="_blank" rel="noopener noreferrer">{r.what}</a>
                ) : (
                  r.what
                ),
            },
            { key: "source", label: "Source" },
          ]}
        />
      </Panel>
    </>
  );
}
