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


class TestAttribution:
    """An amount is only this company's if the headline is about this company.

    Every headline here is real, from the first production run of the feature.
    """

    HAL_RALLY = (
        "BEL, HAL, Bharat Dynamics: Defence stocks rally as DAC clears "
        "₹52,000 crore defence acquisition proposals"
    )

    def test_a_sector_programme_is_not_one_companys_order(self):
        """The regression: this scored HAL 'transformative' at 157% of its own
        revenue and applied the maximum weight, on a government procurement
        figure spanning the sector."""
        verdict = materiality.assess(self.HAL_RALLY, "", _MIDCAP)
        assert verdict["pct_of_revenue"] is None
        assert verdict["band"] == "unknown"
        assert verdict["weight"] == materiality.WEIGHT_MATERIAL

    def test_the_same_figure_is_rejected_for_every_company_named(self):
        """It would otherwise have been credited to BEL and BDL as well."""
        for fin in (_MIDCAP, _MEGACAP):
            assert materiality.assess(self.HAL_RALLY, "order_win", fin)["band"] == (
                "unknown"
            )

    def test_market_commentary_is_never_a_transaction(self):
        for title in (
            "Persistent Systems stock crashes 10%, top midcap loser today",
            "Suzlon shares jump 5% on ₹350 crore order news",
            "Brokerage sets target price of Rs 1,200 crore valuation",
        ):
            assert materiality.amount_is_attributable(title) is False

    def test_programme_level_approvals_are_excluded(self):
        for title in (
            "Cabinet approves Rs 22,919 crore PLI scheme for electronics",
            "CCS clears Rs 62,000 crore fighter engine deal",
            "Government allocates Rs 1.2 lakh crore outlay for defence",
        ):
            assert materiality.amount_is_attributable(title) is False

    def test_a_multi_company_list_headline_is_excluded(self):
        assert materiality.amount_is_attributable("BEL, HAL, BDL: order news") is False

    def test_a_single_company_order_still_scores(self):
        """The guard must not silence the case the feature exists for."""
        title = "BEL bags additional orders worth Rs 1,081 crore"
        assert materiality.amount_is_attributable(title) is True
        verdict = materiality.assess(title, "order_win", _MIDCAP)
        assert verdict["amount_cr"] == 1081.0
        assert verdict["pct_of_revenue"] is not None

    def test_a_colon_without_a_list_is_not_excluded(self):
        """Publishers prefix single-company headlines too: 'Suzlon: wins ...'."""
        assert (
            materiality.amount_is_attributable("Suzlon: wins order worth Rs 500 crore")
            is True
        )


class TestCountedNouns:
    """Lakh and crore count things as readily as they count rupees.

    "Pledges 3.70 Lakh Equity Shares" was extracted as Rs 0.037 crore. It was
    filtered downstream for being the wrong event kind, so nothing reached a
    score -- but the parser had already agreed a share count was money, and
    widening the sized-event vocabulary would have exposed that.
    """

    def test_a_share_count_is_not_a_rupee_amount(self):
        assert (
            materiality.extract_amount_cr(
                "ideaForge Technology Promoter Ankit Mehta Pledges "
                "3.70 Lakh Equity Shares"
            )
            is None
        )

    def test_crore_counts_shares_too(self):
        assert materiality.extract_amount_cr(
            "Company issues 5 crore equity shares"
        ) is (None)

    def test_physical_quantities_are_not_amounts(self):
        for title in (
            "Plant capacity of 5 lakh tonnes commissioned",
            "Sold 1.2 lakh vehicles in July",
            "Leases 1.72 lakh sq ft of office space",
        ):
            assert materiality.extract_amount_cr(title) is None

    def test_a_currency_marker_settles_it(self):
        """'Rs 3 lakh shares buyback fund' is money despite the noun."""
        assert materiality.extract_amount_cr("Rs 3 lakh shares buyback fund") == 0.03

    def test_a_counted_noun_does_not_hide_a_real_price(self):
        """Both numbers are read; the count is dropped and the price kept."""
        assert (
            materiality.extract_amount_cr(
                "Order for 2 crore units valued at Rs 300 crore"
            )
            == 300.0
        )

    def test_the_real_headline_keeps_its_price(self):
        assert (
            materiality.extract_amount_cr(
                "Microchip Technology India has acquired 1.72 lakh sq ft of "
                "office space in EPIP Zone, Whitefield, for ₹176 crore"
            )
            == 176.0
        )


