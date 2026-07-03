"""Tests for the hedge-fund-style research engine additions:
thesis health, estimate revisions, variant perception, curve staging,
and rotation post-mortems."""

import sys
import os
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.revisions import (  # noqa: E402
    snapshot_prior_estimates,
    compute_revision_momentum,
)
from analysis.thesis import compute_thesis_health, thesis_health_sorted  # noqa: E402
from analysis.variant_perception import compute_variant_perception  # noqa: E402
from analysis.curve_stage import classify_sector_curve_stage  # noqa: E402
from analysis import postmortem  # noqa: E402
from analysis.rotation import auto_curate_watchlist  # noqa: E402

# ---------------------------------------------------------------------------
# revisions
# ---------------------------------------------------------------------------


def _wl(ticker, target=None, analyst_count=None, rec_score=None, sector="sec"):
    stock = {"ticker": ticker, "name": f"{ticker} Ltd"}
    if target is not None:
        stock["target"] = target
    if analyst_count is not None:
        stock["analyst_count"] = analyst_count
    if rec_score is not None:
        stock["rec_score"] = rec_score
    return {sector: [stock]}


def test_snapshot_prior_estimates_extracts_fields():
    wl = _wl("AAA", target="100.00", analyst_count=5, rec_score=2.0)
    snap = snapshot_prior_estimates(wl)
    assert snap == {"AAA": {"target": 100.0, "analyst_count": 5.0, "rec_score": 2.0}}


def test_revision_momentum_flags_material_target_move():
    prior = snapshot_prior_estimates(
        _wl("AAA", target="100.00", analyst_count=5, rec_score=2.0)
    )
    current = _wl("AAA", target="120.00", analyst_count=7, rec_score=1.5)
    revisions = compute_revision_momentum(current, prior)
    assert len(revisions) == 1
    r = revisions[0]
    assert r["ticker"] == "AAA"
    assert r["target_change_pct"] == 20.0
    assert r["direction"] == "up"
    assert r["analyst_count_change"] == 2
    assert r["rec_score_change"] == -0.5


def test_revision_momentum_ignores_small_moves():
    prior = snapshot_prior_estimates(_wl("AAA", target="100.00"))
    current = _wl("AAA", target="101.50")  # 1.5% move, below the 3% default gate
    assert compute_revision_momentum(current, prior) == []


def test_revision_momentum_ignores_new_stocks_with_no_prior():
    current = _wl("NEWCO", target="100.00")
    assert compute_revision_momentum(current, {}) == []


def test_revision_momentum_skips_macro_indicators():
    prior = snapshot_prior_estimates(
        _wl("ETF", target="100.00", sector="macro_indicators")
    )
    current = _wl("ETF", target="150.00", sector="macro_indicators")
    assert compute_revision_momentum(current, prior) == []


# ---------------------------------------------------------------------------
# thesis health
# ---------------------------------------------------------------------------


def test_thesis_intact_with_no_risk_warnings():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    health = compute_thesis_health(wl, warnings=[])
    assert health["AAA"]["status"] == "Intact"


def test_thesis_broken_on_critical_warning():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    warnings = [
        {
            "ticker": "AAA",
            "direction": "risk",
            "severity": "Critical",
            "signal": "Heavy promoter selling.",
        }
    ]
    health = compute_thesis_health(wl, warnings)
    assert health["AAA"]["status"] == "Broken"
    assert "Heavy promoter selling." in health["AAA"]["reasons"]


def test_thesis_broken_on_two_high_severity_warnings():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    warnings = [
        {"ticker": "AAA", "direction": "risk", "severity": "High", "signal": "A"},
        {"ticker": "AAA", "direction": "risk", "severity": "High", "signal": "B"},
    ]
    health = compute_thesis_health(wl, warnings)
    assert health["AAA"]["status"] == "Broken"


def test_thesis_weakening_on_single_high_warning():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    warnings = [
        {"ticker": "AAA", "direction": "risk", "severity": "High", "signal": "A"}
    ]
    health = compute_thesis_health(wl, warnings)
    assert health["AAA"]["status"] == "Weakening"


def test_thesis_weakening_on_two_medium_warnings():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    warnings = [
        {"ticker": "AAA", "direction": "risk", "severity": "Medium", "signal": "A"},
        {"ticker": "AAA", "direction": "risk", "severity": "Medium", "signal": "B"},
    ]
    health = compute_thesis_health(wl, warnings)
    assert health["AAA"]["status"] == "Weakening"


def test_thesis_opportunity_warnings_do_not_hurt():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    warnings = [
        {
            "ticker": "AAA",
            "direction": "opportunity",
            "severity": "High",
            "signal": "Great news",
        }
    ]
    health = compute_thesis_health(wl, warnings)
    assert health["AAA"]["status"] == "Intact"


