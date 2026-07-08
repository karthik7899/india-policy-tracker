import datetime

import pandas as pd
import yfinance as yf

from logger import log

_TICKER_CACHE = {}

# How far back an analyst rating change still counts as "recent" enough to
# surface — older changes are already priced in and just add noise.
_UPGRADE_LOOKBACK_DAYS = 30
_MAX_ANALYST_ACTIONS = 5
_MAX_INSTITUTIONAL_HOLDERS = 5


def get_cached_ticker(yahoo_ticker):
    """Retrieves a cached yf.Ticker object for the pipeline run.

    Deliberately takes no session argument: yfinance's YfData is a
    process-wide singleton with its own pooled, curl_cffi-backed session.
    Passing a plain requests.Session reassigns that shared session (racy
    under threads) and drops browser-impersonation headers, causing silent
    fetch failures. Let yfinance manage its own session.
    """
    if yahoo_ticker not in _TICKER_CACHE:
        _TICKER_CACHE[yahoo_ticker] = yf.Ticker(yahoo_ticker)
    return _TICKER_CACHE[yahoo_ticker]


def fetch_stock_data(yahoo_ticker, timeout=10):
    """
    Fetches stock data from Yahoo Finance and normalizes the fields.
    Returns a dictionary of normalized metrics.
    """
    ticker_obj = get_cached_ticker(yahoo_ticker)
    data = {
        "price": None,
        "rating": "N/A",
        "revenue_growth": None,
        "earnings_growth": None,
        "analyst_count": None,
        "target_median": None,
        "target_high": None,
        "target_low": None,
        "target": None,
        "rec_score": None,
    }

    # Fetch price
    hist = ticker_obj.history(period="1d", timeout=timeout)
    if not hist.empty:
        data["price"] = float(hist["Close"].iloc[-1])

    info = ticker_obj.info
    if info:
        _parse_targets(data, info)
        _parse_recommendations(data, info)
        _parse_growth_metrics(data, info)

    data["isin"] = _fetch_isin(ticker_obj)
    data["analyst_actions"] = _fetch_upgrades_downgrades(ticker_obj)
    data["institutional_holders"] = _fetch_institutional_holders(ticker_obj)

    return data


def _fetch_isin(ticker_obj):
    """Best-effort ISIN via yfinance's own lookup.

    Unlike the other fields on this Ticker (history/info/upgrades_downgrades/
    institutional_holders, all backed by Yahoo's own quoteSummary API),
    yfinance's .isin property is explicitly marked "experimental" in its own
    source and is backed by a *different* host (markets.businessinsider.com)
    that this pipeline has never otherwise touched — so this is genuinely
    less certain to work in CI than the rest of this module. Enhancement
    data only: never raises, degrades to None.
    """
    try:
        isin = ticker_obj.isin
        if isin and isin != "-" and len(isin) == 12:
            return isin
    except Exception as e:
        log.warning(
            f"{getattr(ticker_obj, 'ticker', '?')}: ISIN lookup failed: {type(e).__name__}: {str(e)[:150]}"
        )
    return None


