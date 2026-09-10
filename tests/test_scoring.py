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


# ---------------------------------------------------------------------------
# event size and tradeability now move the score
# ---------------------------------------------------------------------------


def test_the_same_order_scores_differently_by_company_size():
    """A Rs 500 crore win is a catalyst for a mid-cap and noise for a giant."""
    headline = _event("Wins order worth Rs 500 crore", event_type="order_win")
    midcap = calculate_aggregate_score(
        _company([headline], sales_trend=[500.0] * 4, roce=25.0)
    )
    megacap = calculate_aggregate_score(
        _company([headline], sales_trend=[62500.0] * 4, roce=25.0)
    )
    assert midcap.momentum_score > megacap.momentum_score


def test_an_unpriced_order_is_not_treated_as_a_small_one():
    """Most headlines omit the value; absence of a number is not evidence."""
    unpriced = calculate_aggregate_score(
        _company(
            [_event("Lands first US purchase order", event_type="order_win")],
            sales_trend=[500.0] * 4,
        )
    )
    tiny = calculate_aggregate_score(
        _company(
            [_event("Wins order worth Rs 1 crore", event_type="order_win")],
            sales_trend=[500.0] * 4,
        )
    )
    assert unpriced.momentum_score > tiny.momentum_score


def test_a_policy_approval_is_not_penalised_for_having_no_rupee_figure():
    approval = calculate_aggregate_score(
        _company(
            [_event("Cabinet approves PLI scheme", event_type="pli")],
            sales_trend=[500.0] * 4,
        )
    )
    assert approval.momentum_score > 1


def test_illiquid_holdings_are_marked_down():
    """A stock that cannot be exited carries a risk no ratio here expressed."""
    tradeable = calculate_aggregate_score(
        _company(roce=25.0, liquidity_band="liquid", advt_cr=250.0)
    )
    trapped = calculate_aggregate_score(
        _company(
            roce=25.0, liquidity_band="illiquid", advt_cr=0.3, days_to_exit_1cr=16.7
        )
    )
    assert trapped.fundamental_score < tradeable.fundamental_score
    assert any("Illiquid" in r for r in trapped.risks)


def test_unmeasured_liquidity_is_not_punished():
    """Silence about an unmeasured stock, not an accusation."""
    unknown = calculate_aggregate_score(_company(roce=25.0))
    measured = calculate_aggregate_score(
        _company(roce=25.0, liquidity_band="adequate", advt_cr=12.0)
    )
    assert unknown.fundamental_score == measured.fundamental_score
    assert not any("Illiquid" in r or "Thin" in r for r in unknown.risks)


# ---------------------------------------------------------------------------
# events have to reach the company they are about
# ---------------------------------------------------------------------------


def test_events_without_a_company_are_dropped_not_filed_under_nothing():
    """The corpus of corporate agreements scored nothing for months.

    The scraper attributed launches and filings to a holding but never
    agreements, so those records carried no company field. builder.py keyed
    every one of them under "" — a key no holding matches — and they sat in
    the payload looking present while contributing zero.
    """
    from dashboard.builder import build_dashboard_views

    data = {
        "corporate_agreements": [
            {"company": "", "title": "Unattributed deal", "date": _TODAY},
            {"company": "Unknown", "title": "Also unattributed", "date": _TODAY},
            {"company": "Test Co", "title": "Real MoU signed", "date": _TODAY},
        ]
    }
    watchlist = {
        "sec": [
            {
                "ticker": "TEST",
                "name": "Test Co",
                "price": "100",
                "screener": {"pe_ratio": 20.0, "roce": 25.0, "q_sales": 100.0},
            }
        ]
    }
    build_dashboard_views(data, watchlist)

    reasons = watchlist["sec"][0]["score"]["reasons"]
    assert any("Real MoU signed" in r for r in reasons)
    assert not any("nattributed" in r for r in reasons)


# --- delivery qualifies the liquidity credit -----------------------------
#
# Turnover counts every share that changed hands; delivery counts the ones
# that settled. Where they disagree, the score was crediting the wrong one.


