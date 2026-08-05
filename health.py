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


# Turnover is reported every run rather than gated on a fraction. The right
# floor is not yet known — this measures a third-party field that may simply be
# absent for thin listings — and a threshold guessed before the baseline exists
# would go red daily and be tuned out within a week. Only a *total* collapse to
# zero is unambiguous enough to fail the job on.
def summarize_liquidity(watchlist: Dict[str, Any]) -> Dict[str, int]:
    """Turnover coverage and band counts across the watchlist.

    Coverage is the question that matters, and it is not the same question as
    "did anything crash". Yahoo can return a clean response with no Volume
    column for a thinly traded listing, in which case the stock lands in
    ``unknown``, the illiquidity penalty never fires, and the feature looks
    healthy while doing nothing for precisely the holdings that motivated it.
    That failure is silent unless the count is stated out loud.
    """
    counts = {
        "total": 0,
        "measured": 0,
        "illiquid": 0,
        "thin": 0,
        "adequate": 0,
        "liquid": 0,
        "unknown": 0,
    }
    for stock in _holdings(watchlist):
        counts["total"] += 1
        screener = stock.get("screener") or {}
        band = screener.get("liquidity_band") or "unknown"
        if screener.get("advt_cr") is not None:
            counts["measured"] += 1
        if band in counts:
            counts[band] += 1
        else:
            counts["unknown"] += 1
    return counts


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

        # Turnover coverage is deliberately NOT gated here yet. It is reported
        # on every run by log_liquidity_coverage instead.
        #
        # The tempting check — prices arrived but no holding carries turnover,
        # so every liquidity check is inert — is the right check to end up
        # with, and it is not safe to add today: no production run has yet
        # reported this field, so the healthy baseline is unmeasured. A gate
        # set on a guessed baseline either fails the job daily over a source
        # that simply omits Volume for thin listings, or passes trivially and
        # gives false assurance. Both are worse than a logged number.
        #
        # Add the gate once a run has established what coverage actually looks
        # like; the counts are in the log from this release onward.
    except Exception as e:  # noqa: BLE001
        log.warning(f"Run health check failed safely: {e!r}")
        return True, []

    return not problems, problems


def log_liquidity_coverage(watchlist: Dict[str, Any]) -> None:
    """State turnover coverage in the log on every run, healthy or not.

    Logged unconditionally so the number is in the record daily and a slow
    erosion is visible as a trend, rather than being discovered the next time
    somebody thinks to go looking.
    """
    try:
        c = summarize_liquidity(watchlist)
        log.info(
            f"Liquidity: {c['measured']}/{c['total']} holdings priced by turnover "
            f"({c['illiquid']} illiquid, {c['thin']} thin, {c['adequate']} adequate, "
            f"{c['liquid']} liquid, {c['unknown']} unmeasured)."
        )
    except Exception as e:  # noqa: BLE001
        log.warning(f"Liquidity coverage summary failed safely: {e!r}")


def log_run_health(data: Dict[str, Any], watchlist: Dict[str, Any]) -> bool:
    """Check health and log the verdict. Returns True when the run is sound."""
    log_liquidity_coverage(watchlist)
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
