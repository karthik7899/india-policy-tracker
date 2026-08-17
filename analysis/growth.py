from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import log
from utils import to_float
import yfinance as yf

# Where turnover waits between the price fetch and the Screener rebuild. A
# sibling of "screener" rather than a field inside it, because only that one
# key is replaced.
_LIQUIDITY_STAGING_KEY = "_liquidity_pending"


def apply_liquidity(watchlist):
    """Merge staged turnover into each holding's screener dict.

    Must run *after* the Screener fetch. Scoring reads these fields off
    ``CompanyFinancials``, which is built from ``screener``, so turnover has to
    live there in the end -- it just cannot be put there before the rebuild
    that would erase it.

    Returns the number of holdings that received turnover, so the caller can
    log coverage instead of assuming it worked. The first production run of
    this feature attached turnover to nothing and reported nothing, which is
    the failure this return value exists to make visible.
    """
    applied = 0
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            staged = stock.pop(_LIQUIDITY_STAGING_KEY, None)
            if not staged:
                continue
            screener = stock.get("screener")
            if not isinstance(screener, dict):
                screener = {}
                stock["screener"] = screener
            screener.update(staged)
            applied += 1
    return applied


def update_single_stock(stock, prefetched_prices=None, prefetched_liquidity=None):
    """Worker function to fetch Yahoo Finance metrics for a single stock."""
    from providers.yahoo import fetch_stock_data
    from logger import log

    if prefetched_prices is None:
        prefetched_prices = {}
    if prefetched_liquidity is None:
        prefetched_liquidity = {}

    ticker = stock["ticker"]
    yahoo_ticker = f"{ticker}.NS"

    try:
        # ⚡ Bolt Optimization: Skip redundant API calls to Yahoo Finance
        # if the price was already batch-fetched via yf.download
        has_prefetched = (
            yahoo_ticker in prefetched_prices
            and prefetched_prices[yahoo_ticker] is not None
        )

        data = fetch_stock_data(yahoo_ticker, fetch_price=not has_prefetched)

        # BSE-only listings 404 under the NSE suffix every run; fall back to
        # the BSE symbol before giving up on the ticker.
        if data.get("price") is None and not has_prefetched:
            bse_data = fetch_stock_data(f"{ticker}.BO")
            if bse_data.get("price") is not None:
                log.info(f"{ticker}: no NSE data, using BSE listing instead.")
                data = bse_data

        # Override price if prefetched
        if has_prefetched:
            data["price"] = float(prefetched_prices[yahoo_ticker])

        if data.get("price") is not None:
            stock["price"] = f"{data['price']:.2f}"

        for k, v in data.items():
            if k != "price" and v is not None:
                stock[k] = v

        # Turnover rides on the same batch download as the price, so it is
        # computed here rather than costing a second round trip per holding.
        #
        # It is staged on a sibling key rather than written into ``screener``
        # directly, because the Screener fetch that runs next replaces that
        # dict wholesale (providers/screener.py assigns ``stock["screener"] =
        # sc_data`). Writing it there produced turnover for all 67 holdings
        # and then silently discarded every one of them. apply_liquidity()
        # merges this in once the rebuild has happened.
        #
        # Merged rather than assigned, because turnover is no longer the only
        # thing staged here: the 52-week range is written to the same key
        # before this runs, and a plain assignment discarded all 69 of them on
        # the first live run. That is the identical failure described above,
        # one level down -- last writer wins, silently.
        liquidity = prefetched_liquidity.get(yahoo_ticker)
        if liquidity:
            stock.setdefault(_LIQUIDITY_STAGING_KEY, {}).update(liquidity)

        live_price = to_float(stock.get("price"))
        if to_float(stock.get("target")) is not None and live_price is not None:
            _calculate_growth_pct(stock, live_price, ticker)

        return data.get("price") is not None

    except Exception as e:
        log.error(
            f"Error updating price/metrics for {yahoo_ticker}: {e}. Using static price."
        )
        return False


def _calculate_growth_pct(stock, live_price, ticker):
    target_price = to_float(stock.get("target")) or 0.0
    if target_price > 0 and live_price > 0:
        growth_val = ((target_price - live_price) / live_price) * 100
        sign = "+" if growth_val > 0 else ""
        stock["growth_pct"] = f"{sign}{growth_val:.1f}%"
        log.info(
            f"Updated {ticker}: Price={live_price:.2f}, Target={target_price:.2f} ({sign}{growth_val:.1f}%)"
        )


def _liquidity_from_frame(frame):
    """Turnover assessment from one ticker's OHLCV frame, or None.

    Isolated so a malformed frame for a single ticker cannot take down the
    whole batch -- these arrive from a third party and a missing Volume
    column on one obscure listing must not cost the other sixty-four their
    prices.
    """
    from analysis.liquidity import assess

    try:
        if "Volume" not in frame:
            return None
        closes = frame["Close"].tolist()
        volumes = frame["Volume"].tolist()
        return assess(closes, volumes)
    except Exception as e:
        log.error(f"Liquidity computation failed for a ticker frame: {e}")
        return None


