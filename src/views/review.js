// Review — the decisions the pipeline leaves to a person.
//
// Three queues used to need a JSON edit or a conversation to clear: partner
// proposals (entity_graph_proposals.json), holdings filed in a sector their
// business does not fit (sector_fit), and the eval labels, all of which are
// drafts nobody has reviewed. Here each takes a click. Decisions are kept in
// this browser and leave it as one GitHub issue the owner submits; the
// dashboard-actions workflow applies them and replies (src/core/review.js).

import { el, mount } from "../core/dom.js";
import { loadProposals, loadLabels } from "../core/data.js";
import { href } from "../core/router.js";
import { shortDate } from "../core/format.js";
import { panel, tickerLink } from "./table.js";
import {
  LABEL_KINDS,
  LABEL_FILES,
  rowId,
  loadDraft,
  saveDraft,
  emptyDraft,
  pruneDraft,
  countDecisions,
  buildPayload,
  issueUrls,
  proposalKey,
} from "../core/review.js";

const PAGE = 10;
const EVENT_TYPES = ["acquisition", "capacity_add", "input_cost_shock", "order_win", "supply_disruption", "tie_up"];
const STANCES = ["contradicts", "supports", "unrelated"];
const DIRECTIONS = ["tailwind", "headwind", "mixed"];
const KIND_LABEL = { thesis: "Thesis check", policy: "Policy reader", event: "Event reader" };

// Rows whose editor is open. Module state, because every change re-renders.
const editing = new Set();
let submitted = null;

function sectorName(key, labels) {
  return labels?.[key]?.label || String(key || "").replace(/_/g, " ");
}

function choice(text, active, onclick, tone = "") {
  return el(
    "button",
    { type: "button", class: `choice${active ? " choice-on" : ""}${tone ? ` choice-${tone}` : ""}`, "aria-pressed": active ? "true" : "false", onclick },
    text,
  );
}

function submitBar(draft, update) {
  const n = countDecisions(draft);
  const urls = n ? issueUrls(buildPayload(draft)) : [];
  return el(
    "section",
    { class: "panel review-bar" },
    el(
      "div",
      { class: "review-bar-row" },
      el("strong", {}, n ? `${n} decision${n === 1 ? "" : "s"} ready` : "No decisions yet"),
      urls.length === 1
        ? el(
            "a",
            { class: "button-primary", href: urls[0], target: "_blank", rel: "noopener noreferrer", onclick: () => (submitted = Date.now()) },
            "Submit on GitHub",
          )
        : urls.length > 1
          ? el(
              "span",
              { class: "review-parts" },
              `Too many for one issue — submit ${urls.length} parts: `,
              urls.map((u, i) =>
                el("a", { href: u, target: "_blank", rel: "noopener noreferrer", onclick: () => (submitted = Date.now()) }, `part ${i + 1}`),
              ),
            )
          : null,
      n
        ? el(
            "button",
            {
              type: "button",
              class: "button-quiet",
              onclick: () => {
                if (globalThis.confirm?.("Forget every decision made here?") !== false) {
                  update((d) => Object.assign(d, emptyDraft()));
                }
              },
            },
            "Clear",
          )
        : null,
    ),
    el(
      "p",
      { class: "section-note" },
      submitted
        ? "Opened on GitHub: press Submit new issue there. A workflow applies the decisions, replies on the issue and closes it; this page catches up when GitHub Pages redeploys, a few minutes later. Until then the decisions stay here."
        : "Saved in this browser only. Submitting opens a pre-filled GitHub issue; you submit it under your own login, and only issues you open are acted on.",
    ),
  );
}

