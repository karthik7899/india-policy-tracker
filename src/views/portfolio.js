// Portfolio — the money: what the book is worth, what it is exposed to, how
// fast it could be sold, how it moves against its benchmark, which limits it
// breaks, and the orders that would restore its targets.
//
// Everything is computed by analysis/portfolio.py from portfolios.json and
// the run's prices; this view only lays it out. The committed book is a
// model (the watchlist in equal weights), and the page says so wherever a
// figure could be mistaken for a real holding's.

import { el, mount, emptyState, disclosure } from "../core/dom.js";
import { resolve } from "../core/data.js";
import { href } from "../core/router.js";
import { pct, shortDate } from "../core/format.js";
import { dataTable, panel, tickerLink } from "./table.js";
import { label } from "./companies.js";
import { pickBook, orderGroups, limitStatus, ordersCsv, csvName } from "../core/portfolio.js";

function cr(value, digits = 1) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return `₹${value.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits })} Cr`;
}

function signedCr(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : value < 0 ? "-" : ""}${cr(Math.abs(value))}`;
}

function fixed(value, digits = 1, suffix = "") {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(digits)}${suffix}` : "—";
}

function tile(labelText, value, detail, tone) {
  return el(
    "div",
    { class: `stat-tile${tone ? ` tone-${tone}` : ""}` },
    el("div", { class: "stat-label" }, labelText),
    el("div", { class: "stat-value" }, value),
    detail ? el("div", { class: "stat-detail" }, detail) : null,
  );
}

function tickers(list) {
  return (list || []).map((t, i) => [i ? ", " : "", tickerLink(t)]);
}

function okPill(ok) {
  if (ok === null) return el("span", { class: "pill pill-warning" }, el("span", { class: "pill-mark", "aria-hidden": "true" }, "?"), "unmeasured");
  return ok
    ? el("span", { class: "pill pill-good" }, el("span", { class: "pill-mark", "aria-hidden": "true" }, "✓"), "within")
    : el("span", { class: "pill pill-critical" }, el("span", { class: "pill-mark", "aria-hidden": "true" }, "✕"), "breached");
}

/** A horizontal bar for a weight, with the target marked on it. */
function weightBar(weight, target, scale) {
  const w = Math.max(0, Math.min(100, (weight / scale) * 100));
  const t = typeof target === "number" ? Math.max(0, Math.min(100, (target / scale) * 100)) : null;
  return el(
    "span",
    { class: "weight-bar", "aria-hidden": "true" },
    el("span", { class: "weight-fill", style: `width:${w.toFixed(1)}%` }),
    t === null ? null : el("span", { class: "weight-target", style: `left:${t.toFixed(1)}%` }),
  );
}

function download(book, asOf) {
  const blob = new Blob([ordersCsv(book)], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: csvName(book, asOf) });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function header(book, data, params) {
  const books = (data.books || []).filter(Boolean);
  return el(
    "header",
    { class: "view-head" },
    el("h2", { class: "view-title" }, "Portfolio"),
    el(
      "p",
      { class: "view-sub" },
      book.name,
      book.kind === "model" ? el("span", { class: "pill pill-warning portfolio-model" }, "model, not real holdings") : null,
      ` · as of ${shortDate(data.as_of)}`,
    ),
    book.note ? el("p", { class: "section-note" }, book.note) : null,
    books.length > 1
      ? el(
          "p",
          { class: "review-actions" },
          books.map((b) =>
            el(
              "a",
              {
                class: `filter-clear${b.id === book.id ? " nav-active" : ""}`,
                href: href("portfolio", { ...params, book: b.id, sort: null, dir: null }),
              },
              b.name || b.id,
            ),
          ),
        )
      : null,
  );
}

