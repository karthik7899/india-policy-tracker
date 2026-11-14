// Daily Intelligence — one evidence-led front page for the latest signals.
// The scraper remains the source of truth; each split dataset is resolved
// through the shared cache rather than read directly from a manifest.

import { el, mount } from "../core/dom.js";
import { resolve } from "../core/data.js";
import { href } from "../core/router.js";
import { shortDate } from "../core/format.js";
import { catalystPill } from "../core/catalyst.js";
import { panel, dataTable, tickerLink } from "./table.js";

const severityRank = { high: 0, critical: 0, medium: 1, low: 2 };
const confidenceRank = { high: 0, medium: 1, low: 2 };

export function priorityWarnings(rows = []) {
  return [...rows].sort((a, b) =>
    (severityRank[String(a.severity || "").toLowerCase()] ?? 3) -
      (severityRank[String(b.severity || "").toLowerCase()] ?? 3) ||
    (confidenceRank[String(a.confidence || "").toLowerCase()] ?? 3) -
      (confidenceRank[String(b.confidence || "").toLowerCase()] ?? 3) ||
    String(a.ticker || "").localeCompare(String(b.ticker || "")),
  );
}

export function catalystRows(policy = [], events = []) {
  const rows = [
    ...policy.map((item) => ({ ...item, kind: "policy", title: item.headline || item.title || "", date: item.date || "" })),
    ...events.map((item) => ({ ...item, kind: "event", title: item.headline || item.title || "", date: item.date || "" })),
  ];
  const strengthRank = { hard: 0, win: 0, l1: 1, announced: 2, proposed: 3, soft: 4, reported: 5 };
  return rows.sort((a, b) => {
    const ap = catalystPill(a);
    const bp = catalystPill(b);
    return (strengthRank[ap?.kind] ?? 6) - (strengthRank[bp?.kind] ?? 6) ||
      String(b.date).localeCompare(String(a.date));
  });
}

function stat(label, value, detail) {
  return el(
    "div",
    { class: "stat-tile" },
    el("div", { class: "stat-label" }, label),
    el("div", { class: "stat-value" }, String(value)),
    el("div", { class: "stat-detail" }, detail),
  );
}

function linkedHeadline(item, text) {
  return item.link
    ? el("a", { href: item.link, target: "_blank", rel: "noopener noreferrer" }, text)
    : text;
}

function evidenceList(rows, limit = 8) {
  if (!rows.length) return el("p", { class: "company-empty" }, "No items in this feed on the latest run.");
  return el(
    "ul",
    { class: "evidence" },
    rows.slice(0, limit).map((item) =>
      el(
        "li",
        {},
        item.ticker ? [tickerLink(item.ticker), " · "] : null,
        linkedHeadline(item, item.text || item.headline || item.title || "Untitled item"),
        item.detail ? el("span", { class: "evidence-meta" }, item.detail) : null,
        item.date ? el("span", { class: "evidence-meta" }, shortDate(item.date)) : null,
      ),
    ),
  );
}

