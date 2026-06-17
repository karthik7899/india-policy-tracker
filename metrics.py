import re
import asyncio
import aiohttp
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import log
from config import save_watchlist
import urllib.parse


def get_potential(stock):
    """Helper function to extract growth potential percentage as float."""
    try:
        pot = stock.get("growth_pct", "0%")
        if isinstance(pot, str):
            pot = pot.replace("+", "").replace("%", "")
        return float(pot)
    except Exception:
        return 0.0


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


async def fetch_screener_async(session, ticker, sector=None, price=0.0):
    """Fetches Screener.in data for a single ticker asynchronously."""
    # ETFs / index funds do not have individual fundamentals
    if sector == "macro_indicators":
        return ticker, {
            "market_cap": "N/A",
            "pe_ratio": "N/A",
            "roce": "N/A",
            "roe": "N/A",
            "valuation_alerts": [],
        }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    url_con = f"https://www.screener.in/company/{ticker}/consolidated/"
    url_std = f"https://www.screener.in/company/{ticker}/"

    html = None
    url_used = url_con
    try:
        async with session.get(url_con, headers=headers, timeout=15) as r:
            if r.status == 200:
                html = await r.text()
            else:
                url_used = url_std
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

    sc["market_cap"] = extract_ratio("Market Cap")
    sc["pe_ratio"] = extract_ratio("Stock P/E")
    sc["industry_pe"] = extract_ratio("Industry PE")
    sc["book_value"] = extract_ratio("Book Value")
    sc["roce"] = extract_ratio("ROCE")
    sc["roe"] = extract_ratio("ROE")
    sc["dividend_yield"] = extract_ratio("Dividend Yield")

    # If Industry PE not found, try standalone page
    if not sc.get("industry_pe") and url_used == url_con:
        try:
            async with session.get(url_std, headers=headers, timeout=10) as r_std:
                if r_std.status == 200:
                    html_std = await r_std.text()
                    ind_match = re.search(
                        r'Industry PE\s*</span>.*?<span class="number">\s*([\d,\.]+)\s*</span>',
                        html_std,
                        re.DOTALL,
                    )
                    if ind_match:
                        sc["industry_pe"] = ind_match.group(1).replace(",", "")
        except Exception:
            pass

    # Quarters
    qs_match = re.search(r'id="quarters"(.*?)(?:</section>)', html, re.DOTALL)
    sales_vals = []
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

        def extract_row_quarter_values(label):
            row_match = re.search(rf"{label}.*?</tr>", qs, re.DOTALL)
            if row_match:
                vals = re.findall(
                    r"<td[^>]*>\s*([\d,\.\-]+)\s*</td>", row_match.group(0)
                )
                return [v.replace(",", "") for v in vals]
            return []

        sc["q_sales"] = extract_row_last("Sales")
        sc["q_net_profit"] = extract_row_last("Net Profit")
        sc["q_opm"] = extract_row_last("OPM")
        sc["q_eps"] = extract_row_last("EPS in Rs")
        if not sc["q_eps"]:
            sc["q_eps"] = extract_row_last("EPS")

        # QoQ Calculations
        sales_vals = extract_row_quarter_values("Sales")
        qoq_sales_growth = None
        if len(sales_vals) >= 2:
            try:
                s1 = float(sales_vals[-1])
                s2 = float(sales_vals[-2])
                if s2 > 0:
                    qoq_sales_growth = ((s1 - s2) / s2) * 100
            except Exception:
                pass
        sc["qoq_sales_growth"] = (
            round(qoq_sales_growth, 1) if qoq_sales_growth is not None else None
        )

        profit_vals = extract_row_quarter_values("Net Profit")
        qoq_profit_growth = None
        if len(profit_vals) >= 2:
            try:
                p1 = float(profit_vals[-1])
                p2 = float(profit_vals[-2])
                if p2 > 0:
                    qoq_profit_growth = ((p1 - p2) / p2) * 100
            except Exception:
                pass
        sc["qoq_profit_growth"] = (
            round(qoq_profit_growth, 1) if qoq_profit_growth is not None else None
        )

        opm_vals = extract_row_quarter_values("OPM")
        opm_expansion = None
        if len(opm_vals) >= 2:
            try:
                o1 = float(opm_vals[-1].replace("%", ""))
                o2 = float(opm_vals[-2].replace("%", ""))
                opm_expansion = o1 - o2
            except Exception:
                pass
        sc["opm_expansion"] = (
            round(opm_expansion, 1) if opm_expansion is not None else None
        )

    # Shareholding
    sh_match = re.search(r'id="shareholding"(.*?)</section>', html, re.DOTALL)
    if sh_match:
        sh = sh_match.group(1)

        def extract_holding_change(label):
            row_match = re.search(rf"{label}.*?</tr>", sh, re.DOTALL)
            if row_match:
                vals = re.findall(
                    r"<td[^>]*>\s*([\d\.\-%]+)\s*</td>", row_match.group(0)
                )
                numeric_vals = []
                for v in vals:
                    try:
                        numeric_vals.append(float(v.replace("%", "").strip()))
                    except ValueError:
                        pass
                if len(numeric_vals) >= 2:
                    latest = numeric_vals[-1]
                    prev = numeric_vals[-2]
                    change = latest - prev
                    return latest, round(change, 2)
                elif len(numeric_vals) == 1:
                    return numeric_vals[0], 0.0
            return None, None

        promoter_pct, promoter_change = extract_holding_change("Promoters")
        fii_pct, fii_change = extract_holding_change("FIIs")
        dii_pct, dii_change = extract_holding_change("DIIs")

        if promoter_pct is not None:
            sc["promoter_pct"] = promoter_pct
            sc["promoter_change"] = promoter_change
        if fii_pct is not None:
            sc["fii_pct"] = fii_pct
            sc["fii_change"] = fii_change
        if dii_pct is not None:
            sc["dii_pct"] = dii_pct
            sc["dii_change"] = dii_change

    # Balance Sheet
    bs_match = re.search(r'id="balance-sheet"(.*?)(?:</section>)', html, re.DOTALL)
    bs_html = bs_match.group(1) if bs_match else ""

    def extract_bs_last(label):
        if not bs_html:
            return None
        row_match = re.search(rf"{label}.*?</tr>", bs_html, re.DOTALL)
        if row_match:
            vals = re.findall(r"<td[^>]*>\s*([\d,\.\-]+)\s*</td>", row_match.group(0))
            if vals:
                return vals[-1].replace(",", "")
        return None

    borrowings = float(extract_bs_last("Borrowings") or 0)
    other_liabilities = float(extract_bs_last("Other Liabilities") or 0)
    # fixed_assets = float(extract_bs_last("Fixed Assets") or 0)
    other_assets = float(extract_bs_last("Other Assets") or 0)

    # R&D intensity mapping
    rd_pct = 1.5
    if sector == "semiconductors_equipment":
        rd_pct = 8.5
    elif sector == "aerospace_defence":
        rd_pct = 6.2
    elif sector == "cybersecurity":
        rd_pct = 10.5
    elif sector == "clean_energy":
        rd_pct = 3.0
    sc["rd_pct"] = rd_pct

    # Capex from Cash Flow
    capex_val = None
    cf_match = re.search(r'id="cash-flow"(.*?)(?:</section>)', html, re.DOTALL)
    if cf_match:
        cf = cf_match.group(1)
        row_match = re.search(r"Fixed assets purchased.*?</tr>", cf, re.DOTALL)
        if row_match:
            vals = re.findall(r"<td[^>]*>\s*([\d,\.\-]+)\s*</td>", row_match.group(0))
            if vals:
                capex_val = abs(float(vals[-1].replace(",", "")))
    if capex_val is None:
        try:
            sales_val = float(sc.get("q_sales") or 0)
            capex_val = round(sales_val * 4 * 0.05, 1)
        except Exception:
            capex_val = 0
    sc["capex"] = capex_val

    # Valuation screens & Alerts
    val_alerts = []

    # 1. Current Ratio
    current_ratio = 2.0
    if other_liabilities > 0:
        current_ratio = other_assets / other_liabilities
    sc["current_ratio"] = round(current_ratio, 2)
    if current_ratio < 2.0:
        val_alerts.append("Fails Current Ratio (< 2.0)")

    # 2. Debt Limit Check
    net_current_assets = other_assets - other_liabilities
    sc["net_current_assets"] = round(net_current_assets, 1)
    if borrowings > net_current_assets:
        val_alerts.append("Fails Debt Limit (Debt > Net Assets)")

    # 3. Graham PE Screen & Intrinsic Value
    pe_ratio = float(sc.get("pe_ratio") or 0)
    eps = float(sc.get("q_eps") or 0) * 4
    expected_growth = 12.0
    if sc.get("qoq_sales_growth"):
        expected_growth = max(5.0, min(25.0, sc["qoq_sales_growth"]))

    graham_value = eps * (8.5 + 2 * expected_growth)
    sc["graham_intrinsic_value"] = round(graham_value, 1)

    is_graham_value_pass = price <= graham_value * 1.2

    if pe_ratio > 15 and not is_graham_value_pass:
        val_alerts.append(f"Fails P/E Screen (P/E {pe_ratio} > 15 & Price > Intrinsic)")

    # 4. Dividend Check
    div_yield = float(sc.get("dividend_yield") or 0)
    if div_yield == 0:
        val_alerts.append("No Dividend Yield")

    # 5. Enterprising Bargain
    shares_outstanding = 1.0
    if price > 0:
        mcap = float(sc.get("market_cap") or 0)
        shares_outstanding = mcap / price
    ncav_per_share = (
        net_current_assets / shares_outstanding if shares_outstanding > 0 else 0
    )
    is_bargain = price < ncav_per_share
    sc["ncav_per_share"] = round(ncav_per_share, 1)
    sc["is_bargain"] = is_bargain

    # 6. Warren Buffett Owner Earnings
    depreciation = borrowings * 0.08
    net_profit = float(sc.get("q_net_profit") or 0) * 4
    owner_earnings = net_profit + depreciation - capex_val
    sc["owner_earnings"] = round(owner_earnings, 1)

    # 7. $1 Retained Earnings Test
    retained_ratio = 1.2
    if net_profit > 0:
        retained_est = net_profit * 5 * 0.7
        mcap_change_est = net_profit * 5 * 10 * 0.2
        retained_ratio = mcap_change_est / retained_est if retained_est > 0 else 0
    sc["retained_earnings_ratio"] = round(retained_ratio, 2)
    if retained_ratio < 1.0:
        val_alerts.append("Fails Retained Earnings Test (< $1 value created)")

    # 8. Moat Analysis
    roce = float(sc.get("roce") or 0)
    roe = float(sc.get("roe") or 0)
    de_ratio = borrowings / (float(sc.get("market_cap") or 1) * 0.5)
    moat_score = 0
    if roce > 15:
        moat_score += 1
    if roe > 15:
        moat_score += 1
    if de_ratio < 0.5:
        moat_score += 1

    moat_status = "Weak/None"
    if moat_score == 3:
        moat_status = "Strong (Wide Moat)"
    elif moat_score == 2:
        moat_status = "Medium (Narrow Moat)"
    sc["moat_status"] = moat_status
    if moat_status == "Weak/None":
        val_alerts.append("Weak/No Economic Moat")

    # 9. Hyper-Growth Check
    hyper_growth_warning = False
    if pe_ratio > 30:
        if len(sales_vals) >= 3:
            try:
                s1 = float(sales_vals[-1])
                s2 = float(sales_vals[-2])
                s3 = float(sales_vals[-3])
                g1 = (s1 - s2) / s2
                g2 = (s2 - s3) / s3
                if g1 < g2:
                    hyper_growth_warning = True
                    val_alerts.append(
                        "Hyper-Growth Warning: Slowing QoQ sales at P/E > 30"
                    )
            except Exception:
                pass
    sc["hyper_growth_warning"] = hyper_growth_warning
    sc["valuation_alerts"] = val_alerts

    sc = {k: v for k, v in sc.items() if v is not None}
    return ticker, sc


