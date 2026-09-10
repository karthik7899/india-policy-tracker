// Small DOM helpers. Everything the views build goes through `el` or `esc`,
// so escaping is structural rather than remembered.
//
// The old app.js interpolated scraped Screener values straight into innerHTML
// and had to be patched for XSS after the fact (PR #138). Building nodes and
// setting `textContent` makes that class of bug impossible rather than fixed.

/** Escape a value for safe interpolation into an HTML string. */
export function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Create an element.
 *
 * Children that are strings become TEXT nodes, never markup — that is the
 * whole point. Pass `{ html }` in props to opt into raw HTML, which makes
 * every such site greppable.
 */
export function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "html") {
      node.innerHTML = value;
    } else if (key === "class") {
      node.className = value;
    } else if (key === "dataset") {
      Object.assign(node.dataset, value);
    } else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else {
      node.setAttribute(key, value);
    }
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

/** Replace a container's contents in one operation. */
export function mount(container, ...nodes) {
  if (!container) return;
  container.replaceChildren(...nodes.flat(Infinity).filter(Boolean));
}

/** A labelled empty state. Silence and "no data" look identical otherwise. */
export function emptyState(message, detail) {
  return el(
    "div",
    { class: "empty-state" },
    el("p", { class: "empty-state-msg" }, message),
    detail ? el("p", { class: "empty-state-detail" }, detail) : null,
  );
}
