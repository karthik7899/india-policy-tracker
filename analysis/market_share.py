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


def compute_industry_share(watchlist, industry_peers, prior_shares=None):
    """Each holding's share of its FULL industry peer group's quarterly sales.

    ``industry_peers`` comes from Screener's peer tables (one per sector) and
    includes every listed industry peer with its absolute quarterly sales —
    a far better denominator than the 2-5 watchlist stocks the peer-group
    estimate uses. All figures in a table come from the same source and
    quarter, so the ratio is internally consistent.

    ``prior_shares`` is {ticker: share_pct} from the previous run (committed
    dashboard data), enabling a run-over-run change until enough history
    accumulates. Annotates each covered stock's screener dict and returns a
    sector rollup for the dashboard.
    """
    prior_shares = prior_shares or {}
    rollup = {}
    for sector, rows in (industry_peers or {}).items():
        if sector == "macro_indicators":
            continue

        sales_by_ticker = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            sales = row.get("sales_qtr")
            if isinstance(sales, (int, float)) and sales > 0:
                sales_by_ticker[row.get("ticker")] = float(sales)

        total = sum(sales_by_ticker.values())
        if total <= 0 or len(sales_by_ticker) < MIN_PEER_GROUP:
            continue

        sector_rows = []
        for stock in watchlist.get(sector, []) or []:
            if not isinstance(stock, dict):
                continue
            ticker = str(stock.get("ticker", "")).upper()
            own_sales = sales_by_ticker.get(ticker)
            if own_sales is None:
                continue

            share = round(own_sales / total * 100, 2)
            prior = prior_shares.get(ticker)
            change_pp = (
                round(share - float(prior), 2)
                if isinstance(prior, (int, float))
                else None
            )

            screener = stock.setdefault("screener", {})
            screener["industry_share_pct"] = share
            screener["industry_peer_count"] = len(sales_by_ticker)
            if change_pp is not None:
                screener["industry_share_change_pp"] = change_pp

            sector_rows.append(
                {
                    "ticker": ticker,
                    "name": stock.get("name"),
                    "share_pct": share,
                    "change_pp": change_pp,
                    "peer_count": len(sales_by_ticker),
                }
            )

        if sector_rows:
            sector_rows.sort(key=lambda r: r["share_pct"], reverse=True)
            rollup[sector] = sector_rows

    if rollup:
        covered = sum(len(v) for v in rollup.values())
        log.info(
            f"Industry market share computed for {covered} stocks "
            f"across {len(rollup)} sectors."
        )
    return rollup


def snapshot_prior_industry_shares(prior_watchlist):
    """{ticker: industry_share_pct} from the previous run, read before this
    run's fetches overwrite the in-memory watchlist."""
    snapshot = {}
    for stocks in (prior_watchlist or {}).values():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            share = (stock.get("screener") or {}).get("industry_share_pct")
            if isinstance(share, (int, float)):
                snapshot[str(stock.get("ticker", "")).upper()] = float(share)
    return snapshot