def test_churn_withdraws_the_liquid_credit_and_states_it_as_a_risk():
    """The case this exists for. WELSPUNLIV traded Rs 1,262 Cr on 14 Aug 2026
    and delivered 8% of it: deep by turnover, almost no real buyers. Before
    this, it earned a green "Liquid" line in the email for exactly that."""
    honest = calculate_aggregate_score(
        _company(roce=25.0, liquidity_band="liquid", advt_cr=1262.0, deliv_pct=68.0)
    )
    churny = calculate_aggregate_score(
        _company(
            roce=25.0,
            liquidity_band="liquid",
            advt_cr=1262.0,
            deliv_pct=8.0,
            turnover_cr_last=1262.0,
            series="EQ",
        )
    )

    assert any("Liquid" in r for r in honest.reasons)
    # The credit is withdrawn, not merely annotated.
    assert not any("Liquid" in r for r in churny.reasons)
    assert any("intraday churn" in r for r in churny.risks)
    assert churny.fundamental_score < honest.fundamental_score


def test_healthy_delivery_is_not_annotated():
    """70% delivery is unremarkable. Saying so on every liquid holding would
    dilute the one case that changes a decision."""
    scored = calculate_aggregate_score(
        _company(
            roce=25.0,
            liquidity_band="liquid",
            advt_cr=250.0,
            deliv_pct=70.0,
            turnover_cr_last=250.0,
            series="EQ",
        )
    )
    assert any("Liquid" in r for r in scored.reasons)
    assert not any("churn" in r for r in scored.risks)


def test_trade_to_trade_delivery_cannot_manufacture_a_signal():
    """Delivery is compulsory in the BE segment, so a low figure there is not
    comparable and a high one is a surveillance rule rather than evidence.
    Neither may move the score."""
    t2t = calculate_aggregate_score(
        _company(
            roce=25.0,
            liquidity_band="liquid",
            advt_cr=250.0,
            deliv_pct=5.0,
            turnover_cr_last=250.0,
            series="BE",
        )
    )
    assert any("Liquid" in r for r in t2t.reasons)
    assert not any("churn" in r for r in t2t.risks)


def test_holdings_without_delivery_data_score_exactly_as_before():
    """The regression guard. Delivery is absent for most of the corpus on any
    given day, and its absence must not change a single score."""
    before = calculate_aggregate_score(
        _company(roce=25.0, liquidity_band="liquid", advt_cr=250.0)
    )
    assert any("Liquid" in r for r in before.reasons)
    assert not any("churn" in r for r in before.risks)


def test_delivery_survives_the_whole_chain_from_csv_to_score():
    """End-to-end over the join that keeps silently breaking here.

    apply_delivery writes into stock["screener"]; dashboard/builder.py then
    rebuilds CompanyFinancials from that dict and scores it. Every hop is a
    place a renamed field vanishes without an error — the failure this repo
    shipped for turnover and again for the 52-week range. Asserting the score
    output is the only version of this test that could catch all of them.
    """
    from models.core import CompanyFinancials
    from providers import nse_delivery

    csv = (
        "SYMBOL,SERIES,TURNOVER_LACS,DELIV_PER,NO_OF_TRADES\n"
        "WELSPUNLIV,EQ,126200,8.00,50000\n"
    )
    watchlist = {
        "textiles": [
            {
                "ticker": "WELSPUNLIV",
                "name": "Welspun Living",
                "screener": {
                    "roce": 25.0,
                    "liquidity_band": "liquid",
                    "advt_cr": 1262.0,
                },
            }
        ]
    }
    assert (
        nse_delivery.apply_delivery(watchlist, nse_delivery.parse_delivery_csv(csv))
        == 1
    )

    stock = watchlist["textiles"][0]
    assert stock["screener"]["delivery_band"] == "churn"

    # The builder's own construction step, verbatim.
    fin = CompanyFinancials(**stock["screener"])
    company = Company(ticker="WELSPUNLIV", name="Welspun Living", price=206.39)
    company.screener = fin
    company.valuation = CompanyValuation()
    company.policy_events = []

    scored = calculate_aggregate_score(company)
    assert any("intraday churn" in r for r in scored.risks), scored.risks
    assert not any("Liquid" in r for r in scored.reasons), scored.reasons
