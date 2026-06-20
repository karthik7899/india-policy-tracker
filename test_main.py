import unittest
from unittest.mock import patch, mock_open, ANY
import datetime
import json
import main

class TestSaveDataForDashboard(unittest.TestCase):
    @patch('main.json.dump')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_data_for_dashboard(self, mock_file, mock_json_dump):
        brief_data = {
            "policy_news": ["policy"],
            "market_news": ["market"],
            "emerging_players": ["player"],
            "curation_log": ["log"]
        }
        watchlist = {"AAPL": {"name": "Apple"}}

        if hasattr(main, 'log'):
            with patch('main.log.info') as mock_log:
                main.save_data_for_dashboard(brief_data, watchlist)
        else:
            main.save_data_for_dashboard(brief_data, watchlist)

        self.assertTrue(mock_file.called)
        self.assertEqual(mock_file.call_args[0][0], "dashboard_data.json")
        self.assertEqual(mock_file.call_args[0][1], "w")

        self.assertTrue(mock_json_dump.called)

        args, kwargs = mock_json_dump.call_args
        output_data = args[0]

        self.assertIn("last_updated", output_data)
        self.assertIn("watchlist", output_data)
        self.assertEqual(output_data["watchlist"], watchlist)

        # Accommodate both implementations
        if "news" in output_data:
            self.assertEqual(output_data["news"], ["policy", "market"])
            self.assertEqual(output_data["emerging_players"], ["player"])
            self.assertEqual(output_data["curation_log"], ["log"])
            self.assertEqual(kwargs.get("indent"), 4)
        else:
            self.assertEqual(output_data["briefing"], brief_data)
            self.assertIn("sectors", output_data)
            self.assertEqual(kwargs.get("indent"), 2)
            self.assertEqual(kwargs.get("ensure_ascii"), False)

if __name__ == '__main__':
    unittest.main()