def _range_from_frame(frame):
    """52-week high, low, and where the last close sits between them.

    ``pct_above_low`` is the figure the pledge tracker reads: a promoter who
    has pledged shares is squeezed by a falling price, so proximity to the
    low is what converts a standing pledge into a live risk. Returns None
    rather than a partial dict, because a range missing one end is not a
    range and a caller that got one would be comparing against nothing.
    """
    import math

    try:
        if frame is None or "Close" not in frame:
            return None
        closes = frame["Close"].dropna()
        if closes.empty:
            return None
        low, high, last = (
            float(closes.min()),
            float(closes.max()),
            float(closes.iloc[-1]),
        )
        if any(math.isnan(v) for v in (low, high, last)) or low <= 0:
            return None
        return {
            "week52_low": round(low, 2),
            "week52_high": round(high, 2),
            "pct_above_low": round((last - low) / low * 100, 2),
        }
    except Exception as e:
        log.error(f"52-week range computation failed for a ticker frame: {e}")
        return None


def update_live_stock_prices(watchlist):
    """Updates watchlist with live prices from Yahoo Finance.

    Returns a freshness dict {"updated": n, "total": m} so downstream
    consumers (email, dashboard) can surface how much of the watchlist
    actually got live data instead of silently presenting stale prices.
    """
    log.info(
        "Fetching live stock prices and metrics from Yahoo Finance (Parallelized)..."
    )
    all_stocks = []
    yahoo_tickers = []
    for sector, stocks in watchlist.items():
        for stock in stocks:
            all_stocks.append(stock)
            yahoo_tickers.append(f"{stock['ticker']}.NS")

    prefetched_prices = {}
    prefetched_liquidity = {}
    if yahoo_tickers:
        try:
            log.info("Batch downloading live prices...")
            # ⚡ Bolt Optimization: Batch fetch history for all tickers at once using yf.download.
            # This significantly reduces network overhead compared to individual requests
            # and helps prevent hitting rate limits while updating the entire watchlist.
            #
            # The window is a month rather than a day because the same response
            # carries the volume series that turnover is computed from. One
            # request answers both "what is it worth" and "can it be traded";
            # the latest close is still the last row.
            data = yf.download(
                yahoo_tickers,
                period="1mo",
                group_by="ticker",
                threads=True,
                timeout=15,
                progress=False,
            )
            if len(yahoo_tickers) == 1:
                if (
                    not data.empty
                    and "Close" in data
                    and not data["Close"].isna().all()
                ):
                    prefetched_prices[yahoo_tickers[0]] = (
                        data["Close"].dropna().iloc[-1]
                    )
                    prefetched_liquidity[yahoo_tickers[0]] = _liquidity_from_frame(data)
            else:
                for ticker in yahoo_tickers:
                    if (
                        ticker in data
                        and not data[ticker].empty
                        and "Close" in data[ticker]
                        and not data[ticker]["Close"].isna().all()
                    ):
                        closes = data[ticker]["Close"].dropna()
                        prefetched_prices[ticker] = closes.iloc[-1]
                        prefetched_liquidity[ticker] = _liquidity_from_frame(
                            data[ticker]
                        )
        except Exception as e:
            log.error(f"Error during batch price download: {e}")

    # 52-week range, for the pledge tracker's "near its low" leg. Fetched as
    # weekly bars rather than by lengthening the month-long download above:
    # that response also feeds turnover, which wants recent daily volume, and
    # 52 weekly rows answer "where in its range is this" just as well as 250
    # daily ones at a fraction of the payload.
    if yahoo_tickers:
        try:
            year = yf.download(
                yahoo_tickers,
                period="1y",
                interval="1wk",
                group_by="ticker",
                threads=True,
                timeout=20,
                progress=False,
            )
            ranged = 0
            for stock in all_stocks:
                symbol = f"{stock['ticker']}.NS"
                staged = _range_from_frame(
                    year[symbol]
                    if (len(yahoo_tickers) > 1 and symbol in year)
                    else (year if len(yahoo_tickers) == 1 else None)
                )
                if staged:
                    # Same staging key discipline as turnover: written to the
                    # stock, merged into screener after the Screener rebuild
                    # that would otherwise erase it.
                    stock.setdefault(_LIQUIDITY_STAGING_KEY, {}).update(staged)
                    ranged += 1
            log.info(f"52-week range: {ranged}/{len(all_stocks)} holdings priced.")
        except Exception as e:
            log.warning(f"52-week range download failed safely: {e!r}")

    # No custom session for yf.Ticker calls — see get_cached_ticker in
    # providers/yahoo.py for why that would be harmful.
    updated = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(
                update_single_stock, stock, prefetched_prices, prefetched_liquidity
            )
            for stock in all_stocks
        ]
        for future in as_completed(futures):
            try:
                if future.result():
                    updated += 1
            except Exception as e:
                log.error(f"Error in parallel stock update task: {e}")

    total = len(all_stocks)
    log.info(f"Live price update complete: {updated}/{total} stocks refreshed.")
    return {"updated": updated, "total": total}
