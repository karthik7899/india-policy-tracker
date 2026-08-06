"""What today's briefing is actually about, computed once.

The subject line, the preheader, the executive summary and the plain-text
alternative are four statements of the same thing, and until now only the last
three existed at all — the subject was the date. Deriving them from one
structure is what stops them contradicting each other: a subject promising two
critical alerts above a body listing three is worse than a dull subject,
because the reader stops trusting the count rather than the formatting.

The day type matters as much as the numbers. A quiet day and a broken run both
produce a short email, and they mean opposite things: one says there is
nothing to do, the other says the briefing cannot be relied on. Saying so in
the subject is the difference between a reader who skims and a reader who is
misled.
"""

from typing import Any, Dict, List

# Below this the run is degraded enough that the signals should be read as
# provisional. Chosen to match health.py's own floor rather than invented
# separately, so the email and the job never disagree about what "healthy"
# means.
MIN_PRICED_FRACTION = 0.6
MIN_SCREENER_FRACTION = 0.5

# How many items reach the email. Everything else is on the dashboard: the
# briefing is a decision aid, and 200 warnings is not a decision aid.
MAX_CRITICAL = 5
MAX_OPPORTUNITIES = 5
MAX_SECTORS = 3


def _holdings(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        s
        for sector, stocks in (watchlist or {}).items()
        if sector != "macro_indicators"
        for s in stocks or []
        if isinstance(s, dict)
    ]


def _coverage(watchlist: Dict[str, Any]) -> Dict[str, Any]:
    holdings = _holdings(watchlist)
    total = len(holdings)
    if not total:
        return {"total": 0, "priced": 0, "fundamentals": 0, "completeness": 0}

    priced = sum(1 for s in holdings if s.get("price"))
    fundamentals = sum(1 for s in holdings if (s.get("screener") or {}))
    growth = sum(
        1
        for s in holdings
        if (s.get("screener") or {}).get("revenue_ttm_growth_pct") is not None
    )
    return {
        "total": total,
        "priced": priced,
        "fundamentals": fundamentals,
        "growth": growth,
        # The mean of the coverages that gate analysis. A count of populated
        # keys would flatter a run that fetched every cheap field and no
        # expensive one.
        "completeness": round((priced + fundamentals + growth) / (3 * total) * 100),
    }


def build_summary(
    brief_data: Dict[str, Any], watchlist: Dict[str, Any]
) -> Dict[str, Any]:
    """The day in one structure: what changed, how much to trust it, and why."""
    warnings = brief_data.get("early_warnings") or []
    is_new = lambda w: (w.get("status") or "ongoing") == "new"  # noqa: E731

    escalated = [w for w in warnings if (w.get("status") or "") == "escalated"]
    new_signals = [w for w in warnings if is_new(w)]

    # Only what changed. These counts previously ran over every warning in the
    # corpus, and the pipeline hands this function the *untrimmed* data — so
    # the first production subject read "11 Critical, 140 Opportunities" while
    # the dashboard showed 42 actionable items and the body listed twelve.
    #
    # A subject line advertising the standing set is the exact wall of alerts
    # this rewrite existed to replace, reproduced in the one place guaranteed
    # to be read. Standing conditions are still counted, as ongoing_total.
    changed = [w for w in warnings if is_new(w) or (w.get("status") == "escalated")]
    critical = [
        w
        for w in changed
        if w.get("severity") == "Critical" and w.get("direction") == "risk"
    ]
    opportunities = [w for w in changed if w.get("direction") == "opportunity"]

    coverage = _coverage(watchlist)
    total = coverage["total"] or 1
    degraded = (
        coverage["priced"] / total < MIN_PRICED_FRACTION
        or coverage["fundamentals"] / total < MIN_SCREENER_FRACTION
    )

    # Standing conditions are counted but not listed: they are the reason the
    # email used to run to 200 items, and they have not changed today.
    ongoing_groups = brief_data.get("warning_summary") or []
    ongoing_total = sum(g.get("count", 0) for g in ongoing_groups)

    broken = [
        t
        for t in (brief_data.get("thesis_health") or {}).values()
        if isinstance(t, dict) and t.get("status") == "Broken"
    ]
    suppressed = [
        s for s in _holdings(watchlist) if s.get("estimate_method") == "No Estimate"
    ]

    # Sectors ranked by how much moved in them, so "sectors needing attention"
    # is derived rather than asserted.
    by_sector: Dict[str, int] = {}
    for w in new_signals + escalated:
        key = w.get("sector") or "unknown"
        by_sector[key] = by_sector.get(key, 0) + 1
    hot_sectors = sorted(by_sector.items(), key=lambda kv: -kv[1])[:MAX_SECTORS]

    if degraded:
        day_type = "degraded"
    elif not new_signals and not escalated:
        day_type = "quiet"
    else:
        day_type = "normal"

    return {
        "day_type": day_type,
        "coverage": coverage,
        "degraded": degraded,
        "critical": critical[:MAX_CRITICAL],
        "critical_total": len(critical),
        "escalated": escalated,
        "opportunities": opportunities[:MAX_OPPORTUNITIES],
        "opportunities_total": len(opportunities),
        "new_total": len(new_signals),
        "ongoing_total": ongoing_total,
        "ongoing_groups": len(ongoing_groups),
        "broken_theses": len(broken),
        "suppressed": suppressed,
        "hot_sectors": hot_sectors,
    }


def _sector_label(key: str) -> str:
    from config import SECTOR_METADATA

    return (SECTOR_METADATA.get(key) or {}).get("name") or key.replace("_", " ").title()


