// Holdings — the book, and the liquidity question about it.
//
// Absorbs the old "Holdings by Sector" and "Stocks Screener" tabs, which
// showed the same rows with different columns and no way to get from one to
// the other.
//
// The chart is delivery against turnover, and it is a SCATTER on purpose. The
// question is whether a name that looks liquid on turnover actually settles,
// and that is a relationship between two measures — the form a two-y-axis bar
// chart gets wrong, which is why the skill calls dual axes the single most
// misread chart.
//
// The filter row scopes the scatter, the count in the subtitle and the table
// together. That is the point of putting it above all three rather than inside
// one panel: there is no arrangement of controls that leaves the chart
// describing seventy holdings while the table describes nine.

import { el, mount } from "../core/dom.js";
import { num, crore, pct, bandIndex, BANDS, shortDate, sizeLabel } from "../core/format.js";
import { loadCoverage } from "../core/data.js";
import * as filters from "../core/filters.js";
import * as charts from "../charts/charts.js";
import { dataTable, panel, chartFrame, tickerLink } from "./table.js";
import { filterBar, filteredEmpty } from "./filterbar.js";

function flatten(watchlist) {
  const out = [];
  for (const [sector, stocks] of Object.entries(watchlist || {})) {
    for (const s of stocks || []) {
      if (s && typeof s === "object" && s.ticker) out.push({ ...s, sector });
    }
  }
  return out;
}

// Enough coverage to judge a signal without turning the drawer into a feed.
const COVERAGE_SHOWN = 8;

// The feed labels analysis/coverage.py uses as `source_kind`. Needed only to
// read sidecars written before event_type and source_kind became separate
// fields: there they are flattened into one `event_tags` list, and the only
// way to tell a classified event type from the name of the feed that carried
// it is to know which strings are feed names.
const SOURCE_KINDS = new Set(["agreement", "launch", "filing", "global", "sector news", "event"]);

/** What the engine read in the story, as opposed to which feed carried it. */
function classifiedType(item) {
  if (item.event_type !== undefined) return item.event_type || "";
  return (item.event_tags || []).find((t) => t && !SOURCE_KINDS.has(String(t).toLowerCase())) || "";
}

/** Which feed carried it. Provenance, not a description of the contents. */
function sourceKind(item) {
  if (item.source_kind !== undefined) return item.source_kind || "";
  return (item.event_tags || []).find((t) => t && SOURCE_KINDS.has(String(t).toLowerCase())) || "";
}

/** analysis/coverage.py's dedupe key, so the two lists agree on "same story". */
function evidenceKey(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9 ]+/g, "")
    .trim();
}


/** One sector-news row: headline as link, its kind as a tag, provenance below. */
// The LLM reader's direction for this sector, with the measure's status so
// a proposal is not read as a done deal. Absent when the item is not policy
// news or the reader has not seen it.
const POLICY_MARK = { tailwind: "\u25b2 policy tailwind", headwind: "\u25bc policy headwind", mixed: "\u25c6 policy mixed" };

export function policyTag(policy) {
  const mark = POLICY_MARK[policy?.direction];
  if (!mark) return "";
  const status = String(policy.status || "").replace(/_/g, " ");
  return status ? `${mark} (${status})` : mark;
}

function sectorRow(n) {
  const kind = (n.tags || [])[0] || "";
  const policy = policyTag(n.policy);
  return el(
    "li",
    {},
    n.url
      ? el("a", { href: n.url, target: "_blank", rel: "noopener noreferrer" }, n.headline || "")
      : n.headline || "",
    (kind && kind !== "other") || policy
      ? el(
          "span",
          { class: "evidence-tags" },
          kind && kind !== "other" ? el("span", { class: "tag" }, kind.replace(/_/g, " ")) : null,
          policy ? el("span", { class: "tag", title: "LLM reading, not verified" }, policy) : null,
        )
      : null,
    el(
      "span",
      { class: "evidence-meta" },
      [n.source, shortDate(n.date)].filter(Boolean).join(" \u00b7 "),
    ),
  );
}

