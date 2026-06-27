import asyncio
from unittest.mock import MagicMock

from providers.rss import fetch_query_feed_async
from analysis.growth import update_single_stock
from analysis.rotation import auto_curate_watchlist
from providers.screener import fetch_screener_async


# --- 1. Empty RSS ---
def test_empty_rss(monkeypatch):
    empty_xml = "<rss><channel></channel></rss>"

    async def mock_fetch(*args, **kwargs):
        return 200, empty_xml

    monkeypatch.setattr("utils.fetch_text_async", mock_fetch)

    mock_session = MagicMock()
    news = asyncio.run(fetch_query_feed_async(mock_session, "energy", "Reliance"))
    assert len(news[1]) == 0


# --- 2. Empty Watchlist ---
def test_empty_watchlist():
    # If the watchlist is empty, auto_curate_watchlist shouldn't crash
    result = auto_curate_watchlist({}, {})
    assert isinstance(result, dict)


# --- 3. Duplicate News ---
def test_duplicate_news(monkeypatch):
    dup_xml = """<rss><channel>
        <item><title>Reliance Ltd Corp</title><link>http://example.com/1</link><description>Summary1</description><pubDate>Sat, 27 Jun 2026 10:00:00 GMT</pubDate></item>
        <item><title>Reliance Ltd Corp</title><link>http://example.com/1</link><description>Summary2</description><pubDate>Sat, 27 Jun 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""

    async def mock_fetch(*args, **kwargs):
        return 200, dup_xml

    monkeypatch.setattr("utils.fetch_text_async", mock_fetch)

    mock_session = MagicMock()
    news = asyncio.run(fetch_query_feed_async(mock_session, "energy", "Reliance"))
    # Feedparser parses it. We just need to check we handle it (even if len is 0 or 2, just no crashes)
    assert isinstance(news[1], list)


# --- 4. Missing Yahoo Fields ---
def test_missing_yahoo_fields(monkeypatch):
    class MockHist:
        empty = False

        def __getitem__(self, key):
            class Series:
                @property
                def iloc(self):
                    return [-1, 100.0]

            return Series()

    class MockTicker:
        def history(self, *args, **kwargs):
            return MockHist()

        @property
        def info(self):
            return {"shortName": "Test Corp"}  # Missing everything else

    monkeypatch.setattr(
        "providers.yahoo.get_cached_ticker", lambda *args, **kwargs: MockTicker()
    )

    stock = {"ticker": "TEST"}
    update_single_stock(stock, {})
    # It should populate defaults for missing info gracefully
    assert stock["rating"] == "N/A"


# --- 5. Malformed Screener HTML ---
def test_malformed_screener_html(monkeypatch):
    malformed_html = "<html><body><h1>Broken</h1><section id='quarters'><!-- no table --></section></body></html>"

    async def mock_fetch(*args, **kwargs):
        return 200, malformed_html

    monkeypatch.setattr("utils.fetch_text_async", mock_fetch)

    ticker, sc = asyncio.run(fetch_screener_async(None, "RELIANCE", "energy", 1000.0))
    assert ticker == "RELIANCE"
    assert sc is None


# --- 6. HTTP Failures ---
def test_http_failures(monkeypatch):
    async def mock_fetch(*args, **kwargs):
        return 500, ""

    monkeypatch.setattr("utils.fetch_text_async", mock_fetch)

    ticker, sc = asyncio.run(fetch_screener_async(None, "RELIANCE", "energy", 1000.0))
    assert sc is None


# --- 7. Invalid stock entries ---
def test_invalid_stock_entries(monkeypatch):
    from config import SECTOR_METADATA

    sector = list(SECTOR_METADATA.keys())[0]
    # simulate resolve_ticker_from_name returning None tuple
    monkeypatch.setattr(
        "analysis.rotation.resolve_ticker_from_name",
        lambda *args, **kwargs: (None, None),
    )

    # brief_data represents news items, so it must have 'title' and 'summary'
    brief_data = {
        sector: [
            {
                "title": "Invalid Corp Limited announces things",
                "summary": "Stuff happens",
                "published": "Sat, 27 Jun 2026 10:00:00 GMT",
            }
        ]
    }
    res = auto_curate_watchlist(brief_data, {sector: []})
    # auto_curate_watchlist looks for emerging players. If it can't resolve "Invalid Corp Limited", it makes an unresolved entry.
    assert len(res.get(sector, [])) == 1
    assert res[sector][0].get("status") == "Unresolved"
