"""Tests for per-holding coverage attribution (analysis/stock_topics.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.stock_topics import MAX_TOPICS_PER_STOCK, build_stock_topics  # noqa: E402

_WATCHLIST = {
    "clean_energy": [
        {"ticker": "SUZLON", "name": "Suzlon Energy"},
        {"ticker": "TATAPOWER", "name": "Tata Power"},
    ],
    "textiles_apparel": [{"ticker": "ARVIND", "name": "Arvind Ltd"}],
    "macro_indicators": [{"ticker": "ETF", "name": "Some ETF"}],
}


def test_attributes_sector_news_to_the_company_it_names():
    data = {
        "clean_energy": [
            {"title": "Suzlon Energy secures 201.6 MW wind order", "link": "u1"},
            {"title": "Tata Power commissions Khavda solar park", "link": "u2"},
        ]
    }
    topics = build_stock_topics(data, _WATCHLIST)
    assert [t["title"] for t in topics["SUZLON"]] == [
        "Suzlon Energy secures 201.6 MW wind order"
    ]
    assert topics["SUZLON"][0]["kind"] == "Sector news"
    assert len(topics["TATAPOWER"]) == 1


def test_person_guard_still_applies():
    """Regression: "CEO Arvind" must not be filed under Arvind Ltd.

    The attribution deliberately reuses title_matches_company rather than a
    substring search, so this judgement lives in one place.
    """
    data = {"textiles_apparel": [{"title": "CEO Arvind Krishna outlines AI plans"}]}
    assert build_stock_topics(data, _WATCHLIST) == {}


def test_reads_each_source_from_its_own_text_field():
    """Launches carry `product`, filings carry `filing` — not `title`."""
    data = {
        "corporate_agreements": [{"title": "Suzlon signs pact with Tata Power"}],
        "product_launches": [{"product": "Suzlon unveils a 3.6 MW turbine"}],
        "corporate_filings": [{"filing": "Tata Power files Q1 results"}],
    }
    topics = build_stock_topics(data, _WATCHLIST)
    assert {t["kind"] for t in topics["SUZLON"]} == {"Agreement", "Launch"}
    # The pact names both parties, so it is coverage for both — and the
    # filing is read off `filing` rather than `title`.
    assert {t["kind"] for t in topics["TATAPOWER"]} == {"Agreement", "Filing"}


def test_market_events_use_resolved_actors_not_rematching():
    data = {
        "market_events": [
            {
                "headline": "A tie-up nobody's name appears in",
                "event_type": "tie_up",
                "actors": ["SUZLON"],
            }
        ]
    }
    topics = build_stock_topics(data, _WATCHLIST)
    assert topics["SUZLON"][0]["kind"] == "Tie Up"


def test_unknown_actors_are_ignored():
    data = {"market_events": [{"headline": "X and Y", "actors": ["NOTHELD"]}]}
    assert build_stock_topics(data, _WATCHLIST) == {}


def test_duplicate_headlines_are_not_repeated():
    data = {
        "clean_energy": [{"title": "Suzlon wins an order"}],
        "corporate_agreements": [{"title": "Suzlon wins an order"}],
    }
    assert len(build_stock_topics(data, _WATCHLIST)["SUZLON"]) == 1


def test_capped_per_stock():
    data = {
        "clean_energy": [
            {"title": f"Suzlon Energy news item number {i}"}
            for i in range(MAX_TOPICS_PER_STOCK + 5)
        ]
    }
    assert len(build_stock_topics(data, _WATCHLIST)["SUZLON"]) == MAX_TOPICS_PER_STOCK


def test_macro_indicators_are_excluded():
    data = {"macro_indicators": [{"title": "Some ETF tracks the index"}]}
    assert build_stock_topics(data, _WATCHLIST) == {}


def test_never_raises_on_junk():
    assert build_stock_topics(None, None) == {}
    assert build_stock_topics({"clean_energy": "not a list"}, _WATCHLIST) == {}
    assert build_stock_topics({"clean_energy": [None, {}]}, _WATCHLIST) == {}
