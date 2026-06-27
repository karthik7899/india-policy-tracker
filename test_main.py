import unittest
from unittest.mock import patch
import main


class TestSaveDataForDashboard(unittest.TestCase):
    @patch("utils.atomic_write_json")
    def test_save_data_for_dashboard(self, mock_atomic_write):
        brief_data = {
            "policy_news": ["policy"],
            "market_news": ["market"],
            "emerging_players": ["player"],
            "curation_log": ["log"],
        }
        watchlist = {"AAPL": {"name": "Apple"}}

        if hasattr(main, "log"):
            with patch("main.log.info") as mock_log:
                main.save_data_for_dashboard(brief_data, watchlist)
        else:
            main.save_data_for_dashboard(brief_data, watchlist)

        self.assertTrue(mock_atomic_write.called)
        self.assertEqual(mock_atomic_write.call_args[0][1], "dashboard_data.json")

        args, kwargs = mock_atomic_write.call_args
        output_data = args[0]

        self.assertIn("last_updated", output_data)
        self.assertIn("watchlist", output_data)
        self.assertEqual(output_data["watchlist"], watchlist)

        # Accommodate both implementations
        if "news" in output_data:
            self.assertEqual(output_data["news"], ["policy", "market"])
            self.assertEqual(output_data["emerging_players"], ["player"])
            self.assertEqual(output_data["curation_log"], ["log"])
        else:
            self.assertEqual(output_data["briefing"], brief_data)
            self.assertIn("sectors", output_data)


if __name__ == "__main__":
    unittest.main()
