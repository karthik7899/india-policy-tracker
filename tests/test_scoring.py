"""Tests for aggregate scoring (analysis/scoring.py).

Anchored on BHEL, whose score of 44 was eleven news items plus an FII flow,
with five failed screens contributing nothing.
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.scoring import (  # noqa: E402
    POLICY_MAX_AGE_DAYS,
    POLICY_POINT_CAP,
    calculate_aggregate_score,
)
from models.core import (  # noqa: E402
    Company,
    CompanyFinancials,
    CompanyValuation,
)

_TODAY = datetime.date.today().isoformat()


def _company(events=None, **fin_kwargs):
    valuation_alerts = fin_kwargs.pop("valuation_alerts", [])
    moat = fin_kwargs.pop("moat_status", None)
    company = Company(ticker="TEST", name="Test Co", price=100.0)
    company.screener = CompanyFinancials(**fin_kwargs)
    company.valuation = CompanyValuation(
        valuation_alerts=valuation_alerts, moat_status=moat
    )
    company.policy_events = events or []
    return company


def _event(title, days_ago=0, event_type="filing"):
    date = (datetime.date.today() - datetime.timedelta(days=days_ago)).isoformat()
    return {"event_type": event_type, "title": title, "date": date}


# ---------------------------------------------------------------------------
# news flow is bounded
# ---------------------------------------------------------------------------


def test_news_flow_cannot_dominate_the_score():
    """Eleven headlines used to be worth ~42 points."""
    events = [_event(f"Some genuinely distinct headline number {i}") for i in range(11)]
    score = calculate_aggregate_score(_company(events, roce=25.0))
    assert score.momentum_score <= POLICY_POINT_CAP


def test_the_same_event_worded_twice_scores_once():
    events = [
        _event("BHEL unveils India's first indigenous 1200 kV transformer"),
        _event("BHEL unveils Indias first indigenous 1200 kV transformer!"),
    ]
    one = calculate_aggregate_score(_company([events[0]], roce=25.0)).momentum_score
    both = calculate_aggregate_score(_company(events, roce=25.0)).momentum_score
    assert one == both


def test_stale_headlines_do_not_score():
    """A 2013 project announcement is history, not a catalyst."""
    fresh = _event("A recent order win", days_ago=5)
    stale = _event(
        "A completely different old project", days_ago=POLICY_MAX_AGE_DAYS + 30
    )
    only_fresh = calculate_aggregate_score(_company([fresh], roce=25.0)).momentum_score
    with_stale = calculate_aggregate_score(
        _company([fresh, stale], roce=25.0)
    ).momentum_score
    assert only_fresh == with_stale


# ---------------------------------------------------------------------------
# risks move the number
# ---------------------------------------------------------------------------


def test_failed_screens_now_cost_points():
    """The BHEL case: flags listed beside a high score that never reduced it."""
    clean = calculate_aggregate_score(_company(roce=25.0))
    flagged = calculate_aggregate_score(
        _company(
            roce=25.0,
            valuation_alerts=[
                "Fails Debt Limit (Debt > Net Assets)",
                "Fails P/E Screen (P/E 58.3 > 15 & Price > Intrinsic)",
            ],
        )
    )
    assert flagged.fundamental_score < clean.fundamental_score
    assert len(flagged.risks) >= 2


def test_promoter_exit_costs_points():
    """ideaForge: promoters cut 3.7% while the headline news was positive."""
    held = calculate_aggregate_score(_company(roce=25.0, promoter_change=0.0))
    exiting = calculate_aggregate_score(_company(roce=25.0, promoter_change=-3.7))
    assert exiting.fundamental_score < held.fundamental_score
    assert any("Promoters cut" in r for r in exiting.risks)


def test_shrinking_revenue_costs_points():
    # Enough populated fields to clear the data-completeness gate.
    base = dict(q_sales=100.0, debt_to_equity=0.4, roce=25.0, sales_trend=[1.0] * 8)
    growing = calculate_aggregate_score(_company(revenue_ttm_growth_pct=27.0, **base))
    shrinking = calculate_aggregate_score(
        _company(revenue_ttm_growth_pct=-12.0, **base)
    )
    assert shrinking.fundamental_score < growing.fundamental_score


def test_growth_reads_the_seasonally_sound_measure():
    """BHEL's sequential figure said -37.5% while it grew 27% year on year."""
    company = _company(
        qoq_sales_growth=-37.47,
        revenue_ttm_growth_pct=27.0,
        q_sales=100.0,
        debt_to_equity=0.4,
        roce=25.0,
        sales_trend=[1.0] * 8,
    )
    score = calculate_aggregate_score(company)
    assert any("TTM" in r for r in score.reasons)
    assert not any("-37" in r for r in score.risks)


def test_a_badly_flagged_company_scores_below_a_clean_one():
    """The whole point: fundamentals must be able to outweigh press coverage."""
    news = [_event(f"Distinct positive headline {i}") for i in range(11)]
    flagged = calculate_aggregate_score(
        _company(
            news,
            debt_to_equity=2.5,
            promoter_change=-3.7,
            revenue_ttm_growth_pct=-10.0,
            valuation_alerts=["Fails Debt Limit", "Fails P/E Screen"],
        )
    )
    clean = calculate_aggregate_score(
        _company(roce=25.0, roe=20.0, debt_to_equity=0.2, revenue_ttm_growth_pct=30.0)
    )
    assert flagged.overall_score < clean.overall_score
    assert flagged.recommendations == ["Avoid / High Risk"]


def test_score_splits_into_fundamental_and_momentum():
    score = calculate_aggregate_score(_company([_event("An order win")], roce=25.0))
    assert score.overall_score == score.fundamental_score + score.momentum_score


def test_no_data_still_returns_a_score():
    score = calculate_aggregate_score(_company())
    assert score.confidence in ("Very Low", "Low")
    assert score.recommendations
