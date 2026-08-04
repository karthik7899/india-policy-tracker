"""Tests for event materiality (analysis/materiality.py).

Headlines here are real ones the pipeline collected, so the parser is
measured against the shapes it actually meets rather than tidy inventions.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis import materiality  # noqa: E402
from models.core import CompanyFinancials  # noqa: E402

# A mid-cap: four quarters of roughly Rs 500 crore, so Rs 2,000 crore TTM.
_MIDCAP = CompanyFinancials(sales_trend=[480.0, 500.0, 510.0, 510.0])
# A mega-cap on the same series shape, Rs 2,50,000 crore TTM.
_MEGACAP = CompanyFinancials(sales_trend=[60000.0, 62000.0, 64000.0, 64000.0])


class TestAmountExtraction:
    def test_reads_plain_crore_amounts(self):
        assert (
            materiality.extract_amount_cr(
                "Bharat Electronics Gets Additional Defence Orders Valued At "
                "₹847 Crore"
            )
            == 847.0
        )

    def test_reads_abbreviated_crore(self):
        assert materiality.extract_amount_cr("BHEL bags Rs 500 cr contract") == 500.0

    def test_lakh_crore_is_not_read_as_lakh(self):
        """The compound unit is ten million times the bare one."""
        assert (
            materiality.extract_amount_cr("L&T secures ₹1.2 lakh crore order")
            == 120000.0
        )

    def test_hyphenated_amounts(self):
        assert (
            materiality.extract_amount_cr("Zen Tech bags 2,000-crore defence order")
            == 2000.0
        )

    def test_dollar_amounts_convert_to_crore(self):
        got = materiality.extract_amount_cr(
            "Varun Beverages Acquires Devyani Food Kenya Business For $32 Million"
        )
        assert 250 < got < 280  # 32mn at ~83/USD is about Rs 266 crore

    def test_takes_the_largest_figure_not_the_first(self):
        """A per-unit price must not be mistaken for the deal size."""
        assert (
            materiality.extract_amount_cr(
                "Rs 12 crore per unit for a Rs 900 crore contract"
            )
            == 900.0
        )

    def test_unquantified_headline_returns_none(self):
        assert (
            materiality.extract_amount_cr("ideaForge lands first US purchase order")
            is None
        )
        assert materiality.extract_amount_cr("") is None

    def test_non_money_numbers_are_ignored(self):
        """Megawatts, percentages and quarters are not rupees."""
        assert materiality.extract_amount_cr("Suzlon wins 300 MW order") is None
        assert materiality.extract_amount_cr("Stock up 5% in Q1 FY27") is None


class TestRevenueNormalisation:
    def test_ttm_revenue_sums_four_quarters(self):
        assert materiality.ttm_revenue_cr(_MIDCAP) == 2000.0

    def test_falls_back_to_annual_when_quarters_are_short(self):
        fin = CompanyFinancials(sales_trend=[100.0], annual_sales_trend=[900.0, 1500.0])
        assert materiality.ttm_revenue_cr(fin) == 1500.0

    def test_no_revenue_yields_none(self):
        assert materiality.ttm_revenue_cr(CompanyFinancials()) is None
        assert materiality.ttm_revenue_cr(None) is None


class TestMateriality:
    def test_same_order_is_transformative_for_midcap_and_noise_for_megacap(self):
        """The whole point: one number, two verdicts."""
        headline = "Wins order worth Rs 500 crore"
        small = materiality.assess(headline, "order_win", _MIDCAP)
        large = materiality.assess(headline, "order_win", _MEGACAP)

        assert small["band"] == "transformative"  # 25% of revenue
        assert large["band"] == "immaterial"  # 0.2% of revenue
        assert small["weight"] > large["weight"]

    def test_immaterial_events_are_damped_not_deleted(self):
        """A small order is still a real order."""
        assert materiality.WEIGHT_IMMATERIAL > 0

    def test_unreadable_size_keeps_full_weight(self):
        """Unknown materiality must not be treated as small materiality."""
        verdict = materiality.assess(
            "ideaForge lands first US purchase order", "order_win", _MIDCAP
        )
        assert verdict["pct_of_revenue"] is None
        assert verdict["weight"] == materiality.WEIGHT_MATERIAL

    def test_non_transactional_events_are_not_judged_on_size(self):
        """A PLI approval has no order value; lacking one is not a demerit."""
        verdict = materiality.assess(
            "Cabinet approves PLI scheme for electronics", "pli", _MIDCAP
        )
        assert verdict["band"] == "unknown"
        assert verdict["weight"] == materiality.WEIGHT_MATERIAL

    def test_missing_revenue_leaves_materiality_unknown(self):
        verdict = materiality.assess(
            "Wins order worth Rs 500 crore", "order_win", CompanyFinancials()
        )
        assert verdict["pct_of_revenue"] is None
        assert verdict["weight"] == materiality.WEIGHT_MATERIAL

    def test_band_boundaries(self):
        assert materiality.classify(20.0) == "transformative"
        assert materiality.classify(7.0) == "material"
        assert materiality.classify(3.0) == "minor"
        assert materiality.classify(0.5) == "immaterial"
        assert materiality.classify(None) == "unknown"
