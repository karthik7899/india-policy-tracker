// The Ask view's model: the question issue, and answers read back.

import { test } from "node:test";
import assert from "node:assert/strict";

import { questionUrl, parseIssue, pickAnswer, answerBlocks, loadQuestions } from "../../src/core/ask.js";

test("a question leaves as an issue the workflow can read", () => {
  const url = new URL(questionUrl("  Why is   SYRMA broken? ", "syrma", "owner/repo"));
  assert.equal(url.origin + url.pathname, "https://github.com/owner/repo/issues/new");
  assert.equal(url.searchParams.get("title"), "Question: Why is SYRMA broken?");
  const body = url.searchParams.get("body");
  const json = body.split("<!-- tracker:question v1 -->")[1].split("```json")[1].split("```")[0];
  assert.deepEqual(JSON.parse(json), { v: 1, question: "Why is SYRMA broken?", focus: "SYRMA" });
  // A long question keeps its full text in the body; only the title is cut.
  const long = "x".repeat(200);
  const u2 = new URL(questionUrl(long, null, "o/r"));
  assert.ok(u2.searchParams.get("title").endsWith("..."));
  assert.match(u2.searchParams.get("body"), new RegExp(`"question":"${long}"`));
});

test("an issue is read back from its request, the title standing in", () => {
  const body = 'text\n<!-- tracker:question v1 -->\n```json\n{"v":1,"question":"What changed?","focus":"DIXON"}\n```';
  assert.deepEqual(
    parseIssue({ number: 7, title: "Question: What chan...", body, state: "closed", html_url: "u", created_at: "2026-10-09T07:00:00Z", comments: 1 }),
    { number: 7, question: "What changed?", focus: "DIXON", state: "closed", url: "u", created: "2026-10-09T07:00:00Z", comments: 1 },
  );
  assert.equal(parseIssue({ title: "Question: Hand typed", body: "" }).question, "Hand typed");
});

test("the answer is the latest comment from the workflow, not from a person", () => {
  const comments = [
    { user: { type: "Bot" }, body: "first" },
    { user: { type: "User" }, body: "thanks" },
    { user: { type: "Bot" }, body: "second" },
  ];
  assert.equal(pickAnswer(comments), "second");
  assert.equal(pickAnswer([{ user: { type: "User" }, body: "x" }]), null);
});

test("an answer becomes paragraphs, lists and bold runs, never markup", () => {
  const { blocks, note } = answerBlocks(
    "SYRMA is **Broken** for two reasons.\n\n- margins fell <b>3</b> quarters\n- Amber is moving in\n\n---\n<sub>✦ LLM reading</sub>",
  );
  assert.deepEqual(blocks[0], {
    type: "para",
    parts: [{ text: "SYRMA is " }, { bold: "Broken" }, { text: " for two reasons." }],
  });
  assert.equal(blocks[1].type, "list");
  // The model's HTML stays text; the view turns it into text nodes.
  assert.deepEqual(blocks[1].items[0], [{ text: "margins fell <b>3</b> quarters" }]);
  assert.equal(note, "✦ LLM reading");
});

function fakeFetch(routes) {
  const calls = [];
  const fn = async (url) => {
    calls.push(url);
    const hit = Object.entries(routes).find(([k]) => url.includes(k));
    const [status, body] = hit ? hit[1] : [404, {}];
    return { ok: status === 200, status, json: async () => body };
  };
  fn.calls = calls;
  return fn;
}

const memory = () => {
  const m = new Map();
  return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) };
};

test("recent questions come with their answers", async () => {
  const fetchFn = fakeFetch({
    "/issues?labels=": [200, [
      { number: 2, title: "Question: B", body: "", state: "open", comments: 0 },
      { number: 1, title: "Question: A", body: "", state: "closed", comments: 1 },
      { number: 9, title: "a PR", pull_request: {}, comments: 0 },
    ]],
    "/issues/1/comments": [200, [{ user: { type: "Bot" }, body: "the answer" }]],
  });
  const { items, error } = await loadQuestions({ slug: "o/r", fetchFn, storage: memory() });
  assert.equal(error, undefined);
  assert.deepEqual(items.map((q) => [q.number, q.answer]), [[2, null], [1, "the answer"]]);
  // Unanswered questions cost no comment request.
  assert.ok(!fetchFn.calls.some((u) => u.includes("/issues/2/comments")));
});

test("a used-up API allowance is said, not shown as no questions", async () => {
  const fetchFn = fakeFetch({ "/issues?labels=": [403, {}] });
  const { items, error } = await loadQuestions({ slug: "o/r", fetchFn, storage: memory() });
  assert.deepEqual(items, []);
  assert.equal(error, "rate");
});

test("questions are cached briefly, and Refresh skips the cache", async () => {
  const storage = memory();
  const fetchFn = fakeFetch({ "/issues?labels=": [200, []] });
  await loadQuestions({ slug: "o/r", fetchFn, storage });
  await loadQuestions({ slug: "o/r", fetchFn, storage });
  assert.equal(fetchFn.calls.length, 1);
  await loadQuestions({ slug: "o/r", fetchFn, storage, fresh: true });
  assert.equal(fetchFn.calls.length, 2);
});
