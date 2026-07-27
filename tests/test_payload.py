"""Tests for the display payload and warning diff (dashboard/payload.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.payload import (  # noqa: E402
    FEED_CAPS,
    TOPICS_PER_STOCK,
    annotate_warning_status,
    build_display_payload,
    summarize_ongoing,
)


def _w(ticker, category, severity, status=None):
    w = {
        "ticker": ticker,
        "category": category,
        "severity": severity,
        "signal": "something happened",
        "direction": "risk",
    }
    if status:
        w["status"] = status
    return w


# ---------------------------------------------------------------------------
# warning diff
# ---------------------------------------------------------------------------


def test_first_sighting_is_new_and_a_repeat_is_ongoing():
    prior = [_w("AAA", "Margin Compression", "High")]
    now = [_w("AAA", "Margin Compression", "High"), _w("BBB", "FII Outflow", "High")]
    annotate_warning_status(now, prior)
    assert {w["ticker"]: w["status"] for w in now} == {
        "AAA": "ongoing",
        "BBB": "new",
    }


def test_worsening_severity_is_escalated():
    prior = [_w("AAA", "Margin Compression", "Medium")]
    now = [_w("AAA", "Margin Compression", "Critical")]
    annotate_warning_status(now, prior)
    assert now[0]["status"] == "escalated"


def test_improving_severity_is_not_escalated():
    prior = [_w("AAA", "Margin Compression", "Critical")]
    now = [_w("AAA", "Margin Compression", "Low")]
    annotate_warning_status(now, prior)
    assert now[0]["status"] == "ongoing"


def test_no_prior_run_makes_everything_new():
    now = [_w("AAA", "X", "High"), _w("BBB", "Y", "Low")]
    annotate_warning_status(now, [])
    assert all(w["status"] == "new" for w in now)


# ---------------------------------------------------------------------------
# collapsing standing conditions
# ---------------------------------------------------------------------------


def test_ongoing_warnings_collapse_by_category_and_severity():
    """46 identical valuation flags are one fact, not 46 alerts."""
    warnings = [
        _w(f"T{i}", "Valuation Stretch", "Medium", "ongoing") for i in range(46)
    ] + [_w("AAA", "FII Outflow", "High", "new")]
    rows = summarize_ongoing(warnings)
    assert len(rows) == 1
    assert rows[0]["count"] == 46
    assert len(rows[0]["tickers"]) == 46  # still inspectable
    assert rows[0]["category"] == "Valuation Stretch"


def test_summary_sorted_by_severity_then_size():
    warnings = [
        _w("A", "Low Thing", "Low", "ongoing"),
        _w("B", "Bad Thing", "Critical", "ongoing"),
        _w("C", "Mid Thing", "Medium", "ongoing"),
    ]
    assert [r["severity"] for r in summarize_ongoing(warnings)] == [
        "Critical",
        "Medium",
        "Low",
    ]


# ---------------------------------------------------------------------------
# payload trimming
# ---------------------------------------------------------------------------


def test_only_actionable_warnings_stay_in_the_payload():
    brief = {
        "early_warnings": [
            _w("AAA", "X", "High", "new"),
            _w("BBB", "Y", "Critical", "escalated"),
            _w("CCC", "Z", "Medium", "ongoing"),
        ]
    }
    payload = build_display_payload(brief)
    assert [w["ticker"] for w in payload["early_warnings"]] == ["AAA", "BBB"]
    assert payload["warning_summary"][0]["count"] == 1


def test_feeds_are_capped_without_touching_the_corpus():
    cap = FEED_CAPS["corporate_agreements"]
    brief = {"corporate_agreements": [{"title": f"item {i}"} for i in range(cap + 25)]}
    payload = build_display_payload(brief)
    assert len(payload["corporate_agreements"]) == cap
    # The input the pipeline computes on must be left alone.
    assert len(brief["corporate_agreements"]) == cap + 25


def test_stock_topics_capped_per_holding():
    brief = {
        "stock_topics": {
            "AAA": [{"title": f"t{i}"} for i in range(TOPICS_PER_STOCK + 4)]
        }
    }
    payload = build_display_payload(brief)
    assert len(payload["stock_topics"]["AAA"]) == TOPICS_PER_STOCK


def test_short_feeds_are_left_alone():
    brief = {"corporate_agreements": [{"title": "only one"}]}
    assert len(build_display_payload(brief)["corporate_agreements"]) == 1


def test_never_raises_on_junk():
    assert build_display_payload(None) == {}
    assert (
        build_display_payload({"corporate_agreements": "not a list"})[
            "corporate_agreements"
        ]
        == "not a list"
    )
    assert annotate_warning_status(None, None) is None
    assert summarize_ongoing(None) == []