function upcomingPanel(calendar) {
  const rows = (calendar?.upcoming || []).slice().sort((a, b) => String(a.date).localeCompare(String(b.date))).slice(0, 8);
  return panel(
    "Upcoming catalysts",
    "Exchange and company dates already tracked by the calendar.",
    rows.length
      ? el("ul", { class: "evidence" }, rows.map((item) =>
          el(
            "li",
            {},
            el("strong", {}, shortDate(item.date)),
            " · ",
            item.ticker ? [tickerLink(item.ticker), " · "] : null,
            linkedHeadline(item, item.title || "Event"),
            item.source ? el("span", { class: "evidence-meta" }, item.source) : null,
          ),
        ))
      : el("p", { class: "company-empty" }, "No upcoming events are available."),
    el("a", { class: "more-link", href: href("calendar") }, "Open full calendar →"),
  );
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const [institutional, marketEvents, policies, globalNews, publisherNews, calendar, digest] = await Promise.all([
    resolve(b, "institutional_activity"),
    resolve(b, "market_events"),
    resolve(b, "policy_impacts"),
    resolve(b, "global_market_news"),
    resolve(b, "publisher_news"),
    resolve(b, "event_calendar"),
    resolve(b, "company_digest"),
  ]);

  const warnings = priorityWarnings(b.early_warnings || []);
  const changes = b.changes || {};
  const newCount = Object.values(changes.counts || {}).reduce((sum, count) => sum + (Number(count) || 0), 0);
  const highRisk = warnings.filter((item) => String(item.severity || "").toLowerCase() === "high").length;
  const institutionalRows = Array.isArray(institutional) ? institutional : [];
  const catalystFeed = catalystRows(
    Array.isArray(policies) ? policies : [],
    Array.isArray(marketEvents) ? marketEvents : [],
  );
  const digestCompanies = digest?.companies || [];
  const newsRows = [
    ...(Array.isArray(globalNews) ? globalNews : []),
    ...(Array.isArray(publisherNews) ? publisherNews : []),
  ].sort((a, b) => {
    const ad = Date.parse(a.date || "");
    const bd = Date.parse(b.date || "");
    return (Number.isNaN(bd) ? -Infinity : bd) - (Number.isNaN(ad) ? -Infinity : ad);
  });

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Daily Intelligence"),
      el(
        "p",
        { class: "view-sub" },
        "Updated " + (payload?.last_updated || "—") + " · evidence-led monitoring across policy, companies, markets and institutions.",
      ),
    ),
    el(
      "div",
      { class: "stat-row" },
      stat("New developments", newCount, changes.first_run ? "First run; no prior comparison" : "Since the previous pipeline run"),
      stat("High-severity risks", highRisk, "From the current warning engine"),
      stat("Institutional signals", institutionalRows.length, "Institutional and block-deal news feed"),
      stat("Companies covered", digestCompanies.length || "—", "With a company activity digest"),
    ),
    panel(
      "Decision queue",
      "High-severity risks appear first, followed by medium and lower-severity signals. Confidence is shown as evidence quality, not as a probability.",
      warnings.length
        ? dataTable(
            warnings,
            [
              { key: "ticker", label: "Company", render: (item) => tickerLink(item.ticker) },
              { key: "severity", label: "Severity" },
              { key: "category", label: "Signal" },
              { key: "signal", label: "Evidence" },
              { key: "confidence", label: "Confidence" },
            ],
            { empty: "No current warnings." },
          )
        : el("p", { class: "company-empty" }, "No current warning signals."),
      el("a", { class: "more-link", href: href("risk") }, "Review all risk signals →"),
    ),
    el(
      "div",
      { class: "two-col" },
      panel(
        "Policy & market catalysts",
        "Hard policy and confirmed events are listed before proposals and unverified reports. This is a stage ranking, not an estimated share-price impact.",
        catalystFeed.length
          ? el(
              "ul",
              { class: "evidence" },
              catalystFeed.slice(0, 10).map((item) => {
                const pill = catalystPill(item);
                return el(
                  "li",
                  {},
                  pill ? el("span", { class: "pill pill-catalyst pill-" + pill.kind }, pill.label) : null,
                  linkedHeadline(item, item.title || "Untitled catalyst"),
                  item.effects?.length
                    ? el("span", { class: "evidence-meta" }, item.effects.map((effect) => String(effect.sector || "").replace(/_/g, " ") + " " + effect.direction).join(" · "))
                    : null,
                  el("span", { class: "evidence-meta" }, (item.date || "Undated") + " · " + (item.source || (item.kind === "policy" ? "Policy feed" : "Market event"))),
                );
              }),
            )
          : el("p", { class: "company-empty" }, "No policy or market catalysts in the latest feeds."),
        el("a", { class: "more-link", href: href("flow", { stream: "policy" }) }, "Open all catalysts in Flow →"),
      ),
      panel(
        "Institutional activity",
        "Reported block deals and institutional positioning headlines. These are news signals, not a substitute for exchange-reported FII / DII cash-market totals.",
        institutionalRows.length
          ? dataTable(
              institutionalRows.slice(0, 8),
              [
                { key: "date", label: "Date", render: (item) => shortDate(item.date) },
                { key: "company", label: "Company / scope" },
                { key: "buyer", label: "Investor" },
                { key: "action", label: "Action" },
                { key: "headline", label: "Report", render: (item) => linkedHeadline(item, item.headline) },
              ],
              { empty: "No institutional activity reported." },
            )
          : el("p", { class: "company-empty" }, "No institutional activity feed is available."),
        el("a", { class: "more-link", href: href("flow", { stream: "institutional" }) }, "Open institutional feed →"),
      ),
    ),
    el(
      "div",
      { class: "two-col" },
      panel(
        "What changed since the last run",
        changes.first_run ? "The next pipeline run will establish the comparison baseline." : "Changes are grouped by the existing pipeline's categories.",
        changes.first_run
          ? null
          : evidenceList(
              Object.entries(changes.items || {}).flatMap(([group, items]) =>
                (items || []).map((item) => ({ ...item, detail: [group, item.detail].filter(Boolean).join(" · ") })),
              ),
              12,
            ),
        el("a", { class: "more-link", href: href("overview") }, "Open full overview →"),
      ),
      panel(
        "Global & company news",
        "Recent external developments and publisher coverage. LLM-only classifications remain explicitly marked by their source data.",
        evidenceList(newsRows, 10),
        el("a", { class: "more-link", href: href("flow", { stream: "global" }) }, "Open full news stream →"),
      ),
    ),
    upcomingPanel(calendar),
  );
}
