import aiohttp
import asyncio
from bs4 import BeautifulSoup
from logger import log
from analysis.parsing import extract_row_values, calculate_trend, calculate_growth
from utils import TransientNetworkError, fetch_text_async, retry_network


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
    # lxml rather than html.parser, for correctness before speed. On the
    # malformed markup scrapers actually meet, html.parser mis-recovers in ways
    # that silently fabricate numbers: an unclosed <td> made it fuse the cells
    # "100" and "200" into a single value of 100200, and an unclosed <tr> let
    # the following row's figures bleed into the row above. lxml recovers both
    # correctly. See tests/test_html_parsing.py::TestParserRecovery.
    soup = BeautifulSoup(text, "lxml")

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
        # The full quarterly EPS series, so earnings can be summed over a
        # trailing year. Annualizing a single quarter (q_eps * 4) reads a
        # seasonal peak or trough as the run rate — the March-quarter skew in
        # Indian capital-goods and defence names roughly doubled it.
        sc["eps_trend"] = q_eps[-8:]
        if len(q_eps) >= 4:
            sc["ttm_eps"] = round(sum(q_eps[-4:]), 2)

    q_net_profit = extract_row_values(soup, "quarters", "Net Profit")
    if q_net_profit:
        sc["q_net_profit"] = q_net_profit[-1]

    # 3. Profit & Loss (Annual OPM Trend)
    a_opm = extract_row_values(soup, "profit-loss", "OPM")
    if a_opm:
        sc["operating_margin_trend"] = calculate_trend(a_opm, 5)

    # Annual revenue is the only series long enough to carry a real multi-year
    # CAGR — the quarterly table tops out at 8 quarters. Annual periods are
    # also seasonality-free by construction (analysis/sector_growth.py).
    a_sales = extract_row_values(soup, "profit-loss", "Sales")
    if a_sales:
        sc["annual_sales_trend"] = a_sales[-6:]

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

    # Pledged promoter holding. Screener prints this row only for companies
    # that have any, so an absent row is the common and correct case -- but it
    # is indistinguishable from a row we failed to match, which is why nothing
    # is written when the lookup comes back empty. A holding with no
    # pledged_pct key reads downstream as "not disclosed"; writing 0.0 here
    # would assert an all-clear this parser has not earned.
    #
    # The label is matched loosely because the exact wording on the page could
    # not be checked from the build sandbox (Screener refuses the connection
    # there); "Pledged percentage" is the observed form, and the alternatives
    # cost nothing to accept.
    pledged = extract_row_values(soup, "shareholding", r"Pledg")
    if pledged:
        sc["pledged_pct"] = pledged[-1]
        if len(pledged) >= 2:
            sc["pledged_change"] = round(pledged[-1] - pledged[-2], 2)
            sc["pledged_trend"] = pledged[-4:]

    sc = {k: v for k, v in sc.items() if v is not None}
    return ticker, sc, warehouse_id


def parse_peer_table(html):
    """Parses Screener's peers-API HTML fragment into industry peer rows.

    The fragment is a table whose header names the columns; we locate the
    Name, Mar Cap, absolute quarterly Sales and Sales-variation columns by
    header text so a column being added or reordered upstream doesn't
    silently corrupt values. Returns ALL rows — watchlist companies
    included — as {name, ticker, sales_var_pct, market_cap, sales_qtr};
    callers split candidates from holdings. The absolute quarterly sales
    column is what makes a true industry-wide market-share denominator
    possible (analysis/market_share.py).
    """
    candidates = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return candidates

    headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
    idx = {}
    for i, h in enumerate(headers):
        if h.startswith("name"):
            idx["name"] = i
        elif "sales var" in h:
            idx["sales_var"] = i
        elif h.startswith("sales qtr"):
            idx["sales_qtr"] = i
        elif "mar cap" in h or "market cap" in h:
            idx["mcap"] = i
        elif "profit var" in h:
            idx["profit_var"] = i
        elif h.startswith("np qtr"):
            idx["np_qtr"] = i
        elif h.startswith("p/e"):
            idx["pe"] = i
        elif h.startswith("roce"):
            idx["roce"] = i
    name_idx = idx.get("name")
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
        candidates.append(
            {
                "name": name,
                "ticker": peer_ticker.upper(),
                "sales_var_pct": _cell_float(cells, idx.get("sales_var")),
                "market_cap": _cell_float(cells, idx.get("mcap")),
                "sales_qtr": _cell_float(cells, idx.get("sales_qtr")),
                # Profit, valuation and returns travel in the same table and
                # cost nothing extra to read. They are what makes a candidate
                # screenable on fundamentals rather than on press coverage.
                "profit_var_pct": _cell_float(cells, idx.get("profit_var")),
                "np_qtr": _cell_float(cells, idx.get("np_qtr")),
                "pe_ratio": _cell_float(cells, idx.get("pe")),
                "roce": _cell_float(cells, idx.get("roce")),
            }
        )
    return candidates


