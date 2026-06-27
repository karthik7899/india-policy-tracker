import yfinance as yf
from logger import log

_TICKER_CACHE = {}

def get_cached_ticker(yahoo_ticker, session=None):
    """Retrieves a cached yf.Ticker object for the pipeline run."""
    if yahoo_ticker not in _TICKER_CACHE:
        _TICKER_CACHE[yahoo_ticker] = yf.Ticker(yahoo_ticker, session=session)
    return _TICKER_CACHE[yahoo_ticker]

def fetch_stock_data(yahoo_ticker, session=None, timeout=10):
    """
    Fetches stock data from Yahoo Finance and normalizes the fields.
    Returns a dictionary of normalized metrics.
    """
    ticker_obj = get_cached_ticker(yahoo_ticker, session=session)
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
        "rec_score": None
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
        
    return data

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
