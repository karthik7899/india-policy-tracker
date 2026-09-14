"""Tests for Graham intrinsic value (analysis/graham.py).

The figures here are anchored on the real inputs that produced the bad
valuations: HAL's March-quarter EPS skew, and the sequential quarterly sales
growth that used to decide the multiple.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.graham import (  # noqa: E402
    _sustainable_growth,
    calculate_graham_intrinsic_value,
    graham_growth_basis,
)
from analysis.valuation import generate_valuation_alerts  # noqa: E402
from models.core import CompanyFinancials  # noqa: E402

# HAL's real quarterly revenue: the March quarter runs ~3x the June quarter.
_SEASONAL_SALES = [4348.0, 5976.0, 6957.0, 13700.0, 4819.0, 6629.0, 7699.0, 13942.0]
# Earnings follow the same shape; 62.74 was the reported March-quarter EPS.
_SEASONAL_EPS = [15.1, 22.4, 27.0, 55.2, 17.3, 24.8, 29.9, 62.74]


def test_uses_trailing_year_of_earnings_not_one_annualized_quarter():
    """The old formula read a seasonal peak as the run rate.

    ``q_eps * 4`` on HAL's March quarter implied annual EPS of 250.96 against
    a real trailing year of 134.74 — an 86% overstatement before the multiple
    was even applied.
    """
    fin = CompanyFinancials(
        q_eps=62.74, eps_trend=_SEASONAL_EPS, sales_trend=_SEASONAL_SALES
    )
    value = calculate_graham_intrinsic_value(fin)
    # Trailing EPS is 134.74; annualizing the single quarter would give 250.96,
    # so the honest valuation must be well under what the old code produced.
    assert 0 < value < 4000
    assert value < 62.74 * 4 * 20


def test_declines_to_value_without_a_full_trailing_year():
    """No year of earnings means no opinion, not an extrapolated one."""
    fin = CompanyFinancials(q_eps=62.74, eps_trend=[29.9, 62.74])
    assert calculate_graham_intrinsic_value(fin) == 0.0
    assert calculate_graham_intrinsic_value(CompanyFinancials()) == 0.0


def test_ttm_eps_field_is_preferred_when_present():
    fin = CompanyFinancials(ttm_eps=100.0, sales_trend=_SEASONAL_SALES)
    # Trailing growth on this series is +6.8%, so the multiple is
    # (8.5 + 13.6) * 4.4/7 = 13.9 -> about 1389 on EPS of 100.
    assert 1300 < calculate_graham_intrinsic_value(fin) < 1450


def test_growth_input_ignores_sequential_quarterly_noise():
    """The multiple must not be set by a seasonal quarter-on-quarter jump.

    HAL's ``qoq_sales_growth`` was +81%, which pinned the old formula to its
    maximum multiple. The trailing-year growth behind the same series is
    +6.8%, and that is what should drive the multiple.
    """
    seasonal = CompanyFinancials(
        ttm_eps=100.0, qoq_sales_growth=81.09, sales_trend=_SEASONAL_SALES
    )
    steady = CompanyFinancials(
        ttm_eps=100.0,
        qoq_sales_growth=0.0,
        sales_trend=[100.0, 100.0, 100.0, 100.0, 106.8, 106.8, 106.8, 106.8],
    )
    # Both series carry ~+6.8% trailing growth, so both must land on the same
    # multiple despite one showing +81% sequentially and the other 0%.
    assert (
        abs(
            calculate_graham_intrinsic_value(seasonal)
            - calculate_graham_intrinsic_value(steady)
        )
        < 1.0
    )


def test_growth_is_capped_at_a_sustainable_rate():
    """One explosive year cannot imply a decade of the same."""
    explosive = CompanyFinancials(
        ttm_eps=10.0,
        sales_trend=[10.0, 10.0, 10.0, 10.0, 100.0, 100.0, 100.0, 100.0],
    )
    capped = CompanyFinancials(
        ttm_eps=10.0,
        sales_trend=[100.0, 100.0, 100.0, 100.0, 115.0, 115.0, 115.0, 115.0],
    )
    assert calculate_graham_intrinsic_value(explosive) == (
        calculate_graham_intrinsic_value(capped)
    )


def test_bond_yield_correction_is_applied():
    """Graham's multiple is quoted against the prevailing bond yield."""
    fin = CompanyFinancials(ttm_eps=100.0, sales_trend=[])
    # Default growth 6.0 -> (8.5 + 12) * 4.4/7 = 12.886 -> 1288.6
    assert calculate_graham_intrinsic_value(fin) == 1288.6


# ---------------------------------------------------------------------------
# earning power has to exist before it can be valued
# ---------------------------------------------------------------------------