function proposalsSection(pending, draft, update) {
  return panel(
    `Partner proposals (${pending.length})`,
    "Tie-ups read from headlines. Accepted partners join the graph: their trouble reaches the holding as a read-through. Correct the name before accepting if the reader got it wrong.",
    pending.length
      ? el(
          "ul",
          { class: "review-list" },
          pending.map((p) => {
            const key = proposalKey(p);
            const d = draft.proposals[key];
            const set = (status) =>
              update((dr) => {
                const name = document.getElementById(`cp-${key}`)?.value?.trim();
                dr.proposals[key] = { status, ...(name && name !== p.counterparty ? { counterparty: name } : {}) };
              });
            return el(
              "li",
              { class: "review-item" },
              el(
                "div",
                { class: "review-head" },
                tickerLink(p.holding),
                " ↔ ",
                el("input", {
                  id: `cp-${key}`,
                  class: "review-input",
                  value: d?.counterparty || p.counterparty || "",
                  "aria-label": `Partner name for ${p.holding}`,
                }),
              ),
              el(
                "ul",
                { class: "evidence" },
                (p.evidence || []).slice(0, 3).map((e) =>
                  el(
                    "li",
                    {},
                    e.link ? el("a", { href: e.link, target: "_blank", rel: "noopener noreferrer" }, e.headline) : e.headline,
                    el("span", { class: "evidence-meta" }, [e.source, shortDate(e.date)].filter(Boolean).join(" · ")),
                  ),
                ),
              ),
              el(
                "div",
                { class: "review-actions" },
                choice("Accept", d?.status === "accepted", () => set("accepted"), "opp"),
                choice("Reject", d?.status === "rejected", () => set("rejected"), "risk"),
                d ? choice("Undo", false, () => update((dr) => delete dr.proposals[key])) : null,
              ),
            );
          }),
        )
      : el("p", { class: "company-empty" }, "No partner proposals waiting."),
  );
}

function placementSection(misfits, draft, update, labels) {
  const sectors = Object.keys(labels || {}).filter((k) => k !== "macro_indicators");
  return panel(
    `Sector placement (${misfits.length})`,
    "Holdings whose own industry does not fit the sector they sit in. The sector decides their index, policy tags and peers. Move one, or keep it where it is and it stops being flagged.",
    misfits.length
      ? el(
          "ul",
          { class: "review-list" },
          misfits.map((m) => {
            const key = String(m.ticker).toUpperCase();
            const d = draft.moves[key];
            const options = [
              ...(m.suggested || []),
              ...sectors.filter((s) => s !== m.sector && !(m.suggested || []).includes(s)),
            ];
            return el(
              "li",
              { class: "review-item" },
              el(
                "div",
                { class: "review-head" },
                tickerLink(m.ticker),
                ` ${m.name || ""} · ${m.industry || "industry unknown"}`,
              ),
              el(
                "p",
                { class: "evidence-meta" },
                `In ${sectorName(m.sector, labels)}`,
                m.suggested?.length ? `; fits ${m.suggested.map((s) => sectorName(s, labels)).join(", ")}` : "; fits none of the sectors",
              ),
              el(
                "div",
                { class: "review-actions" },
                el(
                  "select",
                  {
                    class: "review-input",
                    "aria-label": `Move ${m.ticker} to`,
                    onchange: (e) => e.target.value && update((dr) => (dr.moves[key] = { to: e.target.value })),
                  },
                  el("option", { value: "" }, "Move to…"),
                  options.map((s) =>
                    el(
                      "option",
                      { value: s, selected: d?.to === s ? "" : null },
                      `${sectorName(s, labels)}${(m.suggested || []).includes(s) ? " (fits)" : ""}`,
                    ),
                  ),
                ),
                choice("Keep here", Boolean(d?.keep), () => update((dr) => (dr.moves[key] = { keep: true }))),
                d ? choice("Undo", false, () => update((dr) => delete dr.moves[key])) : null,
              ),
            );
          }),
        )
      : el("p", { class: "company-empty" }, "Every holding fits its sector."),
  );
}

/** A label as a reader would say it. */
export function describeLabel(kind, row) {
  if (kind === "thesis") {
    return `${row.stance || "?"}${row.about === false ? " · not about this company" : ""}`;
  }
  if (kind === "policy") {
    if (!row.is_policy) return "not a policy";
    const effects = (row.effects || []).map((e) => `${String(e.sector).replace(/_/g, " ")} ${e.direction}`);
    return `policy${effects.length ? `: ${effects.join(", ")}` : " (no sector effect)"}`;
  }
  const parts = [row.event_type ? row.event_type.replace(/_/g, " ") : "no event"];
  if (row.actors?.length) parts.push(`actors ${row.actors.join(", ")}`);
  if (row.counterparties?.length) parts.push(`with ${row.counterparties.join(", ")}`);
  return parts.join(" · ");
}