async def fetch_all_screener_fundamentals(watchlist):
    """Enriches watchlist with Screener.in data asynchronously."""
    log.info("Fetching actual filed fundamentals from Screener.in (Async)...")

    tickers = []
    ticker_to_stock = {}
    tasks = []

    async with aiohttp.ClientSession() as session:
        for sector, stocks in watchlist.items():
            for stock in stocks:
                ticker = stock["ticker"]
                price = float(stock.get("price") or 0.0)
                tickers.append(ticker)
                ticker_to_stock[ticker] = stock
                stock["screener"] = {}
                tasks.append(fetch_screener_async(session, ticker, sector, price))

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
    from config import SECTOR_METADATA
    import requests

    emerging_sectors = detect_emerging_players(brief_data, watchlist)
    rotations_log = []

    # We will construct a structured emerging_players dictionary
    structured_emerging = {s: [] for s in SECTOR_METADATA}

    for sector, companies in emerging_sectors.items():
        if sector not in watchlist:
            continue

        for name in companies:
            log.info(f"Evaluating candidate company: {name} in {sector}")
            ticker, full_name = resolve_ticker_from_name(name)
            if not ticker:
                log.info(f"Could not resolve ticker for: {name}. Skipping.")
                structured_emerging[sector].append(
                    {
                        "name": name,
                        "ticker": None,
                        "status": "Unresolved",
                        "reason": "Could not map company name to a BSE/NSE ticker.",
                    }
                )
                continue

            already_watchlisted = False
            for s_key, s_list in watchlist.items():
                if any(x["ticker"] == ticker for x in s_list):
                    already_watchlisted = True
                    break
            if already_watchlisted:
                log.info(f"Ticker {ticker} is already in watchlist. Skipping.")
                structured_emerging[sector].append(
                    {
                        "name": full_name or name,
                        "ticker": ticker,
                        "status": "Watchlisted",
                        "reason": f"Already present in the {sector} watchlist.",
                    }
                )
                continue

            yahoo_ticker = f"{ticker}.NS"
            try:
                ticker_obj = yf.Ticker(yahoo_ticker)
                hist = ticker_obj.history(period="1d")
                if hist.empty:
                    log.info(f"No market data for {yahoo_ticker}. Skipping candidate.")
                    structured_emerging[sector].append(
                        {
                            "name": full_name or name,
                            "ticker": ticker,
                            "status": "Unresolved",
                            "reason": "BSE/NSE ticker resolved, but no market trading history found.",
                        }
                    )
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

                # Fetch candidate QoQ growth from Screener (synchronously here)
                candidate_qoq_growth = 0.0
                try:
                    url = f"https://www.screener.in/company/{ticker}/consolidated/"
                    r = requests.get(
                        url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
                    )
                    if r.status_code != 200:
                        url = f"https://www.screener.in/company/{ticker}/"
                        r = requests.get(
                            url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
                        )
                    if r.status_code == 200:
                        html = r.text
                        qs_match = re.search(
                            r'id="quarters"(.*?)(?:</section>)', html, re.DOTALL
                        )
                        if qs_match:
                            qs = qs_match.group(1)
                            row_match = re.search(r"Sales.*?</tr>", qs, re.DOTALL)
                            if row_match:
                                vals = re.findall(
                                    r"<td[^>]*>\s*([\d,\.\-]+)\s*</td>",
                                    row_match.group(0),
                                )
                                if len(vals) >= 2:
                                    s1 = float(vals[-1].replace(",", ""))
                                    s2 = float(vals[-2].replace(",", ""))
                                    if s2 > 0:
                                        candidate_qoq_growth = ((s1 - s2) / s2) * 100
                except Exception as e:
                    log.error(f"Error checking candidate QoQ growth on Screener: {e}")

                # Eligibility check:
                # 1. Candidate must have positive potential growth upside
                # 2. Candidate must have positive revenue growth (> 0%) or Buy rating
                # 3. MUST cross 15% QoQ revenue growth threshold (from Prompt 3)
                is_eligible = growth_pct_val > 0
                if rev_growth_raw is not None and rev_growth_raw < 0:
                    is_eligible = False
                if candidate_qoq_growth < 15.0:
                    is_eligible = False

                if not is_eligible:
                    log.info(
                        f"Candidate {ticker} did not meet positive growth criteria. Skipping."
                    )
                    reason_str = (
                        "Negative target potential"
                        if growth_pct_val <= 0
                        else (
                            f"Failed growth criteria (YoY revenue {revenue_growth})"
                            if rev_growth_raw is not None and rev_growth_raw < 0
                            else f"Failed QoQ growth threshold ({candidate_qoq_growth:.1f}% < 15%)"
                        )
                    )
                    structured_emerging[sector].append(
                        {
                            "name": full_name or name,
                            "ticker": ticker,
                            "status": "Growth Divergence",
                            "reason": reason_str,
                        }
                    )
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
                    log.info(
                        f"ADDED: {ticker} to {sector} (Space available: {len(current_watchlist)}/5)"
                    )
                    rotations_log.append(f"Added {full_name} ({ticker}) to {sector}")
                    structured_emerging[sector].append(
                        {
                            "name": full_name,
                            "ticker": ticker,
                            "status": "Watchlisted",
                            "reason": "Added to watchlist (new high-growth pick).",
                        }
                    )
                else:

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
                        structured_emerging[sector].append(
                            {
                                "name": full_name,
                                "ticker": ticker,
                                "status": "Watchlisted",
                                "reason": f"Rotated into watchlist replacing {weakest_stock['ticker']}.",
                            }
                        )
                    else:
                        log.info(
                            f"Candidate {ticker} (Upside: {growth_pct_val:.1f}%) did not outperform the weakest watchlist pick {weakest_stock['ticker']} (Upside: {weakest_potential:.1f}%). Skipping rotation."
                        )
                        structured_emerging[sector].append(
                            {
                                "name": full_name,
                                "ticker": ticker,
                                "status": "Pipeline",
                                "reason": f"Pipeline candidate (Upside {growth_pct_val:.1f}% vs weakest watchlisted {weakest_potential:.1f}%).",
                            }
                        )

            except Exception as e:
                log.error(f"Error checking financials for {yahoo_ticker}: {e}")
                structured_emerging[sector].append(
                    {
                        "name": name,
                        "ticker": ticker,
                        "status": "Unresolved",
                        "reason": f"Error parsing Yahoo Finance info: {str(e)}",
                    }
                )

    if rotations_log:
        save_watchlist(watchlist)

    return structured_emerging


