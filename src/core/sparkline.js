// A small inline price line with dots where news and policy landed.
//
// Inline SVG rather than a chart-library canvas: the Companies view draws
// one per holding, and seventy chart instances would cost more than the
// page they decorate. Returned as markup so it can be tested without a
// DOM; every string placed in it goes through esc().

import { esc } from "./dom.js";

const KINDS = new Set(["activity", "tailwind", "headwind", "mixed"]);

/** Index of the last price point on or before `date` (or the first, if earlier). */
function weekOf(prices, date) {
  let hit = -1;
  for (let i = 0; i < prices.length; i += 1) {
    if (prices[i][0] <= date) hit = i;
    else break;
  }
  return hit;
}

/**
 * @param prices  [[isoDate, close], ...] ascending (weekly closes)
 * @param markers [{date, kind: "activity"|"tailwind"|"headwind"|"mixed", label}]
 * @returns SVG markup, or "" when there are fewer than two prices
 */
export function sparkline(prices, markers = [], { width = 280, height = 52, pad = 4 } = {}) {
  const pts = (prices || []).filter((p) => Array.isArray(p) && Number.isFinite(p[1]));
  if (pts.length < 2) return "";
  const values = pts.map((p) => p[1]);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const x = (i) => pad + (i * (width - 2 * pad)) / (pts.length - 1);
  const y = (v) => pad + (height - 2 * pad) * (1 - (v - lo) / span);
  const line = pts.map((p, i) => `${x(i).toFixed(1)},${y(p[1]).toFixed(1)}`).join(" ");

  // One dot per week and kind: several headlines in a week share a dot and
  // its tooltip lists them, so a busy week does not paint a smear.
  const byWeek = new Map();
  for (const m of markers || []) {
    if (!m || !KINDS.has(m.kind) || !m.date || m.date < pts[0][0]) continue;
    const i = weekOf(pts, m.date);
    if (i < 0) continue;
    const key = `${i}:${m.kind}`;
    if (!byWeek.has(key)) byWeek.set(key, { i, kind: m.kind, labels: [] });
    byWeek.get(key).labels.push(`${m.date} · ${m.label || ""}`);
  }
  const offset = { activity: 0, tailwind: -7, headwind: 7, mixed: 7 };
  const dots = [...byWeek.values()]
    .map(
      (d) =>
        `<circle class="spark-dot spark-${d.kind}" cx="${x(d.i).toFixed(1)}" ` +
        `cy="${Math.min(height - 3, Math.max(3, y(pts[d.i][1]) + offset[d.kind])).toFixed(1)}" r="3.2">` +
        `<title>${esc(d.labels.join("\n"))}</title></circle>`,
    )
    .join("");

  const first = pts[0][1];
  const last = pts[pts.length - 1][1];
  const change = ((last - first) / first) * 100;
  const label = `Weekly closes ${pts[0][0]} to ${pts[pts.length - 1][0]}, ${change >= 0 ? "+" : ""}${change.toFixed(1)}%`;
  return (
    `<svg class="spark" viewBox="0 0 ${width} ${height}" width="100%" height="${height}" ` +
    `preserveAspectRatio="none" role="img" aria-label="${esc(label)}">` +
    `<polyline class="spark-line" fill="none" points="${line}"/>${dots}</svg>`
  );
}

/** Percentage change over the series, or null. */
export function seriesChange(prices) {
  const pts = (prices || []).filter((p) => Array.isArray(p) && Number.isFinite(p[1]));
  if (pts.length < 2 || !pts[0][1]) return null;
  return ((pts[pts.length - 1][1] - pts[0][1]) / pts[0][1]) * 100;
}
