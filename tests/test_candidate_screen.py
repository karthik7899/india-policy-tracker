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
    row = {
        "ticker": ticker,
        "name": kw.pop("name", ticker),
        "market_cap": kw.pop("market_cap", 20_000.0),
        "sales_qtr": kw.pop("sales_qtr", 500.0),
        "sales_var_pct": kw.pop("sales_var_pct", 40.0),
        "profit_var_pct": kw.pop("profit_var_pct", None),
    }
    row.update(kw)
    return row


def _industry(*rows):
    return list(rows)


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
            )
        ]
    }
    industry = {
        "electronics": _industry(
            _peer("SYRMA", sales_qtr=1465.0), _peer("HOLDING", sales_qtr=3000.0)
        )
    }
    out = screen_sector_candidates(peers, industry)
    assert [c["ticker"] for c in out["electronics"]] == ["SYRMA"]
    c = out["electronics"][0]
    assert c["growth_pct"] == 58.5
    assert c["industry_share_pct"] > MIN_INDUSTRY_SHARE_PCT
    assert c["basis"] == "revenue growth"


def test_profit_growth_is_preferred_over_revenue_growth():
    """Revenue bought at no margin is not a threat."""
    peers = {"sec": [_peer("A", sales_var_pct=80.0, profit_var_pct=20.0)]}
    out = screen_sector_candidates(peers, {"sec": _industry(_peer("A"))})
    c = out["sec"][0]
    assert c["growth_pct"] == 20.0
    assert c["basis"] == "profit growth"


def test_each_gate_rejects_independently():
    industry = {"sec": _industry(_peer("X", sales_qtr=1000.0))}
    too_small = {
        "sec": [_peer("X", market_cap=MIN_MARKET_CAP_CR - 1, sales_qtr=1000.0)]
    }
    too_slow = {"sec": [_peer("X", sales_var_pct=MIN_GROWTH_PCT - 1, sales_qtr=1000.0)]}
    # A rounding error's worth of the industry's revenue.
    tiny_share = {"sec": [_peer("X", sales_qtr=1.0)]}
    assert screen_sector_candidates(too_small, industry) == {}
    assert screen_sector_candidates(too_slow, industry) == {}
    assert (
        screen_sector_candidates(
            tiny_share,
            {
                "sec": _industry(
                    _peer("X", sales_qtr=1.0), _peer("BIG", sales_qtr=10_000.0)
                )
            },
        )
        == {}
    )


def test_bse_scrip_codes_are_excluded():
    """Screener identifies BSE-only names numerically; they have no .NS quote."""
    peers = {"sec": [_peer("526775", name="Valiant Commun."), _peer("REAL")]}
    out = screen_sector_candidates(
        peers, {"sec": _industry(_peer("526775"), _peer("REAL"))}
    )
    assert [c["ticker"] for c in out["sec"]] == ["REAL"]


def test_unknown_symbols_rejected_when_master_supplied():
    peers = {"sec": [_peer("GHOST"), _peer("REAL")]}
    industry = {"sec": _industry(_peer("GHOST"), _peer("REAL"))}
    out = screen_sector_candidates(peers, industry, known_symbols={"REAL"})
    assert [c["ticker"] for c in out["sec"]] == ["REAL"]


def test_absurd_growth_falls_back_then_rejects():
    """A base-effect number must not win the ranking.

    The profit figure is outside any believable band, so the screen falls back
    to revenue growth rather than trusting it.
    """
    peers = {"sec": [_peer("A", profit_var_pct=90_000.0, sales_var_pct=30.0)]}
    out = screen_sector_candidates(peers, {"sec": _industry(_peer("A"))})
    assert out["sec"][0]["growth_pct"] == 30.0
    assert out["sec"][0]["basis"] == "revenue growth"


def test_ranked_by_growth_and_capped_per_sector():
    peers = {
        "sec": [
            _peer("SLOW", sales_var_pct=20.0),
            _peer("FAST", sales_var_pct=90.0),
            _peer("MID", sales_var_pct=50.0),
            _peer("ALSO", sales_var_pct=45.0),
        ]
    }
    industry = {"sec": _industry(*[_peer(t) for t in ("SLOW", "FAST", "MID", "ALSO")])}
    out = screen_sector_candidates(peers, industry, max_per_sector=2)
    assert [c["ticker"] for c in out["sec"]] == ["FAST", "MID"]


def test_never_raises_on_junk():
    assert screen_sector_candidates(None, None) == {}
    assert screen_sector_candidates({"sec": "not a list"}, {}) == {}
    assert screen_sector_candidates({"sec": [None, {}, {"ticker": ""}]}, {}) == {}


def test_candidates_for_rotation_shape():
    screened = {
        "sec": [{"ticker": "SYRMA", "name": "Syrma SGS Tech.", "growth_pct": 58.5}]
    }
    assert candidates_for_rotation(screened) == {
        "sec": [{"name": "Syrma SGS Tech.", "ticker": "SYRMA"}]
    }
    assert candidates_for_rotation(None) == {}
