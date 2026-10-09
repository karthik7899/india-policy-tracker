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
import * as company from "./views/company.js";
import * as review from "./views/review.js";
import * as holdings from "./views/holdings.js";
import * as valuation from "./views/valuation.js";
import * as risk from "./views/risk.js";
import * as flow from "./views/flow.js";
import * as network from "./views/network.js";
import * as system from "./views/system.js";
import { restoreFocus } from "./views/filterbar.js";
import { mountSearch } from "./views/searchbox.js";

const VIEWS = {
  overview: { label: "Overview", module: overview },
  companies: { label: "Companies", module: companies },
  review: { label: "Review", module: review },
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
  const shown = Object.entries(VIEWS).filter(([, v]) => !v.hidden);
  const link = ([key, { label }], cls) =>
    el(
      "a",
      {
        class: `${cls}${key === active ? " nav-active" : ""}`,
        href: router.href(key),
        role: "tab",
        "aria-selected": key === active ? "true" : "false",
      },
      label,
    );
  // Two forms of the same links; CSS shows one. A phone showed four of the
  // eight tabs and gave no sign the strip scrolled, so half the dashboard
  // was out of sight. Below 640px the strip becomes a menu that lists them all.
  return [
    el("nav", { class: "main-nav", role: "tablist" }, shown.map((v) => link(v, "nav-item"))),
    el(
      "details",
      { class: "nav-menu" },
      el(
        "summary",
        { class: "nav-menu-summary" },
        el("span", {}, VIEWS[active]?.label || "Menu"),
        el("span", { class: "nav-menu-hint" }, `${shown.length} views \u25be`),
      ),
      el("nav", { class: "nav-menu-list", role: "tablist" }, shown.map((v) => link(v, "nav-menu-item"))),
    ),
  ];
}

async function renderRoute(route) {
  const navHost = document.getElementById("nav");
  const viewHost = document.getElementById("view");
  const entry = VIEWS[route.view] || VIEWS.overview;

  const known = VIEWS[route.view] ? route.view : "overview";
  mount(navHost, nav(VIEWS[known].under || known));
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
