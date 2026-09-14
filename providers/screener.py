import aiohttp
import asyncio
from collections import Counter, namedtuple
from bs4 import BeautifulSoup
from logger import log
from analysis.parsing import extract_row_values, calculate_trend, calculate_growth
from utils import (
    TransientNetworkError,
    fetch_text_async,
    retry_after_of,
    retry_network,
)

# The pledge row matched nothing on the first live run — 0 of 69 holdings —
# and Screener refuses connections from the build sandbox, so the labels had
# to be reported from production instead of checked here.
#
# It has since been answered: Screener serves no pledge row for anybody
# (measured across six holdings; see docs/upstream-findings.md).
# This is now a tripwire for Screener changing its mind, not an open
# investigation.
#
# Once per run, but note what that cost the first reading of it: the sample
# it happened to report was HAL, a government-owned company that cannot carry
# a promoter pledge, so its missing row was correct output and said nothing
# about the other 69. A once-per-run diagnostic does not get to choose a
# representative sample, and its output must not be read as one.
_shareholding_rows_reported = False


def _report_shareholding_rows(soup, ticker):
    """Log the shareholding row labels once, when the pledge row is missing.

    A no-op after the first call. Purely diagnostic — it reads nothing into
    the payload and cannot change a number.

    The message says "not served" rather than "not matched": the row is known
    to be absent for every company, so calling it a parse failure would send
    the next reader after a regex that was never the problem.
    """
    global _shareholding_rows_reported
    if _shareholding_rows_reported:
        return
    try:
        section = soup.find("section", id="shareholding")
        if not section:
            log.info(f"No shareholding section for {ticker}.")
            _shareholding_rows_reported = True
            return
        labels = []
        for tr in section.find_all("tr"):
            cells = tr.find_all("td")
            if cells:
                label = cells[0].get_text(" ", strip=True)
                if label:
                    labels.append(label)
        log.info(
            f"Pledge not served by Screener (checked via {ticker}); "
            f"shareholding rows present: {labels}. This is expected — see "
            "docs/upstream-findings.md. Pledge needs another source."
        )
    except Exception as e:  # noqa: BLE001 - a diagnostic must never break a run
        log.warning(f"Could not list shareholding rows for {ticker}: {e!r}")
    _shareholding_rows_reported = True


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
    # MEASURED 2026-09-10 (docs/upstream-findings.md), and the
    # answer is that this will never match: Screener does not serve a pledge
    # row. Six holdings were checked, chosen so a null result would mean
    # something — HAL as a government-owned control that structurally cannot
    # pledge, plus SUZLON, ANANTRAJ, OPTIEMUS, ADSL and FAZE3Q, all
    # promoter-led and several smallcap. Every one carried the same rows
    # (Promoters, FIIs, DIIs, Public, sometimes Government/Others) and none
    # carried a pledge row.
    #
    # The expander behind "Promoters +" was chased to its endpoint,
    # /api/3/{companyId}/investors/{classification}/{period}/, which answers
    # 200 unauthenticated and returns per-shareholder HOLDINGS — names and
    # their quarterly percentages — not pledge.
    #
    # So this is kept only as a cheap tripwire in case Screener starts
    # publishing it. analysis/pledging.py cannot be fed from here and needs a
    # different source (the exchanges' shareholding-pattern filings) to do
    # anything at all.
    pledged = extract_row_values(soup, "shareholding", r"Pledg")
    if pledged:
        sc["pledged_pct"] = pledged[-1]
        if len(pledged) >= 2:
            sc["pledged_change"] = round(pledged[-1] - pledged[-2], 2)
            sc["pledged_trend"] = pledged[-4:]
    else:
        _report_shareholding_rows(soup, ticker)

    sc = {k: v for k, v in sc.items() if v is not None}
    return ticker, sc, warehouse_id


# Header text Screener has used for the company column. "Name" was the
# original; "Company" appeared by 13 Sep 2026 and emptied the entire channel,
# because this is the one column the parser cannot proceed without -- it
# carries the link the peer ticker is read from.
_NAME_HEADERS = ("name", "company")


def _company_column(table):
    """Locate the company column by its LINK rather than its header text.

    The header is the fragile part. Screener renamed it and every peer table in
    the pipeline went unreadable overnight -- 66 fetches a day returning a
    perfectly good 6 KB table that the parser threw away, for at least three
    runs, because one string stopped matching.

    The link is not fragile: every peer row carries an /company/<ticker>/
    anchor, and that anchor is what the ticker is actually read from further
    down. Finding the column structurally means the next rename costs nothing.
    """
    for row in table.find_all("tr"):
        for i, cell in enumerate(row.find_all("td")):
            link = cell.find("a")
            href = link.get("href", "") if link else ""
            parts = [p for p in href.split("/") if p]
            if len(parts) >= 2 and parts[0] == "company":
                return i
    return None


