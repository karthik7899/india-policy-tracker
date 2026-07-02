"""Peer-group market share estimation.

Estimates each holding's share of its sector peer group's combined quarterly
revenue, using the trailing Screener.in sales series already fetched by
``providers/screener.py``. This is share of the *tracked* peer group — not
total industry share — but its trend moves with true market share whenever
the watchlist covers a sector's main listed players, and unlike growth-rate
comparisons it is weighted by revenue base: a tiny challenger growing fast
moves the incumbent's share very little.
"""

from logger import log

# A share number needs at least two revenue streams to divide between.
MIN_PEER_GROUP = 2

# Compare the latest quarter's share against the share this many quarters ago,
# shrinking to whatever history the thinnest peer actually has.
MAX_LOOKBACK_QUARTERS = 4
MIN_LOOKBACK_QUARTERS = 1


def _clean_series(stock):
    """Returns the stock's positive trailing quarterly sales, oldest first."""
    screener = stock.get("screener") if isinstance(stock, dict) else None
    trend = (screener or {}).get("sales_trend") or []
    series = []
    for value in trend:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return []
        if number <= 0:
            return []
        series.append(number)
    return series


def compute_peer_market_share(watchlist):
    """Annotates stocks with peer-group share and returns a sector rollup.

    Each qualifying stock gains ``peer_share_pct``, ``peer_share_change_pp``,
    ``peer_share_lookback`` and ``peer_group_size`` in its screener dict.
    The return value maps sector -> rows sorted by share, for the dashboard.
    """
    rollup = {}
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue

        members = []
        for stock in stocks or []:
            series = _clean_series(stock)
            if len(series) >= MIN_LOOKBACK_QUARTERS + 1:
                members.append((stock, series))

        if len(members) < MIN_PEER_GROUP:
            continue

        lookback = min(
            MAX_LOOKBACK_QUARTERS,
            min(len(series) for _, series in members) - 1,
        )
        total_now = sum(series[-1] for _, series in members)
        total_prev = sum(series[-1 - lookback] for _, series in members)
        if total_now <= 0 or total_prev <= 0:
            continue

        rows = []
        for stock, series in members:
            share_now = series[-1] / total_now * 100
            share_prev = series[-1 - lookback] / total_prev * 100
            change_pp = share_now - share_prev

            screener = stock.setdefault("screener", {})
            screener["peer_share_pct"] = round(share_now, 1)
            screener["peer_share_change_pp"] = round(change_pp, 2)
            screener["peer_share_lookback"] = lookback
            screener["peer_group_size"] = len(members)

            rows.append(
                {
                    "ticker": stock.get("ticker"),
                    "name": stock.get("name"),
                    "share_pct": round(share_now, 1),
                    "share_prev_pct": round(share_prev, 1),
                    "change_pp": round(change_pp, 2),
                    "lookback_quarters": lookback,
                    "peer_count": len(members),
                }
            )

        rows.sort(key=lambda r: r["share_pct"], reverse=True)
        rollup[sector] = rows

    if rollup:
        covered = sum(len(v) for v in rollup.values())
        log.info(
            f"Peer market share computed for {covered} stocks "
            f"across {len(rollup)} sectors."
        )
    return rollup
