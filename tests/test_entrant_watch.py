"""Challengers the radar flagged stay watched after their headline ages out:
searched for every run, and compared with their sector's holdings when they
are listed (analysis/entrant_watch.py, providers/screener.py)."""

import asyncio
import json

import providers.screener as screener
from analysis import entrant_watch
from analysis.candidate_screen import screen_sector_candidates

REGISTERED = {
    "AMBER": "Amber Enterprises India Limited",
    "RELIANCE": "Reliance Industries Limited",
    "RPOWER": "Reliance Power Limited",
    "DIXON": "Dixon Technologies (India) Limited",
}
AMBER = {
    "challenger": "Amber",
    "sector": "manufacturing_electronics",
    "headline": "Amber eyes 20% of Oppo India volumes",
}


def test_a_listed_challenger_is_found_by_its_registered_name():
    assert entrant_watch.listed_as("Amber", REGISTERED) == (
        "AMBER",
        "Amber Enterprises India",
    )
    # Several companies begin "Reliance": none is guessed at.
    assert entrant_watch.listed_as("Reliance", REGISTERED) is None
    assert entrant_watch.listed_as("Tata Electronics", REGISTERED) is None


def test_flagged_refreshed_and_dropped_after_the_watch():
    rows = entrant_watch.update_watched([], [AMBER], REGISTERED, today="2026-10-19")
    assert rows == [
        {
            "name": "Amber",
            "sector": "manufacturing_electronics",
            "ticker": "AMBER",
            "registered_name": "Amber Enterprises India",
            "first_seen": "2026-10-19",
            "last_seen": "2026-10-19",
            "headline": "Amber eyes 20% of Oppo India volumes",
        }
    ]
    rows = entrant_watch.update_watched(rows, [AMBER], REGISTERED, today="2026-12-01")
    assert (rows[0]["first_seen"], rows[0]["last_seen"]) == ("2026-10-19", "2026-12-01")
    # Not flagged again: kept for WATCH_DAYS after it last was, then dropped.
    assert entrant_watch.update_watched(rows, [], REGISTERED, today="2027-05-30")
    assert entrant_watch.update_watched(rows, [], REGISTERED, today="2027-06-01") == []


def test_what_is_searched_and_compared():
    rows = entrant_watch.update_watched(
        [],
        [AMBER, {**AMBER, "challenger": "Tata Electronics"}],
        REGISTERED,
        today="2026-10-19",
    )
    # The registered name, without the country headlines drop.
    assert sorted(entrant_watch.search_names(rows)) == [
        "Amber Enterprises",
        "Tata Electronics",
    ]
    # Only a listed company has Screener numbers to compare.
    assert entrant_watch.screener_entrants(rows) == [
        ("AMBER", "Amber Enterprises India", "manufacturing_electronics")
    ]


def test_the_watch_list_round_trips(tmp_path):
    path = tmp_path / "watched.json"
    rows = entrant_watch.update_watched([], [AMBER], REGISTERED, today="2026-10-19")
    assert entrant_watch.save_watched(rows, str(path))
    assert entrant_watch.load_watched(str(path)) == rows
    assert entrant_watch.load_watched(str(tmp_path / "missing.json")) == []
    path.write_text("not json")
    assert entrant_watch.load_watched(str(path)) == []


def test_the_committed_watch_list_is_well_formed():
    with open(entrant_watch.WATCH_PATH, encoding="utf-8") as f:
        rows = json.load(f)
    for row in rows:
        assert row["name"] and row["sector"] and row["last_seen"], row


def test_an_entrants_own_row_joins_the_sector_it_entered(monkeypatch):
    """Amber files under household appliances, so no electronics holding's
    peer table carries it. Its own row is fetched, and only its own."""

    async def fake_page(
        session, ticker, sector, price, fetch=None, slug=None, name=None
    ):
        return ticker, {}, "4321"

    async def fake_peers(session, ticker, warehouse_id):
        assert warehouse_id == "4321"
        return screener.PeerFetch(
            ticker,
            [
                {"ticker": "VOLTAS", "name": "Voltas", "sales_var_pct": 9.0},
                {"ticker": "AMBER", "name": "Amber Enterp.", "sales_var_pct": 41.0},
            ],
            screener.OUTCOME_OK,
            "",
        )

    monkeypatch.setattr(screener, "fetch_screener_async", fake_page)
    monkeypatch.setattr(screener, "fetch_peers_async", fake_peers)

    async def passthrough(coro):
        return await coro

    rows = asyncio.run(
        screener._fetch_entrant_rows(
            [
                ("AMBER", "Amber Enterprises India", "manufacturing_electronics"),
                # Held now: compared as a holding, not as an entrant.
                ("DIXON", "Dixon Technologies", "manufacturing_electronics"),
            ],
            None,
            passthrough,
            None,
            {"DIXON"},
        )
    )
    assert rows == [
        (
            "manufacturing_electronics",
            {
                "ticker": "AMBER",
                "name": "Amber Enterp.",
                "sales_var_pct": 41.0,
                "watched_entrant": True,
            },
        )
    ]


def test_a_watched_entrant_is_compared_not_offered_to_the_watchlist():
    peers = {
        "manufacturing_electronics": [
            {
                "ticker": "AMBER",
                "name": "Amber Enterprises India",
                "sales_var_pct": 41.0,
                "market_cap": 25000,
                "industry_share_pct": 30.0,
                "watched_entrant": True,
            }
        ]
    }
    assert not screen_sector_candidates(peers).get("manufacturing_electronics")


def test_a_country_flagged_under_older_rules_is_dropped_as_the_list_is_read(
    tmp_path,
):
    """Russia was flagged on 21 Oct. The list is searched before the radar
    runs, so it is dropped as it is read, not at the update."""
    path = tmp_path / "watched.json"
    russia = {
        "name": "Russia",
        "sector": "data_center_support",
        "ticker": None,
        "registered_name": None,
        "first_seen": "2026-10-21",
        "last_seen": "2026-10-21",
        "headline": "Ukraine hits Yandex, Russia targets Kyiv servers",
    }
    amber = entrant_watch.update_watched([], [AMBER], REGISTERED, today="2026-10-19")
    path.write_text(json.dumps([russia] + amber))
    assert [r["name"] for r in entrant_watch.load_watched(str(path))] == ["Amber"]
