import unittest
from unittest.mock import patch, mock_open

import config


class TestLoadWatchlist(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open, read_data='{"test": "data"}')
    def test_load_watchlist_success(self, mock_file):
        result = config.load_watchlist()
        self.assertEqual(result, {"test": "data"})
        mock_file.assert_called_once()

    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("config.log")
    def test_load_watchlist_file_not_found(self, mock_log, mock_file):
        result = config.load_watchlist()
        self.assertEqual(result, config.STOCK_WATCHLIST)
        mock_file.assert_called_once()
        mock_log.warning.assert_called_once_with(
            "watchlist.json not found, using default STOCK_WATCHLIST dictionary."
        )

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("config.log")
    def test_load_watchlist_invalid_json(self, mock_log, mock_file):
        result = config.load_watchlist()
        self.assertEqual(result, config.STOCK_WATCHLIST)
        mock_file.assert_called_once()
        mock_log.error.assert_called_once_with(
            "Error decoding watchlist.json. Using default STOCK_WATCHLIST dictionary."
        )


if __name__ == "__main__":
    unittest.main()