function summaryTiles(book) {
  const s = book.summary || {};
  const r = book.risk || {};
  const liq = Object.fromEntries((book.liquidity?.exitable || []).map((e) => [e.days, e.pct]));
  const bench = book.benchmark?.label || "benchmark";
  const breaches = book.breaches || [];
  return el(
    "div",
    { class: "stat-row portfolio-tiles" },
    tile("Value", cr(s.nav_cr), `${s.positions} positions · ${fixed(s.cash_pct, 1, "%")} cash`),
    typeof s.pnl_cr === "number"
      ? tile(
          "Unrealised P&L",
          signedCr(s.pnl_cr),
          `${pct(s.pnl_pct, 2)} on cost` +
            (typeof s.benchmark_since_inception_pct === "number" && book.inception
              ? ` · ${bench} ${pct(s.benchmark_since_inception_pct)} since ${shortDate(book.inception)}`
              : ""),
        )
      : null,
    tile(
      `Beta to the ${bench}`,
      fixed(r.beta, 2),
      typeof r.vol_pct === "number"
        ? `volatility ${fixed(r.vol_pct, 1, "%")} a year · tracking error ${fixed(r.tracking_error_pct, 1, "%")}`
        : r.insufficient || book.benchmark?.missing || "",
    ),
    tile(
      "1-in-20 week loss",
      r.var_95 ? cr(r.var_95.cr) : "—",
      r.var_95 ? `${fixed(r.var_95.pct, 2, "%")} of NAV · the worst weeks averaged ${fixed(r.var_95.shortfall_pct, 2, "%")}` : "",
    ),
    tile("Sellable in 5 days", fixed(liq[5], 0, "%"), `${fixed(liq[1], 0, "%")} in a day · at ${book.liquidity?.participation_pct ?? 20}% of daily value traded`),
    tile(
      "Limit breaches",
      String(breaches.length),
      breaches.length ? `${breaches.filter((b) => b.new).length} new since the last run` : "every limit met",
      breaches.length ? "critical" : null,
    ),
  );
}

function limitsPanel(book, labels) {
  const status = limitStatus(book);
  const breaches = book.breaches || [];
  const subject = (row) =>
    row.key === "max_sector_pct" ? label(row.subject, labels) : row.subject;
  return panel(
    "Limits",
    "The book's own limits (portfolios.json), checked every run. A position over a cap is cut back by the orders below; the cap and its reason are listed there.",
    status.length
      ? dataTable(
          status,
          [
            { key: "label", label: "Limit" },
            { key: "limit", label: "Set at", numeric: true, render: (r) => `${r.limit}${r.unit.startsWith("%") ? "%" : r.unit === "days" ? " days" : ""}` },
            {
              key: "value",
              label: "Now",
              numeric: true,
              render: (r) =>
                r.value === null ? "—" : `${fixed(r.value, r.unit === "days" ? 1 : 2)}${r.unit.startsWith("%") ? "%" : r.unit === "days" ? " days" : ""}`,
            },
            { key: "subject", label: "Set by", render: (r) => (r.subject && /^[A-Z0-9&-]+$/.test(r.subject) ? tickerLink(r.subject) : subject(r) || "the book") },
            { key: "ok", label: "", render: (r) => okPill(r.ok) },
          ],
          { empty: "" },
        )
      : el("p", { class: "company-empty" }, "This book sets no limits."),
    breaches.length
      ? el(
          "ul",
          { class: "portfolio-breaches" },
          breaches.map((b) =>
            el("li", {}, b.message, b.new ? el("span", { class: "pill pill-critical portfolio-new" }, "new") : null),
          ),
        )
      : null,
    (book.unmeasured || []).length
      ? disclosure(
          `${book.unmeasured.length} figure(s) could not be measured`,
          el("ul", { class: "portfolio-breaches" }, book.unmeasured.map((u) => el("li", {}, u))),
        )
      : null,
  );
}

