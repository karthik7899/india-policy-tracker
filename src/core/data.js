// Loading the payload and its sidecars.
//
// dashboard_data.json carries what the first screen needs. The two heaviest
// keys were split out (dashboard/sidecars.py) and arrive here as manifests
// rather than data:
//
//     stock_topics      -> { sidecar: "data/stock_topics", tickers: [...] }
//     buffett_valuation -> { sidecar: "data/buffett_valuation.json", count: n }
//
// So a key can be in one of three states, and they are NOT the same thing:
//
//     absent      the pipeline step never ran
//     []  or {}   it ran and found nothing
//     a manifest  the data exists, in a file, fetch it when needed
//
// payload.py is deliberate about the first two (see its comments on
// coverage_count and sector_blocks); collapsing them here would throw away a
// distinction the write side went to trouble to preserve.

const PAYLOAD_URL = "dashboard_data.json";

let payloadPromise = null;
const sidecarCache = new Map();

/** The main payload. Fetched once per page load, shared by every view. */
export function loadPayload() {
  if (!payloadPromise) {
    payloadPromise = fetch(PAYLOAD_URL, { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error(`${PAYLOAD_URL}: HTTP ${r.status}`);
        return r.json();
      })
      .catch((err) => {
        // Reset so a retry is possible; a failed load must not poison the
        // cache for the rest of the session.
        payloadPromise = null;
        throw err;
      });
  }
  return payloadPromise;
}

/** True when a value is a sidecar manifest rather than the data itself. */
export function isManifest(value) {
  return Boolean(value && typeof value === "object" && typeof value.sidecar === "string");
}

/**
 * Resolve a key to its data, fetching the sidecar if that is where it lives.
 *
 * Returns null for a key that is absent, and the empty value for a key that is
 * present but empty — preserving the distinction described above.
 */
export async function resolve(briefing, key) {
  if (!briefing || !(key in briefing)) return null;
  const value = briefing[key];
  if (!isManifest(value)) return value;
  if (value.sidecar.endsWith(".json")) {
    const body = await fetchJSON(value.sidecar);
    return body ? body.value : null;
  }
  return value; // per-ticker manifest: use resolveTicker for a single holding
}

/**
 * One holding's slice of a per-ticker sidecar.
 *
 * The manifest lists which tickers have a file, so a holding with no sidecar
 * costs nothing — without that list every miss would be a 404 to discover.
 */
export async function resolveTicker(briefing, key, ticker) {
  const manifest = briefing?.[key];
  if (!isManifest(manifest) || !Array.isArray(manifest.tickers)) return null;
  const safe = String(ticker || "").toUpperCase();
  if (!manifest.tickers.includes(safe)) return null;
  const body = await fetchJSON(`${manifest.sidecar}/${safe}.json`);
  return body ? body.value : null;
}

/** A per-holding news audit, written by history/store.write_coverage_sidecars. */
export async function loadCoverage(ticker) {
  const safe = String(ticker || "").toUpperCase();
  const body = await fetchJSON(`news/${safe}.json`);
  return body ? body.items : null;
}

/** The curated relationship graph. Its own file — it changes rarely. */
export async function loadGraph() {
  const body = await fetchJSON("entity_graph.json");
  return body && Array.isArray(body.edges) ? body.edges : [];
}

/**
 * Fetch and cache one JSON file.
 *
 * A missing sidecar resolves to null rather than throwing: the data being
 * unavailable is a normal state the views render as "not available", and one
 * absent drawer must not take the page down.
 */
async function fetchJSON(path) {
  if (sidecarCache.has(path)) return sidecarCache.get(path);
  const promise = fetch(path, { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : null))
    .catch(() => null);
  sidecarCache.set(path, promise);
  return promise;
}

/** Test seam: drop the caches so a fixture can be loaded fresh. */
export function _resetCaches() {
  payloadPromise = null;
  sidecarCache.clear();
}
