import pytest
import datetime
from unittest.mock import patch
from scraper import clean_news_item


class MockDate(datetime.date):
    @classmethod
    def today(cls):
        return datetime.date(2024, 1, 10)


class MockDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2024, 1, 10, 10, 0, 0)


class FeedParserDictMock(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


@pytest.fixture
def mock_analyze_sentiment():
    with patch("scraper.analyze_sentiment", return_value="Neutral") as mock_sentiment:
        yield mock_sentiment


@patch("scraper.datetime.datetime", MockDateTime)
@patch("scraper.datetime.date", MockDate)
def test_clean_news_item_happy_path(mock_analyze_sentiment):
    entry = FeedParserDictMock(
        {
            "title": "A Great Policy Change - Finance Times",
            "link": "https://example.com/news/123",
            "published": "Tue, 09 Jan 2024 10:00:00 GMT",
            "published_parsed": (2024, 1, 9, 10, 0, 0, 1, 9, 0),
            "summary": "This policy will change everything... Read more",
            "source": {"title": "Finance Times"},
        }
    )

    mock_analyze_sentiment.return_value = "Positive"

    result = clean_news_item(entry, "Policy")

    assert result is not None
    assert result["title"] == "A Great Policy Change"
    assert result["source"] == "Finance Times"
    assert result["link"] == "https://example.com/news/123"
    assert result["date"] == "09 Jan 2024"
    assert result["impact"] == "Positive"
    assert result["relevance"] == "Policy"


@patch("scraper.datetime.datetime", MockDateTime)
@patch("scraper.datetime.date", MockDate)
def test_clean_news_item_missing_details(mock_analyze_sentiment):
    entry = FeedParserDictMock(
        {
            "title": "Short Title",
        }
    )

    result = clean_news_item(entry, "Test")

    assert result is not None
    assert result["title"] == "Short Title"
    assert result["source"] == "Finance Media"  # Default
    assert result["link"] == ""
    assert result["date"] == "10 Jan 2024"  # Default to now() if published is missing
    assert result["impact"] == "Neutral"
    assert result["relevance"] == "Test"


@patch("scraper.datetime.datetime", MockDateTime)
@patch("scraper.datetime.date", MockDate)
def test_clean_news_item_old_article(mock_analyze_sentiment):
    entry = FeedParserDictMock(
        {
            "title": "Old News - Finance Times",
            "published": "Tue, 01 Jan 2024 10:00:00 GMT",
            "published_parsed": (2024, 1, 1, 10, 0, 0, 0, 1, 0),
        }
    )

    result = clean_news_item(entry, "Policy")

    assert result is None  # Older than 7 days (2024-01-10 - 2024-01-01 = 9 days)


@patch("scraper.datetime.datetime", MockDateTime)
@patch("scraper.datetime.date", MockDate)
def test_clean_news_item_source_splitting(mock_analyze_sentiment):
    entry = FeedParserDictMock(
        {
            "title": "A Great Policy Change - Detailed - Finance Times",
        }
    )

    result = clean_news_item(entry, "Policy")

    assert result is not None
    assert result["title"] == "A Great Policy Change"
    assert result["source"] == "Finance Times"


@patch("scraper.datetime.datetime", MockDateTime)
@patch("scraper.datetime.date", MockDate)
def test_clean_news_item_published_parsed_exception(mock_analyze_sentiment):
    entry = FeedParserDictMock(
        {
            "title": "Some News",
            "published": "Invalid Date Format",
            "published_parsed": None,  # Should trigger the except block when trying to index or it will just fall back
        }
    )

    result = clean_news_item(entry, "Test")

    assert result is not None
    assert result["date"] == "10 Jan 2024"


@patch("scraper.datetime.datetime", MockDateTime)
@patch("scraper.datetime.date", MockDate)
def test_clean_news_item_html_stripping(mock_analyze_sentiment):
    entry = FeedParserDictMock(
        {
            "title": "<a href='#'>News Title</a>",
            "summary": "This is a summary.<br>...Read more",
        }
    )
    result = clean_news_item(entry, "Test")
    assert result["title"] == "News Title"
