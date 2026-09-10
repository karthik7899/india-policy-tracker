// Shared presentation components.
//
// JSX escapes interpolated values by construction, so the hand-rolled `esc`
// the previous version needed is gone. That matters here specifically: this
// dashboard renders scraped Screener values, and the old app.js interpolated
// them straight into innerHTML until it had to be patched for XSS after the
// fact. The framework removes the category of bug rather than the instance.

import { href } from "../core/router.js";
import { num } from "../core/format.js";

export function Panel({ title, note, children }) {
  return (
    <section class="panel">
      {title && <h3 class="section-title">{title}</h3>}
      {note && <p class="section-note">{note}</p>}
      {children}
    </section>
  );
}

export function EmptyState({ message, detail }) {
  return (
    <div class="empty-state">
      <p class="empty-state-msg">{message}</p>
      {detail && <p class="empty-state-detail">{detail}</p>}
    </div>
  );
}

/** Loading and empty are different states and must not render the same. */
export function Async({ state, empty, children }) {
  if (state.status === "loading") return <p class="loading">Loading…</p>;
  if (state.status === "error") return <EmptyState message="Could not load this." />;
  if (state.status === "idle") return null;
  const value = state.value;
  const isEmpty = value === null || value === undefined || (Array.isArray(value) && !value.length);
  if (isEmpty) return <EmptyState message={empty || "Nothing to show."} />;
  return children(value);
}

export function StatTile({ label, value, detail, tone }) {
  return (
    <div class={`stat-tile${tone ? ` tone-${tone}` : ""}`}>
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}</div>
      {detail && <div class="stat-detail">{detail}</div>}
    </div>
  );
}

/**
 * A ticker as a link that focuses it.
 *
 * The cross-view thread: the same component in every table, carrying focus
 * into whichever view the reader chooses. Previously a ticker was inert text
 * in six tables and following one meant a manual search.
 */
export function TickerLink({ ticker, view = "holdings" }) {
  if (!ticker) return <>—</>;
  return (
    <a class="ticker-link" href={href(view, { focus: ticker })}>
      {String(ticker).toUpperCase()}
    </a>
  );
}

/** Icon + label. Status colour never carries meaning on its own. */
export function StatusPill({ status, role }) {
  const mark = { Broken: "✕", Weakening: "!", Intact: "✓" }[status] || "?";
  return (
    <span class={`pill pill-${role}`}>
      <span class="pill-mark" aria-hidden="true">
        {mark}
      </span>
      {status || "Unknown"}
    </span>
  );
}

/**
 * The table every list view is built from.
 *
 * Sorting puts unreadable values LAST rather than treating them as zero — a
 * holding whose figure could not be read is not the worst performer.
 */
export function DataTable({ rows, columns, focus, tickerKey = "ticker", empty, sort }) {
  if (!Array.isArray(rows) || !rows.length) return <EmptyState message={empty || "Nothing to show."} />;

  let ordered = rows;
  if (sort) {
    const { key, dir = "desc" } = sort;
    ordered = [...rows].sort((a, b) => {
      const av = num(a[key]);
      const bv = num(b[key]);
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      return dir === "desc" ? bv - av : av - bv;
    });
  }

  return (
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col" class={c.numeric ? "num" : ""}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ordered.map((row, i) => {
            const ticker = row[tickerKey];
            const isFocus = focus && ticker && String(ticker).toUpperCase() === focus;
            return (
              <tr key={ticker || i} class={isFocus ? "row-focus" : ""}>
                {columns.map((c) => (
                  <td key={c.key} class={c.numeric ? "num" : ""}>
                    {c.render ? c.render(row) : (row[c.key] ?? "—")}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
