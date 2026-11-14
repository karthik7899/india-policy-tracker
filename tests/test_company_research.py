import json

from analysis.company_research import (
    _clean,
    _company_input,
    _four_week_return,
    build_company_research,
)


def _fixture():
    watchlist = {
        "industrial": [
            {
                "ticker": "ABC",
                "name": "ABC Ltd",
                "price": 100,
                "screener": {"roce": 18, "revenue_growth": 12},
            }
        ]
    }
    digest = {
        "companies": [
            {
                "ticker": "ABC",
                "name": "ABC Ltd",
                "sector": "industrial",
                "thesis": "Expanding domestic manufacturing",
                "thesis_status": "Intact",
                "activity_count": 1,
                "activity": [
                    {
                        "date": "2026-11-13",
                        "text": "ABC wins a ₹100 crore order",
                        "link": "https://example.com/order",
                        "source": "Example",
                    }
                ],
                "policies": [],
                "calls": [],
                "challenges": [],
            }
        ]
    }
    return watchlist, digest


def test_research_input_uses_only_supplied_metrics_and_evidence():
    watchlist, digest = _fixture()
    company = digest["companies"][0]
    payload = _company_input(company, watchlist["industrial"][0])
    assert payload["metrics"]["roce"] == 18
    assert payload["activity"][0]["link"] == "https://example.com/order"
    assert "portfolio" not in payload


def test_four_week_market_reaction_is_computed_from_weekly_closes():
    company = {
        "prices": [
            ["2026-10-17", 90],
            ["2026-10-24", 94],
            ["2026-10-31", 96],
            ["2026-11-07", 98],
            ["2026-11-14", 100],
        ]
    }
    assert _four_week_return(company) == 11.11
    assert _four_week_return({"prices": []}) is None


def test_evidence_refs_are_bounded_and_grounded():
    inputs = {
        "ABC": {
            "name": "ABC Ltd",
            "activity": [
                {
                    "text": "ABC wins an order",
                    "link": "https://example.com",
                }
            ],
        }
    }
    cleaned = _clean(
        [
            {
                "ticker": "ABC",
                "business_impact": "Order win",
                "market_readthrough": "Insufficient price evidence",
                "opportunity": "Potential order conversion",
                "risks": "Execution risk",
                "thesis_view": "Supports the thesis",
                "evidence_refs": [0, 9, -1, "0", 0],
            }
        ],
        inputs,
    )
    assert cleaned["ABC"]["evidence_count"] == 1
    assert cleaned["ABC"]["evidence"][0]["link"] == "https://example.com"


def test_cache_reuses_identical_company_evidence(tmp_path):
    watchlist, digest = _fixture()
    cache = tmp_path / "research_cache.json"
    calls = []

    def transport(prompt):
        calls.append(prompt)
        return json.dumps(
            [
                {
                    "ticker": "ABC",
                    "business_impact": "Order win",
                    "market_readthrough": "No price reaction supplied",
                    "opportunity": "Potential order execution",
                    "risks": "Execution risk",
                    "thesis_view": "Supports expansion thesis",
                    "evidence_refs": [0],
                }
            ]
        )

    first = build_company_research(
        watchlist,
        digest,
        today="2026-11-14",
        cache_path=str(cache),
        transport=transport,
    )
    second = build_company_research(
        watchlist,
        digest,
        today="2026-11-15",
        cache_path=str(cache),
        transport=transport,
    )
    assert first["status"]["read"] == 1
    assert second["status"]["cached"] == 1
    assert len(calls) == 1


def test_no_key_skips_without_breaking_pipeline(tmp_path, monkeypatch):
    watchlist, digest = _fixture()
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    result = build_company_research(
        watchlist,
        digest,
        cache_path=str(tmp_path / "x.json"),
    )
    assert result["companies"] == {}
    assert "GEMINI_API_KEY" in result["status"]["skipped"]
