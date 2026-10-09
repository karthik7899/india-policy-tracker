// The Review view's model: ids, the draft, and the issue that carries it.

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  fnv1a,
  rowId,
  emptyDraft,
  pruneDraft,
  countDecisions,
  buildPayload,
  issueUrls,
  repoSlug,
  loadDraft,
  saveDraft,
} from "../../src/core/review.js";
import { describeLabel } from "../../src/views/review.js";

test("row ids match scripts/dashboard_actions.py", () => {
  // The same vectors are pinned in tests/test_dashboard_actions.py.
  assert.equal(fnv1a(""), "811c9dc5");
  assert.equal(fnv1a("a"), "e40c292c");
  assert.equal(fnv1a("Dixon eyes product portfolio expansion, scouts new facility"), "c572abdd");
  assert.equal(fnv1a("Lakmē ₹"), "34fec48c");
  assert.equal(
    rowId("thesis", { ticker: "SIEMENS", headline: "Siemens unveils ÖBB Railjet M at InnoTrans" }),
    "5441d511",
  );
});

function draft() {
  const d = emptyDraft();
  d.proposals["TCS|Nordea Bank"] = { status: "accepted", counterparty: "Nordea" };
  d.moves.OFSS = { to: "midcap_it" };
  d.moves.ADANIPOWER = { keep: true };
  d.labels.thesis.aaaaaaaa = { ok: true };
  d.labels.policy.bbbbbbbb = { is_policy: false, effects: [] };
  return d;
}

test("the payload is what the workflow reads", () => {
  assert.deepEqual(buildPayload(draft()), {
    v: 1,
    proposals: [{ holding: "TCS", proposed_as: "Nordea Bank", status: "accepted", counterparty: "Nordea" }],
    moves: [
      { ticker: "OFSS", to: "midcap_it" },
      { ticker: "ADANIPOWER", keep: true },
    ],
    labels: {
      thesis: [{ id: "aaaaaaaa", ok: true }],
      policy: [{ id: "bbbbbbbb", is_policy: false, effects: [] }],
    },
  });
  assert.equal(countDecisions(draft()), 5);
  assert.deepEqual(buildPayload(emptyDraft()), { v: 1 });
});

test("a decision about something no longer waiting is dropped", () => {
  // Once the workflow has applied a submission, its decisions empty out.
  const pruned = pruneDraft(draft(), {
    proposals: [{ holding: "TCS", proposed_as: "Nordea Bank", status: "accepted" }],
    misfits: [{ ticker: "OFSS" }],
    labels: { thesis: [{ ticker: "X", headline: "y", reviewed: "2026-10-09" }] },
  });
  assert.deepEqual(Object.keys(pruned.proposals), []);
  assert.deepEqual(Object.keys(pruned.moves), ["OFSS"]);
  assert.deepEqual(pruned.labels.thesis, {});
  // A file that could not be read keeps its decisions rather than losing them.
  assert.deepEqual(pruned.labels.policy, { bbbbbbbb: { is_policy: false, effects: [] } });
});

test("the issue carries the request after the marker", () => {
  const [url] = issueUrls(buildPayload(draft()), "owner/repo");
  const u = new URL(url);
  assert.equal(u.origin + u.pathname, "https://github.com/owner/repo/issues/new");
  const body = u.searchParams.get("body");
  const json = body.split("<!-- tracker:decisions v1 -->")[1].split("```json")[1].split("```")[0];
  assert.deepEqual(JSON.parse(json), buildPayload(draft()));
  assert.match(body, /Partners: 1 accepted, 0 rejected/);
});

test("a review too long for one issue is split into complete parts", () => {
  const d = emptyDraft();
  for (let i = 0; i < 300; i++) d.labels.event[i.toString(16).padStart(8, "0")] = { ok: true };
  const urls = issueUrls(buildPayload(d), "owner/repo", 2500);
  assert.ok(urls.length > 1);
  const ids = [];
  for (const url of urls) {
    assert.ok(url.length <= 2500, `part is ${url.length} long`);
    const body = new URL(url).searchParams.get("body");
    const json = JSON.parse(body.split("```json")[1].split("```")[0]);
    assert.equal(json.v, 1);
    ids.push(...json.labels.event.map((x) => x.id));
  }
  assert.equal(ids.length, 300);
  assert.equal(new Set(ids).size, 300);
});

test("the repository is read from the github.io address", () => {
  assert.equal(
    repoSlug({ hostname: "someone.github.io", pathname: "/their-fork/" }),
    "someone/their-fork",
  );
  assert.equal(repoSlug({ hostname: "localhost", pathname: "/" }), "karthik7899/india-policy-tracker");
});

test("the draft survives storage that refuses or is missing", () => {
  const refusing = {
    getItem() {
      throw new Error("denied");
    },
    setItem() {
      throw new Error("denied");
    },
  };
  assert.deepEqual(loadDraft(refusing), emptyDraft());
  saveDraft(draft(), refusing);
  const memory = new Map();
  const store = { getItem: (k) => memory.get(k) ?? null, setItem: (k, v) => memory.set(k, v) };
  saveDraft(draft(), store);
  assert.deepEqual(loadDraft(store), draft());
});

test("labels read the way a reviewer would say them", () => {
  assert.equal(describeLabel("thesis", { stance: "unrelated", about: false }), "unrelated · not about this company");
  assert.equal(
    describeLabel("policy", { is_policy: true, effects: [{ sector: "clean_energy", direction: "tailwind" }] }),
    "policy: clean energy tailwind",
  );
  assert.equal(describeLabel("policy", { is_policy: false }), "not a policy");
  assert.equal(
    describeLabel("event", { event_type: "tie_up", actors: ["SYRMA"], counterparties: ["Kaga"] }),
    "tie up · actors SYRMA · with Kaga",
  );
  assert.equal(describeLabel("event", { event_type: null }), "no event");
});
