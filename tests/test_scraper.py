import pytest
from unittest.mock import patch
import datetime
from providers.rss import clean_news_item


class DotDict(dict):
    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)


class MockDate(datetime.date):
    @classmethod
    def today(cls):
        return cls(2024, 1, 10)


class MockDateTime(datetime.datetime):
    @classmethod
    def now(cls):
        return cls(2024, 1, 10, 10, 0, 0)


@pytest.fixture(autouse=True)
def mock_datetime():
    with patch("scraper.datetime.date", MockDate), patch(
        "scraper.datetime.datetime", MockDateTime
    ):
        yield


def test_clean_news_item_basic():
    entry = DotDict(
        {
            "title": "Reliance announces new project - Financial Times",
            "link": "http://example.com",
            "published": "Tue, 09 Jan 2024 10:00:00 GMT",
            "published_parsed": (2024, 1, 9, 10, 0, 0, 1, 9, 0),
            "summary": "This is a great positive news.",
            "source": DotDict({"title": "Financial Times"}),
        }
    )

    result = clean_news_item(entry, "Reliance")

    assert result is not None
    assert result["title"] == "Reliance announces new project"
    assert result["source"] == "Financial Times"
    assert result["link"] == "http://example.com"
    assert result["date"] == "09 Jan 2024"
    assert result["impact"] == "Positive"
    assert result["relevance"] == "Reliance"


def test_clean_news_item_no_dash_in_title():
    entry = DotDict(
        {
            "title": "Tata Motors launches new EV",
            "link": "http://example.com/tata",
            "published": "Tue, 09 Jan 2024 10:00:00 GMT",
            "published_parsed": (2024, 1, 9, 10, 0, 0, 1, 9, 0),
            "summary": "Delay in production reported.",
            "source": DotDict({"title": "Auto News"}),
        }
    )

    result = clean_news_item(entry, "Tata Motors")

    assert result is not None
    assert result["title"] == "Tata Motors launches new EV"
    assert result["source"] == "Auto News"
    assert result["impact"] == "Negative"


def test_clean_news_item_no_source_provided():
    entry = DotDict(
        {
            "title": "Infosys secures new deal",
            "link": "http://example.com/infy",
            "published": "Tue, 09 Jan 2024 10:00:00 GMT",
            "published_parsed": (2024, 1, 9, 10, 0, 0, 1, 9, 0),
            "summary": "This is neutral text.",
        }
    )

    result = clean_news_item(entry, "Infosys")

    assert result is not None
    assert result["title"] == "Infosys secures new deal"
    assert result["source"] == "Finance Media"


def test_clean_news_item_older_than_7_days():
    entry = DotDict(
        {
            "title": "Old News - Some Source",
            "published": "Mon, 01 Jan 2024 10:00:00 GMT",
            "published_parsed": (2024, 1, 1, 10, 0, 0, 0, 1, 0),
            "summary": "Summary",
        }
    )

    result = clean_news_item(entry, "Any")

    assert result is None


def test_clean_news_item_exactly_7_days():
    entry = DotDict(
        {
            "title": "7 Days Ago News - Some Source",
            "published": "Wed, 03 Jan 2024 10:00:00 GMT",
            "published_parsed": (2024, 1, 3, 10, 0, 0, 2, 3, 0),
            "summary": "Summary",
        }
    )

    result = clean_news_item(entry, "Any")

    assert result is not None
    assert result["date"] == "03 Jan 2024"


def test_clean_news_item_missing_published_date():
    entry = DotDict(
        {
            "title": "No Date News - Source",
            "summary": "Summary",
        }
    )

    result = clean_news_item(entry, "Any")

    assert result is not None
    assert result["date"] == "10 Jan 2024"


def test_clean_news_item_invalid_published_parsed():
    entry = DotDict(
        {
            "title": "Invalid Parsed Date News - Source",
            "published": "Some string",
            "published_parsed": None,
            "summary": "Summary",
        }
    )

    result = clean_news_item(entry, "Any")

    assert result is not None
    assert result["date"] == "10 Jan 2024"


def test_clean_news_item_exception_in_date_parsing():
    entry = DotDict(
        {
            "title": "Exception in Date News - Source",
            "published": "Some string",
            "published_parsed": (2024, 1),
            "summary": "Summary",
        }
    )

    result = clean_news_item(entry, "Any")

    assert result is not None
    assert result["date"] == "10 Jan 2024"


# --- corporate filings: exchange primary, news fallback ------------------
#
# The merge is the contract worth pinning. NSE refuses cloud IPs often
# enough that the fallback is not hypothetical, and the failure that would
# hurt is a silent one: an empty filings section on a day the exchange
# happened to block us.


def _news_filing(name="Reported filing"):
    return {
        "company": "Some Co",
        "filing": name,
        "industry": "Corporate",
        "date": "10 Jan 2024",
        "source": "Economic Times",
        "link": "http://example.com/news",
    }


def _nse_filing(name="Awarding of Order / Receipt of Order"):
    return {
        "company": "Tata Motors",
        "filing": name,
        "industry": "Automotive",
        "date": "10 Jan 2024",
        "source": "NSE",
        "link": "https://nsearchives.nseindia.com/corporate/x.pdf",
    }


def _run_filings(nse_result, news_result):
    import asyncio
    import scraper

    async def fake_news(session, watchlist):
        return news_result

    with patch.object(
        scraper, "nse_fetch_filings", return_value=nse_result
    ), patch.object(scraper, "_fetch_filing_news_async", fake_news):
        return asyncio.run(scraper.fetch_exchange_filings_async(None, {}))


def test_filings_merge_both_sources():
    out = _run_filings([_nse_filing()], [_news_filing()])
    assert len(out) == 2
    assert {f["source"] for f in out} == {"NSE", "Economic Times"}


def test_filings_survive_a_blocked_exchange():
    """A blocked NSE degrades the section; it must not empty it."""
    out = _run_filings([], [_news_filing()])
    assert len(out) == 1
    assert out[0]["source"] == "Economic Times"


def test_filings_work_with_no_news_coverage():
    out = _run_filings([_nse_filing()], [])
    assert len(out) == 1
    assert out[0]["source"] == "NSE"


def test_exchange_record_wins_a_duplicate():
    """Same subject from both sides keeps the primary version — the one with
    the exact symbol match and the filed PDF."""
    duplicate = "Awarding of Order / Receipt of Order"
    out = _run_filings([_nse_filing(duplicate)], [_news_filing(duplicate)])
    assert len(out) == 1
    assert out[0]["source"] == "NSE"
    assert out[0]["industry"] == "Automotive"


def test_filings_are_capped():
    many_nse = [_nse_filing(f"NSE filing {i}") for i in range(8)]
    many_news = [_news_filing(f"News filing {i}") for i in range(8)]
    out = _run_filings(many_nse, many_news)
    assert len(out) == 10
    # The cap must not spend itself on the weaker source.
    assert sum(1 for f in out if f["source"] == "NSE") == 8
