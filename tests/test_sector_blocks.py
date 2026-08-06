"""Tests for per-sector blocks (dashboard/sector_blocks.py).

The blocks exist so the email and the dashboard cannot disagree about which
sectors matter. Most of these therefore assert on ordering, caps and the
label/slug matching that has already broken one ranking silently.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import SECTOR_METADATA  # noqa: E402
from dashboard.sector_blocks import (  # noqa: E402
    MAX_FOCUS,
    MAX_NEWS,
    MAX_THREATS,
    build_sector_blocks,
    sector_delta,
)

_KEYS = [k for k in SECTOR_METADATA if k != "macro_indicators"][:4]


def _warning(ticker, sector_key, severity="Medium", status="new"):
    return {
        "ticker": ticker,
        "name": f"{ticker} Ltd",
        # Warnings carry the LABEL, which is the mismatch that broke ranking.
        "sector": SECTOR_METADATA[sector_key]["label"],
        "severity": severity,
        "status": status,
        "direction": "risk",
        "category": "Margin Compression",
        "signal": "OPM fell",
    }


def _brief(**kw):
    data = {"early_warnings": [], "sector_valuation": [], "coverage_count": {}}
    data.update(kw)
    return data


def _watchlist(key, n=5):
    return {
        key: [
            {
                "ticker": f"T{i}",
                "name": f"T{i} Ltd",
                "score": {"overall_score": i},
                "screener": {"pe_vs_peers": "10% above peers"},
            }
            for i in range(n)
        ]
    }


class TestOrdering:
    def test_blocks_are_ordered_by_severity_weighted_delta(self):
        brief = _brief(
            early_warnings=[
                _warning("A", _KEYS[0], "Low"),
                _warning("B", _KEYS[1], "Critical"),
            ]
        )
        for k in _KEYS[:2]:
            brief[k] = []
        blocks = build_sector_blocks(brief, {})
        assert [b["id"] for b in blocks] == [_KEYS[1], _KEYS[0]]

    def test_ordering_is_deterministic(self):
        """A reordered briefing reads as new information."""
        brief = _brief(early_warnings=[_warning("A", k) for k in _KEYS[:3]])
        for k in _KEYS[:3]:
            brief[k] = []
        first = [b["id"] for b in build_sector_blocks(brief, {})]
        for _ in range(5):
            assert [b["id"] for b in build_sector_blocks(brief, {})] == first

    def test_delta_matches_the_label_not_only_the_slug(self):
        brief = _brief(early_warnings=[_warning("A", _KEYS[0], "Critical")])
        assert sector_delta(_KEYS[0], brief) == 4

    def test_ongoing_warnings_are_not_change(self):
        brief = _brief(
            early_warnings=[_warning("A", _KEYS[0], "Critical", status="ongoing")]
        )
        assert sector_delta(_KEYS[0], brief) == 0


class TestInclusion:
    def test_a_sector_with_neither_change_nor_news_is_omitted(self):
        brief = _brief()
        brief[_KEYS[0]] = []
        assert build_sector_blocks(brief, {}) == []

    def test_news_alone_earns_a_block(self):
        brief = _brief()
        brief[_KEYS[0]] = [{"title": "Something happened", "link": "u"}]
        blocks = build_sector_blocks(brief, {})
        assert len(blocks) == 1
        assert blocks[0]["counts"] == {"new": 0, "escalated": 0}


class TestCaps:
    def test_every_list_is_capped(self):
        brief = _brief(
            early_warnings=[_warning(f"T{i}", _KEYS[0], "Critical") for i in range(6)],
            new_entrants=[
                {"challenger": f"C{i}", "sector": _KEYS[0]} for i in range(5)
            ],
            peer_competitors={
                _KEYS[0]: [{"name": f"P{i}", "sales_var_pct": 5.0} for i in range(5)]
            },
        )
        brief[_KEYS[0]] = [{"title": f"headline {i}", "link": "u"} for i in range(10)]
        block = build_sector_blocks(brief, _watchlist(_KEYS[0], 8))[0]
        assert len(block["news"]) <= MAX_NEWS
        assert len(block["focus_stocks"]) <= MAX_FOCUS
        assert len(block["threats"]) <= MAX_THREATS


class TestContent:
    def test_every_news_item_carries_a_url_field(self):
        """The renderer must be able to say a link is missing rather than
        emit dead markup, so the key is always present."""
        brief = _brief()
        brief[_KEYS[0]] = [
            {"title": "with link", "link": "https://example.com"},
            {"title": "without link"},
        ]
        block = build_sector_blocks(brief, {})[0]
        assert all("url" in n for n in block["news"])
        assert any(n["url"] == "" for n in block["news"])

    def test_focus_stocks_carry_a_deep_link_and_coverage_count(self):
        brief = _brief(
            early_warnings=[_warning("T1", _KEYS[0], "Critical")],
            coverage_count={"T1": 7},
        )
        brief[_KEYS[0]] = []
        block = build_sector_blocks(brief, _watchlist(_KEYS[0]))[0]
        top = block["focus_stocks"][0]
        assert top["ticker"] == "T1"
        assert top["deep_link"] == "#stock/T1/snapshot"
        assert top["coverage_count"] == 7

    def test_an_unlisted_challenger_reports_no_growth_rather_than_zero(self):
        brief = _brief(peer_competitors={_KEYS[0]: [{"name": "Unlisted Co"}]})
        brief[_KEYS[0]] = [{"title": "n", "link": "u"}]
        block = build_sector_blocks(brief, {})[0]
        assert block["threats"][0]["detail"] == "unlisted entrant"

    def test_a_stock_with_no_signal_says_so(self):
        brief = _brief()
        brief[_KEYS[0]] = [{"title": "n", "link": "u"}]
        block = build_sector_blocks(brief, _watchlist(_KEYS[0]))[0]
        assert block["focus_stocks"][0]["primary_signal"] == "No signal this cycle"


class TestRobustness:
    def test_malformed_input_yields_no_blocks_rather_than_an_error(self):
        assert build_sector_blocks({}, {}) == []
        assert build_sector_blocks(None, None) == []


class TestParity:
    def test_the_email_ranks_sectors_from_the_shared_blocks(self):
        """Not from its own copy of the ranking logic."""
        from emails.mailer import _sectors_to_render, _CAPS_NORMAL

        brief = _brief(
            early_warnings=[
                _warning("A", _KEYS[0], "Low"),
                _warning("B", _KEYS[1], "Critical"),
            ]
        )
        for k in _KEYS[:2]:
            brief[k] = []
        brief["sector_blocks"] = build_sector_blocks(brief, {})
        selected, total = _sectors_to_render(brief, _CAPS_NORMAL)
        assert selected == [b["id"] for b in brief["sector_blocks"]]
        assert total == len(brief["sector_blocks"])
