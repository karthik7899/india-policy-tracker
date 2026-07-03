"""Sector S-curve staging.

A growth theme moves through recognizable stages — a slow pre-inflection
build-up, a steep adoption phase once barriers fall, then maturity as growth
decelerates and the multiple gets tested. Whale Rock's public framework
maps entire sub-sectors onto this curve before picking names inside it; this
is the automatable slice of that idea, built entirely from quarterly sales
series the pipeline already fetches (``providers/screener.py``'s
``sales_trend``) — no new data source.

Stage is derived from two things per sector: the median trailing QoQ sales
growth (level) and whether that growth is accelerating or decelerating
quarter over quarter (direction). Deliberately coarse — four buckets, not a
precise curve-fit — because the input is a handful of quarterly points per
stock and false precision would be misleading.
"""

from logger import log

_MIN_PEERS = 2


def _clean_series(stock):
    screener = stock.get("screener") if isinstance(stock, dict) else None
    trend = (screener or {}).get("sales_trend") or []
    series = []
    for value in trend:
        try:
            series.append(float(value))
        except (TypeError, ValueError):
            return []
    return series


def _median(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _qoq_growth_series(series):
    """Quarter-over-quarter % growth at each step of a sales series."""
    growths = []
    for prev, curr in zip(series, series[1:]):
        if prev and prev > 0:
            growths.append((curr - prev) / prev * 100)
    return growths


def classify_sector_curve_stage(watchlist):
    """Returns {sector: {stage, median_qoq_growth_pct, acceleration_pp, stock_count}}."""
    results = {}
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue

        latest_growths = []
        accelerations = []
        for stock in stocks or []:
            series = _clean_series(stock)
            growths = _qoq_growth_series(series)
            if not growths:
                continue
            latest_growths.append(growths[-1])
            if len(growths) >= 2:
                accelerations.append(growths[-1] - growths[-2])

        if len(latest_growths) < _MIN_PEERS:
            continue

        median_growth = _median(latest_growths)
        median_accel = _median(accelerations) if accelerations else 0.0

        if median_growth >= 15.0 and median_accel >= 0:
            stage = "Inflection / Steep Adoption"
        elif median_growth >= 15.0 and median_accel < 0:
            stage = "Maturing"
        elif 0 <= median_growth < 15.0 and median_accel > 2.0:
            stage = "Pre-Inflection (building)"
        elif median_growth < 0:
            stage = "Late-Cycle / Contracting"
        else:
            stage = "Steady State"

        results[sector] = {
            "stage": stage,
            "median_qoq_growth_pct": round(median_growth, 1),
            "acceleration_pp": round(median_accel, 1),
            "stock_count": len(latest_growths),
        }

    if results:
        log.info(f"Curve staging computed for {len(results)} sectors.")
    return results
