// A chart as a component, so its lifecycle is the component's lifecycle.
//
// The previous version destroyed charts by hand from the router, because a
// Chart.js instance left attached to a replaced canvas leaks its context and
// makes the next render of the same id fail silently. Tying create/destroy to
// mount/unmount removes the bookkeeping and the class of bug with it.
//
// Chart.js is imported, not loaded from a CDN. That is a direct benefit of
// having a build step: the version is pinned in the lockfile, the page works
// offline, and a blocked CDN cannot silently strip every chart from the page.

import { useRef, useEffect } from "preact/hooks";
import * as builders from "../charts/charts.js";

/**
 * @param {string} kind    one of the builders in charts.js
 * @param {object} spec    that builder's arguments
 * @param {number} height  CSS height; charts size to their frame
 * @param {string} caption a text description of what the chart shows, always
 *                         rendered — the accessibility floor, and the fallback
 *                         when a chart cannot draw
 */
export function Chart({ kind, spec, height = 260, caption }) {
  const canvas = useRef(null);
  const instance = useRef(null);

  useEffect(() => {
    if (!canvas.current) return undefined;
    const build = builders[kind];
    if (typeof build !== "function") return undefined;
    instance.current = build(canvas.current, spec);
    return () => {
      if (instance.current) {
        instance.current.destroy();
        instance.current = null;
      }
    };
  }, [kind, JSON.stringify(spec)]);

  return (
    <figure class="chart-figure">
      <div class="chart-frame" style={`height:${height}px`}>
        <canvas ref={canvas} role="img" aria-label={caption} />
      </div>
      {caption && <figcaption class="chart-caption">{caption}</figcaption>}
    </figure>
  );
}