function editor(kind, row, id, labels, update) {
  const field = (name) => document.getElementById(`${id}-${name}`);
  const sectors = Object.keys(labels || {}).filter((k) => k !== "macro_indicators");
  const list = (v) => String(v || "").split(",").map((s) => s.trim()).filter(Boolean);
  let controls;
  if (kind === "thesis") {
    controls = [
      el(
        "select",
        { id: `${id}-stance`, class: "review-input", "aria-label": "Stance" },
        STANCES.map((s) => el("option", { value: s, selected: s === row.stance ? "" : null }, s)),
      ),
      el(
        "label",
        { class: "review-check" },
        el("input", { id: `${id}-about`, type: "checkbox", checked: row.about === false ? null : "" }),
        " about this company",
      ),
    ];
  } else if (kind === "policy") {
    const effects = row.effects?.length ? row.effects : [{}];
    controls = [
      el(
        "label",
        { class: "review-check" },
        el("input", { id: `${id}-is`, type: "checkbox", checked: row.is_policy ? "" : null }),
        " is a policy",
      ),
      el(
        "div",
        { id: `${id}-effects`, class: "review-effects" },
        effects.map((e, i) =>
          el(
            "div",
            { class: "review-effect" },
            el(
              "select",
              { class: "review-input", "data-role": "sector", "aria-label": `Effect ${i + 1} sector` },
              el("option", { value: "" }, "no effect"),
              sectors.map((s) => el("option", { value: s, selected: s === e.sector ? "" : null }, sectorName(s, labels))),
            ),
            el(
              "select",
              { class: "review-input", "data-role": "direction", "aria-label": `Effect ${i + 1} direction` },
              DIRECTIONS.map((d) => el("option", { value: d, selected: d === e.direction ? "" : null }, d)),
            ),
          ),
        ),
      ),
    ];
  } else {
    controls = [
      el(
        "select",
        { id: `${id}-type`, class: "review-input", "aria-label": "Event type" },
        el("option", { value: "" }, "no event"),
        EVENT_TYPES.map((t) => el("option", { value: t, selected: t === row.event_type ? "" : null }, t.replace(/_/g, " "))),
      ),
      el("input", { id: `${id}-actors`, class: "review-input", value: (row.actors || []).join(", "), placeholder: "actor tickers, comma-separated", "aria-label": "Actors" }),
      el("input", { id: `${id}-cps`, class: "review-input", value: (row.counterparties || []).join(", "), placeholder: "counterparties", "aria-label": "Counterparties" }),
    ];
  }
  const save = () => {
    const fix = {};
    if (kind === "thesis") {
      fix.stance = field("stance").value;
      // "about" is only written when it says something: absent means true.
      if (!field("about").checked || row.about === false) fix.about = field("about").checked;
    } else if (kind === "policy") {
      fix.is_policy = field("is").checked;
      // Not a policy has no sector effect, whatever the selects still show.
      fix.effects = fix.is_policy
        ? [...field("effects").querySelectorAll(".review-effect")]
            .map((r) => ({
              sector: r.querySelector('[data-role="sector"]').value,
              direction: r.querySelector('[data-role="direction"]').value,
            }))
            .filter((e) => e.sector)
        : [];
    } else {
      fix.event_type = field("type").value || null;
      fix.actors = list(field("actors").value).map((t) => t.toUpperCase());
      fix.counterparties = list(field("cps").value);
    }
    const note = field("note").value.trim();
    if (note) fix.note = note;
    editing.delete(id);
    update((dr) => (dr.labels[kind][id] = fix));
  };
  return el(
    "div",
    { class: "review-editor" },
    controls,
    el("input", { id: `${id}-note`, class: "review-input", placeholder: "note (optional)", "aria-label": "Note" }),
    el(
      "div",
      { class: "review-actions" },
      choice("Save correction", false, save, "opp"),
      choice("Cancel", false, () => {
        editing.delete(id);
        update(() => {});
      }),
    ),
  );
}

