// The Ask view's model: the question issue, and answers read back.

import { test } from "node:test";
import assert from "node:assert/strict";

import { questionUrl, parseIssue, threadOf, answerBlocks, loadQuestions } from "../../src/core/ask.js";

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

test("the thread is the workflow's answers and the owner's follow-ups, in order", () => {
  const comments = [
    { user: { type: "Bot" }, body: "first", created_at: "t1" },
    { user: { type: "User" }, author_association: "OWNER", body: "and margins?", created_at: "t2" },
    { user: { type: "User" }, author_association: "NONE", body: "buy now", created_at: "t3" },
    { user: { type: "Bot" }, body: "second", created_at: "t4" },
  ];
  assert.deepEqual(threadOf(comments), [
    { role: "answer", body: "first", created: "t1" },
    { role: "followup", body: "and margins?", created: "t2" },
    { role: "answer", body: "second", created: "t4" },
  ]);
  assert.deepEqual(threadOf(null), []);
});

test("an answer becomes paragraphs, lists and bold runs, never markup", () => {
  const { blocks, note, news } = answerBlocks(
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
  assert.equal(news, null);
});

test("an answer's parts keep their headings, and a list under a heading stays a list", () => {
  const { blocks } = answerBlocks(
    [
      "**From the briefing**",
      "Sales rose 20%.",
      "",
      "**From the news**",
      "- Exports grew [1]",
      "1. Order win [2]",
      "Read [the filing](https://nseindia.com/x) or [this](javascript:alert(1)).",
      "",
      "**Background (general knowledge, not from a source here)**",
      "CP PLUS sells cameras.",
    ].join("\n"),
  );
  assert.deepEqual(
    blocks.map((b) => b.type),
    ["heading", "para", "heading", "list", "para", "heading", "para"],
  );
  assert.equal(blocks[0].text, "From the briefing");
  assert.equal(blocks[5].text, "Background (general knowledge, not from a source here)");
  assert.deepEqual(blocks[3].items, [[{ text: "Exports grew [1]" }], [{ text: "Order win [2]" }]]);
  // Only http(s) links become links.
  assert.deepEqual(blocks[4].parts, [
    { text: "Read " },
    { text: "the filing", href: "https://nseindia.com/x" },
    { text: " or [this](javascript:alert(1))." },
  ]);
});

test("the news an answer cites is read back from the list under it", () => {
  const text = [
    "Exports grew [1].",
    "",
    "<details><summary>News searched: 2 headline(s) for “&quot;L&amp;T&quot; order”</summary>",
    "",
    "1. [L&amp;T wins \\*mega\\* \\[order\\] &lt;b&gt;](https://news.google.com/a_%281%29) · Mint · 2026-10-02",
    "2. [No source](https://x.in/b) · 2026-10-01",
    "",
    "</details>",
    "",
    "<!-- tracker:answered 11 12 -->",
    "",
    "---",
    "<sub>✦ LLM reading. Comment on this issue to ask a follow-up.</sub>",
  ].join("\n");
  const { blocks, note, news } = answerBlocks(text);
  assert.deepEqual(blocks, [{ type: "para", parts: [{ text: "Exports grew [1]." }] }]);
  assert.equal(news.summary, "News searched: 2 headline(s) for “\"L&T\" order”");
  assert.deepEqual(news.items, [
    { n: 1, title: "L&T wins *mega* [order] <b>", url: "https://news.google.com/a_%281%29", meta: "Mint · 2026-10-02" },
    { n: 2, title: "No source", url: "https://x.in/b", meta: "2026-10-01" },
  ]);
  assert.equal(note, "✦ LLM reading. Comment on this issue to ask a follow-up.");
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

test("recent questions come with their threads", async () => {
  const fetchFn = fakeFetch({
    "/issues?labels=": [200, [
      { number: 2, title: "Question: B", body: "", state: "open", comments: 0 },
      { number: 1, title: "Question: A", body: "", state: "closed", comments: 2 },
      { number: 9, title: "a PR", pull_request: {}, comments: 0 },
    ]],
    "/issues/1/comments": [200, [
      { user: { type: "Bot" }, body: "the answer" },
      { user: { type: "User" }, author_association: "OWNER", body: "and then?" },
    ]],
  });
  const { items, error } = await loadQuestions({ slug: "o/r", fetchFn, storage: memory() });
  assert.equal(error, undefined);
  assert.deepEqual(
    items.map((q) => [q.number, q.thread.map((t) => `${t.role}: ${t.body}`)]),
    [[2, []], [1, ["answer: the answer", "followup: and then?"]]],
  );
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
