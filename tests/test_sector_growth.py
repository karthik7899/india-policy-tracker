"""Tests for sector revenue-growth rankings (analysis/sector_growth.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.data_quality import INSUFFICIENT_DATA, OK, OUT_OF_BAND  # noqa: E402
from analysis.sector_growth import (  # noqa: E402
    build_sector_growth,
    compute_stock_growth,
)

# HAL's real reported quarterly revenue, the series that exposed the bug: a
# March-quarter skew roughly three times the size of the June quarter.
_SEASONAL = [4348.0, 5976.0, 6957.0, 13700.0, 4819.0, 6629.0, 7699.0, 13942.0]


def _stock(ticker, sales_trend, annual=None):
    sc = {"sales_trend": sales_trend}
    if annual:
        sc["annual_sales_trend"] = annual
    return {"ticker": ticker, "name": ticker, "screener": sc}


# ---------------------------------------------------------------------------
# per-stock math
# ---------------------------------------------------------------------------


def test_yoy_uses_same_quarter_last_year():
    # 8 quarters; latest 130 vs the same quarter a year earlier (S[-5]=95)
    # -> 130/95 - 1 = +36.8% YoY.
    g = compute_stock_growth([80, 85, 90, 95, 100, 110, 120, 130])
    assert g["yoy_pct"] == 36.8
    assert g["quarters"] == 8


def test_ttm_growth_cancels_seasonality():
    """The headline growth figure must compare whole years, not endpoints.

    The old measure spanned S[0] to S[-1] — seven quarters, so it ran from a
    June-quarter trough to a March-quarter peak and annualized the difference,
    reporting +94.6%. Summing four quarters against the prior four puts every
    quarter of the year on both sides of the ratio.
    """
    g = compute_stock_growth(_SEASONAL)
    assert g["ttm_growth_pct"] == 6.8
    assert g["quality"] == OK


def test_ttm_growth_survives_the_window_rolling_forward():
    """Regression: the shipped figure must not lurch when a quarter arrives.

    Screener returns a trailing 8 quarters, so each results season drops the
    oldest. Under the old point-to-point measure that swung HAL from +94.6% to
    -7.6% — a 102-point move caused entirely by which fiscal quarter happened
    to land at position 0.
    """
    before = compute_stock_growth(_SEASONAL)["ttm_growth_pct"]
    # Next March quarter arrives ~8% above the prior one; oldest drops off.
    rolled = _SEASONAL[1:] + [_SEASONAL[-4] * 1.08]
    after = compute_stock_growth(rolled)["ttm_growth_pct"]
    assert abs(after - before) < 5.0, f"{before} -> {after} is not stable"


def test_cagr_comes_from_the_annual_series():
    # A true multi-year rate is only computable from annual periods: five
    # points compounding at exactly 10% a year.
    g = compute_stock_growth(_SEASONAL, [100.0, 110.0, 121.0, 133.1, 146.41])
    assert g["cagr_pct"] == 10.0
    assert g["annual_periods"] == 5


def test_cagr_absent_without_enough_annual_history():
    g = compute_stock_growth(_SEASONAL, [100.0, 110.0])
    assert g["cagr_pct"] is None
    # The quarterly measures are unaffected by the missing annual row.
    assert g["ttm_growth_pct"] == 6.8


def test_short_series_and_bad_bases_rejected():
    assert compute_stock_growth([100, 110, 120, 130]) is None  # < 5 quarters
    assert compute_stock_growth([0, 10, 20, 30, 40]) is None  # zero base
    assert compute_stock_growth(None) is None
    assert compute_stock_growth(["a", "b"]) is None


def test_five_quarters_gives_yoy_but_flags_ttm_as_insufficient():
    g = compute_stock_growth([100, 105, 110, 115, 130])
    assert g["yoy_pct"] == 30.0
    assert g["ttm_growth_pct"] is None
    assert g["quality"] == INSUFFICIENT_DATA


def test_base_effect_growth_flagged_out_of_band():
    # A near-zero prior year makes the ratio meaningless; it is labelled
    # rather than capped to a number that looks real.
    g = compute_stock_growth([1, 1, 1, 1, 10, 10, 10, 10])
    assert g["ttm_growth_pct"] == 900.0
    assert g["quality"] == OUT_OF_BAND


# ---------------------------------------------------------------------------
# sector rollup
# ---------------------------------------------------------------------------


def test_rollup_ranked_fastest_first_and_annotates():
    wl = {
        "fast_sector": [
            _stock("F1", [100, 105, 110, 115, 120, 130, 140, 150]),
            _stock("F2", [100, 102, 104, 106, 108, 120, 135, 151]),
        ],
        "slow_sector": [
            _stock("S1", [100, 100, 100, 100, 100, 101, 102, 103]),
        ],
        "macro_indicators": [_stock("ETF", [100, 110, 120, 130, 140])],  # skipped
        "no_data": [{"ticker": "N1", "name": "N1"}],
    }
    rollup = build_sector_growth(wl)
    assert [r["sector"] for r in rollup] == ["fast_sector", "slow_sector"]
    fast = rollup[0]
    assert fast["stock_count"] == 2
    assert fast["median_ttm_growth_pct"] > rollup[1]["median_ttm_growth_pct"]
    # annotated in place for the stock views
    sc = wl["fast_sector"][0]["screener"]
    assert sc["revenue_ttm_growth_pct"] is not None
    assert sc["revenue_growth_quality"] == OK


def test_rollup_flags_single_holding_sectors_as_low_confidence():
    wl = {
        "thin": [_stock("T1", [100, 105, 110, 115, 120, 130, 140, 150])],
        "broad": [
            _stock("B1", [100, 105, 110, 115, 120, 130, 140, 150]),
            _stock("B2", [100, 102, 104, 106, 108, 120, 135, 151]),
        ],
    }
    rollup = {r["sector"]: r for r in build_sector_growth(wl)}
    assert rollup["thin"]["low_confidence"] is True
    assert rollup["broad"]["low_confidence"] is False


def test_rollup_excludes_untrustworthy_holdings_and_counts_them():
    """An artifact must not be allowed to set a sector's ranking."""
    wl = {
        "mixed": [
            _stock("GOOD", [100, 105, 110, 115, 120, 130, 140, 150]),
            _stock("ARTIFACT", [1, 1, 1, 1, 10, 10, 10, 10]),  # out of band
        ]
    }
    rollup = build_sector_growth(wl)
    assert len(rollup) == 1
    assert rollup[0]["stock_count"] == 1
    assert rollup[0]["excluded_count"] == 1
    assert rollup[0]["fastest_ticker"] == "GOOD"


def test_rollup_never_raises():
    assert build_sector_growth(None) == []
    assert build_sector_growth({"sec": "junk"}) == []
