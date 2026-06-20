import unittest
from metrics import detect_emerging_players


class TestDetectEmergingPlayers(unittest.TestCase):
    def test_detect_emerging_players_basic(self):
        """Test basic detection of emerging players and ensuring companies in watchlist are ignored."""
        brief_data = {
            "technology": [
                {"title": "Acme Corp announces new product"},
                {"title": "TCS Limited shares fall"},
                {"title": "Some random news without corp names"},
            ],
            "finance": [
                {"title": "Beta Technologies merges with Gamma Solutions"},
                {"title": "India budget announced"},  # 'India' is ignored word
            ],
        }

        watchlist = {
            "technology": [{"ticker": "TCS", "name": "Tata Consultancy Services"}]
        }

        result = detect_emerging_players(brief_data, watchlist)

        self.assertIn("technology", result)
        self.assertEqual(result["technology"], ["Acme Corp"])
        self.assertIn("finance", result)
        self.assertEqual(result["finance"], ["Beta Technologies", "Gamma Solutions"])

    def test_ignore_list(self):
        """Test that words in the ignore list do not trigger detection."""
        brief_data = {
            "general": [
                {"title": "India Technologies launches new service"},
                {"title": "Delhi Infrastructure project started"},
                {"title": "Cabinet Solutions is a weird name"},
                {"title": "National Corp reports earnings"},
            ]
        }
        watchlist = {}
        result = detect_emerging_players(brief_data, watchlist)
        self.assertEqual(result, {})

    def test_short_names(self):
        """Test that very short captured names (< 3 chars) are ignored."""
        brief_data = {
            "general": [
                {"title": "Xi Corp invests heavily"},
                {"title": "Ab Limited announces dividend"},
            ]
        }
        watchlist = {}
        result = detect_emerging_players(brief_data, watchlist)
        self.assertEqual(result, {})

    def test_emerging_players_sector_skipped(self):
        """Test that the emerging_players sector in brief_data is correctly skipped."""
        brief_data = {"emerging_players": [{"title": "Omega Corp is emerging"}]}
        watchlist = {}
        result = detect_emerging_players(brief_data, watchlist)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
