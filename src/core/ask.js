// The Ask view's model: the issue a question leaves as, and the answers read
// back from GitHub's public API. Pure apart from the fetch, so it is tested
// without a network.
//
// A question travels like a Review decision: a pre-filled issue the owner
// submits under their own login. The dashboard-actions workflow answers it
// (analysis/ask.py) as a comment and labels it, which is how the questions
// are found again here. A comment the owner adds to the issue is a
// follow-up, answered in turn; the exchange is read back as a thread.

import { repoSlug } from "./review.js";

export const QUESTION_LABEL = "dashboard-question";
const MAX_QUESTION = 500;
// v2: items carry a thread rather than one answer.
const CACHE_KEY = "tracker-ask-cache-v2";
const CACHE_MS = 2 * 60 * 1000;

/** The new-issue URL that asks a question. */
export function questionUrl(question, focus = null, slug = repoSlug()) {
  const q = String(question || "").replace(/\s+/g, " ").trim().slice(0, MAX_QUESTION);
  const payload = { v: 1, question: q, ...(focus ? { focus: String(focus).toUpperCase() } : {}) };
  const body = [
    "Asked from the dashboard's Ask view. A workflow answers it from the latest briefing and a news search, and closes this issue. Comment on it afterwards to ask a follow-up.",
    "",
    `> ${q}`,
    "",
    "<!-- tracker:question v1 -->",
    "```json",
    JSON.stringify(payload),
    "```",
  ].join("\n");
  const title = `Question: ${q.length > 70 ? `${q.slice(0, 67)}...` : q}`;
  return `https://github.com/${slug}/issues/new?${new URLSearchParams({ title, body })}`;
}

/** One question issue as the view needs it. */
export function parseIssue(issue) {
  let question = String(issue?.title || "").replace(/^Question:\s*/, "");
  let focus = null;
  const block = /<!--\s*tracker:question v1\s*-->\s*```json\s*(\{[\s\S]*?\})\s*```/.exec(issue?.body || "");
  if (block) {
    try {
      const p = JSON.parse(block[1]);
      if (p.question) question = p.question;
      focus = p.focus || null;
    } catch {
      /* the title stands in */
    }
  }
  return {
    number: issue?.number,
    question,
    focus,
    state: issue?.state,
    url: issue?.html_url,
    created: issue?.created_at,
    comments: issue?.comments || 0,
  };
}

/**
 * The exchange on a question issue, in order: the workflow's answers and the
 * owner's follow-ups. Anyone else's comments are left out, as the workflow
 * leaves them out of what it answers.
 */
export function threadOf(comments) {
  return (comments || [])
    .filter((c) => c?.user?.type === "Bot" || c?.author_association === "OWNER")
    .map((c) => ({
      role: c.user?.type === "Bot" ? "answer" : "followup",
      body: String(c.body || ""),
      created: c.created_at,
    }));
}

