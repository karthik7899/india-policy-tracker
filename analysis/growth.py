from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import log
import yfinance as yf


def update_single_stock(stock, prefetched_prices=None):
    """Worker function to fetch Yahoo Finance metrics for a single stock."""
    from providers.yahoo import fetch_stock_data
    from logger import log

    if prefetched_prices is None:
        prefetched_prices = {}

    ticker = stock["ticker"]
    yahoo_ticker = f"{ticker}.NS"

    try:
        data = fetch_stock_data(yahoo_ticker)

        # BSE-only listings 404 under the NSE suffix every run; fall back to
        # the BSE symbol before giving up on the ticker.
        if data.get("price") is None:
            bse_data = fetch_stock_data(f"{ticker}.BO")
            if bse_data.get("price") is not None:
                log.info(f"{ticker}: no NSE data, using BSE listing instead.")
                data = bse_data

        # Override price if prefetched
        if (
            yahoo_ticker in prefetched_prices
            and prefetched_prices[yahoo_ticker] is not None
        ):
            data["price"] = float(prefetched_prices[yahoo_ticker])

        if data.get("price") is not None:
            stock["price"] = f"{data['price']:.2f}"

        for k, v in data.items():
            if k != "price" and v is not None:
                stock[k] = v

        if (
            "target" in stock
            and stock["target"]
            and "price" in stock
            and stock["price"]
        ):
            _calculate_growth_pct(stock, float(stock["price"]), ticker)

        return data.get("price") is not None

    except Exception as e:
        log.error(
            f"Error updating price/metrics for {yahoo_ticker}: {e}. Using static price."
        )
        return False


def _calculate_growth_pct(stock, live_price, ticker):
    target_price = float(stock.get("target", 0))
    if target_price > 0 and live_price > 0:
        growth_val = ((target_price - live_price) / live_price) * 100
        sign = "+" if growth_val > 0 else ""
        stock["growth_pct"] = f"{sign}{growth_val:.1f}%"
        log.info(
            f"Updated {ticker}: Price={live_price:.2f}, Target={target_price:.2f} ({sign}{growth_val:.1f}%)"
        )


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
    if yahoo_tickers:
        try:
            log.info("Batch downloading live prices...")
            # ⚡ Bolt Optimization: Batch fetch history for all tickers at once using yf.download.
            # This significantly reduces network overhead compared to individual requests
            # and helps prevent hitting rate limits while updating the entire watchlist.
            data = yf.download(
                yahoo_tickers,
                period="1d",
                group_by="ticker",
                threads=True,
                timeout=10,
                progress=False,
            )
            if len(yahoo_tickers) == 1:
                if (
                    not data.empty
                    and "Close" in data
                    and not data["Close"].isna().all()
                ):
                    prefetched_prices[yahoo_tickers[0]] = data["Close"].iloc[-1]
            else:
                for ticker in yahoo_tickers:
                    if (
                        ticker in data
                        and not data[ticker].empty
                        and "Close" in data[ticker]
                        and not data[ticker]["Close"].isna().all()
                    ):
                        prefetched_prices[ticker] = data[ticker]["Close"].iloc[-1]
        except Exception as e:
            log.error(f"Error during batch price download: {e}")

    # No custom session for yf.Ticker calls — see get_cached_ticker in
    # providers/yahoo.py for why that would be harmful.
    updated = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(update_single_stock, stock, prefetched_prices)
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