# Two attempts rather than the three the company pages get. These requests run
# sequentially behind the shared pacer, so every retry adds wall-clock time
# directly -- which is what the original "no retries" rule was protecting. The
# 08 Aug run showed the cost of that rule: seven holdings (HAL, LT, ADANIPOWER,
# TATACONSUM, CONCOR, MPHASIS, ZENTEC) lost their peer table to a 429 that the
# company-page path shrugged off on its first retry. Screener's limit is
# short-lived, so one backed-off retry recovers most of them for ~2-6s each
# instead of dropping the industry silently.
_PEERS_MAX_RETRIES = 2
_PEERS_BASE_DELAY = 2.0


@retry_network(max_retries=_PEERS_MAX_RETRIES, base_delay=_PEERS_BASE_DELAY)
async def _fetch_peers_once(session, url, headers):
    """One peers request. Raises TransientNetworkError so the decorator retries.

    Only the transient statuses raise. A 404 is a real answer -- this company
    has no peer table -- and retrying it would spend the budget re-asking a
    question already answered.
    """
    async with session.get(url, headers=headers, timeout=10) as response:
        if response.status in (408, 429, 500, 502, 503, 504):
            raise TransientNetworkError(f"HTTP {response.status} for {url}")
        return response.status, await response.text()


async def fetch_peers_async(session, ticker, warehouse_id):
    """Fetches Screener's peer-comparison table for one company.

    This is a structured competitor-discovery channel that does not depend on
    news headlines: Screener maintains the industry peer set itself, and each
    row arrives with quarterly sales variation attached, so candidates can be
    growth-screened immediately.

    Enhancement data, so it still degrades to an empty list on any failure --
    it just no longer gives up on the first rate-limit response.
    """
    url = f"https://www.screener.in/api/company/{warehouse_id}/peers/"
    headers = {"X-Requested-With": "XMLHttpRequest"}
    try:
        status, text = await _fetch_peers_once(session, url, headers)
    except Exception as e:
        # Includes a transient status that survived every retry. Logged as the
        # data loss it is: this holding's industry goes unscanned this run.
        log.warning(f"{ticker}: Screener peers fetch failed after retries: {e!r}")
        return ticker, []
    if status != 200:
        log.warning(f"{ticker}: Screener peers API returned {status}")
        return ticker, []
    return ticker, parse_peer_table(text)


# Screener.in's limiter is rate-based, not concurrency-based: a live run at
# 5 concurrent requests still drew 429s once the initial burst allowance was
# spent, costing one company its data and most sectors their peer lookups.
# So requests are *paced* — a minimum interval between request starts — with
# a small concurrency cap kept as a belt-and-braces bound on in-flight work.
_SCREENER_CONCURRENCY = 4
_SCREENER_REQUEST_INTERVAL_S = 1.0


