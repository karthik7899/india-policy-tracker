import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.early_warning import generate_early_warnings, _to_float  # noqa: E402


def _categories(warnings):
    return {w["category"] for w in warnings}


def test_empty_inputs_return_empty_list():
    assert generate_early_warnings({}, {}) == []
    assert generate_early_warnings({}, None) == []


def test_macro_indicators_sector_is_skipped():
    watchlist = {
        "macro_indicators": [
            {
                "ticker": "MAKEINDIA",
                "name": "Make in India ETF",
                "screener": {"qoq_sales_growth": -10.0},
            }
        ]
    }
    assert generate_early_warnings({}, watchlist) == []


def test_risk_rules_trigger_expected_categories():
    watchlist = {
        "clean_energy": [
            {
                "ticker": "RISKY",
                "name": "Risky Corp",
                "percent_change": -9.0,
                "screener": {
                    "promoter_change": -2.5,
                    "fii_change": -3.5,
                    "qoq_sales_growth": -8.0,
                    "current_ratio": 0.8,
                    "debt_to_equity": 1.4,
                    "opm_expansion": -3.0,
                    "valuation_alerts": ["High P/E", "High P/E"],
                },
            }
        ]
    }
    warnings = generate_early_warnings({}, watchlist)
    cats = _categories(warnings)
    assert {
        "Promoter Exit",
        "FII Outflow",
        "Revenue Contraction",
        "Liquidity Stress",
        "High Leverage",
        "Margin Compression",
        "Valuation Stretch",
        "Price Breakdown",
    } <= cats
    # Promoter exit and a -9% session both qualify as Critical severity.
    assert any(w["severity"] == "Critical" for w in warnings)
    # Valuation alerts are de-duplicated into a single consolidated signal.
    val = [w for w in warnings if w["category"] == "Valuation Stretch"][0]
    assert val["signal"].count("High P/E") == 1
    assert all(w["direction"] == "risk" for w in warnings)


def test_opportunity_rules_trigger_expected_categories():
    data = {
        "corporate_agreements": [
            {"company": "Winner Corp", "title": "Mega defence MoU"}
        ]
    }
    watchlist = {
        "aerospace_defence": [
            {
                "ticker": "WIN",
                "name": "Winner Corp",
                "percent_change": 6.0,
                "volume_surge": 3.0,
                "screener": {"fii_change": 1.2, "dii_change": 0.9},
            }
        ]
    }
    warnings = generate_early_warnings(data, watchlist)
    cats = _categories(warnings)
    assert {
        "Institutional Accumulation",
        "Policy Catalyst",
        "Momentum Breakout",
    } <= cats
    assert all(w["direction"] == "opportunity" for w in warnings)


def test_risks_sorted_before_opportunities_then_by_severity():
    watchlist = {
        "clean_energy": [
            {
                "ticker": "MIX",
                "name": "Mixed Corp",
                "screener": {
                    "fii_change": 1.0,  # opportunity (Medium)
                    "dii_change": 1.0,  # opportunity (paired -> High)
                    "current_ratio": 0.5,  # risk (High)
                },
            }
        ]
    }
    warnings = generate_early_warnings({}, watchlist)
    directions = [w["direction"] for w in warnings]
    # All risks come before any opportunity.
    assert directions == sorted(directions, key=lambda d: 0 if d == "risk" else 1)
    assert directions[0] == "risk"


def test_missing_and_string_fields_do_not_raise():
    watchlist = {
        "fmcg": [
            {"ticker": "A", "name": "Alpha", "screener": None},
            {"ticker": "B", "name": "Beta"},  # no screener key at all
            {
                "ticker": "C",
                "name": "Gamma",
                "percent_change": "-6.5%",
                "screener": {"debt_to_equity": "1.20", "fii_change": "N/A"},
            },
            "not-a-dict",
        ]
    }
    warnings = generate_early_warnings({}, watchlist)
    # String "-6.5%" parses to a Price Breakdown; "1.20" parses to High Leverage.
    cats = _categories(warnings)
    assert "Price Breakdown" in cats
    assert "High Leverage" in cats


def test_to_float_handles_varied_inputs():
    assert _to_float(None) is None
    assert _to_float(True) is None
    assert _to_float("—") is None
    assert _to_float("N/A") is None
    assert _to_float("+15.5%") == 15.5
    assert _to_float("1,250") == 1250.0
    assert _to_float(3) == 3.0
