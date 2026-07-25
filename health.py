"""Run-health assertions: turn silent degradation into a failed job.

A crash already fails the workflow, because nothing catches exceptions at the
top of the pipeline. What passes unnoticed is *degradation* — Yahoo returning
nothing, Screener rate-limiting the whole fetch, every sector rollup coming
back empty. The briefing still renders, the email still sends, the job still
goes green, and the first sign of trouble is a dashboard that looks subtly
wrong days later.

So the pipeline states what a working run looks like and checks it. The
thresholds sit well below normal (a healthy run prices 47 of 47 holdings, so a
60% floor only trips on real breakage) because a noisy check gets ignored, and
an ignored check is worse than none.

The email is sent *before* this runs. A degraded briefing is still worth
reading, and withholding it would remove the evidence needed to diagnose the
degradation. This only decides whether the job reports success.
"""

from typing import Any, Dict, List, Tuple

from logger import log

# Fraction of holdings that must carry a live price for the run to count.
MIN_PRICED_FRACTION = 0.6
# Fraction that must carry Screener fundamentals. Lower, because Screener is
# the flakier source and several holdings legitimately have thin filings.
MIN_SCREENER_FRACTION = 0.5


def _holdings(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        stock
        for sector, stocks in (watchlist or {}).items()
        if sector != "macro_indicators"
        for stock in stocks or []
        if isinstance(stock, dict)
    ]


def check_run_health(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Return ``(healthy, problems)`` for a completed run.

    Never raises: a health check that can itself fail the run for its own
    reasons would be worse than the problem it exists to catch.
    """
    problems: List[str] = []
    try:
        holdings = _holdings(watchlist)
        total = len(holdings)
        if total == 0:
            return False, ["watchlist is empty"]

        priced = sum(1 for s in holdings if s.get("price"))
        if priced / total < MIN_PRICED_FRACTION:
            problems.append(
                f"only {priced}/{total} holdings carry a live price "
                f"(floor {MIN_PRICED_FRACTION:.0%})"
            )

        with_fundamentals = sum(1 for s in holdings if (s.get("screener") or {}))
        if with_fundamentals / total < MIN_SCREENER_FRACTION:
            problems.append(
                f"only {with_fundamentals}/{total} holdings carry Screener "
                f"fundamentals (floor {MIN_SCREENER_FRACTION:.0%})"
            )

        if not data.get("sector_growth"):
            problems.append("no sector could be ranked for revenue growth")

        if not data.get("early_warnings"):
            problems.append("the early-warning engine produced nothing")
    except Exception as e:  # noqa: BLE001
        log.warning(f"Run health check failed safely: {e!r}")
        return True, []

    return not problems, problems


def log_run_health(data: Dict[str, Any], watchlist: Dict[str, Any]) -> bool:
    """Check health and log the verdict. Returns True when the run is sound."""
    healthy, problems = check_run_health(data, watchlist)
    if healthy:
        log.info("Run health: all coverage checks passed.")
        return True
    for problem in problems:
        log.error(f"Run health: {problem}")
    log.error(
        "Run health: briefing was delivered, but this run is degraded — "
        "failing the job so the breakage is visible."
    )
    return False
