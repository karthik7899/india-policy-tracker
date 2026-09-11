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
import * as holdings from "./views/holdings.js";
import * as valuation from "./views/valuation.js";
import * as risk from "./views/risk.js";
import * as flow from "./views/flow.js";
import * as network from "./views/network.js";
import * as system from "./views/system.js";

const VIEWS = {
  overview: { label: "Overview", module: overview },
  holdings: { label: "Holdings", module: holdings },
  valuation: { label: "Valuation", module: valuation },
  risk: { label: "Risk", module: risk },
  flow: { label: "Flow", module: flow },
  network: { label: "Network", module: network },
  system: { label: "Run health", module: system },
};

let payload = null;

function nav(active) {
  return el(
    "nav",
    { class: "main-nav", role: "tablist" },
    Object.entries(VIEWS).map(([key, { label }]) =>
      el(
        "a",
        {
          class: `nav-item${key === active ? " nav-active" : ""}`,
          href: router.href(key),
          role: "tab",
          "aria-selected": key === active ? "true" : "false",
        },
        label,
      ),
    ),
  );
}

async function renderRoute(route) {
  const navHost = document.getElementById("nav");
  const viewHost = document.getElementById("view");
  const entry = VIEWS[route.view] || VIEWS.overview;

  mount(navHost, nav(VIEWS[route.view] ? route.view : "overview"));

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
  router.onChange(renderRoute);
  router.start();
}

start();