def build_subject(summary: Dict[str, Any], today) -> str:
    """A subject that survives being the only thing the reader sees.

    Named counts and named sectors, because a subject line is read in a list
    of thirty others and "Daily Briefing" competes with none of them.
    """
    date = today.strftime("%d %b")
    if summary["day_type"] == "degraded":
        cov = summary["coverage"]
        return (
            f"India Policy Tracker | {date} | DEGRADED RUN — "
            f"{cov['priced']}/{cov['total']} priced, treat signals as provisional"
        )

    if summary["day_type"] == "quiet":
        return (
            f"India Policy Tracker | {date} | No new signals | "
            f"{summary['ongoing_total']} ongoing"
        )

    parts = []
    if summary["critical_total"]:
        parts.append(f"{summary['critical_total']} Critical")
    if summary["escalated"]:
        parts.append(f"{len(summary['escalated'])} Escalated")
    if summary["opportunities_total"]:
        parts.append(f"{summary['opportunities_total']} Opportunities")
    if not parts:
        parts.append(f"{summary['new_total']} New Signals")

    sectors = ", ".join(_sector_label(k) for k, _ in summary["hot_sectors"][:2])
    tail = f" | {sectors}" if sectors else ""
    return f"India Policy Tracker | {date} | {', '.join(parts)}{tail}"


def build_preheader(summary: Dict[str, Any]) -> str:
    """The line the inbox shows after the subject. Wasting it on "View in
    browser" is the default; it is worth an actual sentence."""
    if summary["day_type"] == "degraded":
        cov = summary["coverage"]
        return (
            f"Data completeness {cov['completeness']}%. "
            f"{cov['priced']}/{cov['total']} holdings priced, "
            f"{cov['fundamentals']}/{cov['total']} with fundamentals. "
            "Signals are provisional."
        )
    if summary["day_type"] == "quiet":
        return (
            f"Nothing appeared or worsened this cycle. "
            f"{summary['ongoing_total']} standing condition(s) across "
            f"{summary['ongoing_groups']} group(s) are unchanged."
        )

    bits = []
    for w in summary["critical"][:2]:
        bits.append(f"{w.get('ticker')} {(w.get('category') or 'risk').lower()}")
    for w in summary["opportunities"][:1]:
        bits.append(f"{w.get('ticker')} {(w.get('category') or 'signal').lower()}")
    return "; ".join(bits) or f"{summary['new_total']} new signal(s) this cycle."


def build_plain_text(summary: Dict[str, Any], dashboard_url: str, today) -> str:
    """Plain-text alternative.

    There was none: the message went out as HTML only, which costs
    deliverability with spam filters and leaves screen readers and text
    clients with whatever the mail client can salvage from the markup.
    """
    cov = summary["coverage"]
    lines = [
        "INDIA POLICY & SECTOR IMPACT TRACKER",
        f"Daily Briefing - {today.strftime('%A, %d %B %Y')}",
        "",
        f"Data completeness: {cov['completeness']}%  |  "
        f"Priced: {cov['priced']}/{cov['total']}  |  "
        f"Run: {'DEGRADED' if summary['degraded'] else 'Healthy'}",
        "",
    ]

    if summary["day_type"] == "degraded":
        lines += [
            "DEGRADED RUN",
            "This run completed but data completeness is below threshold.",
            f"  Priced holdings:      {cov['priced']}/{cov['total']}",
            f"  Fundamentals fetched: {cov['fundamentals']}/{cov['total']}",
            "",
            "Recommendation: treat today's signals as provisional.",
            "",
        ]

    if summary["day_type"] == "quiet":
        lines += [
            "No new or escalated signals this cycle.",
            f"Ongoing conditions: {summary['ongoing_total']} "
            f"across {summary['ongoing_groups']} group(s).",
            "",
        ]
    else:
        lines.append("WHAT CHANGED")
        if summary["critical"]:
            lines.append(f"  Critical risks: {summary['critical_total']}")
        if summary["escalated"]:
            lines.append(f"  Escalated: {len(summary['escalated'])}")
        if summary["opportunities_total"]:
            lines.append(f"  Opportunity signals: {summary['opportunities_total']}")
        if summary["broken_theses"]:
            lines.append(f"  Theses marked broken: {summary['broken_theses']}")
        lines.append("")

        if summary["critical"]:
            lines.append("CRITICAL")
            for w in summary["critical"]:
                lines.append(
                    f"  - {w.get('ticker')} ({w.get('name')}): "
                    f"{w.get('category')} — {w.get('signal')}"
                )
            lines.append("")

        if summary["opportunities"]:
            lines.append("OPPORTUNITY SIGNALS")
            for w in summary["opportunities"]:
                lines.append(
                    f"  - {w.get('ticker')} ({w.get('name')}): "
                    f"{w.get('category')} — {w.get('signal')}"
                )
            lines.append("")

    if summary["suppressed"]:
        lines.append("SUPPRESSED ESTIMATES")
        for s in summary["suppressed"][:5]:
            lines.append(f"  - {s.get('ticker')}: no honest valuation available")
        lines.append("")

    lines += [
        f"Full dashboard: {dashboard_url}",
        "",
        "Sources: PIB, Google News RSS, Screener.in, Yahoo Finance, SEBI "
        "filings, AMFI/MF NAV data.",
        "Generated automatically. May contain data or classification errors. "
        "Not investment advice; verify filings and fundamentals before acting.",
    ]
    return "\n".join(lines)