const ENTITIES = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&#x27;": "'" };
const decode = (s) => s.replace(/&(?:amp|lt|gt|quot|#39|#x27);/g, (m) => ENTITIES[m]);
// What the workflow escaped to keep a headline from being read as Markdown.
const unescape = (s) => decode(s.replace(/\\([\\[\]*_`])/g, "$1"));

function inline(line) {
  return line
    .split(/(\*\*[^*]+\*\*|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/)
    .filter(Boolean)
    .map((part) => {
      if (/^\*\*[^*]+\*\*$/.test(part)) return { bold: part.slice(2, -2) };
      const link = /^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/.exec(part);
      return link ? { text: link[1], href: link[2] } : { text: part };
    });
}

// The collapsed list of headlines the news search found, as the workflow
// writes it (scripts/dashboard_actions.py format_answer).
function newsOf(details) {
  if (!details) return null;
  const summary = /<summary>([\s\S]*?)<\/summary>/.exec(details);
  const items = [];
  for (const line of details.split("\n")) {
    const m = /^(\d+)\. \[((?:\\.|[^\]\\])+)\]\((https?:\/\/[^\s)]+)\)(.*)$/.exec(line.trim());
    if (!m) continue;
    items.push({
      n: Number(m[1]),
      title: unescape(m[2]),
      url: m[3],
      meta: unescape(m[4].replace(/^\s*·\s*/, "").trim()),
    });
  }
  return { summary: summary ? decode(summary[1].trim()) : "", items };
}

/**
 * An answer as blocks to render as text: headings (a line in bold alone),
 * paragraphs and lists, with **bold** runs and http(s) links marked, the
 * news list it cites, and the footer note. Never HTML: the model wrote it,
 * and the page builds nodes from it rather than parsing its markup.
 */
export function answerBlocks(text) {
  let [main, footer] = String(text || "").split(/\n-{3,}\n/);
  let news = null;
  main = main
    .replace(/<details>([\s\S]*?)<\/details>/, (_, d) => {
      news = newsOf(d);
      return "";
    })
    .replace(/<!--[\s\S]*?-->/g, "");
  const blocks = [];
  for (const chunk of main.split(/\n\s*\n/)) {
    let para = [];
    let list = null;
    const flush = () => {
      if (para.length) blocks.push({ type: "para", parts: inline(para.join(" ")) });
      if (list) blocks.push({ type: "list", items: list });
      para = [];
      list = null;
    };
    for (const line of chunk.split("\n").map((l) => l.trim()).filter(Boolean)) {
      const item = /^(?:[-*]|\d+[.)])\s+(.*)$/.exec(line);
      if (/^\*\*[^*]+\*\*:?$/.test(line)) {
        flush();
        blocks.push({ type: "heading", text: line.replace(/^\*\*|\*\*:?$/g, "") });
      } else if (item) {
        if (para.length) flush();
        (list ||= []).push(inline(item[1]));
      } else {
        if (list) flush();
        para.push(line);
      }
    }
    flush();
  }
  const note = footer ? footer.replace(/<\/?sub>/g, "").trim() : "";
  return { blocks, note, news };
}

function cached(storage) {
  try {
    const hit = JSON.parse(storage?.getItem(CACHE_KEY) || "null");
    if (hit && Date.now() - hit.at < CACHE_MS) return hit.items;
  } catch {
    /* no cache */
  }
  return null;
}

/**
 * Recent questions and their threads, from GitHub's public API. Unsigned,
 * so GitHub allows 60 requests an hour from one network; cached for two
 * minutes, and an exhausted allowance comes back as an error to show.
 */
export async function loadQuestions({ slug = repoSlug(), fetchFn = globalThis.fetch, storage = globalThis.sessionStorage, fresh = false, limit = 8 } = {}) {
  if (!fresh) {
    const hit = cached(storage);
    if (hit) return { items: hit };
  }
  const api = `https://api.github.com/repos/${slug}`;
  const get = async (url) => {
    const r = await fetchFn(url, { headers: { Accept: "application/vnd.github+json" } });
    if (r.status === 403 || r.status === 429) throw new Error("rate");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  };
  try {
    const issues = await get(`${api}/issues?labels=${QUESTION_LABEL}&state=all&sort=created&direction=desc&per_page=${limit}`);
    const items = await Promise.all(
      (issues || [])
        .filter((i) => !i.pull_request)
        .map(async (i) => {
          const q = parseIssue(i);
          q.thread = q.comments ? threadOf(await get(`${api}/issues/${q.number}/comments?per_page=100`)) : [];
          return q;
        }),
    );
    try {
      storage?.setItem(CACHE_KEY, JSON.stringify({ at: Date.now(), items }));
    } catch {
      /* not cached */
    }
    return { items };
  } catch (err) {
    return { items: [], error: err.message === "rate" ? "rate" : String(err.message || err) };
  }
}
