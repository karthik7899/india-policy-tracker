"""Tests for Graham intrinsic value (analysis/graham.py).

The figures here are anchored on the real inputs that produced the bad
valuations: HAL's March-quarter EPS skew, and the sequential quarterly sales
growth that used to decide the multiple.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.graham import calculate_graham_intrinsic_value  # noqa: E402
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
