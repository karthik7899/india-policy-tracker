// The calendar and results, for the Calendar view, the Overview and the
// company page. Everything is computed by analysis/event_calendar.py and
// arrives in data/event_calendar.json and data/results.json.

export const KIND_LABEL = {
  results: "Results",
  dividend: "Dividend",
  bonus: "Bonus",
  split: "Split",
  buyback: "Buyback",
  rights: "Rights",
  fund_raising: "Fund raising",
  agm: "AGM",
  egm: "EGM",
  merger: "Merger",
  outcome: "Meeting held",
  board: "Board meeting",
  corporate_action: "Corporate action",
  macro: "Market",
};

export function kindLabel(kind) {
  return KIND_LABEL[kind] || String(kind || "Event").replace(/_/g, " ");
}

function isoDay(date) {
  return date.toISOString().slice(0, 10);
}

/** The Monday of the week an ISO date falls in, as ISO. */
export function weekOf(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  const back = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - back);
  return isoDay(d);
}

/**
 * Events grouped by the week they fall in, earliest first, with the
 * market-wide dates merged in. Each group: {week, events}.
 */
export function byWeek(events, macro = []) {
  const all = [...(events || []), ...(macro || [])]
    .filter((e) => e && e.date)
    .sort((a, b) => a.date.localeCompare(b.date) || String(a.ticker || "").localeCompare(String(b.ticker || "")));
  const groups = [];
  for (const e of all) {
    const week = weekOf(e.date);
    if (!groups.length || groups[groups.length - 1].week !== week) groups.push({ week, events: [] });
    groups[groups.length - 1].events.push(e);
  }
  return groups;
}

/** Events in the `days` from `asOf`, holdings and market dates together. */
export function within(calendar, days, asOf) {
  const start = asOf || calendar?.as_of || isoDay(new Date());
  const end = new Date(`${start}T00:00:00Z`);
  end.setUTCDate(end.getUTCDate() + days);
  const until = isoDay(end);
  return [...(calendar?.upcoming || []), ...(calendar?.macro || [])]
    .filter((e) => e && e.date >= start && e.date <= until)
    .sort((a, b) => a.date.localeCompare(b.date) || String(a.ticker || "").localeCompare(String(b.ticker || "")));
}

/** One holding's events ahead. */
export function eventsFor(calendar, ticker) {
  const key = String(ticker || "").toUpperCase();
  return (calendar?.upcoming || []).filter((e) => String(e.ticker).toUpperCase() === key);
}

/** One holding's latest scorecard, or null. */
export function scorecardFor(results, ticker) {
  const key = String(ticker || "").toUpperCase();
  return (results?.scorecards || []).find((c) => String(c.ticker).toUpperCase() === key) || null;
}
