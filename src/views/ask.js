// Ask — a question about the watchlist, answered from the briefing.
//
// The answer is an LLM reading of an extract of the committed briefing
// (analysis/ask.py), told to cite what it used and to say what the data
// does not contain. It arrives as a comment on a GitHub issue, which is
// public on a public repository; the page says so before anything is asked.

import { el, mount } from "../core/dom.js";
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

function parts(segments) {
  return segments.map((s) => (s.bold ? el("strong", {}, s.bold) : s.text));
}

function answerView(text) {
  const { blocks, note } = answerBlocks(text);
  return el(
    "div",
    { class: "ask-answer" },
    blocks.map((b) =>
      b.type === "list"
        ? el("ul", {}, b.items.map((item) => el("li", {}, parts(item))))
        : el("p", {}, parts(b.parts)),
    ),
    note ? el("p", { class: "evidence-meta" }, note) : null,
  );
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
          items.map((q) =>
            el(
              "li",
              { class: "review-item" },
              el("p", { class: "review-headline" }, el("strong", {}, q.question)),
              el(
                "p",
                { class: "evidence-meta" },
                [shortDate(q.created), q.focus ? `asked from ${q.focus}` : "", q.answer ? `answered ${LLM_MARK}` : q.state === "closed" ? "closed" : "waiting for an answer"]
                  .filter(Boolean)
                  .join(" · "),
                " · ",
                el("a", { href: q.url, target: "_blank", rel: "noopener noreferrer" }, `#${q.number}`),
              ),
              q.answer ? answerView(q.answer) : null,
            ),
          ),
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
        "Answered from today's briefing by the LLM, which is told to cite what it used and to say when the data does not answer.",
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
          "Opens a pre-filled GitHub issue; submit it under your login and an answer is posted on it in a minute or two. ",
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