class TestSharedVehicles:
    """A jointly-owned vehicle's capitalisation belongs to its partners."""

    JV = "Syrma SGS, Kaga Electronics Form ₹250 Million EMS Joint Venture"

    def test_a_joint_venture_figure_is_not_one_partners_order(self):
        assert materiality.amount_is_attributable(self.JV) is False

    def test_the_list_guard_alone_would_have_missed_it(self):
        """The colon lands before the comma once a kind prefix is attached,
        so the multi-company shape is invisible to the list guard."""
        assert materiality._COMPANY_LIST_RE.match(self.JV) is None

    def test_consortium_and_partnership_are_excluded_too(self):
        for title in (
            "Larsen & Toubro in consortium for Rs 5,000 crore metro contract",
            "Tata Power in partnership with a state utility on Rs 900 crore park",
        ):
            assert materiality.amount_is_attributable(title) is False

    def test_a_sole_award_is_untouched(self):
        assert (
            materiality.amount_is_attributable(
                "Syrma SGS wins Rs 250 crore supply order"
            )
            is True
        )


class TestTransactionVocabulary:
    """Sizing must not turn on which verb form the sub-editor chose."""

    def test_the_infinitive_is_sized_like_the_third_person(self):
        title = "Varun Beverages to acquire 100% in a beverage maker for Rs 1,119 crore"
        assert materiality.is_sized_event("launch", title) is True
        assert materiality.assess(title, "launch", _MIDCAP)["amount_cr"] == 1119.0

    def test_divestments_are_sized_events(self):
        title = "LTTS to sell Smart World unit for ₹452 crore to refocus on AI"
        assert materiality.is_sized_event("filing", title) is True

    def test_an_unsized_event_stays_unsized(self):
        """A PLI approval legitimately carries no company-level figure."""
        assert (
            materiality.is_sized_event("filing", "Company reports Q1 results") is False
        )


class TestNonTransactions:
    """Feed names are not event classifications.

    ``corporate_agreements`` is a news query, so earnings, joint ventures and
    sector totals all arrive in it and were sized as deals. Every headline
    below is real and was reaching the scorer as a transaction.
    """

    def test_reported_results_are_not_deals(self):
        for title in (
            "CONCOR Q1 Revenue Reaches ₹2,160 Crore as Net Profit Holds at ₹267 Crore",
            "MRPL Annual Report FY 2025-26: Profit After Tax Surges to ₹1,931 Crore",
            "Fortis Malar Hospitals Q1 Results: Net profit rises to ₹17.71 lakh",
            "Arvind Fashions Q1 revenue rises 15.5% to ₹1,279 crore",
        ):
            assert materiality.amount_is_attributable(title) is False

    def test_an_earnings_figure_is_not_read_as_a_deal_size(self):
        """The headline names a real acquisition but prints only the profit,
        so the deal would have been sized at the earnings number."""
        title = "ITC Hotels Q4 profit up 23% at ₹317 cr; to acquire Zuri Hotels"
        assert materiality.amount_is_attributable(title) is False

    def test_abbreviated_joint_ventures_are_caught(self):
        title = "Dixon Tech Secures IMG Approval for Vivo JV Targeting ₹30,000 Cr"
        assert materiality.amount_is_attributable(title) is False

    def test_a_partnership_total_is_not_one_partners_number(self):
        title = "Trump Announces $300 Billion Partnership with Reliance"
        assert materiality.amount_is_attributable(title) is False

    def test_multi_project_totals_are_excluded(self):
        title = "Eight coal gasification projects to draw ₹65,365 crore investment"
        assert materiality.amount_is_attributable(title) is False

    def test_a_guarantee_is_not_revenue(self):
        title = (
            "ONGC backs MRPL's crude imports from Saudi Aramco with $500 mn guarantee"
        )
        assert materiality.amount_is_attributable(title) is False

    def test_a_prospective_market_size_is_not_an_order(self):
        title = "Zen Technologies jumps 9%, ideaForge hits upper circuit as India eyes Rs 20,000 crore drone buy"
        assert materiality.amount_is_attributable(title) is False

    def test_singular_price_moves_are_caught_like_plural_ones(self):
        """The literal list held 'shares jump' but not 'jumps 9%'."""
        assert materiality.amount_is_attributable(
            "Suzlon jumps 9% on ₹350 cr news"
        ) is (False)

    def test_real_awards_survive_every_guard(self):
        """The guards must not silence the cases the feature exists for."""
        for title in (
            "Defence Ministry signs 1950 crore contract with Bharat Electronics Limited",
            "BEL bags additional orders worth Rs 1,081 crore",
            "Varun Beverages to acquire 100% in a beverage maker for Rs 1,119 crore",
            "Supreme Power Equipment Marks Entry into Maharashtra with ₹13.50 Cr "
            "Transformer Order",
        ):
            assert materiality.amount_is_attributable(title) is True
