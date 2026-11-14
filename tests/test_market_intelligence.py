from analysis.market_intelligence import build_market_intelligence


def _stock(ticker, fundamental=0, **metrics):
    return {
        "ticker": ticker,
        "name": ticker,
        "screener": metrics,
        "score": {"fundamental_score": fundamental},
    }


def test_market_intelligence_keeps_mtf_unknown_and_exposes_sources():
    result = build_market_intelligence(
        {"industry": [_stock(
            "ABC",
            4,
            promoter_pct=45.0,
            promoter_change=-0.5,
            fii_pct=12.0,
            fii_change=0.8,
            dii_pct=8.0,
            dii_change=0.2,
            pledged_pct=3.0,
            advt_cr=12.0,
            liquidity_band="liquid",
            deliv_pct=57.0,
            delivery_band="delivery-led",
            series="EQ",
            days_to_exit_1cr=0.4,
        )]},
        {"companies": []},
        as_of="2026-11-14",
    )
    snapshot = result["snapshots"][0]
    assert snapshot["ownership"]["fii_change_pp"] == 0.8
    assert snapshot["tradeability"]["delivery_pct"] == 57.0
    assert snapshot["mtf"]["status"] == "unavailable"
    assert snapshot["mtf"]["value"] is None
    assert snapshot["ownership"]["source"] == "Screener shareholding pattern"


def test_priority_order_is_lexicographic_business_impact_first():
    watchlist = {
        "industry": [
            _stock("A", 20, revenue_ttm_growth_pct=10),
            _stock("B", -5, revenue_ttm_growth_pct=10),
        ]
    }
    digest = {
        "companies": [
            {"ticker": "A", "activity": [{"kind": "order", "certainty": "completed"}]},
            {"ticker": "B", "activity": []},
        ]
    }
    result = build_market_intelligence(watchlist, digest, as_of="2026-11-14")
    assert result["opportunity_ranking"][0]["ticker"] == "A"
    assert result["opportunity_ranking"][0]["rank"] == 1
    assert result["priority_order"][0] == "business_impact"


def test_market_reaction_uses_four_week_price_change():
    result = build_market_intelligence(
        {"industry": [_stock("A")]},
        {"companies": [{"ticker": "A", "prices": [
            ["2026-10-10", 100],
            ["2026-10-17", 101],
            ["2026-10-24", 102],
            ["2026-10-31", 103],
            ["2026-11-07", 110],
        ]}]},
        as_of="2026-11-14",
    )
    row = result["opportunity_ranking"][0]
    assert row["market_reaction_4w_pct"] == 10.0
    assert row["dimensions"]["market_reaction"] == 75.0
