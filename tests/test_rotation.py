import unittest
from analysis.rotation import detect_emerging_players


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


class TestScreenedCandidatesReachRotation(unittest.TestCase):
    """A peer that cleared the fundamental screen must actually be evaluated.

    Before this path existed, discovery ran only on headline regex plus name
    resolution, so a listed competitor sitting in the Screener peer radar with
    a known ticker was never even looked at.
    """

    def _run(self, screened, monkey):
        import analysis.rotation as rot

        evaluated = []

        def fake_resolve(name, session=None):
            evaluated.append(("resolved", name))
            return None, None

        # Stop evaluation right after resolution so the test never touches
        # the network; what matters is which candidates got that far.
        def fake_ticker(symbol):
            evaluated.append(("priced", symbol))
            raise RuntimeError("no network in tests")

        monkey(rot, "resolve_ticker_from_name", fake_resolve)
        monkey(rot, "get_cached_ticker", fake_ticker)
        watchlist = {"sec": [{"ticker": "HELD", "name": "Held Co"}]}
        rot.auto_curate_watchlist({"sec": []}, watchlist, screened_candidates=screened)
        return evaluated

    def test_preresolved_candidate_skips_name_resolution(self):
        import analysis.rotation as rot

        originals = {}

        def monkey(mod, attr, value):
            originals.setdefault(attr, getattr(mod, attr))
            setattr(mod, attr, value)

        try:
            evaluated = self._run(
                {"sec": [{"name": "Syrma SGS Tech.", "ticker": "SYRMA"}]}, monkey
            )
        finally:
            for attr, value in originals.items():
                setattr(rot, attr, value)

        # It went straight to the price check under its Screener ticker,
        # rather than being thrown away by name resolution.
        self.assertIn(("priced", "SYRMA.NS"), evaluated)
        self.assertNotIn(("resolved", "Syrma SGS Tech."), evaluated)

    def test_existing_holding_is_not_re_added(self):
        import analysis.rotation as rot

        originals = {}

        def monkey(mod, attr, value):
            originals.setdefault(attr, getattr(mod, attr))
            setattr(mod, attr, value)

        try:
            evaluated = self._run(
                {"sec": [{"name": "Held Co", "ticker": "HELD"}]}, monkey
            )
        finally:
            for attr, value in originals.items():
                setattr(rot, attr, value)

        self.assertEqual(evaluated, [])
