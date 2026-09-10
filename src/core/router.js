// Hash routing, and the entity focus that follows a company between views.
//
// Routes look like #/valuation or #/holdings?focus=HAL. The `focus` parameter
// is the mechanism behind "one click follows a company everywhere": it is part
// of the URL, so it survives a reload, is shareable, and every view reads the
// same value rather than each keeping its own idea of what is selected.
//
// The old dashboard had sixteen tabs that shared no state at all. The same
// company appeared in filings, scoring, valuation and its sector as four
// unrelated rows, and getting from one to the next meant going back to a menu
// and searching again.

const listeners = new Set();
let current = { view: "overview", focus: null, params: {} };

/** Parse "#/view?focus=X&q=Y" into a route. */
export function parse(hash) {
  const raw = String(hash || "").replace(/^#\/?/, "");
  const [path, query] = raw.split("?");
  const params = {};
  new URLSearchParams(query || "").forEach((value, key) => {
    params[key] = value;
  });
  return {
    view: path || "overview",
    focus: params.focus ? String(params.focus).toUpperCase() : null,
    params,
  };
}

/** Build a hash for a route. Views use this rather than assembling strings. */
export function href(view, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== null && v !== undefined && v !== ""),
  ).toString();
  return `#/${view}${query ? `?${query}` : ""}`;
}

/** The route now. */
export function route() {
  return current;
}

/**
 * Navigate. Pushing through the hash rather than calling a view directly keeps
 * the back button working, which a tab bar that swaps `display` never did.
 */
export function go(view, params = {}) {
  window.location.hash = href(view, params);
}

/** Focus an entity without leaving the current view. */
export function focusEntity(ticker) {
  go(current.view, { ...current.params, focus: ticker });
}

export function onChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  current = parse(window.location.hash);
  for (const fn of listeners) fn(current);
}

export function start() {
  window.addEventListener("hashchange", emit);
  emit();
}
