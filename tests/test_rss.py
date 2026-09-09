import unittest
import datetime
from unittest.mock import patch
from providers.rss import clean_news_item


class DotDict(dict):
    """A dictionary that supports attribute-style access for mocking feedparser entries."""

    def __getattr__(self, item):
        if item in self:
            return self[item]
        raise AttributeError(f"'DotDict' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value


class TestRSSProvider(unittest.TestCase):
    def setUp(self):
        # A baseline valid entry for a query term
        self.query_term = "Technology"
        self.base_entry = DotDict(
            {
                "title": "A Great Tech Article - TechNews",
                "link": "https://example.com/tech-article",
                "published": "Tue, 15 Aug 2023 10:00:00 GMT",
                "published_parsed": (2023, 8, 15, 10, 0, 0, 1, 227, 0),
                "summary": "This is a great article about technology.",
                "source": {"title": "TechNews"},
            }
        )

    @patch("providers.rss.datetime")
    def test_clean_news_item_happy_path(self, mock_datetime):
        # Mock datetime to ensure the article isn't considered too old
        mock_date = datetime.date(2023, 8, 16)
        mock_datetime.date.today.return_value = mock_date
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 8, 16)

        result = clean_news_item(self.base_entry, self.query_term)

        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "A Great Tech Article")
        self.assertEqual(result["source"], "TechNews")
        self.assertEqual(result["link"], "https://example.com/tech-article")
        self.assertEqual(result["date"], "15 Aug 2023")
        self.assertEqual(result["relevance"], "Technology")
        self.assertIn("impact", result)

    @patch("providers.rss.datetime")
    def test_clean_news_item_html_stripping(self, mock_datetime):
        mock_date = datetime.date(2023, 8, 16)
        mock_datetime.date.today.return_value = mock_date
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 8, 16)

        entry = DotDict(
            {
                "title": "<b>Tech Update</b> &amp; More - NewsSource",
                "link": "https://example.com",
                "published_parsed": (2023, 8, 15, 10, 0, 0, 1, 227, 0),
                "summary": "<p>This is a summary with <i>HTML</i> &amp; stuff.</p>",
            }
        )

        result = clean_news_item(entry, self.query_term)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Tech Update & More")
        self.assertEqual(result["source"], "NewsSource")  # Split from title
        # Actually impact analysis receives title and summary, but we check if they are formatted properly

    @patch("providers.rss.datetime")
    def test_clean_news_item_age_filtering(self, mock_datetime):
        # Current date is more than 7 days after the article's published_parsed date (2023-08-15)
        mock_date = datetime.date(2023, 8, 25)
        mock_datetime.date.today.return_value = mock_date
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 8, 25)

        result = clean_news_item(self.base_entry, self.query_term)
        self.assertIsNone(result)

    @patch("providers.rss.datetime")
    def test_clean_news_item_date_fallback(self, mock_datetime):
        # Entry without published or published_parsed
        entry = DotDict(
            {
                "title": "A Great Tech Article - TechNews",
                "link": "https://example.com/tech-article",
                "summary": "This is a great article about technology.",
                "source": {"title": "TechNews"},
            }
        )

        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 8, 16)
        mock_datetime.date.today.return_value = datetime.date(2023, 8, 16)

        result = clean_news_item(entry, self.query_term)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "16 Aug 2023")

    @patch("providers.rss.datetime")
    def test_clean_news_item_source_extraction(self, mock_datetime):
        mock_date = datetime.date(2023, 8, 16)
        mock_datetime.date.today.return_value = mock_date
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 8, 16)

        # Title contains ' - ' indicating source at the end
        entry = DotDict(
            {
                "title": "New Tech Breakthrough - ImportantSource",
                "link": "https://example.com",
                "published_parsed": (2023, 8, 15, 10, 0, 0, 1, 227, 0),
            }
        )

        result = clean_news_item(entry, self.query_term)
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "New Tech Breakthrough")
        self.assertEqual(result["source"], "ImportantSource")

        # Fallback to source title if no ' - ' in title
        entry2 = DotDict(
            {
                "title": "New Tech Breakthrough",
                "link": "https://example.com",
                "source": {"title": "AnotherSource"},
                "published_parsed": (2023, 8, 15, 10, 0, 0, 1, 227, 0),
            }
        )

        result2 = clean_news_item(entry2, self.query_term)
        self.assertIsNotNone(result2)
        self.assertEqual(result2["title"], "New Tech Breakthrough")
        self.assertEqual(result2["source"], "AnotherSource")

    @patch("providers.rss.datetime")
    @patch("providers.rss.analyze_sentiment")
    def test_clean_news_item_summary_truncation_cleanup(
        self, mock_analyze_sentiment, mock_datetime
    ):
        mock_date = datetime.date(2023, 8, 16)
        mock_datetime.date.today.return_value = mock_date
        mock_datetime.date.side_effect = lambda *args, **kw: datetime.date(*args, **kw)
        mock_datetime.datetime.now.return_value = datetime.datetime(2023, 8, 16)

        mock_analyze_sentiment.return_value = "Neutral"

        entry = DotDict(
            {
                "title": "Article Title",
                "link": "https://example.com",
                "published_parsed": (2023, 8, 15, 10, 0, 0, 1, 227, 0),
                "summary": "This is a summary that gets cut off... Read more",
            }
        )

        result = clean_news_item(entry, self.query_term)
        self.assertIsNotNone(result)

        # We can verify the summary cleanup by checking what is passed to analyze_sentiment
        mock_analyze_sentiment.assert_called_once_with(
            "Article Title", "This is a summary that gets cut off"
        )


if __name__ == "__main__":
    unittest.main()
