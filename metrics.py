import re
import asyncio
import aiohttp
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import log
from config import save_watchlist
import urllib.parse


def update_single_stock(stock):
    """Worker function to fetch Yahoo Finance metrics for a single stock."""
    ticker = stock["ticker"]
    yahoo_ticker = f"{ticker}.NS"

    # Set default values for new keys
    stock["rating"] = "N/A"
    stock["revenue_growth"] = None
    stock["earnings_growth"] = None
    stock["analyst_count"] = None
    stock["target_median"] = None
    stock["target_high"] = None
    stock["target_low"] = None
    stock["rec_score"] = None

    try:
        ticker_obj = yf.Ticker(yahoo_ticker)

        hist = ticker_obj.history(period="1d")
        if not hist.empty:
            live_price = float(hist["Close"].iloc[-1])
            stock["price"] = f"{live_price:.2f}"
        else:
            live_price = float(stock["price"])
            log.warning(f"No close history for {yahoo_ticker}. Using static price.")

        info = ticker_obj.info
        if info:
            median_target = info.get("targetMedianPrice")
            mean_target = info.get("targetMeanPrice")
            high_target = info.get("targetHighPrice")
            low_target = info.get("targetLowPrice")
            analyst_count = info.get("numberOfAnalystOpinions")

            if analyst_count and int(analyst_count) > 0:
                stock["analyst_count"] = int(analyst_count)

            chosen_target = None
            if median_target and float(median_target) > 0:
                chosen_target = float(median_target)
                stock["target_median"] = f"{chosen_target:.2f}"
            if mean_target and float(mean_target) > 0:
                if chosen_target is None:
                    chosen_target = float(mean_target)
                stock["target"] = f"{float(mean_target):.2f}"
            if chosen_target:
                stock["target"] = f"{chosen_target:.2f}"

            if high_target and float(high_target) > 0:
                stock["target_high"] = f"{float(high_target):.2f}"
            if low_target and float(low_target) > 0:
                stock["target_low"] = f"{float(low_target):.2f}"

            rating = info.get("recommendationKey")
            if rating:
                stock["rating"] = rating.replace("_", " ").title()
            rec_mean = info.get("recommendationMean")
            if rec_mean is not None:
                stock["rec_score"] = round(float(rec_mean), 1)

            rev_growth = info.get("revenueGrowth")
            if rev_growth is not None:
                growth_pct = float(rev_growth) * 100
                sign = "+" if growth_pct > 0 else ""
                stock["revenue_growth"] = f"{sign}{growth_pct:.1f}%"

            earn_growth = info.get("earningsGrowth")
            if earn_growth is not None:
                eg_pct = float(earn_growth) * 100
                sign = "+" if eg_pct > 0 else ""
                stock["earnings_growth"] = f"{sign}{eg_pct:.1f}%"

        target_price = float(stock["target"])
        if live_price > 0:
            growth_val = ((target_price - live_price) / live_price) * 100
            sign = "+" if growth_val > 0 else ""
            stock["growth_pct"] = f"{sign}{growth_val:.1f}%"

            log.info(
                f"Updated {ticker}: Price={live_price:.2f}, Target={target_price:.2f} ({sign}{growth_val:.1f}%)"
            )

    except Exception as e:
        log.error(
            f"Error updating price/metrics for {yahoo_ticker}: {e}. Using static price."
        )


def update_live_stock_prices(watchlist):
    """Updates watchlist with live prices from Yahoo Finance."""
    log.info(
        "Fetching live stock prices and metrics from Yahoo Finance (Parallelized)..."
    )
    all_stocks = []
    for sector, stocks in watchlist.items():
        all_stocks.extend(stocks)

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(update_single_stock, stock) for stock in all_stocks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log.error(f"Error in parallel stock update task: {e}")


