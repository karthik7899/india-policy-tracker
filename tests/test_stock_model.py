"""Tests for the typed Stock model and load-boundary normalization."""

import json
import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.stock import Stock, normalize_stock_record  # noqa: E402
from config import _normalize_watchlist  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# coercion into the typed model
# ---------------------------------------------------------------------------


def test_model_coerces_legacy_string_formats():
    stock = Stock.model_validate(
        {
            "ticker": "VBL",
            "price": "482.95",
            "target": "594.00",
            "growth_pct": "+23.0%",
            "revenue_growth": "-8.8%",
            "analyst_count": "26",
            "rec_score": 1.5,
        }
    )
    assert stock.price == 482.95
    assert stock.growth_pct == 23.0
    assert stock.revenue_growth == -8.8
    assert stock.analyst_count == 26


def test_model_coerces_garbage_to_none():
    stock = Stock.model_validate(
        {"ticker": "X", "price": "N/A", "target": "—", "growth_pct": "junk"}
    )
    assert stock.price is None
    assert stock.target is None
    assert stock.growth_pct is None


def test_model_requires_ticker():
    with pytest.raises(ValidationError):
        Stock.model_validate({"name": "No Ticker Corp"})


def test_model_passes_unknown_fields_through():
    stock = Stock.model_validate(
        {"ticker": "X", "screener": {"pe_ratio": 12.0}, "estimate_method": "Analyst"}
    )
    assert stock.screener == {"pe_ratio": 12.0}
    assert stock.estimate_method == "Analyst"


def test_rating_none_becomes_na():
    assert Stock.model_validate({"ticker": "X", "rating": None}).rating == "N/A"


# ---------------------------------------------------------------------------
# wire formatting
# ---------------------------------------------------------------------------


def test_wire_values_render_legacy_formats():
    wire = Stock.model_validate(
        {"ticker": "X", "price": 482.949, "growth_pct": 23.04, "target": 594}
    ).to_wire_values()
    assert wire["price"] == "482.95"
    assert wire["growth_pct"] == "+23.0%"
    assert wire["target"] == "594.00"


def test_wire_values_sign_rules():
    assert (
        Stock.model_validate({"ticker": "X", "growth_pct": -9.2}).to_wire_values()[
            "growth_pct"
        ]
        == "-9.2%"
    )
    assert (
        Stock.model_validate({"ticker": "X", "growth_pct": 0.0}).to_wire_values()[
            "growth_pct"
        ]
        == "0.0%"
    )


# ---------------------------------------------------------------------------
# record normalization
# ---------------------------------------------------------------------------


def test_normalize_repairs_drifted_values():
    record = {
        "ticker": "RIR",
        "price": "1,840.00",  # thousands separator
        "growth_pct": 23.0,  # number where a string belongs
        "target": "N/A",  # junk in a numeric slot
        "screener": {"pe_ratio": 12.0},
    }
    normalized = normalize_stock_record(record)
    assert normalized["price"] == "1840.00"
    assert normalized["growth_pct"] == "+23.0%"
    assert normalized["target"] is None
    assert normalized["screener"] == {"pe_ratio": 12.0}  # untouched


def test_normalize_preserves_key_order_and_absent_keys():
    record = {"catalyst": "c", "ticker": "X", "price": "10.00"}
    normalized = normalize_stock_record(record)
    assert list(normalized.keys()) == ["catalyst", "ticker", "price"]
    assert "target_high" not in normalized  # known fields aren't invented


def test_normalize_raises_validation_error_on_missing_ticker():
    record = {"name": "No Ticker Corp", "price": "10.00"}
    with pytest.raises(ValidationError):
        normalize_stock_record(record)


def test_production_watchlist_roundtrips_byte_identically():
    """The load-bearing regression: normalizing the real committed
    watchlist.json must change nothing, or every auto-commit after this
    lands would carry a spurious reformat diff."""
    with open(os.path.join(_REPO_ROOT, "watchlist.json"), encoding="utf-8") as f:
        original = json.load(f)
    normalized = _normalize_watchlist(json.loads(json.dumps(original)))
    assert normalized == original