/** The drawer: everything known about one holding, fetched on open. */
async function drawer(stock, payload) {
  const sc = stock.screener || {};
  const coverage = await loadCoverage(stock.ticker);

  // The warnings raised for THIS holding, so the evidence below sits next to
  // the claim it supports rather than on another tab.
  const key = String(stock.ticker || "").toUpperCase();
  const signals = (payload?.briefing?.early_warnings || []).filter(
    (w) => String(w.ticker || "").toUpperCase() === key,
  );

  // build_coverage keeps merged duplicates and aged-out stories on purpose, as
  // an audit trail. They are evidence about the PIPELINE, not about the
  // holding, so they are counted here and not listed among the articles.
  const items = coverage || [];
  const setAside = items.filter((c) => (c.status || "counted") !== "counted");

  // What moved in the sector this holding sits in. Coverage above answers
  // "what was written about THIS company"; a PLI scheme or a cabinet approval
  // names no company at all and is exactly the thing a reader holding a
  // beneficiary wants to see. Split by whether the item names this holding,
  // because "the sector moved" and "you were named in it" are different facts
  // and collapsing them would overstate the second.
  const block = (payload?.briefing?.sector_blocks || []).find(
    (s) => s.id === stock.sector,
  );
  const sectorNews = block?.news || [];
  const namesThis = (n) =>
    (n.affected_tickers || []).some((t) => String(t).toUpperCase() === key);
  const sectorDirect = sectorNews.filter(namesThis);
  const sectorWide = sectorNews.filter((n) => !namesThis(n));

  // ONE evidence list, not two. The drawer used to show a "Topics" section
  // beside this one, built from stock_topics — a different code path over the
  // same feeds, rendered as inert text with its links discarded. Measured
  // across the book, every one of its 214 headlines already appears in
  // coverage, and the 17 that looked unique were stories coverage had
  // deliberately set aside. So it was nine tenths duplication and one tenth
  // readmission of excluded stories, and coverage alone is strictly better:
  // it carries the links, and it knows what it excluded and why.
  // Anything already listed above as naming this holding is not repeated
  // here. The sector feed reaches coverage too, attributed "via sector news",
  // so without this the same two headlines appear in both sections — the exact
  // duplication the removal of "Topics" was meant to end.
  const shownAbove = new Set(sectorDirect.map((n) => evidenceKey(n.headline)));
  const counted = items.filter(
    (c) =>
      (c.status || "counted") === "counted" &&
      !shownAbove.has(evidenceKey(c.headline || c.title)),
  );

  const rows = [
    ["Price", stock.price ?? "—"],
    ["Target", stock.target ?? "—"],
    ["Upside", pct(stock.growth_pct)],
    ["P/E", sc.pe_ratio ?? "—"],
    ["ROCE", sc.roce !== undefined ? `${sc.roce}%` : "—"],
    ["Turnover", sc.advt_cr ? `${crore(sc.advt_cr)}/day (${sc.liquidity_band ?? "unknown"})` : "—"],
    [
      "Delivery",
      sc.deliv_pct !== undefined && sc.deliv_pct !== null
        ? `${sc.deliv_pct}% of last session (${sc.delivery_band ?? "unknown"})`
        : "—",
    ],
  ];

  return el(
    "div",
    { class: "drawer" },
    el("h3", { class: "drawer-title" }, `${stock.name || stock.ticker}`),
    el(
      "dl",
      { class: "drawer-facts" },
      rows.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, String(v))]),
    ),
    signals.length
      ? el(
          "div",
          { class: "drawer-section" },
          el("h4", {}, `Signals (${signals.length})`),
          el(
            "ul",
            { class: "evidence" },
            signals.map((w) =>
              el(
                "li",
                {},
                el(
                  "span",
                  { class: `tag tag-${w.direction === "risk" ? "risk" : "opp"}` },
                  w.direction === "risk" ? "risk" : "opportunity",
                ),
                " ",
                w.signal || w.category || "",
                // What the signal was struck from. A number off a results page
                // and a reading of a news story are different kinds of claim,
                // and the reader is entitled to know which one they are being
                // shown before they act on it.
                w.evidence_source
                  ? el("span", { class: "evidence-meta" }, ` — ${w.evidence_source}`)
                  : null,
                // How big it is against this company. Absent when the headline
                // carried no size the guards would attribute to one company —
                // which is "not known", never "small", so nothing is printed.
                typeof w.materiality_pct === "number"
                  ? el(
                      "span",
                      { class: "evidence-meta" },
                      `Sized at ${sizeLabel(w.materiality_pct, w.materiality_band)}`,
                    )
                  : null,
              ),
            ),
          ),
        )
      : null,

    sectorNews.length
      ? el(
          "div",
          { class: "drawer-section" },
          el("h4", {}, `Sector — ${block?.name || stock.sector || ""}`),
          sectorDirect.length
            ? el(
                "div",
                {},
                el("p", { class: "evidence-meta" }, "Names this holding"),
                el("ul", { class: "evidence" }, sectorDirect.map(sectorRow)),
              )
            : null,
          sectorWide.length
            ? el(
                "div",
                {},
                el(
                  "p",
                  { class: "evidence-meta" },
                  sectorDirect.length ? "Elsewhere in the sector" : "Sector-wide",
                ),
                el("ul", { class: "evidence" }, sectorWide.map(sectorRow)),
              )
            : null,
        )
      : null,

    counted.length || setAside.length
      ? el(
          "div",
          { class: "drawer-section" },
          el("h4", {}, `Coverage (${counted.length})`),
          // The articles, as links. Every one of these records already carried
          // source_url, source_label, date and the event tags that say WHY it
          // was attributed — and the drawer rendered the headline as plain
          // text and dropped the rest, so the evidence behind a signal was
          // present in the payload and unreachable from the page.
          el(
            "ul",
            { class: "evidence" },
            counted.slice(0, COVERAGE_SHOWN).map((c) => {
              const headline = c.headline || c.title || "";
              // Only the CLASSIFIED type earns a tag. source_kind names the
              // feed that carried the story, not the story, and showing it as
              // a badge told the reader a profit collapse was an "agreement".
              // It goes in the meta line as provenance, where it is true.
              const type = classifiedType(c);
              const via = sourceKind(c);
              return el(
                "li",
                {},
                c.source_url
                  ? el(
                      "a",
                      { href: c.source_url, target: "_blank", rel: "noopener noreferrer" },
                      headline,
                    )
                  : headline,
                type
                  ? el(
                      "span",
                      { class: "evidence-tags" },
                      el("span", { class: "tag" }, type.replace(/_/g, " ")),
                    )
                  : null,
                el(
                  "span",
                  { class: "evidence-meta" },
                  [c.source_label, shortDate(c.date), via ? `via ${via.toLowerCase()}` : ""]
                    .filter(Boolean)
                    .join(" · "),
                ),
              );
            }),
          ),
          // Set-aside items are named rather than silently dropped: the
          // sidecar keeps duplicates and aged-out stories deliberately, as the
          // audit trail for a scoring defect where one launch was counted
          // twice. "Not shown" and "not collected" are different facts.
          setAside.length || counted.length > COVERAGE_SHOWN
            ? el(
                "p",
                { class: "evidence-meta" },
                [
                  counted.length > COVERAGE_SHOWN
                    ? `${counted.length - COVERAGE_SHOWN} more counted`
                    : "",
                  setAside.length
                    ? `${setAside.length} set aside (duplicate or older than the window)`
                    : "",
                ]
                  .filter(Boolean)
                  .join(" · "),
              )
            : null,
        )
      : null,
  );
}

