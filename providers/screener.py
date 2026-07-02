import aiohttp
import asyncio
from bs4 import BeautifulSoup
from logger import log
from analysis.parsing import extract_row_values, calculate_trend, calculate_growth
from utils import fetch_text_async


async def fetch_screener_async(session, ticker, sector, price):
    # ETFs / index funds do not have individual fundamentals
    if sector == "macro_indicators":
        return (
            ticker,
            {
                "market_cap": "N/A",
                "pe_ratio": "N/A",
                "roce": "N/A",
                "roe": "N/A",
            },
            None,
        )

    url = f"https://www.screener.in/company/{ticker}/consolidated/"
    sc = {}
    try:
        status, text = await fetch_text_async(session, url)
        if not text:
            log.error(f"{ticker}: Screener.in empty response")
            return ticker, None, None
    except Exception as e:
        log.error(f"{ticker}: Screener.in exception: {e}")
        return ticker, None, None
    soup = BeautifulSoup(text, "html.parser")

    # Screener's warehouse id enables the peers API (structured competitor list).
    warehouse_el = soup.find(attrs={"data-warehouse-id": True})
    warehouse_id = warehouse_el.get("data-warehouse-id") if warehouse_el else None

    # 1. Top Ratios Extract
    ratios_div = soup.find("div", class_="company-ratios")
    if ratios_div:
        for li in ratios_div.find_all("li"):
            name_span = li.find("span", class_="name")
            val_span = li.find("span", class_="number")
            if name_span and val_span:
                name = name_span.get_text(strip=True).lower()
                val = val_span.get_text(strip=True).replace(",", "")
                try:
                    num = float(val)
                    if "market cap" in name:
                        sc["market_cap"] = num
                    elif "current price" in name:
                        sc["current_price"] = num
                    elif "stock p/e" in name:
                        sc["pe_ratio"] = num
                    elif "roce" in name:
                        sc["roce"] = num
                    elif "roe" in name:
                        sc["roe"] = num
                    elif "debt to equity" in name:
                        sc["debt_to_equity"] = num
                    elif "dividend yield" in name:
                        sc["dividend_yield"] = num
                except ValueError:
                    pass

    # 2. Quarterly Results
    q_sales = extract_row_values(soup, "quarters", "Sales")
    if q_sales:
        sc["q_sales"] = q_sales[-1]
        if len(q_sales) >= 2:
            sc["qoq_sales_growth"] = calculate_growth(q_sales[-2], q_sales[-1])
        sc["quarterly_revenue_growth"] = calculate_trend(q_sales, 4)
        # Full trailing series (up to 8 quarters) for peer-group market
        # share estimation in analysis/market_share.py.
        sc["sales_trend"] = q_sales[-8:]

    q_opm = extract_row_values(soup, "quarters", "OPM")
    if q_opm:
        sc["q_opm"] = q_opm[-1]
        sc["quarterly_ebitda_margin"] = calculate_trend(q_opm, 4)
        if len(q_opm) >= 2:
            sc["opm_expansion"] = round(q_opm[-1] - q_opm[-2], 1)

    q_eps = extract_row_values(soup, "quarters", "EPS")
    if q_eps:
        sc["q_eps"] = q_eps[-1]

    q_net_profit = extract_row_values(soup, "quarters", "Net Profit")
    if q_net_profit:
        sc["q_net_profit"] = q_net_profit[-1]

    # 3. Profit & Loss (Annual OPM Trend)
    a_opm = extract_row_values(soup, "profit-loss", "OPM")
    if a_opm:
        sc["operating_margin_trend"] = calculate_trend(a_opm, 5)

    # 4. Balance Sheet (Debt Trend)
    borrowings = extract_row_values(soup, "balance-sheet", "Borrowings")
    if borrowings:
        sc["debt_trend"] = calculate_trend(borrowings, 5)
        current_borrowings = borrowings[-1]
    else:
        current_borrowings = 0

    other_liabilities_list = extract_row_values(
        soup, "balance-sheet", "Other Liabilities"
    )
    other_liabilities = other_liabilities_list[-1] if other_liabilities_list else 0

    other_assets_list = extract_row_values(soup, "balance-sheet", "Other Assets")
    other_assets = other_assets_list[-1] if other_assets_list else 0

    # 5. Cash Flow (Capex & Operating Cash Flow Trend)
    cfo = extract_row_values(soup, "cash-flow", "Cash from Operating Activity")
    if cfo:
        sc["cash_flow_trend"] = calculate_trend(cfo, 5)

    capex = extract_row_values(soup, "cash-flow", "Fixed assets purchased")
    if capex:
        sc["capex"] = abs(capex[-1])
    else:
        # Fallback capex estimate
        sales_val = sc.get("q_sales", 0)
        sc["capex"] = round(sales_val * 4 * 0.05, 1)

    # R&D Expenditure (from P&L if present)
    # Usually Screener lists this as "R&D" or inside expenses schedule, but it's rarely a top-level row.
    rd_vals = extract_row_values(soup, "profit-loss", "R&D") or extract_row_values(
        soup, "profit-loss", "Research"
    )
    if rd_vals:
        sc["rd_expenditure"] = rd_vals[-1]
    else:
        # Fallback R&D intensity mapping
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

    # 6. Ratios (ROCE Trend)
    roce_trend = extract_row_values(soup, "ratios", "ROCE")
    if roce_trend:
        sc["roce_trend"] = calculate_trend(roce_trend, 5)

    # 7. Shareholding
    promoters = extract_row_values(soup, "shareholding", "Promoters")
    if promoters:
        sc["promoter_pct"] = promoters[-1]
        if len(promoters) >= 2:
            sc["promoter_change"] = round(promoters[-1] - promoters[-2], 2)

    fiis = extract_row_values(soup, "shareholding", "FIIs")
    if fiis:
        sc["fii_pct"] = fiis[-1]
        if len(fiis) >= 2:
            sc["fii_change"] = round(fiis[-1] - fiis[-2], 2)

    diis = extract_row_values(soup, "shareholding", "DIIs")
    if diis:
        sc["dii_pct"] = diis[-1]
        if len(diis) >= 2:
            sc["dii_change"] = round(diis[-1] - diis[-2], 2)

    sc = {k: v for k, v in sc.items() if v is not None}
    return ticker, sc, warehouse_id