function returnsPanel(book, labels) {
  const ret = book.returns || {};
  const bench = book.benchmark?.label || "Benchmark";
  if (!(ret.windows || []).length) {
    return panel("Returns", null, el("p", { class: "company-empty" }, book.benchmark?.missing || "No weekly closes to measure returns from."));
  }
  const contrib = (rows) =>
    dataTable(
      rows,
      [
        { key: "ticker", label: "Holding", render: (r) => tickerLink(r.ticker) },
        { key: "pct", label: "Contribution", numeric: true, render: (r) => pct(r.pct, 2).replace("%", " pts") },
      ],
      { empty: "" },
    );
  return panel(
    "Returns against the " + bench,
    "A backcast: today's weights held through each window, from weekly closes. It says how the current book would have done, not how this book did — nothing records past positions. Holdings listed for less than a window are left out of it and the rest reweighted.",
    el(
      "p",
      { class: "portfolio-caveat" },
      el("strong", {}, "It flatters the book. "),
      "These holdings are on the watchlist partly because they rose — the rotation engine adds names that are growing and drops ones that are not — so the gap over the benchmark says more about how they were chosen than about what comes next. The track record on the Overview measures each pick from the day it was made.",
    ),
    dataTable(
      ret.windows,
      [
        { key: "label", label: "Window", render: (r) => `${r.label} (from ${shortDate(r.from)})` },
        { key: "portfolio_pct", label: "Book", numeric: true, render: (r) => pct(r.portfolio_pct) },
        { key: "benchmark_pct", label: bench, numeric: true, render: (r) => pct(r.benchmark_pct) },
        { key: "active_pct", label: "Difference", numeric: true, render: (r) => pct(r.active_pct).replace("%", " pts") },
        { key: "unpriced", label: "Left out", render: (r) => (r.unpriced?.length ? tickers(r.unpriced) : "—") },
      ],
      { empty: "" },
    ),
    ret.week
      ? el(
          "p",
          { class: "evidence-meta" },
          `Week of ${shortDate(ret.week.week_of)}: book ${pct(ret.week.portfolio_pct)}, ${bench} ${pct(ret.week.benchmark_pct)}.`,
        )
      : null,
    ret.contribution_window
      ? el(
          "div",
          { class: "company-cols" },
          el("div", {}, el("h4", { class: "portfolio-sub" }, `Added most, ${ret.contribution_window}`), contrib(ret.best || [])),
          el("div", {}, el("h4", { class: "portfolio-sub" }, `Cost most, ${ret.contribution_window}`), contrib(ret.worst || [])),
        )
      : null,
    (ret.by_sector || []).length
      ? disclosure(
          `By sector, ${ret.contribution_window}`,
          dataTable(
            ret.by_sector,
            [
              { key: "sector", label: "Sector", render: (r) => label(r.sector, labels) },
              { key: "pct", label: "Contribution", numeric: true, render: (r) => pct(r.pct, 2).replace("%", " pts") },
            ],
            { empty: "" },
          ),
        )
      : null,
    el(
      "p",
      { class: "evidence-meta" },
      "Allocation and selection against the benchmark need its constituent weights, which no source this pipeline reads provides; contribution by holding and sector is shown instead.",
    ),
  );
}

function exposurePanel(book, labels) {
  const exp = book.exposure || {};
  const sectors = exp.sectors || [];
  const scale = Math.max(1, ...sectors.map((s) => Math.max(s.weight_pct, s.target_pct || 0)), book.limits?.max_sector_pct || 0);
  const c = exp.concentration || {};
  return panel(
    "Exposure",
    `Largest position ${fixed(c.largest_pct, 2, "%")}, top ten ${fixed(c.top10_pct, 1, "%")}. ` +
      `Spread equals ${fixed(c.effective_names, 1)} equal positions (1 ÷ the sum of squared weights).`,
    dataTable(
      sectors,
      [
        { key: "sector", label: "Sector", render: (r) => el("a", { href: href("companies", { sector: r.sector }) }, label(r.sector, labels)) },
        { key: "count", label: "Holdings", numeric: true },
        { key: "weight_pct", label: "Weight", numeric: true, render: (r) => fixed(r.weight_pct, 2, "%") },
        { key: "target_pct", label: "Target", numeric: true, render: (r) => fixed(r.target_pct, 2, "%") },
        { key: "bar", label: "", sortable: false, render: (r) => weightBar(r.weight_pct, r.target_pct, scale) },
      ],
      { empty: "" },
    ),
    (exp.groups || []).length
      ? el(
          "div",
          {},
          el("h4", { class: "portfolio-sub" }, "Business groups"),
          dataTable(
            exp.groups,
            [
              { key: "group", label: "Group" },
              { key: "weight_pct", label: "Weight", numeric: true, render: (r) => fixed(r.weight_pct, 2, "%") },
              { key: "tickers", label: "Holdings", render: (r) => tickers(r.tickers) },
            ],
            { empty: "" },
          ),
          el("p", { class: "evidence-meta" }, "Groups with more than one holding, from business_groups.json, which lists only certain memberships."),
        )
      : null,
  );
}

