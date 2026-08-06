"""Tests for the promoter pledge tracker (analysis/pledging.py).

The load-bearing distinction is between a company with no pledge and a
company whose pledge could not be read. Screener omits the row in both cases,
and treating the second as an all-clear is the failure this module is written
around.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.pledging import assess, pledge_warnings  # noqa: E402


class TestDisclosure:
    def test_a_missing_pledge_is_not_disclosed_not_zero(self):
        """The whole point. Screener prints no row for companies with no
        pledge and for pages this parser failed to match."""
        verdict = assess(None)
        assert verdict["status"] == "not_disclosed"
        assert verdict["pledged_pct"] is None
        assert verdict["severity"] is None

    def test_an_explicit_zero_is_a_real_all_clear(self):
        verdict = assess(0.0)
        assert verdict["status"] == "none"
        assert verdict["pledged_pct"] == 0.0

    def test_an_unreadable_value_is_not_disclosed(self):
        assert assess("n/a")["status"] == "not_disclosed"

    def test_not_disclosed_holdings_raise_no_alerts(self):
        watchlist = {
            "fmcg": [{"ticker": "A", "name": "A Ltd", "screener": {"promoter_pct": 60}}]
        }
        assert pledge_warnings(watchlist) == []


class TestSeverityLadder:
    def test_a_large_pledge_is_critical_on_its_own(self):
        assert assess(45.0)["severity"] == "Critical"

    def test_high_and_rising_is_critical(self):
        """The spec's rule."""
        verdict = assess(18.0, pledged_change=1.2)
        assert verdict["severity"] == "Critical"
        assert verdict["rising"] is True

    def test_high_and_near_the_low_is_critical(self):
        verdict = assess(18.0, pct_above_low=8.0)
        assert verdict["severity"] == "Critical"
        assert verdict["near_low"] is True

    def test_high_but_stable_and_well_off_the_low_is_high_not_critical(self):
        """A standing pledge is not a squeeze in progress."""
        verdict = assess(18.0, pledged_change=0.0, pct_above_low=60.0)
        assert verdict["severity"] == "High"

    def test_a_notable_pledge_rising_into_a_weak_price_escalates(self):
        assert assess(8.0, pledged_change=1.0, pct_above_low=5.0)["severity"] == "High"

    def test_a_small_stable_pledge_raises_nothing(self):
        assert assess(2.0, pledged_change=0.0, pct_above_low=50.0)["severity"] is None

    def test_a_small_but_rising_pledge_is_still_worth_a_medium(self):
        assert assess(2.0, pledged_change=1.5)["severity"] == "Medium"

    def test_rounding_noise_does_not_count_as_rising(self):
        """Pledge percentages are reported to one decimal and move in steps."""
        assert assess(18.0, pledged_change=0.1, pct_above_low=60.0)["rising"] is False


class TestReasons:
    def test_the_pledge_level_is_always_stated(self):
        assert "18.0% of promoter holding pledged" in assess(18.0)["reasons"][0]

    def test_a_missing_price_range_is_stated_not_assumed_safe(self):
        """ "We could not check the price" and "the price is fine" lead to
        different conclusions."""
        reasons = " ".join(assess(18.0, pct_above_low=None)["reasons"])
        assert "52-week range not available" in reasons

    def test_a_known_range_is_quoted(self):
        reasons = " ".join(assess(18.0, pct_above_low=8.0)["reasons"])
        assert "8% above its 52-week low" in reasons
        assert "not available" not in reasons


class TestWarnings:
    WATCHLIST = {
        "fmcg": [
            {
                "ticker": "PLEDGED",
                "name": "Pledged Ltd",
                "screener": {
                    "pledged_pct": 22.0,
                    "pledged_change": 3.0,
                    "pct_above_low": 6.0,
                },
            },
            {
                "ticker": "CLEAN",
                "name": "Clean Ltd",
                "screener": {"pledged_pct": 0.0},
            },
            {"ticker": "UNKNOWN", "name": "Unknown Ltd", "screener": {}},
        ]
    }

    def test_only_the_pledged_holding_alerts(self):
        alerts = pledge_warnings(self.WATCHLIST)
        assert [a["ticker"] for a in alerts] == ["PLEDGED"]

    def test_the_alert_is_a_risk_at_critical(self):
        alert = pledge_warnings(self.WATCHLIST)[0]
        assert alert["direction"] == "risk"
        assert alert["severity"] == "Critical"
        assert alert["category"] == "Promoter Pledging"

    def test_the_signal_carries_every_reason(self):
        signal = pledge_warnings(self.WATCHLIST)[0]["signal"]
        assert "22.0%" in signal and "+3.0pp" in signal and "6% above" in signal

    def test_the_sector_label_is_used_not_the_slug(self):
        """Warnings carry the label; sector ranking downstream keys on it."""
        from config import SECTOR_METADATA

        assert (
            pledge_warnings(self.WATCHLIST)[0]["sector"]
            == SECTOR_METADATA["fmcg"]["label"]
        )

    def test_macro_indicators_are_skipped(self):
        watchlist = {
            "macro_indicators": [
                {"ticker": "IDX", "name": "Index", "screener": {"pledged_pct": 50.0}}
            ]
        }
        assert pledge_warnings(watchlist) == []

    def test_language_stays_in_the_review_register(self):
        signal = pledge_warnings(self.WATCHLIST)[0]["signal"].lower()
        assert "buy" not in signal and "sell" not in signal

    def test_malformed_input_never_raises(self):
        assert pledge_warnings(None) == []
        assert pledge_warnings({"fmcg": [None, "x", {}]}) == []


class TestRangeComputation:
    def test_pct_above_low_is_measured_from_the_low(self):
        import pandas as pd

        from analysis.growth import _range_from_frame

        frame = pd.DataFrame({"Close": [100.0, 50.0, 200.0, 60.0]})
        got = _range_from_frame(frame)
        assert got["week52_low"] == 50.0
        assert got["week52_high"] == 200.0
        assert got["pct_above_low"] == 20.0  # last 60 is 20% above the 50 low

    def test_a_frame_without_closes_yields_nothing(self):
        import pandas as pd

        from analysis.growth import _range_from_frame

        assert _range_from_frame(pd.DataFrame({"Volume": [1, 2]})) is None
        assert _range_from_frame(None) is None

    def test_an_all_nan_series_yields_nothing(self):
        import pandas as pd

        from analysis.growth import _range_from_frame

        assert _range_from_frame(pd.DataFrame({"Close": [float("nan")] * 3})) is None
