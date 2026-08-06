"""Tests for the closing briefing sections (emails/sections.py).

The through-line: a gap must never render as a value. Most of these assert
what is *absent* from the output, because the failure mode this module guards
against is a section that looks complete while quietly dropping what it could
not compute.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from emails.sections import (  # noqa: E402
    build_watchlist_changes_html,
    build_valuation_extremes_html,
    build_data_quality_html,
    build_cta_html,
)


class TestWatchlistChanges:
    LEDGER = [
        {
            "date": "2026-08-06",
            "action": "added",
            "ticker": "PRECOT",
            "name": "Precot Limited",
            "price_at_decision": 802.0,
            "target_at_decision": 1002.5,
            "outcome": None,
        },
        {
            "date": "2026-08-05",
            "action": "rotated_in",
            "ticker": "MRPL",
            "name": "M R P L",
            "price_at_decision": 161.8,
            "target_at_decision": 182.5,
            "outcome": "Thesis Playing Out",
        },
    ]

    def test_changes_render_with_action_and_prices(self):
        html = build_watchlist_changes_html(self.LEDGER)
        assert "PRECOT" in html
        assert "Added" in html
        assert "Rotated in" in html
        assert "802.0" in html and "1002.5" in html

    def test_an_unscored_decision_is_not_reported_as_a_result(self):
        """A pending decision shown as a flat return reads as an outcome the
        pipeline has not earned."""
        html = build_watchlist_changes_html(self.LEDGER)
        assert "Not yet scored" in html
        assert "Thesis Playing Out" in html

    def test_a_missing_price_says_so(self):
        html = build_watchlist_changes_html(
            [{"date": "2026-08-06", "action": "added", "ticker": "X", "name": "X Ltd"}]
        )
        assert "Not available" in html

    def test_an_empty_feed_and_a_missing_feed_differ(self):
        """An empty list means nothing moved. A missing key means the run
        never looked, and must not claim the watchlist held steady."""
        assert "No additions or exits" in build_watchlist_changes_html([])
        assert build_watchlist_changes_html(None) == ""

    def test_overflow_is_stated_not_silently_dropped(self):
        rows = [
            dict(self.LEDGER[0], ticker=f"T{i}", date=f"2026-08-{i:02d}")
            for i in range(1, 12)
        ]
        html = build_watchlist_changes_html(rows, limit=3)
        assert "+ 8 more change(s)" in html

    def test_newest_first(self):
        html = build_watchlist_changes_html(self.LEDGER)
        assert html.index("PRECOT") < html.index("MRPL")

    def test_an_unknown_action_is_labelled_not_dropped(self):
        html = build_watchlist_changes_html(
            [{"date": "2026-08-06", "action": "trimmed", "ticker": "Z", "name": "Z"}]
        )
        assert "Trimmed" in html

    def test_markup_in_a_name_is_escaped(self):
        html = build_watchlist_changes_html(
            [
                {
                    "date": "2026-08-06",
                    "action": "added",
                    "ticker": "X",
                    "name": "<script>alert(1)</script>",
                }
            ]
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestValuationExtremes:
    ROWS = [
        {
            "sector": "banking_financials",
            "label": "Banking & Financials",
            "median_pe": 14.3,
            "cheapest_ticker": "SBIN",
            "cheapest_pe": 11.7,
            "most_expensive_ticker": "ICICIBANK",
            "most_expensive_pe": 18.6,
        },
        {
            "sector": "midcap_it",
            "label": "Midcap IT",
            "median_pe": 38.0,
            "cheapest_ticker": "A",
            "cheapest_pe": 30.0,
            "most_expensive_ticker": "B",
            "most_expensive_pe": 45.0,
        },
    ]

    def test_both_ends_are_shown(self):
        html = build_valuation_extremes_html(self.ROWS)
        assert "Lowest median P/E" in html and "Highest" in html
        assert "SBIN" in html and "ICICIBANK" in html

    def test_suppressed_holdings_are_named_with_a_reason(self):
        """A valuation table that omits what it could not value implies the
        rows shown are the whole picture."""
        html = build_valuation_extremes_html(
            self.ROWS,
            [{"ticker": "QUICKHEAL", "reason": "no analyst or fundamental base"}],
        )
        assert "QUICKHEAL" in html
        assert "Suppressed" in html
        assert "no analyst or fundamental base" in html

    def test_a_suppression_without_a_reason_still_says_it_is_suppressed(self):
        html = build_valuation_extremes_html(self.ROWS, [{"ticker": "X"}])
        assert "reason not recorded" in html

    def test_sectors_without_a_median_do_not_fabricate_one(self):
        html = build_valuation_extremes_html(
            [{"sector": "x", "label": "X", "median_pe": None}]
        )
        assert "No sector carried a median P/E" in html
        assert "0.0" not in html

    def test_nothing_at_all_renders_nothing(self):
        assert build_valuation_extremes_html([], []) == ""
        assert build_valuation_extremes_html(None, None) == ""

    def test_a_missing_peer_ticker_says_not_available(self):
        html = build_valuation_extremes_html(
            [{"sector": "x", "label": "X", "median_pe": 12.0}]
        )
        assert "Not available" in html


class TestDataQuality:
    def test_a_degraded_refresh_is_stated(self):
        html = build_data_quality_html(
            {"freshness": {"live_prices": {"updated": 40, "total": 70}}}
        )
        assert "40/70" in html
        assert "57%" in html

    def test_an_unrecorded_refresh_is_not_reported_as_complete(self):
        html = build_data_quality_html({})
        assert "not recorded" in html
        assert "100%" not in html

    def test_suppressed_estimates_are_counted_against_the_whole(self):
        watchlist = {
            "fmcg": [
                {"ticker": "A", "estimate_method": "No Estimate"},
                {"ticker": "B", "estimate_method": "Analyst"},
            ]
        }
        html = build_data_quality_html({}, watchlist)
        assert "1 of 2 holdings carry no target" in html

    def test_macro_indicators_are_not_counted_as_holdings(self):
        watchlist = {
            "macro_indicators": [{"ticker": "IDX", "estimate_method": "No Estimate"}],
            "fmcg": [{"ticker": "A", "estimate_method": "Analyst"}],
        }
        html = build_data_quality_html({}, watchlist)
        assert "carry no target" not in html

    def test_sized_alerts_are_reported(self):
        html = build_data_quality_html(
            {"early_warnings": [{"materiality_pct": 25.0}, {"materiality_pct": None}]}
        )
        assert "1 alert(s) measured against trailing revenue" in html

    def test_nothing_to_report_renders_nothing(self):
        # No freshness, no coverage, no holdings, no warnings -> the section
        # would be an empty heading, which is worse than absent.
        assert build_data_quality_html({"freshness": {}}, {}) != ""  # states unrecorded

    def test_malformed_input_does_not_raise(self):
        assert isinstance(build_data_quality_html(None, None), str)


class TestCta:
    def test_one_primary_action(self):
        html = build_cta_html("https://example.com/dash")
        assert html.count("cta-button") == 1
        assert "Review today's changes" in html

    def test_at_most_three_secondary_links(self):
        html = build_cta_html("https://example.com/dash")
        assert html.count("<a ") == 4  # one primary plus three secondary

    def test_a_trailing_slash_does_not_double(self):
        html = build_cta_html("https://example.com/dash/")
        assert "dash//" not in html

    def test_language_stays_in_the_review_register(self):
        """House rule: review/verify/validate/monitor, never buy or sell."""
        html = build_cta_html("https://example.com/dash").lower()
        for word in (">buy", ">sell", "buy now", "sell now"):
            assert word not in html
