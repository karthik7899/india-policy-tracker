// The Review view's model: the decisions a reader has made, kept in this
// browser until they are submitted, and the GitHub issue that carries them.
//
// The dashboard is a static page on a public site, so it cannot write to the
// repository and must not hold a credential. A decision travels as an issue
// the owner submits under their own GitHub login; the workflow
// dashboard-actions.yml validates it and applies it
// (scripts/dashboard_actions.py). Pure functions, tested without a DOM.

export const LABEL_KINDS = ["thesis", "policy", "event"];
export const LABEL_FILES = {
  thesis: "eval/thesis_labels.json",
  policy: "eval/policy_labels.json",
  event: "eval/event_labels.json",
};
const DRAFT_KEY = "tracker-review-draft-v1";
const REPO_FALLBACK = "karthik7899/india-policy-tracker";
// GitHub refuses very long new-issue URLs; stay well under the limit and
// split a large review into parts instead.
export const MAX_URL = 7000;

/**
 * 32-bit FNV-1a of the UTF-8 bytes, as 8 hex digits. The same function as
 * dashboard_actions.fnv1a, so a label row has one id on both sides without
 * its headline travelling in the issue.
 */
export function fnv1a(text) {
  let h = 0x811c9dc5;
  for (const byte of new TextEncoder().encode(String(text))) {
    h ^= byte;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

export function rowId(kind, row) {
  const key =
    kind === "thesis" ? `${row?.ticker || ""}\n${row?.headline || ""}` : String(row?.headline || "");
  return fnv1a(key);
}

export function emptyDraft() {
  return { proposals: {}, moves: {}, labels: { thesis: {}, policy: {}, event: {} } };
}

/** The saved draft, or an empty one. Storage can be absent or refuse. */
export function loadDraft(storage = globalThis.localStorage) {
  try {
    const raw = storage?.getItem(DRAFT_KEY);
    const draft = raw ? JSON.parse(raw) : null;
    if (draft && typeof draft === "object") {
      const base = emptyDraft();
      return {
        proposals: draft.proposals || base.proposals,
        moves: draft.moves || base.moves,
        labels: { ...base.labels, ...(draft.labels || {}) },
      };
    }
  } catch {
    /* private mode, or a corrupt entry: start empty */
  }
  return emptyDraft();
}

export function saveDraft(draft, storage = globalThis.localStorage) {
  try {
    storage?.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    /* not saved; the decisions still work for this visit */
  }
}

export const proposalKey = (p) => `${String(p.holding).toUpperCase()}|${p.proposed_as}`;

/**
 * Drop decisions about things that no longer need one: a proposal already
 * decided, a holding no longer misfiled, a label already reviewed. That is
 * how a submitted draft empties itself once the workflow has applied it.
 */
export function pruneDraft(draft, { proposals = [], misfits = [], labels = {} } = {}) {
  const pending = new Set(proposals.filter((p) => p.status === "pending").map(proposalKey));
  const misfiled = new Set(misfits.map((m) => String(m.ticker).toUpperCase()));
  const out = emptyDraft();
  for (const [k, v] of Object.entries(draft.proposals || {})) if (pending.has(k)) out.proposals[k] = v;
  for (const [k, v] of Object.entries(draft.moves || {})) if (misfiled.has(k)) out.moves[k] = v;
  for (const kind of LABEL_KINDS) {
    const rows = labels[kind];
    if (!rows) {
      out.labels[kind] = { ...(draft.labels?.[kind] || {}) };
      continue;
    }
    const open = new Set(rows.filter((r) => !r.reviewed).map((r) => rowId(kind, r)));
    for (const [id, v] of Object.entries(draft.labels?.[kind] || {})) if (open.has(id)) out.labels[kind][id] = v;
  }
  return out;
}

export function countDecisions(draft) {
  return (
    Object.keys(draft.proposals || {}).length +
    Object.keys(draft.moves || {}).length +
    LABEL_KINDS.reduce((n, k) => n + Object.keys(draft.labels?.[k] || {}).length, 0)
  );
}

/** The request the workflow reads (dashboard_actions.parse_request). */
export function buildPayload(draft) {
  const payload = { v: 1 };
  const proposals = Object.entries(draft.proposals || {}).map(([key, d]) => {
    const [holding, ...rest] = key.split("|");
    return {
      holding,
      proposed_as: rest.join("|"),
      status: d.status,
      ...(d.counterparty ? { counterparty: d.counterparty } : {}),
    };
  });
  if (proposals.length) payload.proposals = proposals;
  const moves = Object.entries(draft.moves || {}).map(([ticker, d]) =>
    d.keep ? { ticker, keep: true } : { ticker, to: d.to },
  );
  if (moves.length) payload.moves = moves;
  const labels = {};
  for (const kind of LABEL_KINDS) {
    const items = Object.entries(draft.labels?.[kind] || {}).map(([id, d]) =>
      d.ok ? { id, ok: true } : { id, ...d },
    );
    if (items.length) labels[kind] = items;
  }
  if (Object.keys(labels).length) payload.labels = labels;
  return payload;
}

export function summaryLines(payload) {
  const lines = [];
  const p = payload.proposals || [];
  if (p.length) {
    const acc = p.filter((x) => x.status === "accepted").length;
    lines.push(`- Partners: ${acc} accepted, ${p.length - acc} rejected`);
  }
  const m = payload.moves || [];
  if (m.length) {
    lines.push(
      `- Sector placement: ${m.map((x) => (x.keep ? `keep ${x.ticker}` : `${x.ticker} → ${x.to}`)).join("; ")}`,
    );
  }
  for (const [kind, items] of Object.entries(payload.labels || {})) {
    const ok = items.filter((x) => x.ok).length;
    lines.push(`- ${kind} labels: ${ok} confirmed, ${items.length - ok} corrected`);
  }
  return lines;
}

/** owner/repo of the site being viewed; the project's own when unknown. */
export function repoSlug(loc = globalThis.location) {
  const host = String(loc?.hostname || "");
  const m = /^([^.]+)\.github\.io$/i.exec(host);
  const first = String(loc?.pathname || "").split("/").filter(Boolean)[0];
  return m && first ? `${m[1]}/${first}` : REPO_FALLBACK;
}

function issueUrl(slug, title, body) {
  const q = new URLSearchParams({ title, body });
  return `https://github.com/${slug}/issues/new?${q.toString()}`;
}

function issueBody(payload, part, parts) {
  return [
    "Decisions from the dashboard's Review view. Submitting this issue applies them; a workflow replies with what changed and closes it.",
    parts > 1 ? `\nPart ${part} of ${parts}.` : "",
    "",
    ...summaryLines(payload),
    "",
    "<!-- tracker:decisions v1 -->",
    "```json",
    JSON.stringify(payload),
    "```",
  ].join("\n");
}

/**
 * The new-issue URLs that carry a payload: one when it fits, several when a
 * long review would make the URL too long for GitHub. Each part is a
 * complete request on its own, so they can be submitted in any order.
 */
export function issueUrls(payload, slug = repoSlug(), maxLen = MAX_URL) {
  const title = (n, of) => `Dashboard decisions${of > 1 ? ` (${n}/${of})` : ""}`;
  const whole = issueUrl(slug, title(1, 1), issueBody(payload, 1, 1));
  if (whole.length <= maxLen) return [whole];

  // Split into single-item requests, then pack them greedily.
  const atoms = [];
  for (const p of payload.proposals || []) atoms.push({ v: 1, proposals: [p] });
  for (const m of payload.moves || []) atoms.push({ v: 1, moves: [m] });
  for (const [kind, items] of Object.entries(payload.labels || {})) {
    for (const it of items) atoms.push({ v: 1, labels: { [kind]: [it] } });
  }
  const merge = (a, b) => {
    const out = { v: 1 };
    for (const key of ["proposals", "moves"]) {
      const list = [...(a[key] || []), ...(b[key] || [])];
      if (list.length) out[key] = list;
    }
    const labels = {};
    for (const src of [a.labels || {}, b.labels || {}]) {
      for (const [kind, items] of Object.entries(src)) labels[kind] = [...(labels[kind] || []), ...items];
    }
    if (Object.keys(labels).length) out.labels = labels;
    return out;
  };
  const chunks = [];
  let current = null;
  for (const atom of atoms) {
    const next = current ? merge(current, atom) : atom;
    // Sized with a generous part label so numbering cannot push it over.
    if (current && issueUrl(slug, title(99, 99), issueBody(next, 99, 99)).length > maxLen) {
      chunks.push(current);
      current = atom;
    } else {
      current = next;
    }
  }
  if (current) chunks.push(current);
  return chunks.map((c, i) => issueUrl(slug, title(i + 1, chunks.length), issueBody(c, i + 1, chunks.length)));
}
