"""Tests for fundamental candidate discovery (analysis/candidate_screen.py)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.candidate_screen import (  # noqa: E402
    MIN_GROWTH_PCT,
    MIN_INDUSTRY_SHARE_PCT,
    MIN_MARKET_CAP_CR,
    candidates_for_rotation,
    screen_sector_candidates,
)


def _peer(ticker, **kw):
    """A peer row as it arrives from providers/screener.py.

    ``industry_share_pct`` is stamped there, against the company's own
    industry table, so the screen never recomputes a denominator.
    """
    row = {
        "ticker": ticker,
        "name": kw.pop("name", ticker),
        "market_cap": kw.pop("market_cap", 20_000.0),
        "sales_qtr": kw.pop("sales_qtr", 500.0),
        "sales_var_pct": kw.pop("sales_var_pct", 40.0),
        "profit_var_pct": kw.pop("profit_var_pct", None),
        "industry_share_pct": kw.pop("industry_share_pct", 25.0),
    }
    row.update(kw)
    return row


def test_strong_peer_clears_all_three_gates():
    """Syrma's real numbers: the candidate that sat unusable in the radar."""
    peers = {
        "electronics": [
            _peer(
                "SYRMA",
                name="Syrma SGS Tech.",
                market_cap=24_842.0,
                sales_qtr=1465.0,
                sales_var_pct=58.5,
                industry_share_pct=31.84,
            )
        ]
    }
    out = screen_sector_candidates(peers)
    assert [c["ticker"] for c in out["electronics"]] == ["SYRMA"]
    c = out["electronics"][0]
    assert c["growth_pct"] == 58.5
    assert c["industry_share_pct"] > MIN_INDUSTRY_SHARE_PCT
    assert c["basis"] == "revenue growth"


def test_profit_growth_is_preferred_over_revenue_growth():
    """Revenue bought at no margin is not a threat."""
    peers = {"sec": [_peer("A", sales_var_pct=80.0, profit_var_pct=20.0)]}
    c = screen_sector_candidates(peers)["sec"][0]
    assert c["growth_pct"] == 20.0
    assert c["basis"] == "profit growth"


def test_each_gate_rejects_independently():
    too_small = {"sec": [_peer("X", market_cap=MIN_MARKET_CAP_CR - 1)]}
    too_slow = {"sec": [_peer("X", sales_var_pct=MIN_GROWTH_PCT - 1)]}
    # A rounding error's worth of its industry's revenue.
    tiny_share = {"sec": [_peer("X", industry_share_pct=MIN_INDUSTRY_SHARE_PCT - 0.1)]}
    assert screen_sector_candidates(too_small) == {}
    assert screen_sector_candidates(too_slow) == {}
    assert screen_sector_candidates(tiny_share) == {}


def test_unstamped_share_is_rejected_rather_than_assumed():
    """A row that never got a share stamped cannot clear the share gate."""
    peers = {"sec": [_peer("X", industry_share_pct=None)]}
    assert screen_sector_candidates(peers) == {}


def test_bse_scrip_codes_are_excluded():
    """Screener identifies BSE-only names numerically; they have no .NS quote."""
    peers = {"sec": [_peer("526775", name="Valiant Commun."), _peer("REAL")]}
    assert [c["ticker"] for c in screen_sector_candidates(peers)["sec"]] == ["REAL"]


def test_unknown_symbols_rejected_when_master_supplied():
    peers = {"sec": [_peer("GHOST"), _peer("REAL")]}
    out = screen_sector_candidates(peers, known_symbols={"REAL"})
    assert [c["ticker"] for c in out["sec"]] == ["REAL"]


def test_absurd_growth_falls_back_then_rejects():
    """A base-effect number must not win the ranking.

    The profit figure is outside any believable band, so the screen falls back
    to revenue growth rather than trusting it.
    """
    peers = {"sec": [_peer("A", profit_var_pct=90_000.0, sales_var_pct=30.0)]}
    c = screen_sector_candidates(peers)["sec"][0]
    assert c["growth_pct"] == 30.0
    assert c["basis"] == "revenue growth"


def test_ranked_by_growth_and_capped_per_sector():
    peers = {
        "sec": [
            _peer("SLOW", sales_var_pct=20.0),
            _peer("FAST", sales_var_pct=90.0),
            _peer("MID", sales_var_pct=50.0),
            _peer("ALSO", sales_var_pct=45.0),
        ]
    }
    out = screen_sector_candidates(peers, max_per_sector=2)
    assert [c["ticker"] for c in out["sec"]] == ["FAST", "MID"]


def test_never_raises_on_junk():
    assert screen_sector_candidates(None) == {}
    assert screen_sector_candidates({"sec": "not a list"}) == {}
    assert screen_sector_candidates({"sec": [None, {}, {"ticker": ""}]}) == {}


def test_candidates_for_rotation_shape():
    screened = {
        "sec": [{"ticker": "SYRMA", "name": "Syrma SGS Tech.", "growth_pct": 58.5}]
    }
    assert candidates_for_rotation(screened) == {
        "sec": [{"name": "Syrma SGS Tech.", "ticker": "SYRMA"}]
    }
    assert candidates_for_rotation(None) == {}
