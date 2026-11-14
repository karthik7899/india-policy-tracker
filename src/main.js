// Bootstrap: load the payload once, route, render.
//
// Seven views replace sixteen tabs. The grouping is by the question a reader
// is asking, not by which scraper produced the data — five of the old tabs
// were the same dated-item list separated only by its source, and four asked
// "what is this worth" in four different places.

import { el, mount, emptyState } from "./core/dom.js";
import { loadPayload } from "./core/data.js";
import * as router from "./core/router.js";
import { destroyAll } from "./charts/charts.js";

import * as overview from "./views/overview.js";
import * as companies from "./views/companies.js";
import * as portfolio from "./views/portfolio.js";
import * as calendar from "./views/calendar.js";
import * as company from "./views/company.js";
import * as review from "./views/review.js";
import * as ask from "./views/ask.js";
import * as holdings from "./views/holdings.js";
import * as valuation from "./views/valuation.js";
import * as risk from "./views/risk.js";
import * as flow from "./views/flow.js";
import * as network from "./views/network.js";
import * as system from "./views/system.js";
import { restoreFocus } from "./views/filterbar.js";
import { mountSearch } from "./views/searchbox.js";
import { crumbsFor } from "./core/crumbs.js";
import { NAV_GROUPS, groupForView } from "./core/navigation.js";

const VIEWS = {
  overview: { label: "Overview", module: overview },
  companies: { label: "Companies", module: companies },
  portfolio: { label: "Portfolio", module: portfolio },
  calendar: { label: "Calendar", module: calendar },
  review: { label: "Review", module: review },
  ask: { label: "Ask", module: ask },
  holdings: { label: "Holdings", module: holdings },
  valuation: { label: "Valuation", module: valuation },
  risk: { label: "Risk", module: risk },
  flow: { label: "Flow", module: flow },
  network: { label: "Network", module: network },
  system: { label: "Run health", module: system },
  // Reached from any ticker or the search box, not the tab bar.
  company: { label: "Company", module: company, hidden: true, under: "companies" },
};

let payload = null;

function nav(active) {
  const selected = VIEWS[active]?.under || active;
  const activeGroup = groupForView(selected);
  return el(
    "nav",
    { class: "workstation-nav", "aria-label": "Research workstation" },
    NAV_GROUPS.map((group) => {
      const isActive = group === activeGroup;
      const items = group.views.map((key) => {
        const view = VIEWS[key];
        return el(
          "a",
          {
            class: "workstation-link" + (key === selected ? " nav-active" : ""),
            href: router.href(key),
            "aria-current": key === selected ? "page" : null,
          },
          view.label,
        );
      });
      return el(
        "details",
        { class: "workstation-group" + (isActive ? " group-active" : ""), name: "workstation", open: isActive },
        el(
          "summary",
          { class: "workstation-group-title" },
          el("span", {}, group.label),
          el("span", { class: "workstation-group-current" }, isActive ? VIEWS[selected]?.label || "" : ""),
          el("span", { class: "workstation-chevron", "aria-hidden": "true" }, "⌄"),
        ),
        el("div", { class: "workstation-group-links" }, items),
      );
    }),
  );
}

/**
 * The trail (src/core/crumbs.js), redrawn from the route on every navigation
 * alongside the tab strip, and hidden when there is nothing to trace.
 */
function renderCrumbs(route) {
  const host = document.getElementById("crumbs");
  if (!host) return;
  const steps = crumbsFor(route, { views: VIEWS, watchlist: payload?.watchlist, labels: payload?.sectors });
  host.hidden = !steps.length;
  mount(
    host,
    steps.length
      ? el(
          "ol",
          { class: "crumbs" },
          steps.map((s) =>
            el("li", {}, s.href ? el("a", { href: s.href }, s.text) : el("span", { "aria-current": "page" }, s.text)),
          ),
        )
      : null,
  );
}

async function renderRoute(route) {
  const navHost = document.getElementById("nav");
  const viewHost = document.getElementById("view");
  const entry = VIEWS[route.view] || VIEWS.overview;

  const known = VIEWS[route.view] ? route.view : "overview";
  mount(navHost, nav(VIEWS[known].under || known));
  renderCrumbs(route);
  if (!VIEWS[known].hidden) document.title = "India Policy Tracker";

  // Charts hold canvas contexts; leaving them attached to a replaced DOM leaks
  // and makes the next render of the same canvas id fail silently.
  destroyAll();

  try {
    await entry.module.render(viewHost, { payload, route });
  } catch (err) {
    mount(viewHost, emptyState("This view failed to render.", String(err && err.message)));
    // Rethrow into the console: swallowing it entirely would make a broken
    // view indistinguishable from an empty one, which is the failure this
    // whole product is careful about everywhere else.
    console.error(err);
  }

  // Search re-renders the view on every keystroke, which destroys the input
  // being typed into. One hook, after the view is in the document, puts the
  // caret back — without it the search box accepts a single character.
  restoreFocus();
}

async function start() {
  const viewHost = document.getElementById("view");
  try {
    payload = await loadPayload();
  } catch (err) {
    mount(
      viewHost,
      emptyState("Could not load dashboard_data.json.", String(err && err.message)),
    );
    return;
  }
  mountSearch(document.getElementById("search"), payload);
  router.onChange(renderRoute);
  router.start();
}

start();
