"""Tests for the symbol→ISIN master (providers/isin_master.py)."""

import asyncio
import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from providers import isin_master as im  # noqa: E402
from providers.isin_master import (  # noqa: E402
    annotate_watchlist_isins,
    load_isin_master,
    merge_new_symbols,
    parse_bse_scrip_rows,
    parse_equity_csv,
    refresh_isin_master_async,
)


@pytest.fixture(autouse=True)
def _no_live_bse():
    """The refresh now merges BSE's scrip master too. Left unstubbed these
    tests reach the real exchange — which took this file from under a second
    to 46s, and in CI would read as flakiness rather than a live request."""
    with patch.object(im, "fetch_scrip_master_sync", return_value=[]):
        yield


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


def test_refresh_adds_new_symbols_and_lets_nse_correct_its_own(tmp_path):
    """This test used to assert that NSE could never overwrite, which was the
    bug rather than the contract.

    The module always intended the NSE mapping to win a disagreement, and got
    there by merging NSE first. That works only while the master is empty —
    true exactly once, because it is committed and reloaded — so from run two
    onwards NSE met entries it could not correct and 140 of its own symbols
    were refused their ISIN daily. NSE now merges with authority.
    """
    path = str(tmp_path / "master.json")
    master = {"TATAPOWER": "INE_LOCAL_TRUTH"}
    session = _FakeSession(response=_FakeResponse(200, _EQUITY_CSV))
    added = asyncio.run(refresh_isin_master_async(session, master, path=path))

    assert added == 1  # RELIANCE is the only genuinely new listing
    assert master["RELIANCE"] == "INE002A01018"
    # TATAPOWER is in NSE's list, so NSE's value is the one that must stand.
    assert master["TATAPOWER"] == "INE245A01021"

    persisted = json.load(open(path))
    assert persisted["RELIANCE"] == "INE002A01018"
    assert persisted["TATAPOWER"] == "INE245A01021"


def test_a_correction_alone_is_still_persisted(tmp_path):
    """Once the master is saturated, "nothing added" is every run. Persisting
    only on `added` would compute the corrected mapping and throw it away
    daily — the fix would look right in the log and never reach disk."""
    path = str(tmp_path / "master.json")
    master = {"TATAPOWER": "INE_WRONG", "RELIANCE": "INE002A01018"}
    session = _FakeSession(response=_FakeResponse(200, _EQUITY_CSV))
    asyncio.run(refresh_isin_master_async(session, master, path=path))
    assert json.load(open(path))["TATAPOWER"] == "INE245A01021"


def test_refresh_blocked_or_broken_never_raises(tmp_path):
    path = str(tmp_path / "master.json")
    master = {"TATAPOWER": "INE245A01021"}
    blocked = _FakeSession(response=_FakeResponse(403))
    assert asyncio.run(refresh_isin_master_async(blocked, master, path=path)) == 0
    exploding = _FakeSession(exc=ConnectionError("boom"))
    assert asyncio.run(refresh_isin_master_async(exploding, master, path=path)) == 0
    assert master == {"TATAPOWER": "INE245A01021"}
    assert not os.path.exists(path)  # nothing learned, nothing written


# --- BSE scrip master merge ----------------------------------------------


_BSE_ROWS = [
    {"SCRIP_CD": "500325", "scrip_id": "RELIANCE", "ISIN_NUMBER": "INE002A01018"},
    {"SCRIP_CD": "500002", "scrip_id": "ABB", "ISIN_NUMBER": "INE117A01022"},
    {"SCRIP_CD": "999999", "scrip_id": "BSEONLY", "ISIN_NUMBER": "INE999Z01011"},
    {"SCRIP_CD": "111111", "scrip_id": "JUNK", "ISIN_NUMBER": "NOT-AN-ISIN"},
    {"SCRIP_CD": "222222", "scrip_id": "", "ISIN_NUMBER": "INE888Z01011"},
    "not a dict",
]


