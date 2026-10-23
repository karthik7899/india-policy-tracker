import { test } from "node:test";
import assert from "node:assert/strict";

import { JSDOM } from "jsdom";
const dom = new JSDOM("");
global.DOMParser = dom.window.DOMParser;
global.document = dom.window.document;
global.Node = dom.window.Node;

// Have to make sure to mock conditionally if not already available in environment
import { el } from "../../src/core/dom.js";

test("el with html property sanitizes harmful elements", () => {
  const node = el("div", { html: "<svg><script>console.log(1)</script><circle onclick='alert(1)'></circle></svg>" });
  assert.equal(node.innerHTML, "<svg><circle></circle></svg>");
});

test("el with html property removes javascript URLs", () => {
  const node = el("div", { html: "<a href='javascript:alert(1)'>x</a><a href=' javascript: alert(2)'>y</a><a href='https://example.com'>z</a>" });
  assert.equal(node.innerHTML, "<a>x</a><a>y</a><a href=\"https://example.com\">z</a>");
});
