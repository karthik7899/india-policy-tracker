"""Tests for tradeability (analysis/liquidity.py).

The numbers are scaled to the real split in this book: index names turn over
hundreds of crore a day, while several micro-cap holdings trade under one.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis import liquidity  # noqa: E402


def _series(price, shares, days=20):
    return [price] * days, [shares] * days


class TestADVT:
    def test_turnover_is_value_not_share_count(self):
        """A lakh shares of a Rs 20 stock is not a lakh shares of a Rs 4,000 one."""
        cheap = liquidity.average_daily_value_cr(*_series(20.0, 100000))
        dear = liquidity.average_daily_value_cr(*_series(4000.0, 100000))
        assert cheap == 0.2
        assert dear == 40.0

    def test_pairs_each_close_with_its_own_volume(self):
        """Averaging the two series separately hides the gap days.

        One heavy session at a low price plus one light session at a high
        price: the honest mean is 5.5 crore, but averaging price and volume
        independently gives 10.
        """
        closes = [100.0, 200.0]
        volumes = [100000, 10000]
        # (100*100000 + 200*10000) / 2 = 6,000,000 -> 0.6 crore
        assert liquidity.average_daily_value_cr(closes, volumes) == 0.6

    def test_holiday_rows_do_not_drag_the_average_down(self):
        """Zero-volume rows are closed sessions, not thin ones."""
        closes = [100.0, 100.0, 100.0]
        volumes = [1000000, 0, 1000000]
        assert liquidity.average_daily_value_cr(closes, volumes) == 10.0

    def test_missing_inputs_yield_none_not_zero(self):
        assert liquidity.average_daily_value_cr(None, None) is None
        assert liquidity.average_daily_value_cr([], []) is None
        assert liquidity.average_daily_value_cr([None], [None]) is None


class TestBands:
    def test_bands_track_the_institutional_floor(self):
        assert liquidity.classify(0.4) == "illiquid"
        assert liquidity.classify(3.0) == "thin"
        assert liquidity.classify(12.0) == "adequate"
        assert liquidity.classify(400.0) == "liquid"

    def test_unknown_is_distinct_from_illiquid(self):
        """No data is not the same finding as no volume."""
        assert liquidity.classify(None) == "unknown"


class TestExitHorizon:
    def test_days_to_exit_scales_with_ticket(self):
        # Rs 10 Cr/day at 20% participation absorbs Rs 2 Cr per session.
        assert liquidity.days_to_liquidate(1.0, 10.0) == 0.5
        assert liquidity.days_to_liquidate(5.0, 10.0) == 2.5

    def test_a_thin_stock_takes_many_sessions(self):
        days = liquidity.days_to_liquidate(5.0, 0.5)
        assert days == 50.0

    def test_no_turnover_gives_no_estimate(self):
        assert liquidity.days_to_liquidate(1.0, None) is None
        assert liquidity.days_to_liquidate(1.0, 0) is None


class TestAssessment:
    def test_assessment_reports_its_inputs(self):
        result = liquidity.assess(*_series(100.0, 1000000))
        assert result["advt_cr"] == 10.0
        assert result["liquidity_band"] == "adequate"
        assert result["days_to_exit_1cr"] == 0.5
        assert result["sessions"] == 20

    def test_warning_fires_only_for_hard_to_trade_names(self):
        thin = liquidity.assess(*_series(50.0, 10000))  # Rs 0.05 Cr/day
        warning = liquidity.liquidity_warning("SPELS", thin)
        assert warning is not None
        assert "Illiquid" in warning

        deep = liquidity.assess(*_series(3000.0, 1000000))  # Rs 300 Cr/day
        assert liquidity.liquidity_warning("TCS", deep) is None

    def test_no_warning_when_liquidity_is_unknown(self):
        """Silence about an unmeasured stock, not an accusation."""
        unknown = liquidity.assess(None, None)
        assert liquidity.liquidity_warning("X", unknown) is None


class TestMissingSessions:
    """A gap in the data must read as a gap, never as easy trading."""

    def test_nan_sessions_are_skipped_not_averaged_in(self):
        closes = [100.0, float("nan"), 100.0]
        volumes = [1000000, float("nan"), 1000000]
        assert liquidity.average_daily_value_cr(closes, volumes) == 10.0

    def test_a_nan_turnover_is_unknown_not_liquid(self):
        """Every comparison against NaN is False, so an unguarded band check
        falls through to the most favourable label."""
        assert liquidity.classify(float("nan")) == "unknown"

    def test_an_all_nan_series_yields_no_estimate(self):
        nans = [float("nan")] * 5
        assert liquidity.average_daily_value_cr(nans, nans) is None
        assert liquidity.liquidity_warning("X", liquidity.assess(nans, nans)) is None


class TestSurvivesTheScreenerRebuild:
    """The failure that made this feature inert in its first production run.

    Turnover was written into ``stock["screener"]`` during the price fetch.
    The Screener fetch that runs next assigns that key wholesale
    (``stock["screener"] = sc_data``), so all 67 holdings got turnover and all
    67 lost it before anything read it. Coverage was 0/67 with no error
    anywhere in the log.
    """

    @staticmethod
    def _rebuild_screener(watchlist):
        """What providers/screener.py does to every holding."""
        for stocks in watchlist.values():
            for stock in stocks:
                stock["screener"] = {"pe_ratio": 20.0}

    def test_turnover_survives_the_rebuild(self):
        from analysis.growth import apply_liquidity, _LIQUIDITY_STAGING_KEY

        watchlist = {
            "sec": [{"ticker": "T1", _LIQUIDITY_STAGING_KEY: {"advt_cr": 12.0}}]
        }
        self._rebuild_screener(watchlist)
        assert apply_liquidity(watchlist) == 1

        screener = watchlist["sec"][0]["screener"]
        assert screener["advt_cr"] == 12.0
        assert screener["pe_ratio"] == 20.0  # the rebuild's own data is kept

    def test_staging_key_is_cleared_so_it_never_reaches_the_payload(self):
        from analysis.growth import apply_liquidity, _LIQUIDITY_STAGING_KEY

        watchlist = {
            "sec": [{"ticker": "T1", _LIQUIDITY_STAGING_KEY: {"advt_cr": 1.0}}]
        }
        apply_liquidity(watchlist)
        assert _LIQUIDITY_STAGING_KEY not in watchlist["sec"][0]

    def test_reports_how_many_holdings_it_reached(self):
        """A count the caller can log, so zero coverage is visible."""
        from analysis.growth import apply_liquidity, _LIQUIDITY_STAGING_KEY

        watchlist = {
            "sec": [
                {"ticker": "T1", _LIQUIDITY_STAGING_KEY: {"advt_cr": 1.0}},
                {"ticker": "T2"},
            ]
        }
        assert apply_liquidity(watchlist) == 1

    def test_handles_a_missing_or_malformed_screener(self):
        from analysis.growth import apply_liquidity, _LIQUIDITY_STAGING_KEY

        watchlist = {
            "sec": [
                {"ticker": "T1", _LIQUIDITY_STAGING_KEY: {"advt_cr": 1.0}},
                {
                    "ticker": "T2",
                    "screener": None,
                    _LIQUIDITY_STAGING_KEY: {"advt_cr": 2.0},
                },
                "junk",
            ]
        }
        assert apply_liquidity(watchlist) == 2
        assert watchlist["sec"][1]["screener"]["advt_cr"] == 2.0
