// The trail above every view, built from the route and nothing else.
//
// Where the reader is (a view, the sector it is filtered to, the company it
// is focused on) already lives in the URL; the filter bar and every view
// read it from there. The trail is drawn from the same route by main.js on
// every navigation, so it cannot hold a state of its own that drifts from
// the page. It used to exist only on the company page, built by hand.
//
// Pure: a route and the labels in, a list of steps out.

import { href } from "./router.js";

function sectorLabel(sector, labels) {
  return labels?.[sector]?.label || String(sector || "").replace(/_/g, " ");
}

function sectorOf(watchlist, ticker) {
  const key = String(ticker || "").toUpperCase();
  for (const [sector, stocks] of Object.entries(watchlist || {})) {
    if (sector === "macro_indicators" || !Array.isArray(stocks)) continue;
    if (stocks.some((s) => String(s?.ticker || "").toUpperCase() === key)) return sector;
  }
  return null;
}

/**
 * The steps to show for a route: `[{text, href}]`, the last one the page
 * itself (no href). Empty for a view at its top level, which needs no trail.
 *
 *   #/company?focus=HAL           Companies › Aerospace & Defence › HAL
 *   #/companies?sector=x          Companies › X
 *   #/holdings?sector=x&focus=HAL Holdings › X › HAL
 */
export function crumbsFor(route, { views = {}, watchlist = {}, labels = {} } = {}) {
  const params = route?.params || {};
  const focus = route?.focus || null;
  if (route?.view === "company") {
    if (!focus) return [];
    const sector = sectorOf(watchlist, focus);
    return [
      { text: views.companies?.label || "Companies", href: href("companies") },
      ...(sector ? [{ text: sectorLabel(sector, labels), href: href("companies", { sector }) }] : []),
      { text: focus },
    ];
  }
  const view = views[route?.view] ? route.view : "overview";
  const sector = params.sector || "";
  if (!sector && !focus) return [];
  const trail = [{ text: views[view]?.label || view, href: href(view) }];
  if (sector) trail.push({ text: sectorLabel(sector, labels), ...(focus ? { href: href(view, { sector }) } : {}) });
  if (focus) trail.push({ text: focus });
  return trail;
}
