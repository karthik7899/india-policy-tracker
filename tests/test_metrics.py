import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from metrics import update_single_stock

class TestMetrics(unittest.TestCase):

    @patch("metrics.yf.Ticker")
    def test_update_single_stock_success(self, mock_ticker_class):
        # Setup mock stock dictionary
        stock = {"ticker": "RELIANCE", "price": "2500.00"}

        # Setup mock Ticker instance
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker

        # Mock history DataFrame with 'Close' column
        mock_history = pd.DataFrame({"Close": [2600.00]})
        mock_ticker.history.return_value = mock_history

        # Mock info dictionary
        mock_ticker.info = {
            "targetMedianPrice": 2800.00,
            "targetMeanPrice": 2750.00,
            "targetHighPrice": 3000.00,
            "targetLowPrice": 2400.00,
            "numberOfAnalystOpinions": 10,
            "recommendationKey": "strong_buy",
            "recommendationMean": 1.5,
            "revenueGrowth": 0.15,
            "earningsGrowth": 0.20,
        }

        # Call function
        update_single_stock(stock)

        # Assert stock was updated correctly
        self.assertEqual(stock["price"], "2600.00")
        self.assertEqual(stock["target_median"], "2800.00")
        self.assertEqual(stock["target"], "2800.00")
        self.assertEqual(stock["target_high"], "3000.00")
        self.assertEqual(stock["target_low"], "2400.00")
        self.assertEqual(stock["analyst_count"], 10)
        self.assertEqual(stock["rating"], "Strong Buy")
        self.assertEqual(stock["rec_score"], 1.5)
        self.assertEqual(stock["revenue_growth"], "+15.0%")
        self.assertEqual(stock["earnings_growth"], "+20.0%")

        # Calculate expected growth_pct
        target_price = 2800.00
        live_price = 2600.00
        expected_growth_val = ((target_price - live_price) / live_price) * 100
        expected_sign = "+" if expected_growth_val > 0 else ""
        self.assertEqual(stock["growth_pct"], f"{expected_sign}{expected_growth_val:.1f}%")

    @patch("metrics.yf.Ticker")
    @patch("metrics.log")
    def test_update_single_stock_empty_history(self, mock_log, mock_ticker_class):
        stock = {"ticker": "RELIANCE", "price": "2500.00"}

        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker

        # Empty history
        mock_ticker.history.return_value = pd.DataFrame()

        # Mock info dictionary
        mock_ticker.info = {
            "targetMedianPrice": 2800.00,
        }

        update_single_stock(stock)

        # Price should remain static but still be parsed
        self.assertEqual(stock["price"], "2500.00")
        self.assertEqual(stock["target_median"], "2800.00")
        self.assertEqual(stock["target"], "2800.00")

        # log.warning should have been called
        mock_log.warning.assert_called_once()
        self.assertTrue("No close history" in mock_log.warning.call_args[0][0])

    @patch("metrics.yf.Ticker")
    @patch("metrics.log")
    def test_update_single_stock_exception(self, mock_log, mock_ticker_class):
        stock = {"ticker": "RELIANCE", "price": "2500.00"}

        # Simulate exception
        mock_ticker_class.side_effect = Exception("API Error")

        update_single_stock(stock)

        # Verify defaults were set and not overwritten
        self.assertEqual(stock["rating"], "N/A")
        self.assertIsNone(stock["revenue_growth"])
        self.assertIsNone(stock["earnings_growth"])
        self.assertIsNone(stock["analyst_count"])
        self.assertIsNone(stock["target_median"])
        self.assertIsNone(stock["target_high"])
        self.assertIsNone(stock["target_low"])
        self.assertIsNone(stock["rec_score"])

        # Price and target aren't reset to None, they just don't get updated with fetched values
        # Since 'target' key isn't set beforehand, it won't be present
        self.assertEqual(stock["price"], "2500.00")
        self.assertNotIn("target", stock)

        # Ensure exception was logged
        mock_log.error.assert_called_once()
        self.assertTrue("Error updating price/metrics" in mock_log.error.call_args[0][0])
