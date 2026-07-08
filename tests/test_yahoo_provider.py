"""Tests for the three new opportunistic Yahoo Finance fields: ISIN,
analyst upgrades/downgrades, and institutional holders."""

import datetime
import sys
import os

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from providers.yahoo import (  # noqa: E402
    _fetch_isin,
    _fetch_upgrades_downgrades,
    _fetch_institutional_holders,
    fetch_stock_data,
)


class _FakeTicker:
    ticker = "TEST"

    def __init__(self, isin=None, upgrades_df=None, holders_df=None, raise_on=None):
        self._isin = isin
        self._upgrades_df = upgrades_df
        self._holders_df = holders_df
        self._raise_on = raise_on or set()

    @property
    def isin(self):
        if "isin" in self._raise_on:
            raise ConnectionError("boom")
        return self._isin

    @property
    def upgrades_downgrades(self):
        if "upgrades_downgrades" in self._raise_on:
            raise ConnectionError("boom")
        return self._upgrades_df

    @property
    def institutional_holders(self):
        if "institutional_holders" in self._raise_on:
            raise ConnectionError("boom")
        return self._holders_df

    def history(self, *args, **kwargs):
        return pd.DataFrame()

    @property
    def info(self):
        return {}


# ---------------------------------------------------------------------------
# ISIN
# ---------------------------------------------------------------------------


def test_fetch_isin_accepts_valid_code():
    assert _fetch_isin(_FakeTicker(isin="INE002A01018")) == "INE002A01018"


def test_fetch_isin_rejects_not_found_marker():
    assert _fetch_isin(_FakeTicker(isin="-")) is None


def test_fetch_isin_rejects_wrong_length():
    assert _fetch_isin(_FakeTicker(isin="TOOSHORT")) is None


def test_fetch_isin_handles_none():
    assert _fetch_isin(_FakeTicker(isin=None)) is None


def test_fetch_isin_never_raises():
    assert _fetch_isin(_FakeTicker(raise_on={"isin"})) is None


# ---------------------------------------------------------------------------
# Upgrades / downgrades
# ---------------------------------------------------------------------------


def _upgrades_df(rows):
    """rows: list of (days_ago, firm, action, from_grade, to_grade)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    index = [now - datetime.timedelta(days=d) for d, *_ in rows]
    df = pd.DataFrame(
        {
            "Firm": [r[1] for r in rows],
            "Action": [r[2] for r in rows],
            "FromGrade": [r[3] for r in rows],
            "ToGrade": [r[4] for r in rows],
        },
        index=pd.DatetimeIndex(index),
    )
    return df


def test_upgrades_downgrades_keeps_recent_drops_old():
    df = _upgrades_df(
        [
            (5, "Motilal Oswal", "up", "Hold", "Buy"),
            (400, "ICICI Securities", "down", "Buy", "Hold"),
        ]
    )
    actions = _fetch_upgrades_downgrades(_FakeTicker(upgrades_df=df), lookback_days=30)
    assert len(actions) == 1
    assert actions[0]["firm"] == "Motilal Oswal"
    assert actions[0]["to_grade"] == "Buy"


def test_upgrades_downgrades_sorted_newest_first_and_capped():
    rows = [(d, f"Firm{d}", "up", "Hold", "Buy") for d in [1, 2, 3, 4, 5, 6, 7]]
    df = _upgrades_df(rows)
    actions = _fetch_upgrades_downgrades(_FakeTicker(upgrades_df=df), lookback_days=30)
    assert len(actions) == 5  # capped
    dates = [a["date"] for a in actions]
    assert dates == sorted(dates, reverse=True)


def test_upgrades_downgrades_empty_dataframe():
    assert _fetch_upgrades_downgrades(_FakeTicker(upgrades_df=pd.DataFrame())) == []


def test_upgrades_downgrades_none():
    assert _fetch_upgrades_downgrades(_FakeTicker(upgrades_df=None)) == []


def test_upgrades_downgrades_never_raises():
    assert (
        _fetch_upgrades_downgrades(_FakeTicker(raise_on={"upgrades_downgrades"})) == []
    )


def test_upgrades_downgrades_skips_rows_missing_firm_or_action():
    now = datetime.datetime.now(datetime.timezone.utc)
    df = pd.DataFrame(
        {
            "Firm": [None],
            "Action": ["up"],
            "FromGrade": ["Hold"],
            "ToGrade": ["Buy"],
        },
        index=pd.DatetimeIndex([now]),
    )
    assert _fetch_upgrades_downgrades(_FakeTicker(upgrades_df=df)) == []


# ---------------------------------------------------------------------------
# Institutional holders
# ---------------------------------------------------------------------------


def test_institutional_holders_extracts_fields():
    df = pd.DataFrame(
        {
            "Holder": ["LIC", "HDFC MF"],
            "Shares": [1000000, 500000],
            "Value": [50000000, 25000000],
            "pctHeld": [0.05, 0.025],
            "Date Reported": [
                pd.Timestamp("2026-06-30"),
                pd.Timestamp("2026-06-30"),
            ],
        }
    )
    holders = _fetch_institutional_holders(_FakeTicker(holders_df=df))
    assert len(holders) == 2
    assert holders[0]["holder"] == "LIC"
    assert holders[0]["pct_held"] == 0.05
    assert holders[0]["date_reported"] == "2026-06-30"


def test_institutional_holders_capped_at_top_n():
    df = pd.DataFrame({"Holder": [f"Fund{i}" for i in range(10)]})
    holders = _fetch_institutional_holders(_FakeTicker(holders_df=df), top_n=5)
    assert len(holders) == 5


def test_institutional_holders_empty_or_none():
    assert _fetch_institutional_holders(_FakeTicker(holders_df=None)) == []
    assert _fetch_institutional_holders(_FakeTicker(holders_df=pd.DataFrame())) == []


def test_institutional_holders_never_raises():
    assert (
        _fetch_institutional_holders(_FakeTicker(raise_on={"institutional_holders"}))
        == []
    )


# ---------------------------------------------------------------------------
# fetch_stock_data integration
# ---------------------------------------------------------------------------


def test_fetch_stock_data_includes_new_fields(monkeypatch):
    import providers.yahoo as yahoo_mod

    df = _upgrades_df([(1, "Motilal Oswal", "up", "Hold", "Buy")])
    holders_df = pd.DataFrame({"Holder": ["LIC"], "pctHeld": [0.05]})
    fake = _FakeTicker(isin="INE002A01018", upgrades_df=df, holders_df=holders_df)
    monkeypatch.setattr(yahoo_mod, "get_cached_ticker", lambda *a, **k: fake)

    data = fetch_stock_data("RELIANCE.NS")
    assert data["isin"] == "INE002A01018"
    assert len(data["analyst_actions"]) == 1
    assert data["institutional_holders"][0]["holder"] == "LIC"
