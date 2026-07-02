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