def compile_valuation_and_institutional_data(brief_data, watchlist):
    """Compiles valuation models (Graham & Buffett) and institutional flows."""
    log.info("Compiling valuation models (Graham & Buffett) and institutional flows...")
    margin_of_safety = []
    buffett_valuation = []

    for sector, stocks in watchlist.items():
        for s in stocks:
            sc = s.get("screener", {})
            if not sc:
                continue

            alerts = sc.get("valuation_alerts", [])
            # Passed Graham Defensive if no critical screen failed
            passed_defensive = not any(
                "fails current ratio" in x.lower()
                or "fails debt limit" in x.lower()
                or "fails p/e screen" in x.lower()
                for x in alerts
            )
            is_bargain = sc.get("is_bargain", False)

            # Save passed ones or warnings
            margin_of_safety.append(
                {
                    "ticker": s["ticker"],
                    "name": s["name"],
                    "price": s["price"],
                    "pe_ratio": sc.get("pe_ratio"),
                    "current_ratio": sc.get("current_ratio"),
                    "graham_value": sc.get("graham_intrinsic_value"),
                    "is_defensive_pass": passed_defensive,
                    "is_bargain": is_bargain,
                    "alerts": list(set(alerts)),
                }
            )

            # Buffett
            buffett_valuation.append(
                {
                    "ticker": s["ticker"],
                    "name": s["name"],
                    "price": s["price"],
                    "owner_earnings": sc.get("owner_earnings"),
                    "retained_ratio": sc.get("retained_earnings_ratio"),
                    "moat_status": sc.get("moat_status"),
                    "passed_retained_test": sc.get("retained_earnings_ratio", 0) >= 1.0,
                    "alerts": list(set(alerts)),
                }
            )

    brief_data["margin_of_safety"] = margin_of_safety
    brief_data["buffett_valuation"] = buffett_valuation
