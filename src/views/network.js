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

import { el, mount, emptyState, disclosure } from "../core/dom.js";
import { href } from "../core/router.js";
import { shortDate } from "../core/format.js";
import { loadGraph, loadProposals } from "../core/data.js";

const TYPE_LABEL = {
  anchor_demand: "Demand anchor",
  input_cost: "Input cost",
  partner: "Partner",
};

// Edge types that terminate at a SECTOR. competitor and supplier_customer
// relate two outside entities to each other; they exist to complete a
// read-through chain, and grouping the graph by destination without excluding
// them invents a sector card headed "Google".
//
// partner is excluded for the same reason from the other side: it ends at a
// holding, not a sector, and grouping it here produced cards headed "TCS" and
// "SUZLON" whose "Holdings →" link filtered on a sector that does not exist.
// Partners get their own panel, keyed by the holding they belong to.
const TERMINAL_TYPES = new Set(["anchor_demand", "input_cost"]);

const DIRECTION_MARK = { risk: "▼", opportunity: "▲" };

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

/** Every held ticker, upper-case — which end of a partner edge is ours. */
function heldTickers(watchlist) {
  const out = new Set();
  for (const stocks of Object.values(watchlist || {})) {
    for (const s of stocks || []) {
      if (s && typeof s === "object" && s.ticker) out.add(String(s.ticker).toUpperCase());
    }
  }
  return out;
}

/**
 * Partners: who each holding has a live relationship with.
 *
 * An undirected edge, so "ours" is whichever end we hold. An edge whose ends
 * are both unheld is shown too — a holding can leave the watchlist while its
 * harvested edge stays — and is labelled as such rather than hidden, because a
 * stale edge still drives read-throughs until someone removes it.
 */
function partnersPanel(edges, held, params) {
  const partner = edges.filter((e) => e.type === "partner");
  if (!partner.length) return null;

  const byHolding = new Map();
  for (const e of partner) {
    const src = String(e.src || "");
    const dst = String(e.dst || "");
    const [ours, theirs] = held.has(dst.toUpperCase())
      ? [dst.toUpperCase(), src]
      : held.has(src.toUpperCase())
        ? [src.toUpperCase(), dst]
        : [dst, src];
    if (!byHolding.has(ours)) byHolding.set(ours, []);
    byHolding.get(ours).push({ name: theirs, edge: e });
  }

  return el(
    "section",
    { class: "panel" },
    el("h3", { class: "section-title" }, `Partners · ${partner.length}`),
    el(
      "p",
      { class: "section-note" },
      "Joint ventures and tie-ups a holding is party to. A disruption at the " +
        "partner is read across to the holding in Read-throughs above; the " +
        "partner's good news is not, because it is not ours by default.",
    ),
    el(
      "ul",
      { class: "net-shared-list" },
      [...byHolding.entries()]
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([ours, list]) =>
          el(
            "li",
            {},
            held.has(ours)
              ? el(
                  "a",
                  { class: "ticker-link", href: href("holdings", { ...params, focus: ours }) },
                  ours,
                )
              : el("span", {}, ours, el("span", { class: "evidence-meta" }, "no longer held")),
            " — ",
            list.map(({ name, edge }, i) => [
              i ? ", " : "",
              el("span", { title: edge.note || edge.evidence || "" }, name),
            ]),
          ),
        ),
    ),
  );
}

/**
 * Where to edit the proposals file, when the page is served from GitHub
 * Pages — owner.github.io/repo/. Anywhere else (a local preview, the smoke
 * test) there is no honest link to give, so none is shown.
 */
function proposalsEditUrl() {
  const { hostname, pathname } = window.location;
  if (!hostname.endsWith(".github.io")) return null;
  const owner = hostname.split(".")[0];
  const repo = pathname.split("/").filter(Boolean)[0];
  if (!owner || !repo) return null;
  return `https://github.com/${owner}/${repo}/edit/main/entity_graph_proposals.json`;
}

/**
 * Proposed partners: tie-ups the pipeline read that a person has not ruled on.
 *
 * The review step exists because a wrong edge does not produce a wrong
 * number, it produces a plausible chain — so this shows the evidence a
 * reviewer needs to decide in one glance: the pair, how many separate
 * headlines reported it, and the first of them as a link to the article.
 */
