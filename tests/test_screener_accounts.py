"""Screener's consolidated and standalone accounts (providers/screener.py).

Every run read only the consolidated page. For SCHNEIDER, PAGEIND and RELAXO
it showed shareholding and no figures, and a page with no figures still
counted as a fetch that worked. The fetch requests are faked here, so the
tests are about which page is read and what counts as fetched.
"""

import asyncio
import datetime

import pytest

import providers.screener as screener
from analysis import last_good

RATIOS = (
    '<div class="company-ratios"><ul>'
    '<li><span class="name">Market Cap</span><span class="number">41,234</span></li>'
    '<li><span class="name">Stock P/E</span><span class="number">62.3</span></li>'
    '<li><span class="name">ROCE</span><span class="number">28.1</span></li>'
    "</ul></div>"
)
QUARTERS = (
    '<section id="quarters"><table><tbody>'
    "<tr><td>Sales</td><td>1,000</td><td>1,100</td></tr>"
    "</tbody></table></section>"
)
SHAREHOLDING = (
    '<section id="shareholding"><table><tbody>'
    "<tr><td>Promoters</td><td>51.0</td><td>51.0</td></tr>"
    "<tr><td>FIIs</td><td>20.1</td><td>21.0</td></tr>"
    "</tbody></table></section>"
)


def _page(*parts, warehouse="1234"):
    return (
        f'<html><body><div data-warehouse-id="{warehouse}"></div>'
        + "".join(parts)
        + "</body></html>"
    )


FULL = _page(RATIOS, QUARTERS, SHAREHOLDING)
SHARES_ONLY = _page(SHAREHOLDING)


@pytest.fixture
def pages(monkeypatch):
    """Serve ``pages[url]`` as (status, text); record every request."""
    served, asked = {}, []

    async def fetch(session, url, **kwargs):
        asked.append(url)
        answer = served.get(url, (404, "Not found"))
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(screener, "fetch_text_async", fetch)
    monkeypatch.setattr(screener, "_SCREENER_REQUEST_INTERVAL_S", 0)
    served["asked"] = asked
    return served


CONSOLIDATED = "https://www.screener.in/company/PAGEIND/consolidated/"
STANDALONE = "https://www.screener.in/company/PAGEIND/"


def _fetch(ticker="PAGEIND"):
    return asyncio.run(screener.fetch_screener_async(None, ticker, "x", 0.0))


def test_a_company_without_consolidated_figures_is_read_from_its_standalone_page(
    pages,
):
    pages[CONSOLIDATED] = (200, SHARES_ONLY)
    pages[STANDALONE] = (200, FULL)
    ticker, sc, warehouse = _fetch()
    assert (ticker, warehouse) == ("PAGEIND", "1234")
    assert sc["accounts"] == "standalone"
    assert (sc["market_cap"], sc["pe_ratio"], sc["q_sales"]) == (41234.0, 62.3, 1100.0)
    assert sc["promoter_pct"] == 51.0
    assert pages["asked"] == [CONSOLIDATED, STANDALONE]


def test_a_company_without_a_consolidated_page_is_read_from_its_standalone_one(
    pages,
):
    pages[STANDALONE] = (200, FULL)
    _t, sc, _w = _fetch()
    assert sc["accounts"] == "standalone" and sc["roce"] == 28.1
    assert pages["asked"] == [CONSOLIDATED, STANDALONE]


def test_consolidated_figures_are_read_without_a_second_request(pages):
    pages[CONSOLIDATED] = (200, FULL)
    _t, sc, _w = _fetch()
    assert sc["accounts"] == "consolidated" and screener.has_figures(sc)
    assert pages["asked"] == [CONSOLIDATED]


def test_no_page_under_either_view_is_a_failed_fetch(pages):
    """ASMTEC: nothing but the capex and R&D defaults came back."""
    _t, sc, warehouse = _fetch()
    assert sc is None and warehouse is None
    assert pages["asked"] == [CONSOLIDATED, STANDALONE]


def test_no_figures_in_either_view_keeps_the_shareholding(pages):
    pages[CONSOLIDATED] = (200, SHARES_ONLY)
    pages[STANDALONE] = (200, SHARES_ONLY)
    _t, sc, _w = _fetch()
    assert sc["promoter_pct"] == 51.0
    assert not screener.has_figures(sc) and "accounts" not in sc


