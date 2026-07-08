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
