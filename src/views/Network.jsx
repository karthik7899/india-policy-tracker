// Network — what connects a sector to the world outside it.
//
// entity_graph.json existed for months with ZERO frontend references. 39
// curated edges: 21 anchor_demand (Airbus, Apple, AMD -> the sectors whose
// order books they drive), 16 input_cost, 2 partner.
//
// Deliberately not force-directed. The data is bipartite and 39 edges laid out
// by physics is a hairball where you can see there are connections but read
// none of them. Structure, not more colour.

import { href } from "../core/router.js";
import { useGraph } from "../hooks.js";
import { Panel, Async } from "../components/ui.jsx";

const TYPE_LABEL = {
  anchor_demand: "Demand anchor",
  input_cost: "Input cost",
  partner: "Partner",
};
const TYPE_ORDER = ["anchor_demand", "input_cost", "partner"];

function SectorCard({ sectorKey, edges, sectors, focus }) {
  const byType = new Map(TYPE_ORDER.map((t) => [t, []]));
  for (const e of edges) {
    if (!byType.has(e.type)) byType.set(e.type, []);
    byType.get(e.type).push(e);
  }
  const label = sectors?.[sectorKey]?.name || String(sectorKey).replace(/_/g, " ");

  return (
    <article class={`net-card${focus === sectorKey ? " net-card-focus" : ""}`}>
      <header class="net-card-head">
        <h3 class="net-card-title">{label}</h3>
        {/* The link out. This is what makes the graph navigable rather than
            decorative — the affected holdings are one click away. */}
        <a class="net-card-link" href={href("holdings", { sector: sectorKey })}>
          Holdings →
        </a>
      </header>
      {[...byType.entries()]
        .filter(([, list]) => list.length)
        .map(([type, list]) => (
          <div class="edge-group" key={type}>
            {/* Type is labelled, never colour-only: it survives CVD and print. */}
            <div class="edge-group-label">
              {TYPE_LABEL[type] || type} · {list.length}
            </div>
            <div class="edge-chips">
              {list.map((e) => (
                <span key={e.src} class={`edge-chip edge-${e.type}`} title={e.note || ""}>
                  {e.src}
                </span>
              ))}
            </div>
          </div>
        ))}
    </article>
  );
}

function CrossSector({ edges }) {
  const bySrc = new Map();
  for (const e of edges) {
    if (!bySrc.has(e.src)) bySrc.set(e.src, new Set());
    bySrc.get(e.src).add(e.dst);
  }
  const shared = [...bySrc.entries()].filter(([, d]) => d.size > 1).sort((a, b) => b[1].size - a[1].size);
  if (!shared.length) return null;

  return (
    <Panel
      title="Touches more than one sector"
      note="A single anchor or input feeding several sectors is a correlated exposure: one of these moving affects more of the book than its own sector suggests."
    >
      <ul class="net-shared-list">
        {shared.map(([src, dsts]) => (
          <li key={src}>
            <strong>{src}</strong> → {[...dsts].map((d) => d.replace(/_/g, " ")).join(", ")}
          </li>
        ))}
      </ul>
    </Panel>
  );
}

export function Network({ payload, route }) {
  const state = useGraph();
  const sectors = payload?.sectors || {};

  return (
    <Async state={state} empty="No entity graph available.">
      {(edges) => {
        const byDst = new Map();
        for (const e of edges) {
          if (!byDst.has(e.dst)) byDst.set(e.dst, []);
          byDst.get(e.dst).push(e);
        }
        const ordered = [...byDst.entries()].sort((a, b) => b[1].length - a[1].length);
        return (
          <>
            <header class="view-head">
              <h2 class="view-title">Network</h2>
              <p class="view-sub">
                {edges.length} curated connections between {ordered.length} sectors and the demand
                anchors and input costs outside them.
              </p>
            </header>
            <div class="net-grid">
              {ordered.map(([key, list]) => (
                <SectorCard key={key} sectorKey={key} edges={list} sectors={sectors} focus={route?.focus} />
              ))}
            </div>
            <CrossSector edges={edges} />
          </>
        );
      }}
    </Async>
  );
}
