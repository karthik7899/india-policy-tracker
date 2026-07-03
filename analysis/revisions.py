"""Estimate revision momentum.

Rising analyst price targets and growing analyst coverage are among the most
reliable tailwinds funds trade on — the "estimate revision" factor. This
pipeline already commits ``dashboard_data.json`` to git every run, so the
prior run's targets, analyst counts and recommendation scores are sitting on
disk for free; the only work is diffing them against this run's numbers
before they get overwritten.
"""

from logger import log


def _to_float(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace("+", "").replace(",", "")
        if not cleaned or cleaned.upper() in {"N/A", "NA", "-", "—"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def snapshot_prior_estimates(prior_watchlist):
    """Extracts a lightweight {ticker: {...}} snapshot from the previous run's
    watchlist, before this run's data overwrites it in memory."""
    snapshot = {}
    for stocks in (prior_watchlist or {}).values():
        for stock in stocks or []:
            if not isinstance(stock, dict) or not stock.get("ticker"):
                continue
            snapshot[stock["ticker"]] = {
                "target": _to_float(stock.get("target")),
                "analyst_count": _to_float(stock.get("analyst_count")),
                "rec_score": _to_float(stock.get("rec_score")),
            }
    return snapshot


def compute_revision_momentum(watchlist, prior_snapshot, min_target_move_pct=3.0):
    """Diffs each holding's current estimates against the prior run.

    Returns a flat list of {ticker, name, sector, target_change_pct,
    analyst_count_change, rec_score_change, direction} for stocks whose
    target price moved at least ``min_target_move_pct``, sorted by magnitude
    of target change (largest revisions first). ``rec_score`` falls as
    sentiment improves (1 = Strong Buy, 5 = Strong Sell), so a negative
    ``rec_score_change`` is bullish.
    """
    if not prior_snapshot:
        return []

    results = []
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            ticker = stock.get("ticker")
            prior = prior_snapshot.get(ticker)
            if not prior:
                continue  # newly added this run; nothing to diff against

            new_target = _to_float(stock.get("target"))
            old_target = prior.get("target")
            if new_target is None or old_target is None or old_target == 0:
                continue

            target_change_pct = round((new_target - old_target) / old_target * 100, 2)
            if abs(target_change_pct) < min_target_move_pct:
                continue

            new_count = _to_float(stock.get("analyst_count"))
            old_count = prior.get("analyst_count")
            count_change = (
                int(new_count - old_count)
                if new_count is not None and old_count is not None
                else None
            )

            new_rec = _to_float(stock.get("rec_score"))
            old_rec = prior.get("rec_score")
            rec_change = (
                round(new_rec - old_rec, 2)
                if new_rec is not None and old_rec is not None
                else None
            )

            results.append(
                {
                    "ticker": ticker,
                    "name": stock.get("name"),
                    "sector": sector,
                    "target_change_pct": target_change_pct,
                    "analyst_count_change": count_change,
                    "rec_score_change": rec_change,
                    "direction": "up" if target_change_pct > 0 else "down",
                }
            )

    results.sort(key=lambda r: abs(r["target_change_pct"]), reverse=True)
    if results:
        log.info(
            f"Estimate revisions: {len(results)} stocks moved targets vs prior run."
        )
    return results