function labelsSection(kind, body, draft, update, page, params, labels) {
  const rows = body?.labels || [];
  const open = rows.filter((r) => !r.reviewed);
  const decided = Object.keys(draft.labels[kind] || {}).length;
  const pages = Math.max(1, Math.ceil(open.length / PAGE));
  const at = Math.min(page, pages - 1);
  const shown = open.slice(at * PAGE, at * PAGE + PAGE);
  return panel(
    "Eval labels",
    "The hand labels each reader is scored against were drafted, not reviewed. Confirm a row that is right; fix one that is wrong. Reviewed rows leave the queue.",
    el(
      "nav",
      { class: "lens-nav" },
      LABEL_KINDS.map((k) =>
        el(
          "a",
          { class: `lens${k === kind ? " lens-active" : ""}`, href: href("review", { ...params, labels: k, page: 0 }) },
          KIND_LABEL[k],
        ),
      ),
    ),
    body
      ? el(
          "p",
          { class: "evidence-meta" },
          `${rows.length - open.length} of ${rows.length} reviewed · ${decided} decided here, not yet submitted`,
        )
      : el("p", { class: "company-empty" }, `${LABEL_FILES[kind]} could not be read.`),
    shown.length
      ? el(
          "ul",
          { class: "review-list" },
          shown.map((row) => {
            const id = rowId(kind, row);
            const d = draft.labels[kind][id];
            return el(
              "li",
              { class: "review-item" },
              kind === "thesis"
                ? el("p", { class: "evidence-meta" }, el("strong", {}, row.ticker), ` — thesis: “${row.thesis}”`)
                : null,
              el("p", { class: "review-headline" }, row.headline, row.synthetic ? el("span", { class: "tag" }, "synthetic") : null),
              el("p", { class: "evidence-meta" }, `Labelled: ${describeLabel(kind, row)}${row.note ? ` — ${row.note}` : ""}`),
              d && !d.ok ? el("p", { class: "review-change" }, `Will become: ${describeLabel(kind, { ...row, ...d })}`) : null,
              editing.has(id)
                ? editor(kind, { ...row, ...(d && !d.ok ? d : {}) }, id, labels, update)
                : el(
                    "div",
                    { class: "review-actions" },
                    choice("Correct", Boolean(d?.ok), () => update((dr) => (dr.labels[kind][id] = { ok: true })), "opp"),
                    choice(d && !d.ok ? "Edit fix" : "Fix", Boolean(d && !d.ok), () => {
                      editing.add(id);
                      update(() => {});
                    }),
                    d ? choice("Undo", false, () => update((dr) => delete dr.labels[kind][id])) : null,
                  ),
            );
          }),
        )
      : body
        ? el("p", { class: "company-empty" }, "Every row in this set is reviewed.")
        : null,
    pages > 1
      ? el(
          "nav",
          { class: "review-pages" },
          at > 0 ? el("a", { href: href("review", { ...params, labels: kind, page: at - 1 }) }, "← Previous") : null,
          el("span", { class: "evidence-meta" }, ` Page ${at + 1} of ${pages} `),
          at < pages - 1 ? el("a", { href: href("review", { ...params, labels: kind, page: at + 1 }) }, "Next →") : null,
        )
      : null,
  );
}

export async function render(container, { payload, route }) {
  const params = (route && route.params) || {};
  const kind = LABEL_KINDS.includes(params.labels) ? params.labels : "thesis";
  const page = Math.max(0, parseInt(params.page || "0", 10) || 0);
  const labels = payload?.sectors || {};
  const [proposals, ...sets] = await Promise.all([
    loadProposals(),
    ...LABEL_KINDS.map((k) => loadLabels(LABEL_FILES[k])),
  ]);
  const labelSets = Object.fromEntries(LABEL_KINDS.map((k, i) => [k, sets[i]]));
  const misfits = payload?.briefing?.sector_fit?.misfits || [];
  const pending = (proposals || []).filter((p) => p.status === "pending");

  const draft = pruneDraft(loadDraft(), {
    proposals: proposals || [],
    misfits,
    labels: Object.fromEntries(LABEL_KINDS.map((k) => [k, labelSets[k]?.labels])),
  });
  saveDraft(draft);

  const update = (change) => {
    change(draft);
    saveDraft(draft);
    const y = globalThis.scrollY || 0;
    render(container, { payload, route }).then(() => globalThis.scrollTo?.(0, y));
  };

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Review"),
      el(
        "p",
        { class: "view-sub" },
        `Decisions the pipeline leaves to you · ${pending.length} partner proposal(s), ${misfits.length} holding(s) to place, ` +
          `${LABEL_KINDS.reduce((n, k) => n + (labelSets[k]?.labels || []).filter((r) => !r.reviewed).length, 0)} label(s) unreviewed`,
      ),
    ),
    submitBar(draft, update),
    proposalsSection(pending, draft, update),
    placementSection(misfits, draft, update, labels),
    labelsSection(kind, labelSets[kind], draft, update, page, params, labels),
  );
}