def test_trailing_loss_yields_no_valuation_not_a_negative_one():
    """ideaForge's trailing EPS is -3.96, which produced an intrinsic value
    of *negative* Rs 95.8 — stored and displayed as though it meant
    something."""
    fin = CompanyFinancials(ttm_eps=-3.96, q_eps=13.86, sales_trend=_SEASONAL_SALES)
    assert calculate_graham_intrinsic_value(fin) == 0.0


def test_a_quarter_that_swung_to_a_loss_stops_the_valuation():
    """BPCL: trailing EPS of 39.48 still held profitable quarters, so the
    model valued it at Rs 823 against a Rs 320 price while the company was
    losing money at the operating line."""
    fin = CompanyFinancials(
        ttm_eps=39.48, q_eps=-4.32, q_opm=-2.7, sales_trend=_SEASONAL_SALES
    )
    assert calculate_graham_intrinsic_value(fin) == 0.0


def test_an_operating_loss_alone_is_enough_to_stop_it():
    fin = CompanyFinancials(ttm_eps=39.48, q_eps=1.0, q_opm=-2.7)
    assert calculate_graham_intrinsic_value(fin) == 0.0


def test_a_profitable_company_is_still_valued():
    fin = CompanyFinancials(ttm_eps=100.0, q_eps=25.0, q_opm=12.0, sales_trend=[])
    assert calculate_graham_intrinsic_value(fin) > 0


class TestAnUnvaluedCompanyIsNotACheapOne:
    """0.0 means "we cannot value this", and it must never be compared.

    calculate_graham_intrinsic_value returns 0.0 as an explicit refusal. Its
    docstring says callers gate on that, and three of the four did. The fourth
    wrote `price <= graham_value * 1.2`, which is False for every positive
    price once the value is 0.0 — so every holding the model declined to value
    collected "Fails P/E Screen (... & Price > Intrinsic)", asserting a
    comparison that was never performed against a number that does not exist.

    The verdict was right and does not change here: P/E > 15 with no exemption
    available still fails. What was wrong is the reason attached to it — six
    holdings in the payload at the time told the reader a comparison had been
    made that never was, sending anyone who checked after an intrinsic value
    the model had explicitly refused to produce.
    """

    def _declined(self, pe_ratio):
        # Graham refuses: the latest quarter has swung to an operating loss.
        return CompanyFinancials(
            pe_ratio=pe_ratio,
            current_ratio=2.5,
            dividend_yield=1.5,
            net_current_assets=1000.0,
            debt_trend=[100.0],
            ttm_eps=39.48,
            q_eps=1.0,
            q_opm=-2.7,
            sales_trend=_SEASONAL_SALES,
        )

    def test_the_alert_does_not_claim_a_comparison_it_never_made(self):
        fin = self._declined(28.0)
        assert calculate_graham_intrinsic_value(fin) == 0.0
        alerts = generate_valuation_alerts(fin, price=320.0)
        pe_alerts = [a for a in alerts if "P/E Screen" in a]
        assert pe_alerts, "P/E > 15 with no intrinsic value still fails the screen"
        assert "Price > Intrinsic" not in pe_alerts[0], pe_alerts[0]
        assert "no intrinsic value" in pe_alerts[0], pe_alerts[0]

    def test_a_low_pe_company_is_not_failed_for_being_unvaluable(self):
        """The exemption is missing, but the rule it exempts from never fired."""
        fin = self._declined(9.0)
        alerts = generate_valuation_alerts(fin, price=320.0)
        assert not [a for a in alerts if "P/E Screen" in a], alerts

    def test_a_valued_company_below_intrinsic_still_passes(self):
        fin = CompanyFinancials(
            pe_ratio=28.0,
            current_ratio=2.5,
            dividend_yield=1.5,
            net_current_assets=1000.0,
            debt_trend=[100.0],
            ttm_eps=100.0,
            q_eps=25.0,
            q_opm=12.0,
            sales_trend=_SEASONAL_SALES,
        )
        value = calculate_graham_intrinsic_value(fin)
        assert value > 0
        alerts = generate_valuation_alerts(fin, price=value * 0.5)
        assert not [a for a in alerts if "P/E Screen" in a], alerts

    def test_a_valued_company_above_intrinsic_still_fails_with_the_real_reason(self):
        fin = CompanyFinancials(
            pe_ratio=28.0,
            current_ratio=2.5,
            dividend_yield=1.5,
            net_current_assets=1000.0,
            debt_trend=[100.0],
            ttm_eps=100.0,
            q_eps=25.0,
            q_opm=12.0,
            sales_trend=_SEASONAL_SALES,
        )
        value = calculate_graham_intrinsic_value(fin)
        alerts = generate_valuation_alerts(fin, price=value * 3)
        pe_alerts = [a for a in alerts if "P/E Screen" in a]
        assert pe_alerts and "Price > Intrinsic" in pe_alerts[0], alerts