def test_thesis_negative_revision_worsens_status():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    revisions = [
        {
            "ticker": "AAA",
            "direction": "down",
            "target_change_pct": -15.0,
        }
    ]
    health = compute_thesis_health(wl, warnings=[], revisions=revisions)
    assert health["AAA"]["status"] == "Weakening"
    assert any("Consensus target cut" in r for r in health["AAA"]["reasons"])


def test_thesis_negative_revision_pushes_weakening_to_broken():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA Ltd"}]}
    warnings = [
        {"ticker": "AAA", "direction": "risk", "severity": "High", "signal": "A"}
    ]
    revisions = [{"ticker": "AAA", "direction": "down", "target_change_pct": -12.0}]
    health = compute_thesis_health(wl, warnings, revisions)
    assert health["AAA"]["status"] == "Broken"


def test_thesis_macro_indicators_skipped():
    wl = {"macro_indicators": [{"ticker": "ETF", "name": "ETF"}]}
    assert compute_thesis_health(wl, []) == {}


def test_thesis_health_sorted_broken_first():
    wl = {
        "sec": [
            {"ticker": "GOOD", "name": "Good"},
            {"ticker": "BAD", "name": "Bad"},
        ]
    }
    warnings = [
        {"ticker": "BAD", "direction": "risk", "severity": "Critical", "signal": "X"}
    ]
    health = compute_thesis_health(wl, warnings)
    ordered = thesis_health_sorted(health)
    assert ordered[0]["ticker"] == "BAD"
    assert ordered[0]["status"] == "Broken"
    assert ordered[-1]["ticker"] == "GOOD"


# ---------------------------------------------------------------------------
# variant perception
# ---------------------------------------------------------------------------


def test_variant_perception_flags_large_divergence():
    wl = {
        "sec": [
            {
                "ticker": "AAA",
                "name": "AAA Ltd",
                "estimate_method": "Analyst Consensus",
                "target": "100.00",
                "fundamental_value": 180.0,
            }
        ]
    }
    rows = compute_variant_perception(wl)
    assert len(rows) == 1
    assert rows[0]["divergence_pct"] == 80.0
    assert rows[0]["direction"] == "more_bullish"


def test_variant_perception_skips_fundamental_estimate_method():
    wl = {
        "sec": [
            {
                "ticker": "AAA",
                "name": "AAA Ltd",
                "estimate_method": "Fundamental Estimate",
                "target": "100.00",
                "fundamental_value": 180.0,
            }
        ]
    }
    assert compute_variant_perception(wl) == []


def test_variant_perception_skips_small_divergence():
    wl = {
        "sec": [
            {
                "ticker": "AAA",
                "name": "AAA Ltd",
                "estimate_method": "Analyst Consensus",
                "target": "100.00",
                "fundamental_value": 105.0,
            }
        ]
    }
    assert compute_variant_perception(wl) == []


def test_variant_perception_sorted_by_magnitude():
    wl = {
        "sec": [
            {
                "ticker": "SMALL",
                "name": "Small",
                "estimate_method": "Analyst Consensus",
                "target": "100.00",
                "fundamental_value": 120.0,
            },
            {
                "ticker": "BIG",
                "name": "Big",
                "estimate_method": "Analyst Consensus",
                "target": "100.00",
                "fundamental_value": 200.0,
            },
        ]
    }
    rows = compute_variant_perception(wl)
    assert [r["ticker"] for r in rows] == ["BIG", "SMALL"]


# ---------------------------------------------------------------------------
# curve stage
# ---------------------------------------------------------------------------


def _stock_with_sales(ticker, sales_trend):
    return {"ticker": ticker, "screener": {"sales_trend": sales_trend}}


def test_curve_stage_inflection_for_high_accelerating_growth():
    wl = {
        "sec": [
            _stock_with_sales("A", [100, 110, 125, 145, 170]),
            _stock_with_sales("B", [100, 112, 128, 148, 172]),
        ]
    }
    result = classify_sector_curve_stage(wl)
    assert result["sec"]["stage"] == "Inflection / Steep Adoption"


def test_curve_stage_contracting_for_negative_growth():
    wl = {
        "sec": [
            _stock_with_sales("A", [100, 95, 90]),
            _stock_with_sales("B", [100, 92, 85]),
        ]
    }
    result = classify_sector_curve_stage(wl)
    assert result["sec"]["stage"] == "Late-Cycle / Contracting"


def test_curve_stage_needs_at_least_two_peers():
    wl = {"sec": [_stock_with_sales("A", [100, 120, 140])]}
    assert classify_sector_curve_stage(wl) == {}


def test_curve_stage_macro_indicators_skipped():
    wl = {
        "macro_indicators": [
            _stock_with_sales("A", [100, 120]),
            _stock_with_sales("B", [100, 130]),
        ]
    }
    assert classify_sector_curve_stage(wl) == {}


# ---------------------------------------------------------------------------
# rotation post-mortem
# ---------------------------------------------------------------------------


