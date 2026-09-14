// Chart builders. One function per JOB, named for the job.
//
// The old dashboard had exactly one chart across sixteen tabs; everything else
// was a table. These exist because the data's job is comparison and a table
// makes the reader do the comparing.
//
// Form is chosen by what the reader has to do, per the dataviz form heuristic:
//
//   magnitude, low->high        -> bar, SEQUENTIAL (one hue)
//   above/below a baseline      -> diverging bar
//   an ordered state            -> stacked bar in STATUS colours
//   an ordered band scale       -> bar on a one-hue ORDINAL ramp
//   two measures, one series    -> scatter
//
// Rules that hold in every one of them:
//   * Never a dual axis. Two measures of different scale get two charts or a
//     scatter — never two y-scales, which is the single most misread form.
//   * Text wears text tokens, never the series colour.
//   * Grid and axes recede; the data is the only thing with weight.
//   * A hover layer is default, not an extra.

// `ordinal` is deliberately not imported: no chart here draws an ordered band
// scale today. palette.js keeps it exported and validated for when one does —
// the wrong move would be to reach for it again on nominal categories.
import { tokens, categorical, diverging, statusColour } from "./palette.js";

const registry = new Map();

/** Chart.js is a CDN global. Absent, callers fall back to their table view. */
export function available() {
  return typeof window !== "undefined" && typeof window.Chart !== "undefined";
}

function destroy(canvas) {
  const existing = registry.get(canvas);
  if (existing) {
    existing.destroy();
    registry.delete(canvas);
  }
}

function baseOptions(
  t,
  { horizontal = false, valueSuffix = "", axisLabel = "", meta = null } = {},
) {
  // The VALUE axis is x when the bars run horizontally, y when they run up.
  // Naming it matters: a bare 0-45 scale does not say 45 of what, and the unit
  // was previously reachable only by hovering — which makes the tooltip the
  // only way to read the units, and a tooltip must enhance rather than gate.
  const valueAxis = horizontal ? "x" : "y";
  const title = axisLabel
    ? { display: true, text: axisLabel, color: t.muted, font: { size: 11 } }
    : { display: false };
  return {
    indexAxis: horizontal ? "y" : "x",
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 220 },
    plugins: {
      // One series needs no legend box — the title names it. A legend for a
      // single series is chrome pretending to be information.
      legend: { display: false },
      tooltip: {
        backgroundColor: t.surface,
        titleColor: t.ink,
        bodyColor: t.inkSecondary,
        borderColor: t.axis,
        borderWidth: 1,
        padding: 10,
        displayColors: true,
        callbacks: {
          label: (ctx) => {
            const v = ctx.parsed[horizontal ? "x" : "y"];
            const head =
              v === null || v === undefined ? "no data" : `${v}${valueSuffix}`;
            // An extra line per bar for what the value stands on — a median
            // over one holding and a median over five are not the same claim,
            // and the bar cannot show the difference.
            const extra = meta?.[ctx.dataIndex];
            return extra ? [head, extra] : head;
          },
        },
      },
    },
    scales: {
      x: {
        grid: {
          display: horizontal,
          color: t.grid,
          drawBorder: false,
          lineWidth: 1,
        },
        ticks: { color: t.muted, font: { size: 11 } },
        border: { color: t.axis },
        title: valueAxis === "x" ? title : { display: false },
      },
      y: {
        grid: {
          display: !horizontal,
          color: t.grid,
          drawBorder: false,
          lineWidth: 1,
        },
        ticks: { color: t.muted, font: { size: 11 } },
        border: { color: t.axis },
        title: valueAxis === "y" ? title : { display: false },
      },
    },
  };
}