class _RequestPacer:
    """Serialises request start times so they are at least ``interval`` apart."""

    def __init__(self, interval):
        self._interval = interval
        self._lock = asyncio.Lock()
        self._next_at = 0.0

    async def wait(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            delay = max(0.0, self._next_at - now)
            self._next_at = max(now, self._next_at) + self._interval
        if delay:
            await asyncio.sleep(delay)


async def fetch_all_screener_fundamentals(watchlist):
    """Loads Screener fundamentals into each stock and discovers peer competitors.

    Returns (peer_competitors, industry_tables):
      - peer_competitors: {sector: [row, ...]} of Screener industry peers NOT
        in the watchlist — the competitor-discovery radar, merged across every
        industry scanned for that sector.
      - industry_tables: [{sector, via_ticker, rows}, ...] — one entry per
        industry scanned, kept apart so market share is measured within an
        industry rather than across a sector's several industries.
    Both empty when peer data is unavailable.
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

    semaphore = asyncio.Semaphore(_SCREENER_CONCURRENCY)
    pacer = _RequestPacer(_SCREENER_REQUEST_INTERVAL_S)

    async def throttled(coro):
        await pacer.wait()
        async with semaphore:
            return await coro

    async with aiohttp.ClientSession() as session:
        for sector, stocks in watchlist.items():
            for stock in stocks:
                ticker = stock["ticker"]
                price = float(stock.get("price") or 0.0)
                ticker_to_stock[ticker] = stock
                ticker_to_sector[ticker] = sector
                stock["screener"] = {}
                tasks.append(
                    throttled(fetch_screener_async(session, ticker, sector, price))
                )

        results = await asyncio.gather(*tasks)

        holdings = []
        for ticker, sc_data, warehouse_id in results:
            if sc_data:
                ticker_to_stock[ticker]["screener"] = sc_data
                log.info(
                    f"{ticker}: Screener data loaded (PE={sc_data.get('pe_ratio', 'N/A')})"
                )
            if warehouse_id and ticker_to_sector.get(ticker):
                holdings.append((ticker, warehouse_id))

        peer_results = await _fetch_industry_tables(holdings, throttled, session)

    return _assemble_peer_views(peer_results, ticker_to_sector, watchlist_tickers)


async def _fetch_industry_tables(holdings, throttled, session):
    """Fetch one peer table per *industry* represented in the watchlist.

    Screener's peer table is industry-level, and the previous implementation
    read that as "one table per sector" — it fetched a single table for each
    sector, from whichever holding happened to be first. But our sectors are
    thesis groupings, not industries: clean_energy holds a power utility, a
    wind-turbine maker and a renewable IPP, which Screener files in three
    different industries. Only the first was ever scanned, so 29 of 47
    holdings sat in industries this pipeline never looked at, and the
    competitors living there — solar module makers, EMS companies — could not
    be discovered at all.

    A holding that turns up inside an already-fetched table shares that
    industry, so its own table would be near-identical and is skipped. That
    keeps the request count near one per distinct industry rather than one per
    holding, which matters because Screener rate-limits and has returned 429s
    on this pipeline before.

    Deciding what to skip requires seeing each response before issuing the
    next, so these run sequentially. That costs nothing: the shared pacer
    already spaces request *starts* a second apart, so a concurrent gather
    finishes no sooner unless a response outruns the pacing interval.
    """
    covered = set()
    tables = []
    for ticker, warehouse_id in holdings:
        if ticker in covered:
            continue
        _, rows = await throttled(fetch_peers_async(session, ticker, warehouse_id))
        covered.add(ticker)
        if not rows:
            continue
        tables.append((ticker, rows))
        # Everyone in this table is in the same industry as `ticker`.
        covered.update(r["ticker"] for r in rows)
    log.info(
        f"Peer radar: {len(tables)} industry table(s) fetched for "
        f"{len(holdings)} holding(s)."
    )
    return tables


def _assemble_peer_views(peer_results, ticker_to_sector, watchlist_tickers):
    """Split raw peer tables into the candidate radar and the share tables.

    Returns ``(peer_competitors, industry_tables)``:

    * ``peer_competitors`` — {sector: [row]} of non-holding competitors, merged
      across every industry scanned for that sector. Merging is right here:
      these are challengers to the sector's thesis whichever industry they sit
      in.
    * ``industry_tables`` — one entry per fetched table, kept separate on
      purpose. Market share is a company's slice of *its own industry*, so
      pooling several industries into one denominator would understate every
      holding's share. Each row is stamped with the share it holds inside its
      own table, so downstream consumers never have to rebuild a denominator.
    """
    peer_competitors = {}
    industry_tables = []

    for via_ticker, rows in peer_results:
        sector = ticker_to_sector.get(via_ticker)
        if not sector or not rows:
            continue

        total = sum(
            row["sales_qtr"]
            for row in rows
            if isinstance(row.get("sales_qtr"), (int, float)) and row["sales_qtr"] > 0
        )
        for row in rows:
            row["via_ticker"] = via_ticker
            sales = row.get("sales_qtr")
            if total > 0 and isinstance(sales, (int, float)) and sales > 0:
                row["industry_share_pct"] = round(sales / total * 100, 2)
            row["industry_peer_count"] = len(rows)

        industry_tables.append(
            {"sector": sector, "via_ticker": via_ticker, "rows": rows}
        )

        bucket = peer_competitors.setdefault(sector, [])
        seen = {r["ticker"] for r in bucket}
        for row in rows:
            if row["ticker"] in seen or row["ticker"] in watchlist_tickers:
                continue
            seen.add(row["ticker"])
            bucket.append(row)

    if peer_competitors:
        found = sum(len(v) for v in peer_competitors.values())
        log.info(f"Peer radar: {found} non-watchlist competitors discovered.")
    return peer_competitors, industry_tables