def test_log_decision_appends_valid_entry():
    ledger = []
    postmortem.log_decision(
        ledger,
        "added",
        "sec",
        {"ticker": "AAA", "name": "AAA Ltd", "price": "100.00", "target": "150.00"},
        today=datetime.date(2026, 1, 1),
    )
    assert len(ledger) == 1
    assert ledger[0]["ticker"] == "AAA"
    assert ledger[0]["scored"] is False


def test_log_decision_skips_unparseable_price():
    ledger = []
    postmortem.log_decision(
        ledger,
        "added",
        "sec",
        {"ticker": "AAA", "name": "AAA", "price": None, "target": "150.00"},
    )
    assert ledger == []


def test_score_pending_decision_win():
    ledger = []
    postmortem.log_decision(
        ledger,
        "added",
        "sec",
        {"ticker": "WIN", "name": "Winner", "price": "100.00", "target": "150.00"},
        today=datetime.date(2026, 1, 1),
    )
    wl = {"sec": [{"ticker": "WIN", "price": "140.00"}]}  # captured >50% of the upside
    postmortem.score_pending_decisions(ledger, wl, today=datetime.date(2026, 3, 1))
    assert ledger[0]["scored"] is True
    assert ledger[0]["outcome"] == "Thesis Playing Out"
    assert ledger[0]["realized_return_pct"] == 40.0


def test_score_pending_decision_loss():
    ledger = []
    postmortem.log_decision(
        ledger,
        "added",
        "sec",
        {"ticker": "LOSE", "name": "Loser", "price": "100.00", "target": "150.00"},
        today=datetime.date(2026, 1, 1),
    )
    wl = {"sec": [{"ticker": "LOSE", "price": "95.00"}]}
    postmortem.score_pending_decisions(ledger, wl, today=datetime.date(2026, 3, 1))
    assert ledger[0]["outcome"] == "Underperforming"


def test_score_pending_decision_too_young_stays_pending():
    ledger = []
    postmortem.log_decision(
        ledger,
        "added",
        "sec",
        {"ticker": "AAA", "name": "AAA", "price": "100.00", "target": "150.00"},
        today=datetime.date(2026, 1, 1),
    )
    wl = {"sec": [{"ticker": "AAA", "price": "140.00"}]}
    postmortem.score_pending_decisions(ledger, wl, today=datetime.date(2026, 1, 10))
    assert ledger[0]["scored"] is False


def test_score_pending_decision_untracked_when_ticker_left_watchlist():
    ledger = []
    postmortem.log_decision(
        ledger,
        "added",
        "sec",
        {"ticker": "GONE", "name": "Gone", "price": "100.00", "target": "150.00"},
        today=datetime.date(2026, 1, 1),
    )
    postmortem.score_pending_decisions(ledger, {}, today=datetime.date(2026, 3, 1))
    assert ledger[0]["scored"] is True
    assert ledger[0]["outcome"] == "Left Watchlist (unscored)"
    assert ledger[0]["realized_return_pct"] is None


def test_compute_hit_rate_only_counts_judged_entries():
    ledger = [
        {"outcome": "Thesis Playing Out"},
        {"outcome": "Thesis Playing Out"},
        {"outcome": "Underperforming"},
        {"outcome": "Left Watchlist (unscored)"},
        {"outcome": None},
    ]
    stats = postmortem.compute_hit_rate(ledger)
    assert stats == {"total_scored": 3, "wins": 2, "win_rate_pct": 66.7}


def test_compute_hit_rate_empty_ledger():
    assert postmortem.compute_hit_rate([]) == {
        "total_scored": 0,
        "wins": 0,
        "win_rate_pct": None,
    }


def test_recent_outcomes_sorted_newest_first():
    ledger = [
        {"date": "2026-01-01", "outcome": "Thesis Playing Out"},
        {"date": "2026-03-01", "outcome": "Underperforming"},
        {"date": "2026-02-01", "outcome": None},  # unjudged, excluded
    ]
    recent = postmortem.recent_outcomes(ledger, limit=5)
    assert [e["date"] for e in recent] == ["2026-03-01", "2026-01-01"]


def test_load_ledger_missing_file_returns_empty(tmp_path):
    assert postmortem.load_ledger(str(tmp_path / "nope.json")) == []


def test_save_and_load_ledger_roundtrip(tmp_path):
    path = str(tmp_path / "ledger.json")
    ledger = [{"ticker": "AAA", "scored": False}]
    assert postmortem.save_ledger(ledger, path) is True
    assert postmortem.load_ledger(path) == ledger


# ---------------------------------------------------------------------------
# auto_curate_watchlist now returns (structured_emerging, decisions)
# ---------------------------------------------------------------------------


def test_auto_curate_watchlist_returns_decisions_tuple():
    result = auto_curate_watchlist({}, {})
    assert isinstance(result, tuple)
    assert len(result) == 2
    structured, decisions = result
    assert isinstance(structured, dict)
    assert decisions == []