/**
 * Magnitude, low to high. ONE hue for every bar.
 *
 * It used to tint each bar darker-where-bigger off the ordinal ramp, which is
 * a named anti-pattern on nominal categories: sectors have no inherent order,
 * so a value-ramp double-encodes bar length as hue and burns the only free
 * channel on information the chart already shows. Rendered, it was worse than
 * redundant — fifteen of sixteen sector bars landed on the same step, so the
 * ramp looked meaningful and carried nothing.
 *
 * The ordinal ramp is still right for a genuinely ordered band scale
 * (liquidity tiers, age buckets). This is not one.
 *
 * Horizontal by default: sector and company names are long, and rotated
 * x-labels are a legibility tax paid to keep a chart vertical for no reason.
 */
export function rankedBar(
  canvas,
  { labels, values, suffix = "", horizontal = true, axisLabel = "", meta = null },
) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();

  const chart = new window.Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: categorical(0),
          // 4px rounded data-ends, anchored to the baseline: the rounding goes
          // on the value end only, so the bar still starts flat at zero.
          borderRadius: { topLeft: 0, bottomLeft: 0, topRight: 4, bottomRight: 4 },
          borderSkipped: "start",
          // A 2px surface gap keeps adjacent fills from reading as one mass.
          borderColor: t.surface,
          borderWidth: 2,
          barPercentage: 0.8,
        },
      ],
    },
    options: baseOptions(t, { horizontal, valueSuffix: suffix, axisLabel, meta }),
  });
  registry.set(canvas, chart);
  return chart;
}

/**
 * Above or below a baseline. Diverging: blue above, red below, gray at zero.
 *
 * Used where the sign is the story — a sector trading above or below its peer
 * median, a target cut or raised. A sequential ramp here would hide the sign.
 */
export function divergingBar(
  canvas,
  { labels, values, baseline = 0, suffix = "", axisLabel = "" },
) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();
  const chart = new window.Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: values.map((v) => diverging(v, baseline)),
          borderRadius: 4,
          borderColor: t.surface,
          borderWidth: 2,
          barPercentage: 0.8,
        },
      ],
    },
    options: {
      ...baseOptions(t, { horizontal: true, valueSuffix: suffix, axisLabel }),
    },
  });
  registry.set(canvas, chart);
  return chart;
}

/**
 * An ordered state across a population — thesis health, delivery bands.
 *
 * Part-to-whole, so a single stacked horizontal bar. Status colours, which are
 * reserved and never reused as series hues, and every segment is legended by
 * NAME: on the light surface warning and serious are sub-3:1 by design, and
 * colour is never allowed to carry the meaning alone.
 */
export function statusBand(canvas, { segments }) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();
  const chart = new window.Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: [""],
      datasets: segments.map((seg) => ({
        label: `${seg.label} (${seg.value})`,
        data: [seg.value],
        backgroundColor: statusColour(seg.status),
        borderColor: t.surface,
        borderWidth: 2,
        borderRadius: 3,
      })),
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 220 },
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { color: t.inkSecondary, boxWidth: 10, font: { size: 11 } },
        },
        tooltip: { enabled: true },
      },
      scales: {
        x: { stacked: true, display: false },
        y: { stacked: true, display: false },
      },
    },
  });
  registry.set(canvas, chart);
  return chart;
}

/**
 * Two measures per item, one series — delivery against turnover.
 *
 * A scatter, NOT a two-axis bar. The whole question is whether a name that
 * looks liquid on turnover actually settles, and that is a relationship
 * between two numbers, which is what a scatter is for. One series, so the
 * all-pairs colour cap is not in play.
 */