async def fetch_screener_async(session, ticker):
    """Fetches Screener.in data for a single ticker asynchronously."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url_con = f"https://www.screener.in/company/{ticker}/consolidated/"
    url_std = f"https://www.screener.in/company/{ticker}/"

    html = None
    try:
        async with session.get(url_con, headers=headers, timeout=15) as r:
            if r.status == 200:
                html = await r.text()
            else:
                async with session.get(url_std, headers=headers, timeout=15) as r2:
                    if r2.status == 200:
                        html = await r2.text()
    except Exception as e:
        log.error(f"{ticker}: Screener.in request error: {e}")
        return ticker, {}

    if not html:
        return ticker, {}

    sc = {}

    def extract_ratio(label):
        pattern = rf'{label}\s*</span>.*?<span class="number">\s*([\d,\.]+)\s*</span>'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            return match.group(1).replace(",", "")
        return None

    sc["pe_ratio"] = extract_ratio("Stock P/E")
    sc["industry_pe"] = extract_ratio("Industry PE")
    sc["roce"] = extract_ratio("ROCE")
    sc["roe"] = extract_ratio("ROE")

    qs_match = re.search(r'id="quarters"(.*?)(?:</section>)', html, re.DOTALL)
    if qs_match:
        qs = qs_match.group(1)
        q_headers = re.findall(r'data-date-key="[^"]*">\s*(\w+ \d{4})', qs)
        if q_headers:
            sc["latest_quarter"] = q_headers[-1]

        def extract_row_last(label):
            row_match = re.search(rf"{label}.*?</tr>", qs, re.DOTALL)
            if row_match:
                vals = re.findall(
                    r"<td[^>]*>\s*([\d,\.\-]+)\s*</td>", row_match.group(0)
                )
                if vals:
                    return vals[-1].replace(",", "")
            return None

        sc["q_sales"] = extract_row_last("Sales")
        sc["q_net_profit"] = extract_row_last("Net Profit")

    sh_match = re.search(r'id="shareholding"(.*?)(?:</section>|id=")', html, re.DOTALL)
    if sh_match:
        sh = sh_match.group(1)

        def extract_holding(label):
            match = re.search(rf"{label}.*?<td[^>]*>\s*([\d\.]+)\s*%", sh, re.DOTALL)
            return match.group(1) if match else None

        sc["promoter_pct"] = extract_holding("Promoters")
        sc["fii_pct"] = extract_holding("FIIs")

    sc = {k: v for k, v in sc.items() if v is not None}
    return ticker, sc


async def fetch_all_screener_fundamentals(watchlist):
    """Enriches watchlist with Screener.in data asynchronously."""
    log.info("Fetching actual filed fundamentals from Screener.in (Async)...")

    tickers = []
    ticker_to_stock = {}
    for sector, stocks in watchlist.items():
        for stock in stocks:
            tickers.append(stock["ticker"])
            ticker_to_stock[stock["ticker"]] = stock
            stock["screener"] = {}

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_screener_async(session, ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)

    for ticker, sc_data in results:
        if sc_data:
            ticker_to_stock[ticker]["screener"] = sc_data
            log.info(
                f"{ticker}: Screener data loaded (PE={sc_data.get('pe_ratio', 'N/A')})"
            )


def detect_emerging_players(brief_data, watchlist):
    """Scans aggregated news titles for corporate names not currently in the watchlist."""
    log.info("Scanning headlines for emerging players...")
    emerging_players = {}

    existing_ids = set()
    for sector, stocks in watchlist.items():
        for s in stocks:
            existing_ids.add(s["ticker"].lower())
            existing_ids.add(s["name"].lower())
            for part in s["name"].split():
                if len(part) > 3:
                    existing_ids.add(part.lower())

    ignored = {
        "india",
        "delhi",
        "mumbai",
        "pib",
        "union",
        "minister",
        "cabinet",
        "government",
        "ministry",
        "national",
        "state",
        "budget",
        "digital",
        "system",
    }
    corp_pattern = re.compile(
        r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+(?:Ltd|Limited|Corp|Corporation|Technologies|Enterprises|Solutions|Infrastructure)\b"
    )

    for sector, news_items in brief_data.items():
        if sector == "emerging_players":
            continue
        detected = []
        for item in news_items:
            title = item["title"]
            for m in corp_pattern.finditer(title):
                captured = m.group(1)
                full = m.group(0)
                captured_lower = captured.lower()
                if (
                    captured_lower not in existing_ids
                    and captured_lower not in ignored
                    and len(captured) >= 3
                ):
                    if full not in detected:
                        detected.append(full)
                        log.info(f"Detected emerging player in {sector}: {full}")
        if detected:
            emerging_players[sector] = detected

    return emerging_players


def resolve_ticker_from_name(company_name):
    import requests

    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(company_name)}&quotesCount=5"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            quotes = data.get("quotes", [])
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".NS"):
                    return (
                        symbol.split(".")[0],
                        q.get("longname") or q.get("shortname") or company_name,
                    )
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".BO"):
                    return (
                        symbol.split(".")[0],
                        q.get("longname") or q.get("shortname") or company_name,
                    )
    except Exception as e:
        log.error(f"Error resolving ticker for {company_name}: {e}")
    return None, None


def auto_curate_watchlist(brief_data, watchlist):
    """Discovers emerging competitors and rotates underperforming stocks."""
    log.info("Starting automated watchlist curation and rotation cycle...")
    emerging_sectors = detect_emerging_players(brief_data, watchlist)

    rotations_log = []

    for sector, companies in emerging_sectors.items():
        if sector not in watchlist:
            continue

        for name in companies:
            log.info(f"Evaluating candidate company: {name} in {sector}")
            ticker, full_name = resolve_ticker_from_name(name)
            if not ticker:
                continue

            already_watchlisted = False
            for s_key, s_list in watchlist.items():
                if any(x["ticker"] == ticker for x in s_list):
                    already_watchlisted = True
                    break
            if already_watchlisted:
                continue

            yahoo_ticker = f"{ticker}.NS"
            try:
                ticker_obj = yf.Ticker(yahoo_ticker)
                hist = ticker_obj.history(period="1d")
                if hist.empty:
                    continue

                live_price = float(hist["Close"].iloc[-1])
                info = ticker_obj.info or {}

                consensus_target = info.get("targetMeanPrice")
                if consensus_target and float(consensus_target) > 0:
                    target_price = float(consensus_target)
                else:
                    target_price = live_price * 1.25

                growth_pct_val = ((target_price - live_price) / live_price) * 100
                rating = info.get("recommendationKey", "N/A").replace("_", " ").title()

                rev_growth_raw = info.get("revenueGrowth")
                revenue_growth = (
                    f"{float(rev_growth_raw) * 100:.1f}%"
                    if rev_growth_raw is not None
                    else None
                )

                is_eligible = growth_pct_val > 0
                if rev_growth_raw is not None and rev_growth_raw < 0:
                    is_eligible = False

                if not is_eligible:
                    continue

                related_headline = f"Policy tailwinds in the {sector} segment."
                for item in brief_data.get(sector, []):
                    if name.lower() in item["title"].lower():
                        related_headline = item["title"]
                        break

                candidate_stock = {
                    "ticker": ticker,
                    "name": full_name,
                    "price": f"{live_price:.2f}",
                    "target": f"{target_price:.2f}",
                    "growth_pct": f"{growth_pct_val:.1f}%",
                    "catalyst": f"Auto-discovered via media radar. Catalyst: {related_headline}",
                    "rating": rating,
                    "revenue_growth": revenue_growth,
                }

                current_watchlist = watchlist[sector]
                if len(current_watchlist) < 5:
                    current_watchlist.append(candidate_stock)
                    log.info(f"ADDED: {ticker} to {sector}")
                    rotations_log.append(f"Added {full_name} ({ticker}) to {sector}")
                else:

                    def get_potential(stock):
                        try:
                            return float(stock["growth_pct"].replace("%", ""))
                        except Exception:
                            return 0.0

                    sorted_watchlist = sorted(current_watchlist, key=get_potential)
                    weakest_stock = sorted_watchlist[0]
                    weakest_potential = get_potential(weakest_stock)

                    if growth_pct_val > weakest_potential:
                        watchlist[sector] = [
                            x
                            for x in current_watchlist
                            if x["ticker"] != weakest_stock["ticker"]
                        ]
                        watchlist[sector].append(candidate_stock)
                        log.info(
                            f"ROTATED: Replaced {weakest_stock['ticker']} with {ticker}"
                        )
                        rotations_log.append(
                            f"Rotated {weakest_stock['name']} out for {full_name} in {sector}"
                        )

            except Exception as e:
                log.error(f"Error checking financials for {yahoo_ticker}: {e}")

    if rotations_log:
        save_watchlist(watchlist)
        return emerging_sectors
    return emerging_sectors