function liquidityPanel(book) {
  const liq = book.liquidity || {};
  const rate = liq.participation_pct ?? 20;
  const pro = Object.fromEntries((liq.pro_rata || []).map((p) => [p.share_pct, p.days]));
  return panel(
    "Liquidity at the real size",
    `Days to sell each position at ${rate}% of its average daily value traded over the last month, and how much of the book could be sold how fast if every position were sold at once. No order-book depth is behind these.`,
    el(
      "p",
      { class: "portfolio-line" },
      (liq.exitable || []).map((e, i) => [i ? " · " : "", el("strong", {}, `${fixed(e.pct, 1, "%")}`), ` in ${e.days} day${e.days > 1 ? "s" : ""}`]),
      ` · selling a quarter of every position takes ${fixed(pro[25], 1)} days, half ${fixed(pro[50], 1)} (the slowest sets the pace) · value-weighted ${fixed(liq.weighted_days, 1)} days`,
    ),
    dataTable(
      liq.slowest || [],
      [
        { key: "ticker", label: "Slowest to sell", render: (r) => tickerLink(r.ticker) },
        { key: "value_cr", label: "Position", numeric: true, render: (r) => cr(r.value_cr, 2) },
        { key: "advt_cr", label: "Traded a day", numeric: true, render: (r) => cr(r.advt_cr, 2) },
        { key: "pct_of_adv", label: "× a day's trading", numeric: true, render: (r) => fixed(r.pct_of_adv / 100, 1, "×") },
        { key: "days_to_exit", label: "Days to exit", numeric: true, render: (r) => fixed(r.days_to_exit, 1) },
      ],
      { empty: "" },
    ),
    (liq.unmeasured || []).length
      ? el("p", { class: "evidence-meta" }, "No traded value on record for ", tickers(liq.unmeasured), "; counted as not sellable above.")
      : null,
  );
}

function riskPanel(book) {
  const r = book.risk || {};
  const bench = book.benchmark?.label || "benchmark";
  if (typeof r.vol_pct !== "number") {
    return panel("Risk", null, el("p", { class: "company-empty" }, r.insufficient || book.benchmark?.missing || "Not enough weekly closes yet."));
  }
  const dd = r.max_drawdown || {};
  const w4 = r.worst_4_weeks;
  const stats = [
    ["Volatility", `${fixed(r.vol_pct, 1, "%")} a year`, `${bench} ${fixed(r.benchmark_vol_pct, 1, "%")}`],
    ["Beta", fixed(r.beta, 2), `correlation ${fixed(r.correlation, 2)}`],
    ["Tracking error", `${fixed(r.tracking_error_pct, 1, "%")} a year`, "how far the book strays from the benchmark in a typical year"],
    ["Deepest fall", fixed(dd.pct, 1, "%"), dd.peak ? `${shortDate(dd.peak)} to ${shortDate(dd.trough)} · ${bench} ${fixed(r.benchmark_max_drawdown_pct, 1, "%")} at its worst` : ""],
    ["Worst week", fixed(r.worst_week?.pct, 2, "%"), r.worst_week ? `week of ${shortDate(r.worst_week.week_of)} · ${bench} ${pct(r.worst_week.benchmark_pct, 2)}` : ""],
  ];
  return panel(
    "Risk",
    `From ${r.weeks} weekly returns (${shortDate(r.from)} to ${shortDate(r.to)}) at today's weights. A year is short: these figures move a lot from one year to the next.`,
    el(
      "dl",
      { class: "portfolio-stats" },
      stats.map(([k, v, d]) => [el("dt", {}, k), el("dd", {}, el("strong", {}, v), d ? el("span", { class: "evidence-meta" }, ` ${d}`) : null)]),
    ),
    w4
      ? el(
          "p",
          { class: "portfolio-line" },
          `Worst four weeks: ${shortDate(w4.from)} to ${shortDate(w4.to)}, ${pct(w4.pct, 2)} (${signedCr(w4.cr)}) against ${bench} ${pct(w4.benchmark_pct, 2)}. Most of it came from `,
          w4.contributors.map((c, i) => [i ? ", " : "", tickerLink(c.ticker), ` ${pct(c.pct, 2).replace("%", " pts")}`]),
          ".",
        )
      : null,
    el(
      "div",
      { class: "company-cols" },
      el(
        "div",
        {},
        el("h4", { class: "portfolio-sub" }, "Where the swings come from"),
        dataTable(
          r.contributors || [],
          [
            { key: "ticker", label: "Holding", render: (x) => tickerLink(x.ticker) },
            { key: "weight_pct", label: "Weight", numeric: true, render: (x) => fixed(x.weight_pct, 2, "%") },
            { key: "risk_share_pct", label: "Share of risk", numeric: true, render: (x) => fixed(x.risk_share_pct, 1, "%") },
            { key: "beta", label: "Beta", numeric: true, render: (x) => fixed(x.beta, 2) },
          ],
          { empty: "" },
        ),
      ),
      el(
        "div",
        {},
        el("h4", { class: "portfolio-sub" }, "Holdings that move together"),
        dataTable(
          r.correlated_pairs || [],
          [
            { key: "a", label: "Pair", render: (x) => [tickerLink(x.a), " + ", tickerLink(x.b)] },
            { key: "correlation", label: "Correlation", numeric: true, render: (x) => fixed(x.correlation, 2) },
            { key: "weight_pct", label: "Together", numeric: true, render: (x) => fixed(x.weight_pct, 2, "%") },
          ],
          { empty: "" },
        ),
      ),
    ),
    (r.no_history || []).length
      ? el("p", { class: "evidence-meta" }, "Under half a year of prices, so no beta or volatility of their own: ", tickers(r.no_history), ".")
      : null,
  );
}

