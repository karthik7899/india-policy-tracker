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

// Chart.js is a pinned dependency, not a CDN global — the build step's most
// concrete benefit. A blocked CDN used to strip every chart from the page with
// nothing but a console error to say so.
//
// Only the pieces each form needs are registered. The auto-registering entry
// point pulls in every controller, scale and plugin Chart.js ships; this app
// draws bars and scatters, and the rest is dead weight in the bundle.
import {
  Chart as ChartJS,
  BarController,
  BarElement,
  ScatterController,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
  Title,
} from "chart.js";

import { tokens, ordinal, diverging, statusColour } from "./palette.js";

ChartJS.register(
  BarController,
  BarElement,
  ScatterController,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
  Title,
);

const registry = new Map();

/** Kept for callers that still branch on it; with a bundled Chart.js it is
 * always true, and the table under every chart is the real fallback. */
export function available() {
  return true;
}

function destroy(canvas) {
  const existing = registry.get(canvas);
  if (existing) {
    existing.destroy();
    registry.delete(canvas);
  }
}

function baseOptions(t, { horizontal = false, valueSuffix = "" } = {}) {
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
            return v === null || v === undefined ? "no data" : `${v}${valueSuffix}`;
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
      },
    },
  };
}

/**
 * Magnitude, low to high. Sequential — one hue, more is darker.
 *
 * Horizontal by default: sector and company names are long, and rotated
 * x-labels are a legibility tax paid to keep a chart vertical for no reason.
 */
export function rankedBar(canvas, { labels, values, suffix = "", horizontal = true }) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();
  const max = Math.max(...values.map((v) => Math.abs(Number(v) || 0)), 1);
  const colours = values.map((v) => {
    const share = Math.abs(Number(v) || 0) / max;
    return ordinal(Math.round(share * 3), 4);
  });

  const chart = new ChartJS(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colours,
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
    options: baseOptions(t, { horizontal, valueSuffix: suffix }),
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
export function divergingBar(canvas, { labels, values, baseline = 0, suffix = "" }) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();
  const chart = new ChartJS(canvas.getContext("2d"), {
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
      ...baseOptions(t, { horizontal: true, valueSuffix: suffix }),
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
  const chart = new ChartJS(canvas.getContext("2d"), {
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
export function scatter(canvas, { points, xLabel, yLabel, marker }) {
  if (!available() || !canvas) return null;
  destroy(canvas);
  const t = tokens();
  const chart = new ChartJS(canvas.getContext("2d"), {
    type: "scatter",
    data: {
      datasets: [
        {
          data: points,
          // >=8px markers, with a 2px surface ring so overlapping points stay
          // countable instead of merging into a blob.
          pointRadius: 5,
          pointHoverRadius: 8,
          pointBorderWidth: 2,
          pointBorderColor: t.surface,
          pointBackgroundColor: points.map((p) => marker?.(p) ?? t.muted),
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 220 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: t.surface,
          titleColor: t.ink,
          bodyColor: t.inkSecondary,
          borderColor: t.axis,
          borderWidth: 1,
          callbacks: {
            label: (ctx) => {
              const p = ctx.raw;
              return `${p.label}: ${p.x} ${xLabel}, ${p.y} ${yLabel}`;
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

/** Tear down every chart before a view is replaced, so canvases are reusable. */
export function destroyAll() {
  for (const chart of registry.values()) chart.destroy();
  registry.clear();
}
