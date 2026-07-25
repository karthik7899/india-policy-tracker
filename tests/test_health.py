"""Tests for run-health assertions (health.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from health import check_run_health  # noqa: E402


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