def test_bse_rows_are_keyed_on_scrip_id_not_scrip_code():
    """scrip_id is BSE's ticker. SCRIP_CD is a numeric code the watchlist
    never speaks, so keying on it would produce a master nothing can look
    anything up in."""
    assert parse_bse_scrip_rows(_BSE_ROWS) == {
        "RELIANCE": "INE002A01018",
        "ABB": "INE117A01022",
        "BSEONLY": "INE999Z01011",
    }


def test_bse_rows_survive_junk():
    assert parse_bse_scrip_rows(None) == {}
    assert parse_bse_scrip_rows([]) == {}


def test_merge_adds_only_what_is_missing():
    master = {"RELIANCE": "INE002A01018"}
    added, conflicts, corrected = merge_new_symbols(
        master, {"RELIANCE": "INE002A01018", "BSEONLY": "INE999Z01011"}, "BSE"
    )
    assert (added, conflicts, corrected) == (1, 0, 0)
    assert master["BSEONLY"] == "INE999Z01011"


def test_a_disagreeing_symbol_is_counted_and_never_applied():
    """The cross-namespace risk: NSE's SYMBOL and BSE's scrip_id are different
    namespaces, so the same ticker can mean different companies. BSE has no
    authority here, so the existing mapping must win and the collision must be
    visible."""
    master = {"XYZ": "INE111A01011"}
    added, conflicts, corrected = merge_new_symbols(
        master, {"XYZ": "INE222B01022"}, "BSE"
    )
    assert (added, conflicts, corrected) == (0, 1, 0)
    assert master["XYZ"] == "INE111A01011"


# ---------------------------------------------------------------------------
# Precedence: NSE owns its own namespace
# ---------------------------------------------------------------------------


def test_an_authoritative_source_corrects_what_it_disagrees_with():
    """The 140-a-day bug.

    Merging NSE first was meant to mean the NSE mapping survives. With a
    committed master that is reloaded every run, going first only helps while
    the file is empty — true exactly once. Afterwards NSE met BSE-sourced
    entries it could never overwrite, and 140 NSE symbols were refused their
    own ISIN daily.
    """
    master = {"NEWCO": "INE999Z01099"}  # BSE-sourced on an earlier run
    added, conflicts, corrected = merge_new_symbols(
        master, {"NEWCO": "INE333C01033"}, "NSE", authoritative=True
    )
    assert (added, conflicts, corrected) == (0, 0, 1)
    assert master["NEWCO"] == "INE333C01033"


def test_authority_does_not_extend_to_rewriting_a_whole_feed():
    """An exchange's ISINs do not change wholesale overnight. A fetch wanting
    to rewrite most of what it carries is a corrupt feed, and applying it
    would destroy identity data the snapshot cannot get back."""
    master = {f"S{i}": "INE111A01011" for i in range(200)}
    before = dict(master)
    added, conflicts, corrected = merge_new_symbols(
        master,
        {f"S{i}": "INE222B01022" for i in range(200)},  # 100% disagreement
        "NSE",
        authoritative=True,
    )
    assert corrected == 0
    assert conflicts == 200
    assert master == before, "a corrupt feed must change nothing"


def test_the_corruption_guard_needs_enough_feed_to_judge():
    """One row disagreeing out of one is 100% and says nothing. The guard is
    for a mass rewrite of a full exchange listing, so it does not engage on a
    fetch too small to be one."""
    master = {"NEWCO": "INE999Z01099"}
    _added, _conflicts, corrected = merge_new_symbols(
        master, {"NEWCO": "INE333C01033"}, "NSE", authoritative=True
    )
    assert corrected == 1
    assert master["NEWCO"] == "INE333C01033"


def test_a_realistic_collision_rate_is_under_the_bound():
    """The observed figure is ~7% (140 of ~2,000). The guard must not block
    the very case it was built to let through."""
    master = {f"S{i}": "INE111A01011" for i in range(100)}
    fetched = {f"S{i}": "INE111A01011" for i in range(100)}
    for i in range(7):
        fetched[f"S{i}"] = "INE222B01022"
    _added, conflicts, corrected = merge_new_symbols(
        master, fetched, "NSE", authoritative=True
    )
    assert (conflicts, corrected) == (0, 7)


