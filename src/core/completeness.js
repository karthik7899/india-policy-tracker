// How complete a holding's data is, field by field.
//
// A run's completeness was one number, in the email, and a holding's was
// nowhere: a card with no ROCE looked the same whether Screener had refused
// the request or the company does not report one. This reads each field the
// analysis uses straight off the holding and sorts it into:
//
//   fresh            fetched this run
//   kept             a source failed this run and an earlier value, under
//                    a week old, stands in (analysis/last_good.py records
//                    these in the holding's _stale_fields)
//   missing          not there; the source named is the one that failed
//   not applicable   not there because there is nothing to report: no P/E
//                    on a loss, no promoter holding without a promoter group
//
// The percentage is fresh and kept over the fields that apply. Pure, so it is
// tested without a DOM.

const sc = (s) => s?.screener || {};
const has = (v) => v !== null && v !== undefined && v !== "" && v !== "N/A";

// [key, label, source, value]
export const FIELDS = [
  ["price", "Price", "Yahoo", (s) => s?.price],
  ["market_cap", "Market cap", "Screener", (s) => sc(s).market_cap],
  ["pe_ratio", "P/E", "Screener", (s) => sc(s).pe_ratio],
  ["roce", "ROCE", "Screener", (s) => sc(s).roce],
  ["roe", "ROE", "Screener", (s) => sc(s).roe],
  ["q_sales", "Quarterly sales", "Screener", (s) => sc(s).q_sales],
  // A lender's is its financing margin, kept apart from q_opm (providers/screener.py).
  ["q_opm", "Quarterly margin", "Screener", (s) => sc(s).q_opm ?? sc(s).q_fin_margin],
  ["q_eps", "Quarterly EPS", "Screener", (s) => sc(s).q_eps],
  ["revenue_ttm_growth_pct", "Revenue growth", "computed from Screener", (s) => sc(s).revenue_ttm_growth_pct],
  ["promoter_pct", "Promoter holding", "Screener", (s) => sc(s).promoter_pct],
  ["advt_cr", "Turnover", "Yahoo", (s) => sc(s).advt_cr],
  ["deliv_pct", "Delivery %", "NSE", (s) => sc(s).deliv_pct],
  ["week52_low", "52-week range", "Yahoo", (s) => sc(s).week52_low],
];

// The field a row's value can come from instead, and is marked kept under.
const STALE_ALIAS = { q_opm: "q_fin_margin" };

/** Why a missing field has nothing to report, or null when it should exist. */
function notApplicable(key, stock) {
  const s = sc(stock);
  if (key === "pe_ratio" && typeof s.ttm_eps === "number" && s.ttm_eps <= 0) {
    return "a loss over the last four quarters";
  }
  if (key === "promoter_pct" && (has(s.fii_pct) || has(s.dii_pct))) return "no promoter group";
  return null;
}

/**
 * ``{pct, fresh, kept, missing, notApplicable}`` for one holding. ``kept``
 * entries carry the day the value was fetched; the others name the field
 * and where it comes from.
 */
export function completeness(stock) {
  const stale = stock?._stale_fields || {};
  const out = { fresh: [], kept: [], missing: [], notApplicable: [] };
  for (const [key, label, source, value] of FIELDS) {
    const field = { key, label, source };
    if (has(value(stock))) {
      const since = stale[key] || stale[STALE_ALIAS[key]];
      if (since) out.kept.push({ ...field, since });
      else out.fresh.push(field);
      continue;
    }
    const why = notApplicable(key, stock);
    if (why) out.notApplicable.push({ ...field, why });
    else out.missing.push(field);
  }
  const applicable = out.fresh.length + out.kept.length + out.missing.length;
  out.pct = applicable ? Math.round((100 * (out.fresh.length + out.kept.length)) / applicable) : 100;
  return out;
}

/** One line for a tooltip: what is missing, what is kept, what does not apply. */
export function describeCompleteness(c, day = (d) => d) {
  return [
    c.missing.length ? `Missing: ${c.missing.map((f) => `${f.label} (${f.source})`).join(", ")}` : "",
    c.kept.length ? `Kept from an earlier run: ${c.kept.map((f) => `${f.label} (${day(f.since)})`).join(", ")}` : "",
    c.notApplicable.length ? `Not applicable: ${c.notApplicable.map((f) => `${f.label}, ${f.why}`).join("; ")}` : "",
  ]
    .filter(Boolean)
    .join(". ");
}