class TestGrowthIsEarningsOverYearsNotRevenueOverOne:
    """Graham's ``g`` is EARNINGS growth SUSTAINED over 7-10 years.

    It used to be fed one year of REVENUE growth — the wrong quantity over the
    wrong span. Revenue flatters any company growing the top line faster than
    the bottom, and a single year is the opposite of sustained.

    The ranking is: every multi-year basis before any single-year one, earnings
    before revenue within each. Span outranks quantity because "sustained" is
    the load-bearing word, and because a single year of EPS growth clamps at
    one end or the other for two watchlist holdings in three.
    """

    _FLAT_QUARTERS = [1074.0, 998.0, 1052.0, 1019.0, 1034.0, 1257.0, 1441.0, 1910.0]

    def test_earnings_beat_revenue_when_both_span_years(self):
        fin = CompanyFinancials(
            ttm_eps=10.0,
            annual_eps_trend=[10.0, 11.0, 12.0, 13.0, 14.0],
            annual_sales_trend=[100.0, 200.0, 400.0, 800.0, 1600.0],
        )
        growth, basis = _sustainable_growth(fin)
        assert basis.startswith("EPS CAGR"), basis
        assert 8 < growth < 10, growth  # ~8.8%, not the 100% revenue implies

    def test_a_rebound_year_cannot_reprice_a_flat_five_years(self):
        """STLTECH: 0.7% compounded over five years, +36% on the trailing year.

        The one-year input read the rebound as a trend and handed it the 15%
        ceiling.
        """
        fin = CompanyFinancials(
            ttm_eps=10.0,
            annual_sales_trend=[5437.0, 6925.0, 4083.0, 3996.0, 4745.0, 5642.0],
            sales_trend=self._FLAT_QUARTERS,
        )
        growth, basis = _sustainable_growth(fin)
        assert "floored by trailing year" in basis, basis
        assert growth < 2.0, growth

    def test_an_old_boom_cannot_reprice_a_shrinking_company(self):
        """ZENTEC: 70 -> 974 -> 671. First-to-last compounds at 57% a year while
        revenue is well off its peak, so a CAGR alone would hand a shrinking
        business the maximum multiple.

        This guards the CAGR-only design that was nearly shipped here, not the
        original one-year-revenue bug — that one already returned 0.0 for this
        company, for the unrelated reason that its trailing year is down 23%.
        Kept because the floor is load-bearing and nothing else pins it.
        """
        fin = CompanyFinancials(
            ttm_eps=10.0,
            annual_sales_trend=[70.0, 219.0, 440.0, 974.0, 688.0, 671.0],
            sales_trend=[242.0, 152.0, 325.0, 158.0, 174.0, 178.0, 178.0, 142.0],
        )
        growth, basis = _sustainable_growth(fin)
        assert "floored by trailing year" in basis, basis
        assert growth == 0.0, growth

    def test_a_multi_year_revenue_cagr_outranks_one_year_of_earnings(self):
        fin = CompanyFinancials(
            ttm_eps=10.0,
            annual_sales_trend=[100.0, 104.0, 108.0, 112.0, 116.0],
            eps_trend=[1.0] * 4 + [9.0] * 4,  # +800% on the trailing year
        )
        growth, basis = _sustainable_growth(fin)
        assert basis.startswith("revenue CAGR"), basis
        assert growth < 6.0, growth

    def test_one_year_of_earnings_is_still_better_than_nothing(self):
        fin = CompanyFinancials(
            ttm_eps=10.0, eps_trend=[1.0, 1.0, 1.0, 1.0, 1.1, 1.1, 1.1, 1.1]
        )
        growth, basis = _sustainable_growth(fin)
        assert basis == "trailing-year EPS growth", basis
        assert 9 < growth < 11, growth

    def test_no_usable_series_says_so_rather_than_inventing_a_number(self):
        growth, basis = _sustainable_growth(CompanyFinancials(ttm_eps=10.0))
        assert basis == "default (no usable series)"
        assert growth == 6.0

    def test_the_basis_is_reportable(self):
        fin = CompanyFinancials(
            ttm_eps=10.0, annual_eps_trend=[10.0, 11.0, 12.0, 13.0, 14.0]
        )
        assert graham_growth_basis(fin).startswith("EPS CAGR")

    def test_a_loss_making_endpoint_does_not_produce_a_growth_rate(self):
        """A negative endpoint makes the root imaginary, and a company that was
        losing money is not described by a growth rate anyway."""
        fin = CompanyFinancials(
            ttm_eps=10.0, annual_eps_trend=[5.0, 4.0, 3.0, 2.0, -1.0]
        )
        _growth, basis = _sustainable_growth(fin)
        assert "EPS CAGR" not in basis, basis
