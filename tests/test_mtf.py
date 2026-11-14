from providers.mtf import apply_mtf, parse_mtf_payload


def test_parse_mtf_payload_normalizes_stock_book_and_change():
    payload = {
        "meta": {"as_of": "2026-11-13"},
        "stocks": [
            {
                "symbol": "BDL",
                "outstanding_cr": "245.60",
                "change_1m_pct": "18.4",
                "change_1w_pct": "-2.1",
                "rank": 27,
            },
            {"symbol": "UNKNOWN", "outstanding_cr": None},
            {"symbol": "", "outstanding_cr": 10},
        ],
    }
    rows = parse_mtf_payload(payload)
    assert rows["BDL"]["mtf_outstanding_cr"] == 245.6
    assert rows["BDL"]["mtf_change_1m_pct"] == 18.4
    assert rows["BDL"]["mtf_change_1w_pct"] == -2.1
    assert rows["BDL"]["mtf_as_of"] == "2026-11-13"
    assert rows["BDL"]["mtf_status"] == "available"
    assert rows["BDL"]["mtf_source_url"].endswith("/methodology")
    assert "UNKNOWN" not in rows


def test_parse_mtf_payload_does_not_turn_missing_or_negative_book_into_zero():
    assert parse_mtf_payload({"stocks": [{"symbol": "A", "outstanding_cr": None}]}) == {}
    assert parse_mtf_payload({"stocks": [{"symbol": "A", "outstanding_cr": -2}]}) == {}


def test_apply_mtf_only_updates_matched_holdings_and_preserves_unknowns():
    watchlist = {
        "industry": [
            {"ticker": "BDL", "screener": {"pe_ratio": 30}},
            {"ticker": "ABC", "screener": {"pe_ratio": 20}},
        ]
    }
    rows = {
        "BDL": {
            "mtf_outstanding_cr": 245.6,
            "mtf_status": "available",
            "mtf_source": "test",
        }
    }
    assert apply_mtf(watchlist, rows) == 1
    assert watchlist["industry"][0]["screener"]["mtf_outstanding_cr"] == 245.6
    assert watchlist["industry"][1]["screener"] == {"pe_ratio": 20}
