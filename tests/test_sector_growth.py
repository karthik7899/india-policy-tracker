"""Tests for sector revenue-growth rankings (analysis/sector_growth.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.sector_growth import (  # noqa: E402
    build_sector_growth,
    compute_stock_growth,
)


def _stock(ticker, sales_trend):
    return {"ticker": ticker, "name": ticker, "screener": {"sales_trend": sales_trend}}


# ---------------------------------------------------------------------------
# per-stock math
# ---------------------------------------------------------------------------


def test_yoy_uses_same_quarter_last_year():
    # 8 quarters; latest 130 vs the same quarter a year earlier (S[-5]=95)
    # → 130/95 - 1 = +36.8% YoY.
    g = compute_stock_growth([80, 85, 90, 95, 100, 110, 120, 130])
    assert g["yoy_pct"] == 36.8
    assert g["quarters"] == 8


def test_cagr_annualizes_over_span():
    # 100 → 200 across 8 points (7 quarterly intervals):
    # (2)^(4/7) - 1 ≈ 48.6% annualized.
    g = compute_stock_growth([100, 110, 120, 130, 140, 160, 180, 200])
    assert 48.0 <= g["cagr_pct"] <= 49.2


def test_short_series_and_bad_bases_rejected():
    assert compute_stock_growth([100, 110, 120, 130]) is None  # < 5 quarters
    assert compute_stock_growth([0, 10, 20, 30, 40]) is None  # zero base
    assert compute_stock_growth(None) is None
    assert compute_stock_growth(["a", "b"]) is None


def test_base_effect_growth_capped():
    g = compute_stock_growth([1, 1, 1, 1, 1, 1, 1, 500])
    assert g["yoy_pct"] == 200.0  # capped, not 49900%
    assert g["cagr_pct"] == 200.0


# ---------------------------------------------------------------------------
# sector rollup
# ---------------------------------------------------------------------------


def test_rollup_ranked_fastest_first_and_annotates():
    wl = {
        "fast_sector": [
            _stock("F1", [100, 105, 110, 115, 120, 130, 140, 150]),  # +30.4% YoY
            _stock("F2", [100, 102, 104, 106, 108, 120, 135, 151]),  # +42.5% YoY
        ],
        "slow_sector": [
            _stock("S1", [100, 100, 100, 100, 100, 101, 102, 103]),  # +3% YoY
        ],
        "macro_indicators": [_stock("ETF", [100, 110, 120, 130, 140])],  # skipped
        "no_data": [{"ticker": "N1", "name": "N1"}],
    }
    rollup = build_sector_growth(wl)
    assert [r["sector"] for r in rollup] == ["fast_sector", "slow_sector"]
    fast = rollup[0]
    assert fast["stock_count"] == 2
    assert fast["fastest_ticker"] == "F2"
    # annotated in place for the stock views
    assert wl["fast_sector"][0]["screener"]["revenue_yoy_pct"] == 30.4
    assert "revenue_cagr_pct" in wl["fast_sector"][0]["screener"]


def test_rollup_never_raises():
    assert build_sector_growth(None) == []
    assert build_sector_growth({"sec": "junk"}) == []
