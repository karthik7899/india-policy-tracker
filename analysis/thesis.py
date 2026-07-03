"""Thesis health: is the reason we own this still true?

Every watchlist entry's ``catalyst`` field is an investment thesis, but as
plain text it has no kill criteria — nothing can ever falsify it. This module
doesn't ask the pipeline to fetch anything new; it re-reads the early-warning
signals and estimate-revision momentum already computed this run and asks a
sharper question than "is there a risk flag": does the accumulated evidence
mean the original catalyst is still standing, cracking, or gone.

Three states, deliberately coarse so they're skimmable in an email:
  - Intact:     no material risk signal contradicts the thesis this cycle.
  - Weakening:  one credible risk signal, or a negative estimate revision.
  - Broken:     a critical signal, multiple high-severity signals, or both a
                risk signal and a negative revision — the kill criteria for a
                falsifiable thesis, tripped.
"""

from logger import log

_BROKEN = "Broken"
_WEAKENING = "Weakening"
_INTACT = "Intact"
_ORDER = {_BROKEN: 0, _WEAKENING: 1, _INTACT: 2}

# A revision move at least this large counts as a kill-criteria input.
_MATERIAL_REVISION_PCT = 10.0


def _worsen(status):
    return {_INTACT: _WEAKENING, _WEAKENING: _BROKEN, _BROKEN: _BROKEN}[status]


def compute_thesis_health(watchlist, warnings, revisions=None):
    """Classifies each holding's thesis using this run's own signal set.

    ``warnings`` is the output of ``early_warning.generate_early_warnings``;
    ``revisions`` is the output of ``revisions.compute_revision_momentum``.
    Returns {ticker: {status, name, sector, reasons: [...]}}.
    """
    by_ticker = {}
    for w in warnings or []:
        by_ticker.setdefault(w.get("ticker"), []).append(w)

    revision_by_ticker = {r["ticker"]: r for r in (revisions or [])}

    results = {}
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        sector_label = sector
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            ticker = stock.get("ticker")
            if not ticker:
                continue

            ticker_warnings = by_ticker.get(ticker, [])
            risks = [w for w in ticker_warnings if w.get("direction") == "risk"]
            critical = [w for w in risks if w.get("severity") == "Critical"]
            high = [w for w in risks if w.get("severity") == "High"]
            other_risk = [w for w in risks if w.get("severity") in ("Medium", "Low")]

            reasons = []
            if critical:
                status = _BROKEN
                reasons.append(critical[0]["signal"])
            elif len(high) >= 2:
                status = _BROKEN
                reasons.extend(w["signal"] for w in high[:2])
            elif high:
                status = _WEAKENING
                reasons.append(high[0]["signal"])
            elif len(other_risk) >= 2:
                status = _WEAKENING
                reasons.extend(w["signal"] for w in other_risk[:2])
            else:
                status = _INTACT

            revision = revision_by_ticker.get(ticker)
            if (
                revision
                and revision["direction"] == "down"
                and abs(revision["target_change_pct"]) >= _MATERIAL_REVISION_PCT
            ):
                status = _worsen(status)
                reasons.append(
                    f"Consensus target cut {revision['target_change_pct']:.1f}% "
                    f"since the last run."
                )

            results[ticker] = {
                "ticker": ticker,
                "name": stock.get("name"),
                "sector": sector_label,
                "status": status,
                "reasons": reasons[:2],
            }

    counts = {_BROKEN: 0, _WEAKENING: 0, _INTACT: 0}
    for r in results.values():
        counts[r["status"]] += 1
    log.info(
        f"Thesis health: {counts[_INTACT]} intact, {counts[_WEAKENING]} weakening, "
        f"{counts[_BROKEN]} broken."
    )
    return results


def thesis_health_sorted(health_map):
    """Broken first, then Weakening, then Intact — the reading order for a briefing."""
    return sorted(health_map.values(), key=lambda r: (_ORDER[r["status"]], r["ticker"]))
