"""Tests for exchange-disclosed events (fundraising + bulk/block deals)
and the industry-wide market-share computation."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from providers.exchange_events import (  # noqa: E402
    classify_fundraising,
    match_watchlist_company,
    parse_announcements,
    parse_deals,
)
from analysis.market_share import (  # noqa: E402
    compute_industry_share,
    snapshot_prior_industry_shares,
)
from analysis.early_warning import generate_early_warnings  # noqa: E402

_WATCHLIST = {
    "clean_energy": [
        {"ticker": "TATAPOWER", "name": "Tata Power"},
        {"ticker": "SUZLON", "name": "Suzlon Energy"},
    ]
}


# ---------------------------------------------------------------------------
# classification and matching
# ---------------------------------------------------------------------------


def test_classify_fundraising_hits_and_misses():
    assert classify_fundraising("Board approves Rights Issue of equity shares")
    assert classify_fundraising("Outcome: Qualified Institutions Placement opens")
    assert classify_fundraising("Allotment of Convertible Warrants to promoters")
    assert classify_fundraising("Intimation regarding Buyback of shares")
    assert classify_fundraising("Raising of funds via NCDs") == "raising of funds"
    assert classify_fundraising("Investor presentation Q1 FY27") is None
    assert classify_fundraising("") is None
    assert classify_fundraising(None) is None


def test_match_watchlist_company_containment():
    assert match_watchlist_company("Tata Power Company Ltd", _WATCHLIST) == "TATAPOWER"
    assert match_watchlist_company("SUZLON ENERGY LTD.", _WATCHLIST) == "SUZLON"
    # Same-group but different company must NOT match.
    assert match_watchlist_company("Tata Motors Ltd", _WATCHLIST) is None
    assert match_watchlist_company("", _WATCHLIST) is None


# ---------------------------------------------------------------------------
# announcement parsing
# ---------------------------------------------------------------------------

_ANNOUNCEMENTS_PAYLOAD = {
    "Table": [
        {
            "SLONGNAME": "Tata Power Company Ltd",
            "NEWSSUB": "Board approves raising of funds by way of QIP",
            "CATEGORYNAME": "Board Meeting",
            "NEWS_DT": "2026-07-03T09:00:00",
        },
        {
            "SLONGNAME": "Unrelated Industries Ltd",
            "NEWSSUB": "Rights Issue record date fixed",
            "CATEGORYNAME": "Corp. Action",
            "NEWS_DT": "2026-07-02T15:00:00",
        },
        {
            "SLONGNAME": "Quiet Corp Ltd",
            "NEWSSUB": "Investor meet intimation",
            "CATEGORYNAME": "Company Update",
            "NEWS_DT": "2026-07-02T10:00:00",
        },
    ]
}


def test_parse_announcements_extracts_fundraising_only():
    events = parse_announcements(_ANNOUNCEMENTS_PAYLOAD, _WATCHLIST)
    assert len(events) == 2  # investor meet excluded
    tata = events[0]
    assert tata["ticker"] == "TATAPOWER"
    assert tata["keyword"] == "qip"
    assert tata["date"] == "2026-07-03"
    # Non-watchlist companies are kept (rival capital raises are intel)
    assert events[1]["ticker"] is None


def test_parse_announcements_handles_garbage():
    assert parse_announcements(None, _WATCHLIST) == []
    assert parse_announcements({}, _WATCHLIST) == []
    assert parse_announcements({"Table": "not-a-list"}, _WATCHLIST) == []
    assert parse_announcements({"Table": [None, 42]}, _WATCHLIST) == []


# ---------------------------------------------------------------------------
# deals parsing
# ---------------------------------------------------------------------------

_DEALS_PAYLOAD = {
    "Table": [
        {
            "SNAME": "Suzlon Energy Ltd",
            "CLIENTNAME": "BIG ALPHA FUND",
            "BUYSELL": "B",
            "QTY": 1000000,
            "RATE": 57.2,
            "DT": "2026-07-02",
        },
        {
            "SNAME": "Somebody Else Ltd",
            "CLIENTNAME": "OTHER FUND",
            "BUYSELL": "S",
            "QTY": 5000,
            "RATE": 100.0,
            "DT": "2026-07-02",
        },
    ]
}


def test_parse_deals_keeps_only_watchlist_and_maps_side():
    deals = parse_deals(_DEALS_PAYLOAD, _WATCHLIST, "bulk")
    assert len(deals) == 1
    d = deals[0]
    assert d["ticker"] == "SUZLON"
    assert d["side"] == "buy"
    assert d["client"] == "BIG ALPHA FUND"
    assert d["deal_type"] == "bulk"


def test_parse_deals_handles_garbage():
    assert parse_deals(None, _WATCHLIST, "bulk") == []
    assert parse_deals({"Table": [None]}, _WATCHLIST, "block") == []


# ---------------------------------------------------------------------------
# exchange-event early-warning signals
# ---------------------------------------------------------------------------


def test_deal_buy_and_sell_signals():
    data = {
        "institutional_deals": [
            {
                "ticker": "SUZLON",
                "side": "buy",
                "client": "BIG ALPHA FUND",
                "quantity": 1000000,
                "deal_type": "bulk",
            },
            {
                "ticker": "TATAPOWER",
                "side": "sell",
                "client": "EXITING FUND",
                "quantity": 200000,
                "deal_type": "block",
            },
        ]
    }
    warnings = generate_early_warnings(data, _WATCHLIST)
    buys = [w for w in warnings if w["category"] == "Institutional Buy (Deal)"]
    sells = [w for w in warnings if w["category"] == "Institutional Sell (Deal)"]
    assert len(buys) == 1 and buys[0]["ticker"] == "SUZLON"
    assert buys[0]["direction"] == "opportunity"
    assert len(sells) == 1 and sells[0]["direction"] == "risk"


def test_fundraising_signal_for_watchlist_company_only():
    data = {
        "fundraising_events": [
            {"ticker": "TATAPOWER", "keyword": "qip", "subject": "QIP approved"},
            {"ticker": None, "keyword": "rights issue", "subject": "Rival raise"},
        ]
    }
    warnings = generate_early_warnings(data, _WATCHLIST)
    raises = [w for w in warnings if w["category"] == "Capital Raise"]
    assert len(raises) == 1
    assert raises[0]["ticker"] == "TATAPOWER"


# ---------------------------------------------------------------------------
# industry market share
# ---------------------------------------------------------------------------

_INDUSTRY_PEERS = {
    "clean_energy": [
        {"ticker": "TATAPOWER", "name": "Tata Power", "sales_qtr": 600.0},
        {"ticker": "SUZLON", "name": "Suzlon Energy", "sales_qtr": 200.0},
        {"ticker": "RIVAL1", "name": "Rival One", "sales_qtr": 800.0},
        {"ticker": "RIVAL2", "name": "Rival Two", "sales_qtr": 400.0},
    ]
}


def test_industry_share_uses_full_peer_denominator():
    import copy

    wl = copy.deepcopy(_WATCHLIST)
    rollup = compute_industry_share(wl, _INDUSTRY_PEERS)
    rows = {r["ticker"]: r for r in rollup["clean_energy"]}
    # denominator = 2000 across 4 companies, not just the 2 watchlist stocks
    assert rows["TATAPOWER"]["share_pct"] == 30.0
    assert rows["SUZLON"]["share_pct"] == 10.0
    assert rows["TATAPOWER"]["peer_count"] == 4
    sc = wl["clean_energy"][0]["screener"]
    assert sc["industry_share_pct"] == 30.0
    assert "industry_share_change_pp" not in sc  # no prior yet


def test_industry_share_change_vs_prior_run():
    import copy

    wl = copy.deepcopy(_WATCHLIST)
    rollup = compute_industry_share(wl, _INDUSTRY_PEERS, {"TATAPOWER": 32.5})
    rows = {r["ticker"]: r for r in rollup["clean_energy"]}
    assert rows["TATAPOWER"]["change_pp"] == -2.5
    assert wl["clean_energy"][0]["screener"]["industry_share_change_pp"] == -2.5


def test_industry_share_skips_bad_data():
    wl = {"sec": [{"ticker": "AAA", "name": "AAA"}]}
    peers = {
        "sec": [{"ticker": "AAA", "sales_qtr": 0}, {"ticker": "B", "sales_qtr": -5}]
    }
    assert compute_industry_share(wl, peers) == {}
    assert compute_industry_share(wl, {}) == {}
    assert compute_industry_share(wl, None) == {}


def test_snapshot_prior_industry_shares():
    wl = {
        "sec": [
            {"ticker": "AAA", "screener": {"industry_share_pct": 12.5}},
            {"ticker": "BBB", "screener": {}},
        ]
    }
    assert snapshot_prior_industry_shares(wl) == {"AAA": 12.5}


def test_industry_share_drives_market_share_signal():
    wl = {
        "sec": [
            {
                "ticker": "AAA",
                "name": "AAA Ltd",
                "screener": {
                    "industry_share_pct": 28.0,
                    "industry_share_change_pp": -1.5,
                    "industry_peer_count": 12,
                },
            }
        ]
    }
    warnings = [
        w for w in generate_early_warnings({}, wl) if w["category"] == "Market Share"
    ]
    assert len(warnings) == 1
    assert warnings[0]["direction"] == "risk"
    assert "12-company industry group" in warnings[0]["signal"]
    assert "29.5% → 28.0%" in warnings[0]["signal"]


def test_parse_functions_tolerate_string_payload():
    """Regression for run #65: BSE returned HTTP 200 whose body json-parses
    to a *string*, which crashed the whole pipeline via asyncio.gather."""
    assert parse_announcements("No data found", _WATCHLIST) == []
    assert parse_announcements(["a", "list"], _WATCHLIST) == []
    assert parse_announcements(42, _WATCHLIST) == []
    assert parse_deals("blocked", _WATCHLIST, "bulk") == []
    assert parse_deals(3.14, _WATCHLIST, "block") == []


def test_fetch_wrappers_never_raise(monkeypatch):
    """Even if a parser somehow raises, the fetch coroutines must swallow it."""
    import asyncio
    import providers.exchange_events as ee

    async def bad_fetch(session, url):
        return {"Table": []}

    def exploding_parser(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ee, "_fetch_json", bad_fetch)
    monkeypatch.setattr(ee, "parse_announcements", exploding_parser)
    monkeypatch.setattr(ee, "parse_deals", exploding_parser)

    events = asyncio.run(ee.fetch_fundraising_events_async(None, _WATCHLIST))
    deals = asyncio.run(ee.fetch_institutional_deals_async(None, _WATCHLIST))
    assert events == []
    assert deals == []