def test_normalize_watchlist_keeps_broken_records_raw():
    watchlist = {
        "sec": [
            {"name": "No Ticker Corp", "price": "10.00"},  # unfixable: no ticker
            {"ticker": "OK", "price": "10.00"},
            "not-a-dict",
        ],
        "not_a_list": 42,
    }
    result = _normalize_watchlist(watchlist)
    assert result["sec"][0] == {"name": "No Ticker Corp", "price": "10.00"}
    assert result["sec"][1]["price"] == "10.00"
    assert result["sec"][2] == "not-a-dict"
    assert result["not_a_list"] == 42


# ---------------------------------------------------------------------------
# to_wire_values formatting coverage
# ---------------------------------------------------------------------------


def test_to_wire_values_all_fields():
    stock = Stock(
        ticker="AAPL",
        name="Apple Inc.",
        catalyst="Earnings",
        rating="Buy",
        price=150.25,
        target=180.0,
        target_median=175.5,
        target_high=200.0,
        target_low=150.0,
        growth_pct=15.5,
        revenue_growth=-2.5,
        earnings_growth=10.0,
        analyst_count=35,
        rec_score=1.2,
        fundamental_value=160.0,
    )
    wire = stock.to_wire_values()

    assert wire["ticker"] == "AAPL"
    assert wire["name"] == "Apple Inc."
    assert wire["catalyst"] == "Earnings"
    assert wire["rating"] == "Buy"
    assert wire["price"] == "150.25"
    assert wire["target"] == "180.00"
    assert wire["target_median"] == "175.50"
    assert wire["target_high"] == "200.00"
    assert wire["target_low"] == "150.00"
    assert wire["growth_pct"] == "+15.5%"
    assert wire["revenue_growth"] == "-2.5%"
    assert wire["earnings_growth"] == "+10.0%"
    assert wire["analyst_count"] == 35
    assert wire["rec_score"] == 1.2
    assert wire["fundamental_value"] == 160.0


def test_to_wire_values_none_fields():
    stock = Stock(ticker="MSFT")
    wire = stock.to_wire_values()

    assert wire["ticker"] == "MSFT"
    assert wire["name"] == ""
    assert wire["catalyst"] == ""
    assert wire["rating"] == "N/A"
    assert wire["price"] is None
    assert wire["target"] is None
    assert wire["target_median"] is None
    assert wire["target_high"] is None
    assert wire["target_low"] is None
    assert wire["growth_pct"] is None
    assert wire["revenue_growth"] is None
    assert wire["earnings_growth"] is None
    assert wire["analyst_count"] is None
    assert wire["rec_score"] is None
    assert wire["fundamental_value"] is None


def test_fractional_analyst_count_truncates_rather_than_failing():
    """Regression, merged and caught the same day: analyst_count needs its own
    validator because the field is declared int, and pydantic rejects a float
    carrying a fractional part for an int field.

    Folding it into the float validator looks like harmless deduplication and
    passes every test that existed at the time, because none supplied a
    fractional count. The cost only shows in production: normalize_stock_record
    lets ValidationError propagate, so one odd analyst_count discards the whole
    record rather than one field.

    The validator also reads as dead code to a caller-counting scan — pydantic
    holds the reference and calls it by registration, never by name.
    """
    assert (
        Stock.model_validate({"ticker": "X", "analyst_count": 12.5}).analyst_count == 12
    )
    assert (
        Stock.model_validate({"ticker": "X", "analyst_count": "12.5"}).analyst_count
        == 12
    )
    # And the ordinary shapes still land where they did.
    assert (
        Stock.model_validate({"ticker": "X", "analyst_count": "12"}).analyst_count == 12
    )
    assert (
        Stock.model_validate({"ticker": "X", "analyst_count": None}).analyst_count
        is None
    )
    assert (
        Stock.model_validate({"ticker": "X", "analyst_count": "N/A"}).analyst_count
        is None
    )
