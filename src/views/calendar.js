// Calendar — what each holding has coming up, and what its latest results
// said.
//
// Dates come from NSE's event calendar and corporate actions, from the board
// meeting notices companies file a week or more ahead, and from
// macro_events.json for market-wide dates a person entered. Results are set
// against a year earlier first: several holdings are seasonal, and with no
// consensus estimate available nothing is called a beat or a miss.

import { el, mount, emptyState, disclosure } from "../core/dom.js";
import { resolve } from "../core/data.js";
import { shortDate, pct } from "../core/format.js";
import { dataTable, panel, tickerLink } from "./table.js";
import { label } from "./companies.js";
import { byWeek, kindLabel } from "../core/calendar.js";
import { pickBook, positionOf } from "../core/portfolio.js";

function day(iso) {
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short" });
}

function kindPill(kind) {
  return el("span", { class: `tag cal-kind cal-${kind || "board"}` }, kindLabel(kind));
}

function eventRow(e, book, labels) {
  const position = e.ticker && book ? positionOf(book, e.ticker) : null;
  return el(
    "li",
    { class: "cal-event" },
    el("span", { class: "cal-day" }, day(e.date)),
    el(
      "span",
      { class: "cal-what" },
      e.ticker ? [tickerLink(e.ticker), " "] : null,
      kindPill(e.kind),
      " ",
      e.link ? el("a", { href: e.link, target: "_blank", rel: "noopener noreferrer" }, e.title) : e.title,
      e.detail ? el("span", { class: "evidence-meta" }, e.detail) : null,
      el(
        "span",
        { class: "evidence-meta" },
        [
          e.ticker ? `${e.name || ""}${e.sector ? ` · ${label(e.sector, labels)}` : ""}` : (e.sectors || []).map((s) => label(s, labels)).join(", "),
          position ? `${position.weight_pct.toFixed(2)}% of the book` : "",
          e.source ? `${e.source}${e.carried ? " (from an earlier run)" : ""}` : "",
        ]
          .filter(Boolean)
          .join(" · "),
      ),
    ),
  );
}

function resultsPanel(results) {
  const cards = results?.scorecards || [];
  const today = new Set(results?.reported_today || []);
  return panel(
    "Results",
    "Each holding's latest quarter as it appeared in its reported figures, against a year earlier first. The quarter is inferred from the day the figures changed. No consensus estimate is available, so none is called a beat or a miss.",
    cards.length
      ? dataTable(
          cards,
          [
            { key: "ticker", label: "Holding", render: (c) => [tickerLink(c.ticker), today.has(c.ticker) ? el("span", { class: "pill pill-good portfolio-new" }, "new") : null] },
            { key: "quarter", label: "Quarter", render: (c) => c.quarter || "—" },
            { key: "sales_cr", label: "Sales", numeric: true, render: (c) => `₹${Math.round(c.sales_cr).toLocaleString("en-IN")} Cr` },
            { key: "sales_yoy_pct", label: "vs a year ago", numeric: true, render: (c) => pct(c.sales_yoy_pct) },
            { key: "sales_qoq_pct", label: "vs the quarter before", numeric: true, render: (c) => pct(c.sales_qoq_pct) },
            { key: "eps_yoy_pct", label: "EPS vs a year ago", numeric: true, render: (c) => pct(c.eps_yoy_pct) },
            { key: "opm_change_pp", label: "Margin", numeric: true, render: (c) => (typeof c.opm_pct === "number" ? `${c.opm_pct.toFixed(0)}% (${pct(c.opm_change_pp).replace("%", " pts")})` : "—") },
            { key: "detected", label: "Seen", render: (c) => shortDate(c.detected) },
          ],
          { sort: { key: "detected", dir: "desc" }, empty: "" },
        )
      : el(
          "p",
          { class: "company-empty" },
          results?.tracking_since
            ? `No holding has reported since ${shortDate(results.tracking_since)}, when results began to be tracked. A holding that reported before then has no scorecard until its next quarter.`
            : "Results appear here once a holding reports; the first run only records each holding's figures to compare with.",
        ),
  );
}

export async function render(container, { payload }) {
  const b = payload?.briefing || {};
  const labels = payload?.sectors || {};
  const [calendar, results, portfolio] = await Promise.all([
    resolve(b, "event_calendar"),
    resolve(b, "results"),
    resolve(b, "portfolio"),
  ]);
  if (!calendar) {
    mount(
      container,
      el("header", { class: "view-head" }, el("h2", { class: "view-title" }, "Calendar")),
      emptyState("No calendar on this run.", "It is built from NSE's calendars and the companies' own filings."),
    );
    return;
  }
  const book = pickBook(portfolio);
  const weeks = byWeek(calendar.upcoming, calendar.macro);
  const src = calendar.sources || {};
  const nse = src.nse || {};
  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Calendar"),
      el(
        "p",
        { class: "view-sub" },
        `The next ${calendar.ahead_days} days for every holding, as of ${shortDate(calendar.as_of)}.`,
      ),
    ),
    resultsPanel(results),
    panel(
      "Coming up",
      "Board meetings and their purpose, dividend and other ex-dates, and AGMs. Dates come from NSE's event calendar and corporate actions, and from the notices companies file ahead of a board meeting; a date seen on an earlier run stays until it passes." +
        (book && book.kind === "model" ? " Weights are the model book's." : ""),
      weeks.length
        ? weeks.map((w) =>
            el(
              "section",
              { class: "cal-week" },
              el("h4", { class: "portfolio-sub" }, `Week of ${shortDate(w.week)}`),
              el("ul", { class: "cal-list" }, w.events.map((e) => eventRow(e, book, labels))),
            ),
          )
        : el("p", { class: "company-empty" }, "Nothing dated in the window."),
      el(
        "p",
        { class: "evidence-meta" },
        [
          Object.keys(nse).length
            ? `NSE: ${Object.entries(nse).map(([k, n]) => `${n} ${k.replace(/_/g, " ")} record(s)`).join(", ")}`
            : "NSE calendars not read on this run",
          (src.nse_errors || []).length ? `failed: ${src.nse_errors.join("; ")}` : "",
          `${src.filings || 0} from board-meeting notices`,
          `${src.carried || 0} kept from an earlier run`,
        ]
          .filter(Boolean)
          .join(" · "),
      ),
      (calendar.macro || []).length
        ? null
        : el("p", { class: "evidence-meta" }, "Market-wide dates (an RBI policy, the Budget) are added by hand to macro_events.json; none are entered."),
    ),
    (calendar.recent || []).length
      ? panel(
          null,
          null,
          disclosure(
            `${calendar.recent.length} event(s) in the last ${calendar.back_days} days`,
            el("ul", { class: "cal-list" }, calendar.recent.map((e) => eventRow(e, book, labels))),
          ),
        )
      : null,
  );
}