def _fetch_upgrades_downgrades(ticker_obj, lookback_days=_UPGRADE_LOOKBACK_DAYS):
    """Recent analyst rating changes — Yahoo's own quoteSummary API
    (upgradeDowngradeHistory module), the same mechanism .info already uses
    successfully in this pipeline. A discrete, human-readable complement to
    the target-price revision momentum already tracked from committed
    run-over-run snapshots (analysis/revisions.py). Enhancement data only:
    never raises, degrades to an empty list.
    """
    try:
        df = ticker_obj.upgrades_downgrades
        if df is None or df.empty:
            return []
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=lookback_days
        )
        actions = []
        for grade_date, row in df.iterrows():
            row_date = grade_date.to_pydatetime()
            if row_date.tzinfo is None:
                row_date = row_date.replace(tzinfo=datetime.timezone.utc)
            if row_date < cutoff:
                continue
            firm = row.get("Firm")
            action = row.get("Action")
            # pandas NaN is truthy in Python — `not firm` alone would let a
            # missing value through as the literal string "nan".
            if pd.isna(firm) or not firm or pd.isna(action) or not action:
                continue
            from_grade = row.get("FromGrade")
            to_grade = row.get("ToGrade")
            actions.append(
                {
                    "firm": str(firm),
                    "action": str(action),
                    "from_grade": (
                        None
                        if pd.isna(from_grade) or not from_grade
                        else str(from_grade)
                    ),
                    "to_grade": (
                        None if pd.isna(to_grade) or not to_grade else str(to_grade)
                    ),
                    "date": row_date.strftime("%Y-%m-%d"),
                }
            )
        actions.sort(key=lambda a: a["date"], reverse=True)
        return actions[:_MAX_ANALYST_ACTIONS]
    except Exception as e:
        log.warning(
            f"{getattr(ticker_obj, 'ticker', '?')}: upgrades/downgrades lookup failed: "
            f"{type(e).__name__}: {str(e)[:150]}"
        )
        return []


def _fetch_institutional_holders(ticker_obj, top_n=_MAX_INSTITUTIONAL_HOLDERS):
    """Top institutional holders — Yahoo's own quoteSummary API
    (institutionOwnership module). Enhancement data only: never raises,
    degrades to an empty list."""
    try:
        df = ticker_obj.institutional_holders
        if df is None or df.empty:
            return []
        holders = []
        for _, row in df.iterrows():
            holder = row.get("Holder")
            if pd.isna(holder) or not holder:
                continue
            date_reported = row.get("Date Reported")
            holders.append(
                {
                    "holder": str(holder),
                    "shares": row.get("Shares"),
                    "value": row.get("Value"),
                    "pct_held": row.get("pctHeld"),
                    "date_reported": (
                        date_reported.strftime("%Y-%m-%d")
                        if hasattr(date_reported, "strftime")
                        else None
                    ),
                }
            )
        return holders[:top_n]
    except Exception as e:
        log.warning(
            f"{getattr(ticker_obj, 'ticker', '?')}: institutional holders lookup failed: "
            f"{type(e).__name__}: {str(e)[:150]}"
        )
        return []


def _parse_targets(data, info):
    median_target = info.get("targetMedianPrice")
    mean_target = info.get("targetMeanPrice")
    high_target = info.get("targetHighPrice")
    low_target = info.get("targetLowPrice")
    analyst_count = info.get("numberOfAnalystOpinions")

    if analyst_count and int(analyst_count) > 0:
        data["analyst_count"] = int(analyst_count)

    chosen_target = None
    if median_target and float(median_target) > 0:
        chosen_target = float(median_target)
        data["target_median"] = f"{chosen_target:.2f}"
    if mean_target and float(mean_target) > 0:
        if chosen_target is None:
            chosen_target = float(mean_target)
        data["target"] = f"{float(mean_target):.2f}"
    if chosen_target:
        data["target"] = f"{chosen_target:.2f}"

    if high_target and float(high_target) > 0:
        data["target_high"] = f"{float(high_target):.2f}"
    if low_target and float(low_target) > 0:
        data["target_low"] = f"{float(low_target):.2f}"


def _parse_recommendations(data, info):
    rating = info.get("recommendationKey")
    if rating:
        data["rating"] = rating.replace("_", " ").title()
    rec_mean = info.get("recommendationMean")
    if rec_mean is not None:
        data["rec_score"] = round(float(rec_mean), 1)


def _parse_growth_metrics(data, info):
    rev_growth = info.get("revenueGrowth")
    if rev_growth is not None:
        growth_pct = float(rev_growth) * 100
        sign = "+" if growth_pct > 0 else ""
        data["revenue_growth"] = f"{sign}{growth_pct:.1f}%"

    earn_growth = info.get("earningsGrowth")
    if earn_growth is not None:
        eg_pct = float(earn_growth) * 100
        sign = "+" if eg_pct > 0 else ""
        data["earnings_growth"] = f"{sign}{eg_pct:.1f}%"