function scenariosPanel(book) {
  const rows = book.scenarios || [];
  if (!rows.length) return null;
  return panel(
    "What if",
    "Read from prices the run already has. Shocks to crude, the rupee or rates are not here: a year of weekly prices cannot tell a holding's sensitivity to them from noise.",
    dataTable(
      rows,
      [
        { key: "label", label: "Scenario", render: (r) => [el("strong", {}, r.label), el("div", { class: "evidence-meta" }, r.basis)] },
        { key: "pct", label: "Book", numeric: true, render: (r) => pct(r.pct, 2) },
        { key: "cr", label: "Rupees", numeric: true, render: (r) => signedCr(r.cr) },
        {
          key: "contributors",
          label: "Hit hardest",
          render: (r) => (r.contributors || []).slice(0, 3).map((c, i) => [i ? ", " : "", tickerLink(c.ticker)]),
        },
      ],
      { empty: "" },
    ),
  );
}

function ordersPanel(book, asOf) {
  const o = book.orders || {};
  const { main, settle } = orderGroups(o);
  const rows = o.rows || [];
  const columns = [
    { key: "side", label: "Side", render: (r) => el("span", { class: r.side === "SELL" ? "order-sell" : "order-buy" }, r.side) },
    { key: "ticker", label: "Holding", render: (r) => tickerLink(r.ticker) },
    { key: "quantity", label: "Shares", numeric: true, render: (r) => r.quantity.toLocaleString("en-IN") },
    { key: "value_cr", label: "Value", numeric: true, render: (r) => cr(r.value_cr, 2) },
    { key: "weight_now_pct", label: "Now → target", numeric: true, render: (r) => `${fixed(r.weight_now_pct, 2, "%")} → ${fixed(r.target_pct, 2, "%")}` },
    { key: "days_to_trade", label: "Days", numeric: true, render: (r) => fixed(r.days_to_trade, 1) },
    { key: "reason", label: "Why" },
  ];
  const after = o.breaches_after || [];
  return panel(
    "Orders to restore the targets",
    `Whole shares at today's prices. Drift under ${o.band_pct ?? 0.25} percentage points is left alone; a position over a cap, a name leaving or joining the targets, and the cash those trades free or need are always traded. Nothing is sent anywhere: download the list for the desk.`,
    rows.length
      ? el(
          "p",
          { class: "review-actions" },
          el("button", { type: "button", class: "button-primary", onclick: () => download(book, asOf) }, `Download ${rows.length} orders (CSV)`),
          el(
            "span",
            { class: "evidence-meta" },
            `${cr(o.sell_cr, 2)} sold, ${cr(o.buy_cr, 2)} bought · turnover ${fixed(o.turnover_pct, 2, "%")} of NAV · ${cr(o.cash_after_cr, 2)} cash after · ` +
              (after.length ? `${after.length} breach(es) remain` : "every limit met after"),
          ),
        )
      : el("p", { class: "company-empty" }, "The book is on target: nothing to trade."),
    (o.capped || []).length
      ? el(
          "div",
          {},
          el("h4", { class: "portfolio-sub" }, "Targets cut to fit a limit"),
          dataTable(
            o.capped,
            [
              { key: "ticker", label: "Holding", render: (r) => tickerLink(r.ticker) },
              { key: "requested_pct", label: "Asked", numeric: true, render: (r) => fixed(r.requested_pct, 2, "%") },
              { key: "target_pct", label: "Allowed", numeric: true, render: (r) => fixed(r.target_pct, 2, "%") },
              { key: "because", label: "Because" },
            ],
            { empty: "" },
          ),
          o.to_cash_pct ? el("p", { class: "evidence-meta" }, `${fixed(o.to_cash_pct, 2, "%")} of NAV could go nowhere within the limits and stays in cash.`) : null,
        )
      : null,
    main.length ? dataTable(main, columns, { empty: "" }) : null,
    settle.length
      ? disclosure(
          `${settle.length} smaller orders that settle the cash (${cr(settle.reduce((a, r) => a + r.value_cr, 0), 2)})`,
          dataTable(settle, columns, { empty: "" }),
        )
      : null,
    after.length
      ? el("ul", { class: "portfolio-breaches" }, after.map((b) => el("li", {}, `Still after the orders: ${b.message}`)))
      : null,
  );
}