def parse_peer_table(html):
    """Parses Screener's peers-API HTML fragment into industry peer rows.

    The fragment is a table whose header names the columns; we locate the
    company, Mar Cap, absolute quarterly Sales and Sales-variation columns by
    header text so a column being added or reordered upstream doesn't
    silently corrupt values. Returns ALL rows — watchlist companies
    included — as {name, ticker, sales_var_pct, market_cap, sales_qtr};
    callers split candidates from holdings. The absolute quarterly sales
    column is what makes a true industry-wide market-share denominator
    possible (analysis/market_share.py).

    The company column is the exception to header matching: it falls back to
    finding the column by its link, because losing it costs every row rather
    than one field.
    """
    candidates = []
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return candidates

    # Joined with a space rather than concatenated: Screener nests units in
    # their own elements, so strip-only gives "Mar CapRs.Cr." and "Qtr Sales
    # Var%". The current matchers survive that, but only by luck.
    headers = [
        " ".join(th.get_text(" ", strip=True).split()).lower()
        for th in table.find_all("th")
    ]
    idx = {}
    for i, h in enumerate(headers):
        if h.startswith(_NAME_HEADERS):
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
        # No header we recognise. Rather than discard a table that is very
        # likely fine, find the company column the way the rows themselves
        # identify it.
        name_idx = _company_column(table)
        if name_idx is not None:
            log.info(
                "Screener peers: no recognised company header in "
                f"{headers!r}; using column {name_idx} found by its link."
            )
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

# Stop once this many holdings in a row come back with no usable table.
#
# Eight is comfortably more than any plausible run of genuinely peerless
# companies -- a holding with no peer table is rare, and eight consecutive is
# not a coincidence, it is the channel being down. The 13 Sep run spent 75
# seconds and 66 requests to learn this the slow way, drawing six 429s from a
# service that was already telling us to back off.
_PEERS_ABORT_AFTER_EMPTY = 8

# The looser bound for a network that is simply down. Higher than the readable
# bound because being unreachable is transient and worth more patience, low
# enough that a genuine outage does not cost sixty pointless requests.
_PEERS_ABORT_AFTER_UNREACHABLE = 20


@retry_network(max_retries=_PEERS_MAX_RETRIES, base_delay=_PEERS_BASE_DELAY)
async def _fetch_peers_once(session, url, headers):
    """One peers request. Raises TransientNetworkError so the decorator retries.

    Only the transient statuses raise. A 404 is a real answer -- this company
    has no peer table -- and retrying it would spend the budget re-asking a
    question already answered.

    A 429 carries Screener's own Retry-After when it sends one, so the backoff
    waits as long as the service asked rather than guessing shorter and
    earning the next 429.
    """
    async with session.get(url, headers=headers, timeout=10) as response:
        if response.status in (408, 429, 500, 502, 503, 504):
            raise TransientNetworkError(
                f"HTTP {response.status} for {url}",
                retry_after=retry_after_of(response),
            )
        # Content-Type travels with the body because it is the cheapest way to
        # tell "the HTML changed shape" from "this endpoint returns JSON now"
        # from "we were handed a login page", and this environment cannot
        # reach Screener to find out by hand.
        content_type = ""
        try:
            content_type = response.headers.get("Content-Type", "") or ""
        except Exception:  # noqa: BLE001 - diagnostics must never raise
            content_type = ""
        return response.status, await response.text(), content_type


# One fetch's outcome, kept apart from its rows.
#
# The old signature returned a bare list, so "the network died", "Screener
# said 404" and "we got a page and understood none of it" were all the same
# empty list. That is why a channel could return nothing for every holding on
# three consecutive runs and leave no trace in the log saying which of those
# three things happened -- the information was discarded at the only point it
# existed.
PeerFetch = namedtuple("PeerFetch", "ticker rows outcome detail")

OUTCOME_OK = "ok"
OUTCOME_NO_ROWS = "no_rows"
OUTCOME_HTTP = "http_error"
OUTCOME_UNREACHABLE = "unreachable"


def describe_fragment(text, content_type="", limit=220):
    """A bounded description of a response we could not parse.

    This exists to answer, from the log alone, the question that otherwise
    needs a live request to Screener: what IS the server sending us? It states
    the size, whether a table is present at all, and the header cells found, so
    a shape change, an empty body and a login wall are told apart without
    guessing. Bounded and stripped, because a log line is not a place to paste
    a web page.
    """
    if text is None:
        return "no body"
    raw = str(text)
    try:
        soup = BeautifulSoup(raw, "lxml")
        table = soup.find("table")
        headers = (
            [th.get_text(strip=True) for th in table.find_all("th")][:12]
            if table
            else []
        )
        visible = " ".join(soup.get_text(" ", strip=True).split())[:limit]
    except Exception:  # noqa: BLE001 - diagnostics must never raise
        table, headers, visible = None, [], raw[:limit]
    return (
        f"{len(raw)} bytes, type={content_type or 'unstated'!r}, "
        f"table={'yes' if table is not None else 'no'}, "
        f"headers={headers!r}, text={visible!r}"
    )