export async function render(container, { payload, route }) {
  const b = payload?.briefing || {};
  const all = flatten(payload?.watchlist);
  const active = filters.read(route);
  const thesisByTicker = filters.thesisIndex(b);
  const rows = filters.applyHoldings(all, active, { thesisByTicker });
  const params = (route && route.params) || {};
  const sectors = Object.keys(payload?.watchlist || {}).sort();

  // Grouped by delivery band, one dataset each, so the legend names every
  // colour on screen. These are the reserved STATUS roles rather than
  // categorical hues, which is correct — a band is an ordered judgement about
  // a holding, not an identity — and status colour never travels without its
  // label.
  //
  // trade-to-trade is `warning` and not `good` on purpose: delivery is
  // compulsory in that segment, so a high figure there is a surveillance rule
  // rather than evidence of real buyers, and colouring it like delivery-led
  // would manufacture a bullish signal out of a trading restriction.
  const BAND_SERIES = [
    { band: "delivery-led", label: "Delivery-led", status: "good" },
    { band: "mixed", label: "Mixed", status: "serious" },
    { band: "churn", label: "Churn", status: "critical" },
    { band: "trade-to-trade", label: "Trade-to-trade", status: "warning" },
    { band: null, label: "Band not reported", status: "unknown" },
  ];

  const plotted = rows
    .map((s) => {
      const sc = s.screener || {};
      const x = num(sc.advt_cr);
      const y = num(sc.deliv_pct);
      return x !== null && y !== null
        ? { x: Number(x.toFixed(1)), y: Number(y.toFixed(1)), label: s.ticker, band: sc.delivery_band }
        : null;
    })
    .filter(Boolean);

  const known = new Set(BAND_SERIES.map((s) => s.band).filter(Boolean));
  const series = BAND_SERIES.map((s) => ({
    label: s.label,
    status: s.status,
    points: plotted.filter((p) =>
      s.band === null ? !p.band || !known.has(p.band) : p.band === s.band,
    ),
  }));

  const filtered = filters.activeCount(active) > 0;

  mount(
    container,
    el(
      "header",
      { class: "view-head" },
      el("h2", { class: "view-title" }, "Holdings"),
      el(
        "p",
        { class: "view-sub" },
        filtered
          ? `${rows.length} of ${all.length} holdings`
          : `${all.length} holdings across ${sectors.length} sectors`,
      ),
    ),

    filterBar({
      view: "holdings",
      route,
      filters: active,
      fields: ["q", "sector", "thesis", "band"],
      sectors,
      summary: plotted.length ? `${plotted.length} plotted` : "",
    }),

    plotted.length
      ? panel(
          "Delivery against turnover",
          "Turnover counts every share that changed hands; delivery counts the " +
            "ones that settled. A name high on the x-axis and low on the y traded " +
            "heavily and delivered little — deep by turnover, few real buyers. " +
            "Holdings missing either figure are absent from the plot rather than " +
            "drawn at zero, so the count above may be lower than the table's.",
          chartFrame("chart-delivery", 330),
        )
      : null,

    panel(
      filtered ? "Matching holdings" : "All holdings",
      null,
      dataTable(
        rows,
        [
          {
            key: "ticker",
            label: "Stock",
            render: (r) => tickerLink(r.ticker, "holdings", params),
          },
          { key: "name", label: "Name" },
          { key: "sector", label: "Sector", render: (r) => String(r.sector).replace(/_/g, " ") },
          { key: "price", label: "Price", numeric: true },
          { key: "growth_pct", label: "Upside", numeric: true, render: (r) => pct(r.growth_pct) },
          {
            key: "advt_cr",
            label: "Turnover",
            numeric: true,
            sortValue: (r) => r.screener?.advt_cr,
            render: (r) => crore(r.screener?.advt_cr),
          },
          {
            key: "deliv_pct",
            label: "Delivery",
            numeric: true,
            sortValue: (r) => r.screener?.deliv_pct,
            render: (r) => {
              const d = num(r.screener?.deliv_pct);
              if (d === null) return "—";
              const band = r.screener?.delivery_band;
              // Direct label, always. The relief rule from the palette
              // validation: a mark whose hue is sub-3:1 must carry text.
              return el(
                "span",
                { class: `band-${band || "unknown"}` },
                `${d.toFixed(0)}%${band === "churn" ? " churn" : ""}`,
              );
            },
          },
        ],
        {
          focus: route?.focus,
          view: "holdings",
          route,
          empty: filtered ? filteredEmpty("holdings", params, "holdings") : "No holdings loaded.",
        },
      ),
    ),

    el("div", { id: "holding-drawer" }),
  );

  if (plotted.length) {
    charts.scatter(document.getElementById("chart-delivery"), {
      series,
      xLabel: "₹ Cr traded/day",
      yLabel: "% delivered",
    });
  }

  if (route?.focus) {
    const stock = all.find((s) => String(s.ticker).toUpperCase() === route.focus);
    if (stock) {
      const host = document.getElementById("holding-drawer");
      mount(host, await drawer(stock, payload));
      host.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }
}

export { BANDS, bandIndex };