@pytest.mark.parametrize(
    "answer",
    [ConnectionError("reset"), (403, "Forbidden"), (200, "")],
    ids=["exception", "refused", "empty"],
)
def test_a_failed_request_is_not_repeated_under_the_other_view(pages, answer):
    """Only a 404 says the other view may have the page. A 429 arrives here as
    an exception, after fetch_text_async's own retries."""
    pages[CONSOLIDATED] = answer
    _t, sc, _w = _fetch()
    assert sc is None
    assert pages["asked"] == [CONSOLIDATED]


def test_a_failed_second_view_keeps_the_first_views_shareholding(pages):
    pages[CONSOLIDATED] = (200, SHARES_ONLY)
    pages[STANDALONE] = ConnectionError("reset")
    _t, sc, _w = _fetch()
    assert sc["promoter_pct"] == 51.0 and not screener.has_figures(sc)


async def _no_tables(*args):
    return []


def test_the_batch_queues_every_request_the_standalone_one_included(pages, monkeypatch):
    """Screener limits by rate, so each request takes a turn from the run's
    pacer. The fallback request used to go out on a timer of its own, beside
    whichever company's turn it was."""
    turns = []

    class Pacer:
        def __init__(self, interval):
            pass

        async def wait(self):
            turns.append(len(pages["asked"]))

    monkeypatch.setattr(screener, "_RequestPacer", Pacer)
    monkeypatch.setattr(screener, "_fetch_industry_tables", _no_tables)
    monkeypatch.setattr(screener, "_assemble_peer_views", lambda *a: ({}, []))
    pages[CONSOLIDATED] = (200, SHARES_ONLY)
    pages[STANDALONE] = (200, FULL)
    pages["https://www.screener.in/company/HAL/consolidated/"] = (200, FULL)
    watchlist = {"x": [{"ticker": "PAGEIND"}, {"ticker": "HAL"}]}
    asyncio.run(screener.fetch_all_screener_fundamentals(watchlist))
    assert len(pages["asked"]) == len(turns) == 3
    assert watchlist["x"][0]["screener"]["accounts"] == "standalone"


def test_only_a_page_with_figures_counts_as_fetched(monkeypatch):
    """A page showing shareholding alone used to be marked fetched, so the
    last-known-good step put nothing back for it."""
    results = {
        "HAL": ({"market_cap": 1.0, "accounts": "consolidated"}, "1"),
        "PAGEIND": ({"market_cap": 2.0, "accounts": "standalone"}, "2"),
        "RELAXO": ({"promoter_pct": 63.0, "capex": 0.0}, "3"),
        "ASMTEC": (None, None),
    }

    async def fake_fetch(session, ticker, sector, price, fetch=None, **kwargs):
        return (ticker, *results[ticker])

    monkeypatch.setattr(screener, "fetch_screener_async", fake_fetch)
    monkeypatch.setattr(screener, "_fetch_industry_tables", _no_tables)
    monkeypatch.setattr(screener, "_assemble_peer_views", lambda *a: ({}, []))
    monkeypatch.setattr(screener, "_SCREENER_REQUEST_INTERVAL_S", 0)
    stocks = {t: {"ticker": t, "screener": {"roce": 9.9}} for t in results}
    watchlist = {"x": list(stocks.values())}
    prior = last_good.snapshot(watchlist)
    asyncio.run(screener.fetch_all_screener_fundamentals(watchlist))

    fetched = {t: "screener" in s.get("_fetched", {}) for t, s in stocks.items()}
    assert fetched == {"HAL": True, "PAGEIND": True, "RELAXO": False, "ASMTEC": False}
    assert stocks["RELAXO"]["screener"] == {"promoter_pct": 63.0, "capex": 0.0}

    # So the next step treats RELAXO's figures as undelivered and keeps them.
    last_good.restore(
        watchlist, prior, when=datetime.datetime.now(datetime.timezone.utc)
    )
    assert stocks["RELAXO"]["screener"]["roce"] == 9.9
    assert "roce" in stocks["RELAXO"]["_stale_fields"]
    # A fresh page keeps its own figures.
    assert stocks["HAL"]["screener"]["market_cap"] == 1.0