async def fetch_peers_async(session, ticker, warehouse_id):
    """Fetches Screener's peer-comparison table for one company.

    This is a structured competitor-discovery channel that does not depend on
    news headlines: Screener maintains the industry peer set itself, and each
    row arrives with quarterly sales variation attached, so candidates can be
    growth-screened immediately.

    Enhancement data, so it still degrades to no rows on any failure -- but the
    reason is carried out with it rather than thrown away.
    """
    url = f"https://www.screener.in/api/company/{warehouse_id}/peers/"
    headers = {"X-Requested-With": "XMLHttpRequest"}
    try:
        status, text, content_type = await _fetch_peers_once(session, url, headers)
    except Exception as e:
        return PeerFetch(ticker, [], OUTCOME_UNREACHABLE, repr(e))
    if status != 200:
        return PeerFetch(ticker, [], OUTCOME_HTTP, f"HTTP {status}")
    rows = parse_peer_table(text)
    if not rows:
        # A 200 we could not read. Distinct from every other empty result, and
        # the only one whose cause lives in the response body.
        return PeerFetch(
            ticker, [], OUTCOME_NO_ROWS, describe_fragment(text, content_type)
        )
    return PeerFetch(ticker, rows, OUTCOME_OK, "")


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
    outcomes = Counter()
    first_unreadable = None
    consecutive_empty = 0
    consecutive_unreachable = 0
    attempted = 0

    for index, (ticker, warehouse_id) in enumerate(holdings):
        if ticker in covered:
            continue
        result = await throttled(fetch_peers_async(session, ticker, warehouse_id))
        covered.add(ticker)
        attempted += 1
        outcomes[result.outcome] += 1

        if result.outcome == OUTCOME_NO_ROWS and first_unreadable is None:
            # Captured once, not per holding: 66 copies of the same diagnostic
            # is not 66 times the evidence.
            first_unreadable = (result.ticker, result.detail)

        if not result.rows:
            # Only an ANSWER we cannot use counts toward giving up. The abort
            # exists to stop asking a channel that replies uselessly; a network
            # failure is not that, it is the retry layer's business and it is
            # transient by definition.
            #
            # The 14 Sep run proved the difference: Screener was unreachable
            # for about half the holdings, the first eight peer fetches failed
            # on the network, and the whole channel was abandoned for the day
            # over an outage that had nothing to do with whether the peer table
            # is readable. A separate, looser bound still stops a completely
            # dead network from burning sixty requests.
            if result.outcome == OUTCOME_UNREACHABLE:
                consecutive_unreachable += 1
                consecutive_empty = 0
            else:
                consecutive_empty += 1
                consecutive_unreachable = 0

            if consecutive_unreachable >= _PEERS_ABORT_AFTER_UNREACHABLE:
                remaining = len(holdings) - (index + 1)
                log.warning(
                    f"Peer radar: {consecutive_unreachable} consecutive holdings "
                    f"were unreachable; the network looks down rather than the "
                    f"channel. Skipping the remaining {remaining} request(s)."
                )
                if remaining:
                    outcomes["skipped"] = remaining
                break

            if consecutive_empty >= _PEERS_ABORT_AFTER_EMPTY:
                # The channel is not answering. Continuing would issue another
                # fifty requests that cannot succeed, to a service that is
                # already rate-limiting us — the run gets slower, Screener gets
                # loaded, and the result is the same empty list.
                remaining = len(holdings) - (index + 1)
                log.warning(
                    f"Peer radar: giving up after {consecutive_empty} consecutive "
                    f"holdings returned no usable peer table. Skipping the "
                    f"remaining {remaining} request(s)."
                )
                if remaining:
                    outcomes["skipped"] = remaining
                break
            continue

        consecutive_empty = 0
        consecutive_unreachable = 0
        tables.append((result.ticker, result.rows))
        # Everyone in this table is in the same industry as `ticker`.
        covered.update(r["ticker"] for r in result.rows)

    _log_peer_radar(tables, holdings, attempted, outcomes, first_unreadable)
    return tables


def _log_peer_radar(tables, holdings, attempted, outcomes, first_unreadable):
    """State what the peer channel actually did, in one line per run.

    Previously this was a bare count of tables, which cannot distinguish "every
    industry was already covered" from "every request failed" — and the second
    is what had been happening, unnoticed, for at least three runs.
    """
    breakdown = ", ".join(
        f"{count} {name.replace('_', ' ')}" for name, count in sorted(outcomes.items())
    )
    summary = (
        f"Peer radar: {len(tables)} industry table(s) from {attempted} request(s) "
        f"across {len(holdings)} holding(s)"
        f"{' — ' + breakdown if breakdown else ''}."
    )

    # A channel that produced nothing at all is a broken feature, not a quiet
    # day, and must not be reported at the same level as a normal result.
    if holdings and not tables:
        log.warning(summary)
        log.warning(
            "Peer radar: competitor discovery, candidate screening and "
            "industry share all depend on this and will be empty this run."
        )
    else:
        log.info(summary)

    if first_unreadable:
        ticker, detail = first_unreadable
        log.warning(f"Peer radar: unreadable response for {ticker} — {detail}")


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
