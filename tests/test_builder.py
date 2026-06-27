import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dashboard.builder import build_dashboard_views  # noqa: E402
from analysis.valuation import check_hyper_growth_risk  # noqa: E402
from models.core import CompanyFinancials  # noqa: E402


def _make_watchlist(screener):
    return {
        "clean_energy": [
            {
                "ticker": "TEST",
                "name": "Test Corp",
                "price": "100.0",
                "screener": dict(screener),
            }
        ]
    }


def test_build_dashboard_views_enriches_stock_screener_and_score():
    watchlist = _make_watchlist(
        {
            "pe_ratio": 12.0,
            "current_ratio": 2.5,
            "roce": 22.0,
            "roe": 18.0,
            "q_eps": 5.0,
            "q_net_profit": 50.0,
            "qoq_sales_growth": 18.0,
            "dividend_yield": 1.2,
            "debt_trend": [10.0],
            "net_current_assets": 500.0,
            "market_cap": 1000.0,
        }
    )
    data = {}
    build_dashboard_views(data, watchlist)

    sc = watchlist["clean_energy"][0]["screener"]
    # The analytics must be written back onto the stock's screener dict.
    for key in (
        "graham_intrinsic_value",
        "owner_earnings",
        "retained_earnings_ratio",
        "moat_status",
        "is_bargain",
        "valuation_alerts",
        "hyper_growth_warning",
    ):
        assert key in sc, f"missing enriched field: {key}"

    # The aggregate score must be persisted on the stock.
    score = watchlist["clean_energy"][0].get("score")
    assert score is not None
    for key in ("overall_score", "confidence", "reasons", "risks", "recommendations"):
        assert key in score


def test_margin_of_safety_and_buffett_list_keys():
    watchlist = _make_watchlist(
        {
            "pe_ratio": 10.0,
            "current_ratio": 2.5,
            "roce": 25.0,
            "roe": 20.0,
            "q_eps": 8.0,
            "q_net_profit": 80.0,
            "qoq_sales_growth": 20.0,
            "dividend_yield": 2.0,
            "debt_trend": [5.0],
            "net_current_assets": 900.0,
            "market_cap": 1000.0,
        }
    )
    data = {}
    build_dashboard_views(data, watchlist)

    assert data["margin_of_safety"], "expected at least one margin_of_safety entry"
    mos = data["margin_of_safety"][0]
    assert "is_defensive_pass" in mos
    assert "graham_intrinsic_value" in mos

    buf = data["buffett_valuation"][0]
    # Both the legacy 'moat' and the consumer-facing 'moat_status' must be present.
    assert buf.get("moat_status") == buf.get("moat")
    assert "passed_retained_test" in buf


def test_hyper_growth_reality_check():
    # P/E > 30 with decelerating quarterly revenue -> flagged.
    decel = CompanyFinancials(
        pe_ratio=45.0, quarterly_revenue_growth=[100.0, 120.0, 110.0]
    )
    assert check_hyper_growth_risk(decel) is True

    # P/E > 30 but QoQ growth cooled below the high-growth bar -> flagged.
    cooling = CompanyFinancials(pe_ratio=40.0, qoq_sales_growth=8.0)
    assert check_hyper_growth_risk(cooling) is True

    # Cheap stock is never a hyper-growth risk regardless of growth.
    cheap = CompanyFinancials(pe_ratio=12.0, qoq_sales_growth=2.0)
    assert check_hyper_growth_risk(cheap) is False

    # Expensive but still accelerating -> not flagged.
    accelerating = CompanyFinancials(
        pe_ratio=50.0,
        quarterly_revenue_growth=[80.0, 100.0, 130.0],
        qoq_sales_growth=30.0,
    )
    assert check_hyper_growth_risk(accelerating) is False