# ---------------------------------------------------------------------------
# A company Screener files under another name
# ---------------------------------------------------------------------------

# Screener's answer for "ASMTEC" on 14 Oct 2026, verbatim.
ASMTEC_SEARCH = (
    '[{"id": 300, "name": "ASM Technologies Ltd", '
    '"url": "/company/526433/consolidated/"}, {"id": null, '
    '"name": "Search everywhere: ASMTEC", "url": "/full-text-search/?q=ASMTEC"}]'
)
SEARCH = screener.SEARCH_URL.format(query="ASMTEC")
BSE_PAGE = "https://www.screener.in/company/526433/consolidated/"


def _fetch_asmtec(**kwargs):
    return asyncio.run(
        screener.fetch_screener_async(None, "ASMTEC", "x", 0.0, **kwargs)
    )


def test_a_company_with_no_page_under_its_ticker_is_found_through_search(pages):
    pages[SEARCH] = (200, ASMTEC_SEARCH)
    pages[BSE_PAGE] = (200, FULL)
    _t, sc, _w = _fetch_asmtec(name="ASM Technologies")
    assert sc["slug"] == "526433" and sc["accounts"] == "consolidated"
    assert sc["market_cap"] == 41234.0
    assert pages["asked"] == [
        "https://www.screener.in/company/ASMTEC/consolidated/",
        "https://www.screener.in/company/ASMTEC/",
        SEARCH,
        BSE_PAGE,
    ]


def test_the_page_found_before_is_read_without_searching(pages):
    pages[BSE_PAGE] = (200, FULL)
    _t, sc, _w = _fetch_asmtec(slug="526433", name="ASM Technologies")
    assert sc["slug"] == "526433"
    assert pages["asked"] == [BSE_PAGE]


def test_only_a_missing_page_is_searched_for(pages):
    """Not after a failure, and not without a name to check the answer by."""
    pages["https://www.screener.in/company/ASMTEC/consolidated/"] = ConnectionError()
    _t, sc, _w = _fetch_asmtec(name="ASM Technologies")
    assert sc is None and SEARCH not in pages["asked"]
    pages["asked"].clear()
    del pages["https://www.screener.in/company/ASMTEC/consolidated/"]
    _t, sc, _w = _fetch_asmtec()
    assert sc is None and SEARCH not in pages["asked"]


def test_a_search_answer_must_be_the_holdings_company():
    hits = [
        {"id": 1, "name": "ASM Infra Ltd", "url": "/company/ASMINFRA/"},
        {
            "id": 2,
            "name": "ASM Technologies Ltd Partly Paidup",
            "url": "/company/id/1275222/",
        },
        {
            "id": None,
            "name": "Search everywhere: ASM",
            "url": "/full-text-search/?q=ASM",
        },
    ]
    assert screener.slug_from_search(hits, "ASM Technologies") is None
    hits.append({"id": 300, "name": "ASM Technologies Ltd", "url": "/company/526433/"})
    assert screener.slug_from_search(hits, "ASM Technologies") == "526433"
    assert screener.slug_from_search(hits, None) is None
    assert screener.slug_from_search("not a list", "ASM Technologies") is None


def test_the_batch_reads_where_the_last_run_found_the_page(monkeypatch):
    seen = {}

    async def fake_fetch(session, ticker, sector, price, fetch=None, **kwargs):
        seen[ticker] = kwargs
        return ticker, None, None

    monkeypatch.setattr(screener, "fetch_screener_async", fake_fetch)
    monkeypatch.setattr(screener, "_fetch_industry_tables", _no_tables)
    monkeypatch.setattr(screener, "_assemble_peer_views", lambda *a: ({}, []))
    stock = {
        "ticker": "ASMTEC",
        "name": "ASM Technologies",
        "screener": {"slug": "526433", "roce": 27.0},
    }
    asyncio.run(screener.fetch_all_screener_fundamentals({"x": [stock]}))
    assert seen["ASMTEC"] == {"slug": "526433", "name": "ASM Technologies"}
