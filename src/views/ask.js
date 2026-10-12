// Ask — a question about the watchlist, answered from the briefing, the news
// and, for background, the model's general knowledge.
//
// The answer is an LLM reading (analysis/ask.py) in up to three labelled
// parts: what the committed briefing says, what headlines from a news search
// run for the question say, and background the model knows. It is told to
// cite what it used and never to give a figure from memory. It arrives as a
// comment on a GitHub issue, which is public on a public repository; the page
// says so before anything is asked. A comment the owner adds to the issue is
// a follow-up, and the exchange is shown here as a thread.

import { el, mount, disclosure } from "../core/dom.js";
import { href } from "../core/router.js";
import { shortDate, LLM_MARK } from "../core/format.js";
import { panel } from "./table.js";
import { questionUrl, loadQuestions, answerBlocks, QUESTION_LABEL } from "../core/ask.js";
import { repoSlug } from "../core/review.js";

const EXAMPLES = [
  "Why is SYRMA's thesis graded Broken?",
  "Which defence holdings have a policy tailwind this month?",
  "What changed for Dixon this week?",
];

function holdingsList(watchlist) {
  return Object.entries(watchlist || {})
    .filter(([sector, stocks]) => sector !== "macro_indicators" && Array.isArray(stocks))
    .flatMap(([, stocks]) => stocks.filter((s) => s && s.ticker))
    .sort((a, b) => String(a.ticker).localeCompare(String(b.ticker)));
}

const external = (url, text) => el("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, text);

function parts(segments) {
  return segments.map((s) => (s.bold ? el("strong", {}, s.bold) : s.href ? external(s.href, s.text) : s.text));
}

function blockView(b) {
  if (b.type === "heading") return el("p", { class: "ask-part" }, b.text);
  if (b.type === "list") return el("ul", {}, b.items.map((item) => el("li", {}, parts(item))));
  return el("p", {}, parts(b.parts));
}

function answerView(text) {
  const { blocks, note, news } = answerBlocks(text);
  return el(
    "div",
    { class: "ask-answer" },
    blocks.map(blockView),
    news && news.items.length
      ? disclosure(
          news.summary || `News searched: ${news.items.length} headline(s)`,
          el(
            "ol",
            { class: "ask-news" },
            news.items.map((n) =>
              el("li", { value: String(n.n) }, external(n.url, n.title), n.meta ? el("span", { class: "evidence-meta" }, ` · ${n.meta}`) : null),
            ),
          ),
        )
      : null,
    note ? el("p", { class: "evidence-meta" }, note) : null,
  );
}

function followUpView(text) {
  const { blocks } = answerBlocks(text);
  return el("div", { class: "ask-followup" }, el("p", { class: "ask-part" }, "Follow-up"), blocks.map(blockView));
}

function threadView(q) {
  const turns = q.thread || [];
  const answered = turns.some((t) => t.role === "answer");
  const waiting = turns.length && turns[turns.length - 1].role === "followup";
  return [
    turns.map((t) => (t.role === "answer" ? answerView(t.body) : followUpView(t.body))),
    waiting ? el("p", { class: "evidence-meta" }, "Waiting for an answer to the follow-up.") : null,
    answered
      ? el(
          "p",
          { class: "evidence-meta" },
          external(q.url, "Ask a follow-up on GitHub →"),
          " Comment on the issue; the answer is posted there and reads the exchange so far.",
        )
      : null,
  ];
}

function questionsPanel(result, refresh) {
  const { items, error } = result;
  const onGitHub = `https://github.com/${repoSlug()}/issues?q=label%3A${QUESTION_LABEL}`;
  return panel(
    "Recent questions",
    null,
    el(
      "p",
      { class: "review-actions" },
      el("button", { type: "button", class: "button-quiet", onclick: refresh }, "Refresh"),
      el("a", { href: onGitHub, target: "_blank", rel: "noopener noreferrer" }, "All of them on GitHub →"),
    ),
    error === "rate"
      ? el(
          "p",
          { class: "company-empty" },
          "GitHub's public API allows 60 requests an hour from one network, and that is used up. Read the answers on GitHub, or try again later.",
        )
      : error
        ? el("p", { class: "company-empty" }, `Could not load questions (${error}).`)
        : null,
    !error && !items.length
      ? el("p", { class: "company-empty" }, "No questions yet. Answers appear here a minute or two after an issue is submitted.")
      : null,
    items.length
      ? el(
          "ul",
          { class: "review-list" },
          items.map((q) => {
            const answers = (q.thread || []).filter((t) => t.role === "answer").length;
            const followUps = (q.thread || []).filter((t) => t.role === "followup").length;
            return el(
              "li",
              { class: "review-item" },
              el("p", { class: "review-headline" }, el("strong", {}, q.question)),
              el(
                "p",
                { class: "evidence-meta" },
                [
                  shortDate(q.created),
                  q.focus ? `asked from ${q.focus}` : "",
                  answers ? `answered ${LLM_MARK}` : q.state === "closed" ? "closed" : "waiting for an answer",
                  followUps ? `${followUps} follow-up${followUps === 1 ? "" : "s"}` : "",
                ]
                  .filter(Boolean)
                  .join(" · "),
                " · ",
                external(q.url, `#${q.number}`),
              ),
              threadView(q),
            );
          }),
        )
      : null,
  );
}

export async function render(container, { payload, route, fresh = false }) {
  const params = (route && route.params) || {};
  const focus = params.focus || "";
  const holdings = holdingsList(payload?.watchlist);
  const result = await loadQuestions({ fresh });

  const textarea = el("textarea", {
    id: "ask-text",
    class: "review-input ask-text",
    rows: "3",
    maxlength: "500",
    placeholder: "Ask about a holding, a sector, or the day's briefing",
    "aria-label": "Question",
  });
  const select = el(
    "select",
    { id: "ask-focus", class: "review-input", "aria-label": "About which holding" },
    el("option", { value: "" }, "Any holding"),
    holdings.map((s) => el("option", { value: s.ticker, selected: s.ticker === focus ? "" : null }, `${s.ticker} — ${s.name || ""}`)),
  );
  const ask = () => {
    const q = textarea.value.trim();
    if (!q) {
      textarea.focus();
      return;
    }
    window.open(questionUrl(q, select.value || null), "_blank", "noopener");
  };

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Ask"),
      el(
        "p",
        { class: "view-sub" },
        "Answered by the LLM from today's briefing first, then from a news search run for the question, then from its general knowledge for background, each part labelled. It is told to cite what it used and never to give a figure from memory.",
      ),
    ),
    panel(
      null,
      null,
      el(
        "div",
        { class: "ask-form" },
        textarea,
        el(
          "div",
          { class: "review-actions" },
          select,
          el("button", { type: "button", class: "button-primary", onclick: ask }, "Ask on GitHub"),
        ),
        el(
          "p",
          { class: "section-note" },
          "Opens a pre-filled GitHub issue; submit it under your login and an answer is posted on it in a minute or two. To ask a follow-up, comment on the same issue. ",
          el("strong", {}, "Questions and answers are public"),
          ": they are issues on a public repository.",
        ),
        el(
          "p",
          { class: "evidence-meta" },
          "For example: ",
          EXAMPLES.map((x, i) => [
            i ? " · " : "",
            el(
              "a",
              {
                href: href("ask", params),
                onclick: (e) => {
                  e.preventDefault();
                  textarea.value = x;
                  textarea.focus();
                },
              },
              x,
            ),
          ]),
        ),
      ),
    ),
    questionsPanel(result, () => render(container, { payload, route, fresh: true })),
  );
}
