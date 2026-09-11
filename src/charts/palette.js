// Chart colour tokens, by the job the colour does.
//
// Every set below was run through the dataviz validator rather than chosen by
// eye, and the results are recorded so a future edit knows what it has to
// clear. Re-run before changing any hex:
//
//   node scripts/validate_palette.js "<hex,...>" --mode light|dark [--pairs all] [--ordinal]
//
// CATEGORICAL, slots 1-3, --pairs all:
//   light  CVD dE 9.2 (deutan) · normal-vision 24.0 · PASS
//   dark   CVD dE 9.4 (deutan) · normal-vision 20.9 · PASS
// Capped at three deliberately. The all-pairs gate cannot seat a fourth slot:
// slot 4 puts yellow beside orange, which fails at 13.7 normal-vision (light)
// and 4.8 CVD (dark). A fourth series folds into "Other" or facets instead —
// it never gets a generated hue.
//
// RELIEF RULE: aqua (#1baf7a) sits at 2.74:1 on the light surface, below 3:1.
// The validator returns this as a WARN, and a WARN here is an obligation, not
// a suggestion: anything drawn in aqua carries a visible direct label. Views
// that cannot label directly must show the table view instead.
//
// ORDINAL (liquidity bands), --ordinal, light: monotone L, adjacent dL >= 0.06,
// light end 2.06:1 vs surface · PASS. One hue — an ordinal scale is magnitude,
// not identity, so it must not be rainbow.

const isDark = () =>
  document.documentElement.dataset.theme === "dark" ||
  (document.documentElement.dataset.theme !== "light" &&
    window.matchMedia?.("(prefers-color-scheme: dark)").matches);

const LIGHT = {
  categorical: ["#2a78d6", "#eb6834", "#1baf7a"],
  sequential: ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#104281"],
  // Ordinal starts at step 250: anything lighter fails the 2:1 floor against
  // the light surface and the lightest band would recede into the page.
  ordinal: ["#86b6ef", "#3987e5", "#256abf", "#104281"],
  divergingLow: "#d03b3b",
  divergingMid: "#f0efec",
  divergingHigh: "#2a78d6",
  surface: "#fcfcfb",
  grid: "#e1e0d9",
  axis: "#c3c2b7",
  muted: "#898781",
  ink: "#0b0b0b",
  inkSecondary: "#52514e",
};

const DARK = {
  categorical: ["#3987e5", "#d95926", "#199e70"],
  sequential: ["#104281", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"],
  ordinal: ["#9ec5f4", "#3987e5", "#256abf", "#184f95"],
  divergingLow: "#d03b3b",
  divergingMid: "#383835",
  divergingHigh: "#3987e5",
  surface: "#1a1a19",
  grid: "#2c2c2a",
  axis: "#383835",
  muted: "#898781",
  ink: "#ffffff",
  inkSecondary: "#c3c2b7",
};

// Status is FIXED — never themed, never reused as "series 4". These four are
// deliberately stepped apart from the categorical slots so a status colour
// cannot impersonate a series. They always ship with a label, because on the
// light surface warning and serious are sub-3:1 by design and hue alone is
// not allowed to carry the meaning.
export const STATUS = {
  good: "#0ca30c",
  warning: "#fab219",
  serious: "#ec835a",
  critical: "#d03b3b",
};

export function tokens() {
  return isDark() ? DARK : LIGHT;
}

/**
 * A categorical hue by slot index.
 *
 * Colour follows the ENTITY, never its rank — so callers pass a stable index
 * for the thing being drawn, not its position after a sort. A filter that
 * changes the series count must not repaint the survivors.
 */
export function categorical(index) {
  const set = tokens().categorical;
  return set[index] ?? tokens().muted;
}

/** An ordinal step for a band, low to high. Magnitude, so one hue. */
export function ordinal(index, count) {
  const ramp = tokens().ordinal;
  if (count <= 1) return ramp[ramp.length - 1];
  const pos = Math.round((index / (count - 1)) * (ramp.length - 1));
  return ramp[Math.max(0, Math.min(ramp.length - 1, pos))];
}

/** Diverging: blue above the baseline, red below, neutral gray at zero. */
export function diverging(value, baseline = 0) {
  const t = tokens();
  if (value === null || value === undefined || Number.isNaN(Number(value))) return t.muted;
  if (Number(value) > baseline) return t.divergingHigh;
  if (Number(value) < baseline) return t.divergingLow;
  return t.divergingMid;
}

/** The status step for a thesis/liquidity/delivery state, by name. */
export function statusColour(name) {
  return STATUS[name] ?? tokens().muted;
}
