import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// The site is served from a repo subpath, not a domain root:
// https://karthik7899.github.io/india-policy-tracker/
// Without `base`, every built asset URL points at the domain root and the page
// loads a blank shell with four 404s — the classic Pages-subpath failure.
const BASE = process.env.VITE_BASE ?? "/india-policy-tracker/";

export default defineConfig({
  base: BASE,
  plugins: [preact()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Readable names in the deployed bundle. This is a small app and a
    // stack trace from a real browser is worth more than a few bytes.
    sourcemap: true,
  },
  server: { port: 5173 },
  test: undefined,
});
