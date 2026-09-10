// The app's state, as hooks.
//
// Three things are shared: the route, the payload, and whatever sidecar a view
// has asked for. Before the framework each view fetched and cached these
// itself, which is why the same holding could be current in one view and stale
// in another.

import { useState, useEffect, useRef } from "preact/hooks";
import * as router from "./core/router.js";
import { loadPayload, resolve, resolveTicker, loadCoverage, loadGraph } from "./core/data.js";

/** The current route, re-rendering the tree on every hash change. */
export function useRoute() {
  const [route, setRoute] = useState(router.route());
  useEffect(() => {
    const off = router.onChange(setRoute);
    router.start();
    return off;
  }, []);
  return route;
}

/**
 * The payload: loading / error / data, never collapsed into one another.
 *
 * "Still loading" and "loaded and empty" render identically if you only track
 * the data, and that is the exact confusion this product spends its comments
 * warning about on the Python side.
 */
export function usePayload() {
  const [state, setState] = useState({ status: "loading", data: null, error: null });
  useEffect(() => {
    let live = true;
    loadPayload()
      .then((data) => live && setState({ status: "ready", data, error: null }))
      .catch((error) => live && setState({ status: "error", data: null, error }));
    return () => {
      live = false;
    };
  }, []);
  return state;
}

/**
 * An async value with the same three states.
 *
 * `deps` decides when it refetches. The guard on `live` matters: a reader
 * clicking through holdings faster than the network answers would otherwise
 * see an earlier holding's data land in the current one's drawer.
 */
function useAsync(fn, deps, enabled = true) {
  const [state, setState] = useState({ status: enabled ? "loading" : "idle", value: null });
  const latest = useRef(0);
  useEffect(() => {
    if (!enabled) {
      setState({ status: "idle", value: null });
      return undefined;
    }
    const token = ++latest.current;
    setState({ status: "loading", value: null });
    Promise.resolve(fn())
      .then((value) => {
        if (token === latest.current) setState({ status: "ready", value });
      })
      .catch(() => {
        if (token === latest.current) setState({ status: "error", value: null });
      });
    return undefined;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

/** A whole sidecar key, fetched when the view that needs it mounts. */
export function useSidecar(briefing, key, enabled = true) {
  return useAsync(() => resolve(briefing, key), [briefing, key, enabled], enabled);
}

/** One holding's slice of a per-ticker sidecar. */
export function useTickerSidecar(briefing, key, ticker) {
  return useAsync(
    () => resolveTicker(briefing, key, ticker),
    [briefing, key, ticker],
    Boolean(ticker),
  );
}

/** A holding's news audit. */
export function useCoverage(ticker) {
  return useAsync(() => loadCoverage(ticker), [ticker], Boolean(ticker));
}

/** The curated relationship graph. */
export function useGraph() {
  return useAsync(() => loadGraph(), []);
}