function positionsPanel(book, labels, route) {
  return panel(
    "Positions",
    "Every position at today's price. Days to exit at 20% of daily value traded; share owned against market value.",
    dataTable(
      book.positions || [],
      [
        { key: "ticker", label: "Holding", render: (r) => [tickerLink(r.ticker), r.in_watchlist === false ? el("span", { class: "evidence-meta" }, " not on the watchlist") : null] },
        { key: "sector", label: "Sector", render: (r) => label(r.sector, labels) },
        { key: "weight_pct", label: "Weight", numeric: true, render: (r) => fixed(r.weight_pct, 2, "%") },
        { key: "target_pct", label: "Target", numeric: true, render: (r) => fixed(r.target_pct, 2, "%") },
        { key: "value_cr", label: "Value", numeric: true, render: (r) => cr(r.value_cr, 2) },
        { key: "pnl_pct", label: "P&L", numeric: true, render: (r) => pct(r.pnl_pct, 2) },
        { key: "return_pct", label: "Year", numeric: true, render: (r) => pct(r.return_pct) },
        { key: "beta", label: "Beta", numeric: true, render: (r) => fixed(r.beta, 2) },
        { key: "days_to_exit", label: "Days to exit", numeric: true, render: (r) => fixed(r.days_to_exit, 1) },
        { key: "ownership_pct", label: "Owned", numeric: true, render: (r) => fixed(r.ownership_pct, 2, "%") },
      ],
      { view: "portfolio", route, sort: { key: "weight_pct", dir: "desc" }, empty: "No positions." },
    ),
  );
}

export async function render(container, { payload, route }) {
  const params = (route && route.params) || {};
  const labels = payload?.sectors || {};
  const data = await resolve(payload?.briefing, "portfolio");
  const book = pickBook(data, params.book);
  if (!book) {
    mount(
      container,
      el("header", { class: "view-head" }, el("h2", { class: "view-title" }, "Portfolio")),
      emptyState(
        "No portfolio was measured on this run.",
        "Books are read from portfolios.json; scripts/model_portfolio.py writes a model one.",
      ),
    );
    return;
  }
  if (book.error) {
    mount(container, header(book, data, params), emptyState(`${book.name || book.id} could not be measured.`, book.error));
    return;
  }
  mount(
    container,
    header(book, data, params),
    summaryTiles(book),
    limitsPanel(book, labels),
    ordersPanel(book, data.as_of),
    returnsPanel(book, labels),
    riskPanel(book),
    scenariosPanel(book),
    liquidityPanel(book),
    exposurePanel(book, labels),
    positionsPanel(book, labels, route),
  );
}
