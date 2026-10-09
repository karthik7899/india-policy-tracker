// The header search box: type a company or sector, arrive at it.
//
// A combobox in the ARIA sense: arrow keys move through the matches, Enter
// opens one (the first if none is chosen), Escape closes the list. "/"
// anywhere outside a text field puts the cursor in it.

import { el, mount } from "../core/dom.js";
import { buildIndex, search } from "../core/search.js";

function typingIn(target) {
  const tag = (target?.tagName || "").toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || target?.isContentEditable;
}

export function mountSearch(host, payload) {
  if (!host) return;
  const index = buildIndex(payload);
  const listId = "app-search-results";
  const input = el("input", {
    type: "search",
    class: "app-search-input",
    placeholder: "Search a company or sector",
    "aria-label": "Search a company or sector",
    role: "combobox",
    "aria-expanded": "false",
    "aria-controls": listId,
    "aria-autocomplete": "list",
    autocomplete: "off",
    spellcheck: "false",
  });
  const list = el("ul", { id: listId, class: "app-search-results", role: "listbox" });
  list.hidden = true;
  let results = [];
  let active = -1;

  function close() {
    list.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
  }

  function open(entry) {
    if (!entry) return;
    input.value = "";
    close();
    input.blur();
    window.location.hash = entry.href;
  }

  function draw() {
    if (!input.value.trim()) {
      close();
      return;
    }
    mount(
      list,
      results.length
        ? results.map((r, i) =>
            el(
              "li",
              {
                id: `${listId}-${i}`,
                role: "option",
                class: `app-search-option${i === active ? " is-active" : ""}`,
                "aria-selected": i === active ? "true" : "false",
                // mousedown, not click: click fires after the input's blur,
                // which has already closed the list.
                onmousedown: (e) => {
                  e.preventDefault();
                  open(r);
                },
              },
              el("span", { class: "app-search-title" }, r.title),
              el("span", { class: "app-search-hint" }, r.hint),
            ),
          )
        : el("li", { class: "app-search-empty", role: "option", "aria-disabled": "true" }, "No company or sector matches."),
    );
    list.hidden = false;
    input.setAttribute("aria-expanded", "true");
    if (active >= 0) input.setAttribute("aria-activedescendant", `${listId}-${active}`);
    else input.removeAttribute("aria-activedescendant");
  }

  input.addEventListener("input", () => {
    results = search(index, input.value);
    active = results.length ? 0 : -1;
    draw();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" && results.length) {
      e.preventDefault();
      active = (active + 1) % results.length;
      draw();
    } else if (e.key === "ArrowUp" && results.length) {
      e.preventDefault();
      active = (active - 1 + results.length) % results.length;
      draw();
    } else if (e.key === "Enter") {
      e.preventDefault();
      open(results[active >= 0 ? active : 0]);
    } else if (e.key === "Escape") {
      input.value = "";
      close();
      input.blur();
    }
  });
  input.addEventListener("blur", close);
  input.addEventListener("focus", () => {
    if (input.value.trim()) draw();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && !e.metaKey && !e.ctrlKey && !typingIn(e.target)) {
      e.preventDefault();
      input.focus();
    }
  });

  mount(host, el("div", { class: "app-search" }, input, list));
}
