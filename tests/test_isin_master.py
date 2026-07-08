"""Tests for the symbol→ISIN master (providers/isin_master.py)."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from providers.isin_master import (  # noqa: E402
    annotate_watchlist_isins,
    load_isin_master,
    parse_equity_csv,
    refresh_isin_master_async,
)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

_EQUITY_CSV = """\
SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE
RELIANCE,Reliance Industries Limited,EQ,29-NOV-1995,10,1,INE002A01018,10
TATAPOWER,Tata Power Company Limited,EQ,01-JAN-1996,1,1,INE245A01021,1
BADROW,Broken Company,,,,,NOT-AN-ISIN,
"""


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------


def test_parse_equity_csv_extracts_valid_rows_only():
    mapping = parse_equity_csv(_EQUITY_CSV)
    assert mapping == {
        "RELIANCE": "INE002A01018",
        "TATAPOWER": "INE245A01021",
    }


def test_parse_equity_csv_handles_garbage():
    assert parse_equity_csv("") == {}
    assert parse_equity_csv(None) == {}
    assert parse_equity_csv("<html>blocked</html>") == {}


# ---------------------------------------------------------------------------
# committed master integrity — the load-bearing checks
# ---------------------------------------------------------------------------


def test_committed_master_loads_and_is_well_formed():
    master = load_isin_master()
    assert len(master) > 1500
    for symbol, isin in master.items():
        assert symbol == symbol.upper()
        assert len(isin) == 12 and isin.startswith("IN"), (symbol, isin)


def test_committed_master_covers_every_watchlist_ticker():
    """New holdings must be added to the master (or resolvable by the live
    refresh) — a gap here means the entity master silently loses coverage."""
    master = load_isin_master()
    with open(os.path.join(_REPO_ROOT, "watchlist.json"), encoding="utf-8") as f:
        watchlist = json.load(f)
    tickers = {s["ticker"] for stocks in watchlist.values() for s in stocks}
    missing = sorted(t for t in tickers if t not in master)
    assert missing == [], f"watchlist tickers missing from isin_master.json: {missing}"


def test_load_missing_file_returns_empty(tmp_path):
    assert load_isin_master(str(tmp_path / "nope.json")) == {}


# ---------------------------------------------------------------------------
# annotation
# ---------------------------------------------------------------------------


def test_annotate_stamps_known_and_skips_unknown():
    watchlist = {
        "sec": [
            {"ticker": "RELIANCE", "name": "Reliance"},
            {"ticker": "UNKNOWNCO", "name": "Unknown", "screener": {}},
        ]
    }
    master = {"RELIANCE": "INE002A01018"}
    covered = annotate_watchlist_isins(watchlist, master)
    assert covered == 1
    assert watchlist["sec"][0]["screener"]["isin"] == "INE002A01018"
    assert "isin" not in watchlist["sec"][1]["screener"]


def test_annotate_never_overwrites_existing_isin():
    watchlist = {
        "sec": [{"ticker": "RELIANCE", "screener": {"isin": "INE_ALREADY_SET"}}]
    }
    annotate_watchlist_isins(watchlist, {"RELIANCE": "INE002A01018"})
    assert watchlist["sec"][0]["screener"]["isin"] == "INE_ALREADY_SET"


def test_annotate_is_idempotent_and_tolerant():
    watchlist = {"sec": [{"ticker": "X"}, "not-a-dict"]}
    assert annotate_watchlist_isins(watchlist, {}) == 0
    assert annotate_watchlist_isins(None, {}) == 0


# ---------------------------------------------------------------------------
# live refresh (fail-safe merge)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, status, text=""):
        self.status = status
        self._text = text

    async def text(self):
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class _FakeSession:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    def get(self, *args, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


def test_refresh_merges_new_symbols_never_overwrites(tmp_path):
    path = str(tmp_path / "master.json")
    master = {"TATAPOWER": "INE_LOCAL_TRUTH"}
    session = _FakeSession(response=_FakeResponse(200, _EQUITY_CSV))
    added = asyncio.run(refresh_isin_master_async(session, master, path=path))
    assert added == 1  # RELIANCE added; TATAPOWER untouched
    assert master["TATAPOWER"] == "INE_LOCAL_TRUTH"
    assert master["RELIANCE"] == "INE002A01018"
    persisted = json.load(open(path))
    assert persisted["RELIANCE"] == "INE002A01018"


def test_refresh_blocked_or_broken_never_raises(tmp_path):
    path = str(tmp_path / "master.json")
    master = {"TATAPOWER": "INE245A01021"}
    blocked = _FakeSession(response=_FakeResponse(403))
    assert asyncio.run(refresh_isin_master_async(blocked, master, path=path)) == 0
    exploding = _FakeSession(exc=ConnectionError("boom"))
    assert asyncio.run(refresh_isin_master_async(exploding, master, path=path)) == 0
    assert master == {"TATAPOWER": "INE245A01021"}
    assert not os.path.exists(path)  # nothing learned, nothing written