export function scatter(canvas, { series, xLabel, yLabel }) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();
  const groups = (series || []).filter((s) => s.points.length);
  const chart = new window.Chart(canvas.getContext("2d"), {
    type: "scatter",
    data: {
      // One dataset per band rather than one dataset with per-point colours.
      // The colours mean something, so they need a key on screen — and a
      // legend Chart.js derives from real datasets is one the reader can also
      // click to isolate a band.
      datasets: groups.map((group) => ({
        label: group.label,
        data: group.points,
        backgroundColor: statusColour(group.status),
        // >=8px markers, with a 2px surface ring so overlapping points stay
        // countable instead of merging into a blob.
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBorderWidth: 2,
        pointBorderColor: t.surface,
        // The hit target is bigger than the mark. A 10px dot is a pinpoint
        // nobody lands on; this gives each point a ~24px catch radius, which
        // is the difference between a chart that answers on hover and one
        // that looks broken.
        hitRadius: 12,
        hoverBorderWidth: 2,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 220 },
      // Nearest-point in both axes, so the pointer only has to be closest
      // rather than dead-centre on a dot.
      interaction: { mode: "nearest", intersect: false },
      plugins: {
        legend: {
          display: groups.length > 1,
          position: "bottom",
          labels: {
            color: t.inkSecondary,
            boxWidth: 8,
            usePointStyle: true,
            pointStyle: "circle",
            font: { size: 11 },
          },
        },
        tooltip: {
          backgroundColor: t.surface,
          titleColor: t.ink,
          bodyColor: t.inkSecondary,
          borderColor: t.axis,
          borderWidth: 1,
          padding: 10,
          callbacks: {
            // The value leads and the label follows: the reader already knows
            // which dot they are pointing at and wants the numbers.
            title: (items) => items[0]?.raw?.label ?? "",
            label: (ctx) => {
              const p = ctx.raw;
              const lines = [`${p.x} ${xLabel}`, `${p.y} ${yLabel}`];
              // The band is the reading of the two numbers. The legend already
              // names it; repeating it here means a reader who is hovering does
              // not have to look away to the key.
              if (p.band) lines.push(`band: ${p.band}`);
              return lines;
            },
          },
        },
      },
      scales: {
        x: {
          title: { display: true, text: xLabel, color: t.muted, font: { size: 11 } },
          grid: { color: t.grid, drawBorder: false },
          ticks: { color: t.muted, font: { size: 11 } },
        },
        y: {
          title: { display: true, text: yLabel, color: t.muted, font: { size: 11 } },
          grid: { color: t.grid, drawBorder: false },
          ticks: { color: t.muted, font: { size: 11 } },
        },
      },
    },
  });
  registry.set(canvas, chart);
  return chart;
}

/**
 * The same ordered state, broken out across groups — thesis health per sector.
 *
 * The single statusBand answers "how much of the book is broken". It cannot
 * answer "where", and a portfolio with nine broken theses in one sector is a
 * different situation from nine spread evenly. Same reserved status colours,
 * same rule that every segment is named in the legend.
 *
 * Stacked to 100% would make a one-holding sector look as weighty as a
 * fifteen-holding one, so these are absolute counts and the bar lengths are
 * comparable across rows.
 */
export function statusByGroup(canvas, { groups, statuses }) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();
  const chart = new window.Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels: groups.map((g) => g.label),
      datasets: statuses.map((s) => ({
        label: s.label,
        data: groups.map((g) => g.counts[s.key] || 0),
        backgroundColor: statusColour(s.status),
        borderColor: t.surface,
        borderWidth: 2,
        borderRadius: 3,
        barPercentage: 0.82,
      })),
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 220 },
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { color: t.inkSecondary, boxWidth: 10, font: { size: 11 } },
        },
        tooltip: {
          backgroundColor: t.surface,
          titleColor: t.ink,
          bodyColor: t.inkSecondary,
          borderColor: t.axis,
          borderWidth: 1,
          padding: 10,
          // Every series at this row, so the pointer never has to find a
          // particular segment to read the split.
          mode: "index",
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.x}`,
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          grid: { color: t.grid, drawBorder: false },
          ticks: { color: t.muted, font: { size: 11 }, precision: 0 },
          border: { color: t.axis },
        },
        y: {
          stacked: true,
          grid: { display: false },
          ticks: { color: t.muted, font: { size: 11 } },
          border: { color: t.axis },
        },
      },
    },
  });
  registry.set(canvas, chart);
  return chart;
}

/** Tear down every chart before a view is replaced, so canvases are reusable. */
export function destroyAll() {
  for (const chart of registry.values()) chart.destroy();
  registry.clear();
}
