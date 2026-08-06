"""The closing sections of the briefing: what changed, what is extreme, what
the run could not see, and where to go next.

These sit after the sector blocks because they answer questions the reader
only has once they have read the day's findings: did the watchlist itself
move, which valuations are at the edges, and how much of this should be
trusted given what the run failed to fetch.

The last of those is the reason this module exists separately. A briefing
that reports only what it found reads identically on a day when everything
worked and a day when half the fetches failed. Suppressions and gaps are
stated here rather than omitted, and nothing in this file invents a value to
fill a hole: a missing number renders as "Not available", and a deliberately
withheld one as "Suppressed" with the reason attached.
"""

import html as html_lib
from typing import Any, Dict, List

# Rows per closing section. These are the last thing in the document, so they
# are the first thing the size ladder should be willing to shed.
MAX_CHANGES = 6
MAX_EXTREMES = 5
MAX_SUPPRESSED = 8

_ACTION_LABEL = {
    "added": ("Added", "#34d399", "#065f46"),
    "rotated_in": ("Rotated in", "#34d399", "#065f46"),
    "rotated_out": ("Rotated out", "#f87171", "#7f1d1d"),
    "removed": ("Removed", "#f87171", "#7f1d1d"),
}

_NOT_AVAILABLE = (
    "<span style='color: #6b7280; font-style: italic;'>Not available</span>"
)


def _esc(value: Any) -> str:
    return html_lib.escape(str(value)) if value is not None else ""