def test_bse_still_yields_after_nse_has_corrected():
    """The end-to-end precedence. NSE takes the key; BSE's colliding scrip_id
    is declined, which is the correct outcome and keeps the collision visible
    in the count."""
    master = {"XYZ": "INE999Z01099"}
    merge_new_symbols(master, {"XYZ": "INE111A01011"}, "NSE", authoritative=True)
    assert master["XYZ"] == "INE111A01011"
    _added, conflicts, _corrected = merge_new_symbols(
        master, {"XYZ": "INE999Z01099"}, "BSE"
    )
    assert conflicts == 1
    assert master["XYZ"] == "INE111A01011"


def test_bse_merge_never_raises():
    with patch.object(im, "fetch_scrip_master_sync", side_effect=RuntimeError("down")):
        assert asyncio.run(im.refresh_bse_scrips({})) == 0


def test_refresh_merges_nse_first_then_bse(tmp_path):
    """NSE wins a tie because it is the namespace the watchlist speaks."""
    path = str(tmp_path / "master.json")
    master = {}
    session = _FakeSession(response=_FakeResponse(200, _EQUITY_CSV))

    with patch.object(
        im,
        "fetch_scrip_master_sync",
        return_value=[
            {"scrip_id": "RELIANCE", "ISIN_NUMBER": "INE999Z01011"},
            {"scrip_id": "BSEONLY", "ISIN_NUMBER": "INE888Z01011"},
        ],
    ):
        added = asyncio.run(refresh_isin_master_async(session, master, path=path))

    assert added == 3
    # NSE's mapping survived the BSE row that disagreed with it.
    assert master["RELIANCE"] == "INE002A01018"
    assert master["BSEONLY"] == "INE888Z01011"
    with open(path, encoding="utf-8") as f:
        assert json.load(f)["RELIANCE"] == "INE002A01018"


def test_bse_still_merges_when_nse_is_blocked(tmp_path):
    """Either source failing must not stop the other."""
    path = str(tmp_path / "master.json")
    master = {}
    with patch.object(
        im,
        "fetch_scrip_master_sync",
        return_value=[{"scrip_id": "BSEONLY", "ISIN_NUMBER": "INE999Z01011"}],
    ):
        added = asyncio.run(
            refresh_isin_master_async(
                _FakeSession(response=_FakeResponse(403, "")), master, path=path
            )
        )
    assert added == 1
    assert master == {"BSEONLY": "INE999Z01011"}


def test_a_post_corporate_action_isin_is_a_correction_not_a_collision():
    """What the 140 actually were.

    The module assumed an ISIN "never changes for the life of a listing" and
    built never-overwrite on it. It is not true: a split or face-value change
    issues a new ISIN for the same company — the issuer prefix stays, the
    issue-series digits increment, the check digit follows.

    Letting NSE apply its 140 and reading the git diff settled it: in all 140
    the first nine characters were unchanged and the series only ever moved
    up. Not one was a different issuer. ADANIPOWER below is a real one, and it
    is a live holding.
    """
    master = {"ADANIPOWER": "INE814H01011"}  # pre-split, as committed
    _added, conflicts, corrected = merge_new_symbols(
        master, {"ADANIPOWER": "INE814H01029"}, "NSE", authoritative=True
    )
    assert (conflicts, corrected) == (0, 1)
    assert master["ADANIPOWER"] == "INE814H01029"
    # Same issuer, later series — the signature of a corporate action rather
    # than of two different companies sharing a ticker.
    assert "INE814H01011"[:9] == "INE814H01029"[:9]


def test_bse_cannot_undo_a_correction_it_has_no_standing_to_make():
    """BSE cannot arbitrate which value is current, so a stale BSE row must
    not drag a corrected mapping back."""
    master = {"ADANIPOWER": "INE814H01029"}
    _added, conflicts, corrected = merge_new_symbols(
        master, {"ADANIPOWER": "INE814H01011"}, "BSE"
    )
    assert (conflicts, corrected) == (1, 0)
    assert master["ADANIPOWER"] == "INE814H01029"
