import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from entities import (  # noqa: E402
    extract_isin,
    build_entity_master,
    find_duplicate_holdings,
    resolve_entity_by_isin,
)


def test_extract_isin_finds_valid_code_in_free_text():
    text = "Some header BSE: 500325 NSE: RELIANCE ISIN: INE002A01018 more text"
    assert extract_isin(text) == "INE002A01018"


def test_extract_isin_returns_none_when_absent():
    assert extract_isin("no identifiers here") is None
    assert extract_isin("") is None
    assert extract_isin(None) is None


def _stock(ticker, name, isin=None):
    sc = {"isin": isin} if isin else {}
    return {"ticker": ticker, "name": name, "screener": sc}


def test_build_entity_master_indexes_by_isin_and_skips_unresolved():
    watchlist = {
        "clean_energy": [
            _stock("TATAPOWER", "Tata Power", "INE245A01021"),
            _stock("SUZLON", "Suzlon Energy"),  # no ISIN yet
        ]
    }
    master = build_entity_master(watchlist)
    assert list(master.keys()) == ["INE245A01021"]
    assert master["INE245A01021"]["ticker"] == "TATAPOWER"
    assert master["INE245A01021"]["sector"] == "clean_energy"


def test_find_duplicate_holdings_detects_same_isin_two_sectors():
    watchlist = {
        "manufacturing_electronics": [
            _stock("DIXON", "Dixon Technologies", "INE935N01012")
        ],
        "surveillance_security": [
            _stock("DIXON", "Dixon Technologies", "INE935N01012")
        ],
    }
    dupes = find_duplicate_holdings(watchlist)
    assert len(dupes) == 1
    assert dupes[0]["isin"] == "INE935N01012"
    sectors = {h["sector"] for h in dupes[0]["holdings"]}
    assert sectors == {"manufacturing_electronics", "surveillance_security"}


def test_find_duplicate_holdings_empty_when_all_unique():
    watchlist = {
        "clean_energy": [
            _stock("TATAPOWER", "Tata Power", "INE245A01021"),
            _stock("SUZLON", "Suzlon Energy", "INE040H01021"),
        ]
    }
    assert find_duplicate_holdings(watchlist) == []


def test_resolve_entity_by_isin():
    master = {"INE245A01021": {"isin": "INE245A01021", "ticker": "TATAPOWER"}}
    assert resolve_entity_by_isin("INE245A01021", master)["ticker"] == "TATAPOWER"
    assert resolve_entity_by_isin("INE000000000", master) is None
    assert resolve_entity_by_isin(None, master) is None