def _num(value: Any, suffix: str = "", places: int = 1) -> str:
    """A number, or an explicit statement that there is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _NOT_AVAILABLE
    if value != value:  # NaN compares unequal to itself
        return _NOT_AVAILABLE
    return f"{value:.{places}f}{suffix}"


def _section(title: str, body: str, note: str = "") -> str:
    note_html = (
        f"<p style='font-size: 11px; color: #6b7280; margin: 10px 0 0 0;'>{note}</p>"
        if note
        else ""
    )
    return f"""
    <div class="section-card">
        <h3 style="margin: 0 0 12px 0; color: #93c5fd; font-size: 13px;
                   text-transform: uppercase; letter-spacing: 0.5px;">{title}</h3>
        {body}
        {note_html}
    </div>
    """


def build_watchlist_changes_html(
    changes: List[Dict[str, Any]], limit: int = MAX_CHANGES
) -> str:
    """Holdings that entered or left the watchlist, newest first.

    Returns "" when the pipeline shipped no changes feed at all. That is not
    the same as a run where the watchlist held steady, and the two must not
    render identically -- an empty list says "nothing moved", a missing key
    says "we did not look".
    """
    if not isinstance(changes, list):
        return ""
    rows = [c for c in changes if isinstance(c, dict)]
    if not rows:
        return _section(
            "Watchlist Changes",
            "<p style='font-size: 13px; color: #94a3b8; margin: 0;'>"
            "No additions or exits this cycle.</p>",
        )

    items = ""
    for change in rows[:limit]:
        label, fg, bg = _ACTION_LABEL.get(
            str(change.get("action", "")).lower(),
            (str(change.get("action") or "Changed").title(), "#9ca3af", "#374151"),
        )
        price = change.get("price_at_decision")
        target = change.get("target_at_decision")
        # An unscored decision has no outcome yet, and saying so is the
        # honest render. Reporting a pending decision as a flat return would
        # read as a result the pipeline has not earned.
        outcome = change.get("outcome")
        outcome_html = (
            f"<span style='color: #94a3b8;'>{_esc(outcome)}</span>"
            if outcome
            else "<span style='color: #6b7280; font-style: italic;'>"
            "Not yet scored</span>"
        )
        items += f"""
        <tr>
            <td class="ew-td"><span class="stock-ticker">{_esc(change.get('ticker'))}</span></td>
            <td class="ew-td" style="color: #cbd5e1;">{_esc(change.get('name'))}</td>
            <td class="ew-td">
                <span class="badge" style="background-color: {bg}; color: {fg};">{_esc(label)}</span>
            </td>
            <td class="ew-td" style="color: #94a3b8;">{_esc(change.get('date'))}</td>
            <td class="ew-td" style="color: #94a3b8;">{_num(price, places=1)} &rarr; {_num(target, places=1)}</td>
            <td class="ew-td">{outcome_html}</td>
        </tr>
        """

    overflow = len(rows) - limit
    note = (
        f"+ {overflow} more change(s) in the rotation ledger." if overflow > 0 else ""
    )
    body = f"""
    <table class="stock-table">
        <thead><tr>
            <th>Ticker</th><th>Company</th><th>Action</th>
            <th>Date</th><th>Price &rarr; Target</th><th>Outcome</th>
        </tr></thead>
        <tbody>{items}</tbody>
    </table>
    """
    return _section("Watchlist Changes", body, note)


def build_valuation_extremes_html(
    sector_valuation: List[Dict[str, Any]],
    suppressed: List[Dict[str, str]] = None,
    limit: int = MAX_EXTREMES,
) -> str:
    """The cheapest and dearest names, and the ones deliberately not valued.

    The suppressed list is the point of the section. A valuation table that
    silently omits the holdings it could not value implies the ones shown are
    the whole picture; naming them, with the reason, keeps the omission
    visible.
    """
    rows = [s for s in (sector_valuation or []) if isinstance(s, dict)]
    suppressed = [s for s in (suppressed or []) if isinstance(s, dict)]
    if not rows and not suppressed:
        return ""

    priced = [r for r in rows if isinstance(r.get("median_pe"), (int, float))]
    priced.sort(key=lambda r: r["median_pe"])

    body = ""
    if priced:
        cheap = priced[:limit]
        dear = list(reversed(priced[-limit:]))
        body += "<table class='stock-table'><thead><tr>"
        body += "<th>Sector</th><th>Median P/E</th><th>Cheapest</th>"
        body += "<th>Most expensive</th></tr></thead><tbody>"
        for group, heading in ((cheap, "Lowest median P/E"), (dear, "Highest")):
            body += (
                f"<tr><td class='ew-td' colspan='4' "
                f"style='color: #60a5fa; font-size: 11px; "
                f"text-transform: uppercase;'>{heading}</td></tr>"
            )
            for r in group:
                body += f"""
                <tr>
                    <td class="ew-td" style="color: #cbd5e1;">{_esc(r.get('label') or r.get('sector'))}</td>
                    <td class="ew-td" style="color: #e2e8f0;">{_num(r.get('median_pe'))}</td>
                    <td class="ew-td" style="color: #34d399;">{_esc(r.get('cheapest_ticker')) or _NOT_AVAILABLE} ({_num(r.get('cheapest_pe'))})</td>
                    <td class="ew-td" style="color: #f87171;">{_esc(r.get('most_expensive_ticker')) or _NOT_AVAILABLE} ({_num(r.get('most_expensive_pe'))})</td>
                </tr>
                """
        body += "</tbody></table>"
    else:
        body += (
            "<p style='font-size: 13px; color: #94a3b8; margin: 0;'>"
            "No sector carried a median P/E this run.</p>"
        )

    if suppressed:
        shown = suppressed[:MAX_SUPPRESSED]
        listed = ", ".join(
            f"<strong>{_esc(s.get('ticker'))}</strong> "
            f"(Suppressed &mdash; {_esc(s.get('reason') or 'reason not recorded')})"
            for s in shown
        )
        extra = len(suppressed) - len(shown)
        if extra > 0:
            listed += f", and {extra} more"
        body += f"""
        <p style="font-size: 12px; color: #94a3b8; margin: 14px 0 0 0;
                  padding-top: 12px; border-top: 1px dashed #374151;">
            <span style="color: #fbbf24;">Not valued this run:</span> {listed}.
        </p>
        """

    return _section("Valuation Extremes", body)


def build_data_quality_html(
    brief_data: Dict[str, Any], watchlist: Dict[str, Any] = None
) -> str:
    """What the run could not see.

    Every number above this section is only as good as the fetches behind it,
    and three separate bugs this cycle produced confident output from broken
    inputs. Stating the gaps costs a few lines and makes the rest falsifiable.
    """
    brief_data = brief_data or {}
    notes = []

    freshness = (brief_data.get("freshness") or {}).get("live_prices") or {}
    updated, total = freshness.get("updated"), freshness.get("total")
    if isinstance(updated, int) and isinstance(total, int) and total:
        pct = updated / total * 100
        colour = "#34d399" if pct >= 95 else ("#fbbf24" if pct >= 80 else "#f87171")
        notes.append(
            f"<span style='color: {colour};'>Live prices:</span> "
            f"{updated}/{total} holdings refreshed ({pct:.0f}%)."
        )
    else:
        notes.append(
            "<span style='color: #6b7280;'>Live prices:</span> "
            "refresh status not recorded this run."
        )

    coverage = brief_data.get("coverage_count")
    if isinstance(coverage, dict):
        covered = sum(1 for v in coverage.values() if v)
        notes.append(
            f"<span style='color: #93c5fd;'>News coverage:</span> "
            f"{covered} of {len(coverage)} holdings had attributable items."
        )

    held = sum(
        len(v or [])
        for k, v in (watchlist or {}).items()
        if k != "macro_indicators" and isinstance(v, list)
    )
    if held:
        no_estimate = sum(
            1
            for k, v in (watchlist or {}).items()
            if k != "macro_indicators" and isinstance(v, list)
            for s in v
            if isinstance(s, dict) and s.get("estimate_method") == "No Estimate"
        )
        if no_estimate:
            notes.append(
                f"<span style='color: #fbbf24;'>Estimates suppressed:</span> "
                f"{no_estimate} of {held} holdings carry no target, because "
                f"neither analyst coverage nor a usable fundamental base was "
                f"available."
            )

        # Screener omits the pledge row for companies with no pledge and for
        # a page the parser could not match, so this count is the only way to
        # tell a clean watchlist from a blind one.
        pledge_known = sum(
            1
            for k, v in (watchlist or {}).items()
            if k != "macro_indicators" and isinstance(v, list)
            for s in v
            if isinstance(s, dict)
            and (s.get("screener") or {}).get("pledged_pct") is not None
        )
        notes.append(
            f"<span style='color: #93c5fd;'>Promoter pledging:</span> "
            f"{pledge_known} of {held} holdings disclosed a pledge figure; "
            f"the rest are unread, not confirmed unpledged."
        )

    # Commodity and FX inputs. Reported whenever the key exists, including
    # when nothing priced: a run that could not reach the price source must
    # not read the same as a calm month in the commodity complex.
    shock = brief_data.get("input_cost_shock")
    if isinstance(shock, dict):
        priced = len(shock.get("inputs") or {})
        unmeasured = shock.get("unmeasured") or []
        shocked = sum(
            1
            for row in (shock.get("sectors") or {}).values()
            if isinstance(row, dict) and row.get("band") in ("material", "severe")
        )
        if priced:
            notes.append(
                f"<span style='color: #93c5fd;'>Input costs:</span> {priced} "
                f"input(s) priced; {shocked} sector(s) carrying a material move."
            )
        if unmeasured:
            named = ", ".join(
                _esc(u.get("label") or u.get("input")) for u in unmeasured[:4]
            )
            more = len(unmeasured) - 4
            notes.append(
                f"<span style='color: #f87171;'>Inputs not priced:</span> {named}"
                f"{f', and {more} more' if more > 0 else ''} &mdash; "
                f"treated as unmeasured, not as unchanged."
            )

    warnings = brief_data.get("early_warnings")
    if isinstance(warnings, list):
        sized = sum(
            1
            for w in warnings
            if isinstance(w, dict) and w.get("materiality_pct") is not None
        )
        if sized:
            notes.append(
                f"<span style='color: #93c5fd;'>Order sizing:</span> {sized} "
                f"alert(s) measured against trailing revenue; the rest carried "
                f"no attributable figure."
            )

    if not notes:
        return ""

    body = (
        "<ul style='margin: 0; padding-left: 18px; font-size: 12px; color: #94a3b8;'>"
    )
    body += "".join(f"<li style='margin-bottom: 6px;'>{n}</li>" for n in notes)
    body += "</ul>"
    return _section("Data Quality", body)


def build_cta_html(dashboard_url: str) -> str:
    """One primary action, three secondary. Never more.

    A briefing that ends in a wall of equally-weighted links asks the reader
    to choose, which is the one thing the digest exists to save them from.
    """
    base = (dashboard_url or "").rstrip("/")
    secondary = (
        ("Alerts", f"{base}#overview"),
        ("Sectors", f"{base}#sectors"),
        ("System health", f"{base}#system"),
    )
    links = " &nbsp;·&nbsp; ".join(
        f"<a href='{_esc(url)}' style='color: #60a5fa; text-decoration: none;' "
        f"target='_blank'>{_esc(label)}</a>"
        for label, url in secondary
    )
    return f"""
    <div class="section-card" style="text-align: center;">
        <a href="{_esc(base)}" class="cta-button" target="_blank"
           style="margin-top: 0;">Review today's changes</a>
        <p style="font-size: 12px; color: #6b7280; margin: 14px 0 0 0;">{links}</p>
    </div>
    """