def parse_peer_table(html, exclude_tickers):
    """Parses Screener's peers-API HTML fragment into competitor candidates.

    The fragment is a table whose header names the columns; we locate the
    Name, Mar Cap and quarterly Sales-variation columns by header text so a
    column being added or reordered upstream doesn't silently corrupt values.
    Returns a list of {name, ticker, sales_var_pct, market_cap} dicts for
    companies not already tracked.
    """
    candidates = []
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return candidates

    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    name_idx = sales_var_idx = mcap_idx = None
    for i, h in enumerate(headers):
        if h.startswith("name"):
            name_idx = i
        elif "sales var" in h:
            sales_var_idx = i
        elif "mar cap" in h or "market cap" in h:
            mcap_idx = i
    if name_idx is None:
        return candidates

    def _cell_float(cells, idx):
        if idx is None or idx >= len(cells):
            return None
        raw = cells[idx].get_text(strip=True).replace(",", "").replace("%", "")
        try:
            return float(raw)
        except ValueError:
            return None

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) <= name_idx:
            continue
        link = cells[name_idx].find("a")
        if not link:
            continue
        name = link.get_text(strip=True)
        href = link.get("href", "")
        parts = [p for p in href.split("/") if p]
        peer_ticker = parts[1] if len(parts) >= 2 and parts[0] == "company" else None
        if not name or not peer_ticker:
            continue
        if peer_ticker.upper() in exclude_tickers:
            continue
        candidates.append(
            {
                "name": name,
                "ticker": peer_ticker.upper(),
                "sales_var_pct": _cell_float(cells, sales_var_idx),
                "market_cap": _cell_float(cells, mcap_idx),
            }
        )
    return candidates


async def fetch_peers_async(session, ticker, warehouse_id, exclude_tickers):
    """Fetches Screener's peer-comparison table for one company.

    This is a structured competitor-discovery channel that does not depend on
    news headlines: Screener maintains the industry peer set itself, and each
    row arrives with quarterly sales variation attached, so candidates can be
    growth-screened immediately. Degrades to an empty list on any failure.
    """
    url = f"https://www.screener.in/api/company/{warehouse_id}/peers/"
    try:
        status, text = await fetch_text_async(session, url)
        if not text:
            return ticker, []
        return ticker, parse_peer_table(text, exclude_tickers)
    except Exception as e:
        log.error(f"{ticker}: Screener peers fetch failed: {e}")
        return ticker, []


async def fetch_all_screener_fundamentals(watchlist):
    """Loads Screener fundamentals into each stock and discovers peer competitors.

    Returns {sector: [candidate, ...]} of Screener-listed industry peers that
    are not in the watchlist — a competitor-discovery channel independent of
    news headlines. Empty dict when peer data is unavailable.
    """
    log.info("Fetching actual filed fundamentals from Screener.in (Async)...")
    ticker_to_stock = {}
    ticker_to_sector = {}
    tasks = []

    watchlist_tickers = {
        str(stock["ticker"]).upper()
        for stocks in watchlist.values()
        for stock in stocks
    }

    async with aiohttp.ClientSession() as session:
        for sector, stocks in watchlist.items():
            for stock in stocks:
                ticker = stock["ticker"]
                price = float(stock.get("price") or 0.0)
                ticker_to_stock[ticker] = stock
                ticker_to_sector[ticker] = sector
                stock["screener"] = {}
                tasks.append(fetch_screener_async(session, ticker, sector, price))

        results = await asyncio.gather(*tasks)

        peer_tasks = []
        for ticker, sc_data, warehouse_id in results:
            if sc_data:
                ticker_to_stock[ticker]["screener"] = sc_data
                log.info(
                    f"{ticker}: Screener data loaded (PE={sc_data.get('pe_ratio', 'N/A')})"
                )
            if warehouse_id:
                peer_tasks.append(
                    fetch_peers_async(session, ticker, warehouse_id, watchlist_tickers)
                )

        peer_results = await asyncio.gather(*peer_tasks) if peer_tasks else []

    peer_competitors = {}
    for ticker, candidates in peer_results:
        sector = ticker_to_sector.get(ticker)
        if not sector or not candidates:
            continue
        bucket = peer_competitors.setdefault(sector, [])
        seen = {c["ticker"] for c in bucket}
        for cand in candidates:
            if cand["ticker"] not in seen:
                seen.add(cand["ticker"])
                bucket.append(cand)

    if peer_competitors:
        found = sum(len(v) for v in peer_competitors.values())
        log.info(f"Peer radar: {found} non-watchlist competitors discovered.")
    return peer_competitors
