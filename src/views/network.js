// The entity network — what connects a sector to the world outside it.
//
// entity_graph.json has existed for months and was referenced ZERO times by
// the frontend. It holds 39 curated edges: 21 anchor_demand (Airbus, Apple,
// AMD -> the sectors whose order books they drive), 16 input_cost (the
// commodities that feed them), 2 partner.
//
// Deliberately NOT a force-directed graph. The data is bipartite — outside
// entity to sector — and 39 edges laid out by physics produces a hairball
// where the reader can see there are connections but not read any of them.
// The dataviz rule for "more than ~7 classes that all carry meaning" is
// structure, not more colour. So: sectors as rows, their edges grouped by
// type, and a link out to the holdings that actually sit in each sector.
//
// That last part is the point of putting this in the app at all. A graph you
// can look at is a curiosity; a graph that takes you to the positions it
// affects is a tool.

import { el, mount, emptyState } from "../core/dom.js";
import { href } from "../core/router.js";
import { loadGraph } from "../core/data.js";

const TYPE_LABEL = {
  anchor_demand: "Demand anchor",
  input_cost: "Input cost",
  partner: "Partner",
};

// Type carries meaning, so it is labelled, never colour-only. Three types sits
// inside the categorical cap, but a label costs nothing and survives both CVD
// and a greyscale print.
const TYPE_ORDER = ["anchor_demand", "input_cost", "partner"];

function sectorLabel(key, sectors) {
  return sectors?.[key]?.name || String(key).replace(/_/g, " ");
}

function edgeChip(edge) {
  return el(
    "span",
    { class: `edge-chip edge-${edge.type}`, title: edge.note || "" },
    el("span", { class: "edge-chip-name" }, edge.src),
  );
}

function sectorCard(key, edges, sectors, focus) {
  const byType = new Map(TYPE_ORDER.map((t) => [t, []]));
  for (const e of edges) {
    if (!byType.has(e.type)) byType.set(e.type, []);
    byType.get(e.type).push(e);
  }

  const groups = [...byType.entries()]
    .filter(([, list]) => list.length)
    .map(([type, list]) =>
      el(
        "div",
        { class: "edge-group" },
        el(
          "div",
          { class: "edge-group-label" },
          `${TYPE_LABEL[type] || type} · ${list.length}`,
        ),
        el("div", { class: "edge-chips" }, list.map(edgeChip)),
      ),
    );

  return el(
    "article",
    { class: `net-card${focus === key ? " net-card-focus" : ""}` },
    el(
      "header",
      { class: "net-card-head" },
      el("h3", { class: "net-card-title" }, sectorLabel(key, sectors)),
      // The link out. This is what makes the graph navigable rather than
      // decorative — the sector's holdings are one click away, in the view
      // that already knows how to render them.
      el(
        "a",
        { class: "net-card-link", href: href("holdings", { sector: key }) },
        `Holdings →`,
      ),
    ),
    ...groups,
  );
}

/** A source that touches several sectors is doing more work than one that does not. */
function crossSectorSummary(edges) {
  const bySrc = new Map();
  for (const e of edges) {
    if (!bySrc.has(e.src)) bySrc.set(e.src, new Set());
    bySrc.get(e.src).add(e.dst);
  }
  const shared = [...bySrc.entries()]
    .filter(([, dsts]) => dsts.size > 1)
    .sort((a, b) => b[1].size - a[1].size);

  if (!shared.length) return null;
  return el(
    "section",
    { class: "net-shared" },
    el("h3", { class: "section-title" }, "Touches more than one sector"),
    el(
      "p",
      { class: "section-note" },
      "A single anchor or input feeding several sectors is a correlated exposure: " +
        "one of these moving affects more of the book than its own sector suggests.",
    ),
    el(
      "ul",
      { class: "net-shared-list" },
      shared.map(([src, dsts]) =>
        el(
          "li",
          {},
          el("strong", {}, src),
          ` → ${[...dsts].map((d) => d.replace(/_/g, " ")).join(", ")}`,
        ),
      ),
    ),
  );
}

export async function render(container, { payload, route }) {
  const edges = await loadGraph();
  if (!edges.length) {
    mount(
      container,
      emptyState(
        "No entity graph available.",
        "entity_graph.json is missing or carries no edges.",
      ),
    );
    return;
  }

  const sectors = payload?.sectors || {};
  const byDst = new Map();
  for (const e of edges) {
    if (!byDst.has(e.dst)) byDst.set(e.dst, []);
    byDst.get(e.dst).push(e);
  }
  const ordered = [...byDst.entries()].sort((a, b) => b[1].length - a[1].length);

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Network"),
      el(
        "p",
        { class: "view-sub" },
        `${edges.length} curated connections between ${ordered.length} sectors and ` +
          `the demand anchors and input costs outside them.`,
      ),
    ),
    el(
      "div",
      { class: "net-grid" },
      ordered.map(([key, list]) => sectorCard(key, list, sectors, route?.focus)),
    ),
    crossSectorSummary(edges),
  );
}
