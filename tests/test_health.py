"""Tests for run-health assertions (health.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from health import check_run_health, summarize_liquidity  # noqa: E402


def _watchlist(n, priced=None, with_screener=None):
    priced = n if priced is None else priced
    with_screener = n if with_screener is None else with_screener
    stocks = []
    for i in range(n):
        stock = {"ticker": f"T{i}", "name": f"T{i}"}
        if i < priced:
            stock["price"] = "100.00"
        if i < with_screener:
            stock["screener"] = {"pe_ratio": 20.0}
        stocks.append(stock)
    return {"sec": stocks}


def _healthy_data():
    return {
        "sector_growth": [{"sector": "sec"}],
        "early_warnings": [{"ticker": "T0"}],
    }


def test_a_normal_run_is_healthy():
    ok, problems = check_run_health(_healthy_data(), _watchlist(10))
    assert ok is True
    assert problems == []


def test_collapsed_price_coverage_fails_the_run():
    """The failure this exists for: Yahoo returns nothing and nobody notices."""
    ok, problems = check_run_health(_healthy_data(), _watchlist(10, priced=2))
    assert ok is False
    assert any("live price" in p for p in problems)


def test_collapsed_screener_coverage_fails_the_run():
    ok, problems = check_run_health(_healthy_data(), _watchlist(10, with_screener=1))
    assert ok is False
    assert any("Screener" in p for p in problems)


def test_partial_outage_within_tolerance_still_passes():
    """A few unreachable symbols is normal and must not cry wolf."""
    ok, _ = check_run_health(_healthy_data(), _watchlist(10, priced=7, with_screener=6))
    assert ok is True


def test_empty_analysis_output_fails_the_run():
    ok, problems = check_run_health(
        {"sector_growth": [], "early_warnings": []}, _watchlist(10)
    )
    assert ok is False
    assert any("sector" in p for p in problems)
    assert any("early-warning" in p for p in problems)


def test_empty_watchlist_fails():
    ok, problems = check_run_health(_healthy_data(), {})
    assert ok is False
    assert problems == ["watchlist is empty"]


def test_macro_indicators_excluded_from_coverage_math():
    """Index trackers carry no fundamentals and must not drag the ratio down."""
    wl = _watchlist(10)
    wl["macro_indicators"] = [{"ticker": "ETF", "name": "ETF"}]
    ok, _ = check_run_health(_healthy_data(), wl)
    assert ok is True


def test_never_raises_on_junk():
    # A health check that fails for its own reasons is worse than none.
    ok, _ = check_run_health(None, None)
    assert ok is False  # empty watchlist
    ok, _ = check_run_health({"sector_growth": [1]}, {"sec": "not a list"})
    assert isinstance(ok, bool)


# ---------------------------------------------------------------------------
# turnover coverage is reported every run, and only a total collapse fails it
# ---------------------------------------------------------------------------


def _with_liquidity(n, bands):
    """Watchlist of n holdings where bands[i] is the i-th holding's band."""
    wl = _watchlist(n)
    for stock, band in zip(wl["sec"], bands):
        if band is not None:
            stock["screener"]["liquidity_band"] = band
            stock["screener"]["advt_cr"] = 0.4 if band == "illiquid" else 50.0
    return wl


def test_coverage_summary_counts_each_band():
    counts = summarize_liquidity(
        _with_liquidity(5, ["illiquid", "thin", "adequate", "liquid", None])
    )
    assert counts["total"] == 5
    assert counts["measured"] == 4
    assert counts["illiquid"] == 1
    assert counts["thin"] == 1
    assert counts["adequate"] == 1
    assert counts["liquid"] == 1
    assert counts["unknown"] == 1


def test_turnover_coverage_is_reported_not_gated():
    """Coverage is logged, never failed — the healthy baseline for this field
    has not been measured in production yet, and a gate on a guessed baseline
    either cries wolf daily or passes trivially."""
    ok, problems = check_run_health(
        _healthy_data(), _with_liquidity(10, ["liquid"] + [None] * 9)
    )
    assert ok is True
    assert not any("traded-value" in p or "turnover" in p for p in problems)


def test_zero_turnover_coverage_still_does_not_fail_the_run():
    ok, problems = check_run_health(_healthy_data(), _with_liquidity(10, [None] * 10))
    assert ok is True
    assert not any("traded-value" in p or "turnover" in p for p in problems)


def test_summary_survives_a_malformed_watchlist():
    """The health module must never be the reason a run fails."""
    assert summarize_liquidity({})["total"] == 0
    assert summarize_liquidity({"sec": [None, "junk"]})["total"] == 0