function proposalsPanel(proposals) {
  const pending = (proposals || []).filter((p) => p && p.status === "pending");
  if (!pending.length) return null;
  const editUrl = proposalsEditUrl();

  const body = el(
    "div",
    {},
    el(
      "p",
      { class: "section-note" },
      "Nothing here affects any signal until accepted. To decide, set a " +
        "proposal's status to \u201caccepted\u201d or \u201crejected\u201d in " +
        "entity_graph_proposals.json; accepted pairs join the graph on the next run. " +
        "Correct the counterparty's name first if it is wrong.",
      editUrl
        ? [" ", el("a", { href: editUrl, target: "_blank", rel: "noopener noreferrer" }, "Edit on GitHub \u2192")]
        : null,
    ),
    el(
      "ul",
      { class: "evidence" },
      pending.map((p) => {
        const first = (p.evidence || [])[0] || {};
        const seen = (p.evidence || []).length;
        return el(
          "li",
          {},
          el("strong", {}, `${p.holding} \u2194 ${p.counterparty}`),
          el(
            "span",
            { class: "evidence-tags" },
            el("span", { class: "tag" }, `${seen >= 5 ? "5+" : seen} headline${seen === 1 ? "" : "s"}`),
          ),
          el(
            "span",
            { class: "evidence-meta" },
            first.link
              ? el("a", { href: first.link, target: "_blank", rel: "noopener noreferrer" }, first.headline || "")
              : first.headline || "",
            first.date ? ` \u00b7 ${shortDate(first.date)}` : "",
          ),
        );
      }),
    ),
  );

  return el(
    "section",
    { class: "panel" },
    disclosure(`${pending.length} proposed partner${pending.length === 1 ? "" : "s"} awaiting review`, body),
  );
}

/**
 * Read-throughs: what an event about someone else means for what we hold.
 *
 * Rendered here rather than in Risk on purpose. Risk grades evidence — a
 * thesis moves only when this cycle's numbers contradict the catalyst. A
 * read-through is a hypothesis assembled from curated relationships and a
 * keyword, and putting it beside graded evidence would let the two be read as
 * the same kind of claim. It belongs with the graph it was derived from.
 *
 * The chain is shown in full, always. A conclusion whose reasoning is hidden
 * cannot be disagreed with, and this is the one thing in the product that
 * asserts causation nobody wrote down.
 */
function readThroughPanel(rows, params) {
  if (!Array.isArray(rows) || !rows.length) return null;

  return el(
    "section",
    { class: "panel" },
    el("h3", { class: "section-title" }, "Read-throughs"),
    el(
      "p",
      { class: "section-note" },
      "Events that name nothing we hold, and what they imply for holdings that " +
        "sit downstream of them. Each is a hypothesis with its reasoning " +
        "attached — read the chain before acting on the conclusion. These " +
        "deliberately do not feed scoring or thesis health.",
    ),
    el(
      "ul",
      { class: "rt-list" },
      rows.map((r) =>
        el(
          "li",
          { class: `rt-item rt-${r.direction}` },
          el(
            "div",
            { class: "rt-head" },
            el(
              "span",
              { class: "rt-mark", "aria-hidden": "true" },
              DIRECTION_MARK[r.direction] || "•",
            ),
            el("span", { class: "rt-sector" }, String(r.sector || "").replace(/_/g, " ")),
            el("span", { class: "rt-mech" }, String(r.mechanism || "").replace(/_/g, " ")),
            el(
              "span",
              { class: "rt-confidence" },
              r.confidence === "curated" ? "curated links" : "harvested links",
            ),
          ),
          el("p", { class: "rt-trigger" }, r.trigger || ""),
          el(
            "ol",
            { class: "rt-chain" },
            (r.chain || []).map((step) => el("li", {}, step)),
          ),
          el(
            "p",
            { class: "rt-tickers" },
            (r.tickers || []).map((t, i) => [
              i ? ", " : "",
              el(
                "a",
                { class: "ticker-link", href: href("holdings", { ...params, focus: t }) },
                t,
              ),
            ]),
          ),
        ),
      ),
    ),
  );
}

export async function render(container, { payload, route }) {
  const [edges, proposals] = await Promise.all([loadGraph(), loadProposals()]);
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
  const terminal = edges.filter((e) => TERMINAL_TYPES.has(e.type));
  const byDst = new Map();
  for (const e of terminal) {
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
        `${edges.length} connections between ${ordered.length} sectors and ` +
          `the demand anchors and input costs outside them.`,
      ),
    ),
    readThroughPanel(payload?.briefing?.read_throughs, (route && route.params) || {}),
    el(
      "div",
      { class: "net-grid" },
      ordered.map(([key, list]) => sectorCard(key, list, sectors, route?.focus)),
    ),
    crossSectorSummary(terminal),
    partnersPanel(edges, heldTickers(payload?.watchlist), (route && route.params) || {}),
    proposalsPanel(proposals),
  );
}
