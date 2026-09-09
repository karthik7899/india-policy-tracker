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
        mock_log.error.assert_called_once()
        self.assertIn("watchlist.json not found", mock_log.error.call_args[0][0])

    @patch("builtins.open", new_callable=mock_open, read_data="invalid json")
    @patch("config.log")
    def test_load_watchlist_invalid_json(self, mock_log, mock_file):
        result = config.load_watchlist()
        self.assertEqual(result, config.STOCK_WATCHLIST)
        mock_file.assert_called_once()
        mock_log.error.assert_called_once()
        self.assertIn("corrupt", mock_log.error.call_args[0][0])

    def test_seed_watchlist_is_minimal(self):
        """The fallback seed must never carry stale market data snapshots."""
        allowed_keys = {"ticker", "name", "catalyst"}
        for sector, stocks in config.STOCK_WATCHLIST.items():
            for stock in stocks:
                self.assertTrue(
                    set(stock) <= allowed_keys,
                    f"{sector}/{stock.get('ticker')} has non-seed keys: "
                    f"{set(stock) - allowed_keys}",
                )


class TestSaveWatchlist(unittest.TestCase):

    @patch("utils.atomic_write_json")
    def test_save_watchlist_success(self, mock_atomic):
        watchlist = {"test": "data"}
        result = config.save_watchlist(watchlist)
        self.assertTrue(result)
        mock_atomic.assert_called_once()
        args, _ = mock_atomic.call_args
        self.assertEqual(args[0], watchlist)
        self.assertTrue(args[1].endswith("watchlist.json"))

    @patch("utils.atomic_write_json", side_effect=OSError("Disk full"))
    def test_save_watchlist_oserror(self, mock_atomic):
        watchlist = {"test": "data"}
        result = config.save_watchlist(watchlist)
        self.assertFalse(result)
        mock_atomic.assert_called_once()
        args, _ = mock_atomic.call_args
        self.assertEqual(args[0], watchlist)
        self.assertTrue(args[1].endswith("watchlist.json"))


if __name__ == "__main__":
    unittest.main()
