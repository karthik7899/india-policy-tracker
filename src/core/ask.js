// The Ask view's model: the issue a question leaves as, and the answers read
// back from GitHub's public API. Pure apart from the fetch, so it is tested
// without a network.
//
// A question travels like a Review decision: a pre-filled issue the owner
// submits under their own login. The dashboard-actions workflow answers it
// from the briefing (analysis/ask.py) as a comment and labels it, which is
// how the questions are found again here.

import { repoSlug } from "./review.js";

export const QUESTION_LABEL = "dashboard-question";
const MAX_QUESTION = 500;
const CACHE_KEY = "tracker-ask-cache-v1";
const CACHE_MS = 2 * 60 * 1000;

/** The new-issue URL that asks a question. */
export function questionUrl(question, focus = null, slug = repoSlug()) {
  const q = String(question || "").replace(/\s+/g, " ").trim().slice(0, MAX_QUESTION);
  const payload = { v: 1, question: q, ...(focus ? { focus: String(focus).toUpperCase() } : {}) };
  const body = [
    "Asked from the dashboard's Ask view. A workflow answers it from the latest briefing and closes this issue.",
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

/** The workflow's answer among an issue's comments: the latest from a bot. */
export function pickAnswer(comments) {
  const bot = (comments || []).filter((c) => c?.user?.type === "Bot");
  return bot.length ? String(bot[bot.length - 1].body || "") : null;
}

/**
 * An answer as blocks to render as text: paragraphs and "- " lists, with
 * **bold** runs marked. Never HTML: the model wrote it, and the page builds
 * nodes from it rather than parsing its markup.
 */
export function answerBlocks(text) {
  const [main, footer] = String(text || "").split(/\n-{3,}\n/);
  const inline = (line) =>
    line
      .split(/(\*\*[^*]+\*\*)/)
      .filter(Boolean)
      .map((part) => (/^\*\*[^*]+\*\*$/.test(part) ? { bold: part.slice(2, -2) } : { text: part }));
  const blocks = [];
  for (const chunk of main.split(/\n\s*\n/)) {
    const lines = chunk.split("\n").map((l) => l.trim()).filter(Boolean);
    if (!lines.length) continue;
    if (lines.every((l) => /^[-*] /.test(l))) {
      blocks.push({ type: "list", items: lines.map((l) => inline(l.slice(2))) });
    } else {
      blocks.push({ type: "para", parts: inline(lines.join(" ")) });
    }
  }
  const note = footer ? footer.replace(/<\/?sub>/g, "").trim() : "";
  return { blocks, note };
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
 * Recent questions and their answers, from GitHub's public API. Unsigned,
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
          q.answer = q.comments ? pickAnswer(await get(`${api}/issues/${q.number}/comments`)) : null;
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
