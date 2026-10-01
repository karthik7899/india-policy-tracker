"""Rotation picks against the Nifty 50, from the day each was made."""

import datetime

from analysis import track_record
from analysis.track_record import build_track_record, summarise, unique_decisions

TODAY = datetime.date(2026, 9, 27)


def _series(start_value, end_value, dates=("2026-07-09", "2026-08-01", "2026-09-26")):
    """Closes on the given dates, linear from start to end."""
    step = (end_value - start_value) / (len(dates) - 1)
    return [(d, start_value + i * step) for i, d in enumerate(dates)]


CLOSES = {
    "WIN.NS": _series(100, 130),  # +30%
    "LOSE.NS": _series(100, 90),  # -10%, and exited
    "BANKY.NS": _series(200, 220),  # +10%
    "BSEONLY.BO": _series(50, 60),  # +20%, BSE listing only
    "^NSEI": _series(1000, 1100),  # +10%
    "^NSEBANK": _series(500, 575),  # +15%
}


def fake_fetch(calls=None):
    def fetch(symbols, start):
        if calls is not None:
            calls.append((tuple(symbols), start))
        return {s: CLOSES[s] for s in symbols if s in CLOSES}

    return fetch


LEDGER = [
    {
        "date": "2026-07-10",
        "action": "added",
        "sector": "fmcg",
        "ticker": "WIN",
        "price_at_decision": 100,
    },
    {
        "date": "2026-07-10",
        "action": "added",
        "sector": "fmcg",
        "ticker": "LOSE",
        "price_at_decision": 100,
    },
    {
        "date": "2026-07-10",
        "action": "rotated_in",
        "sector": "banking_financials",
        "ticker": "BANKY",
        "price_at_decision": 200,
    },
    {
        "date": "2026-07-10",
        "action": "added",
        "sector": "fmcg",
        "ticker": "BSEONLY",
        "price_at_decision": 50,
    },
    # Re-logged two days later: the same pick, not a second one.
    {
        "date": "2026-07-12",
        "action": "rotated_in",
        "sector": "fmcg",
        "ticker": "WIN",
        "price_at_decision": 101,
    },
    # Too young to judge.
    {
        "date": "2026-09-20",
        "action": "rotated_in",
        "sector": "fmcg",
        "ticker": "NEW",
        "price_at_decision": 10,
    },
]
WATCHLIST = {
    "fmcg": [{"ticker": "WIN"}, {"ticker": "BSEONLY"}],
    "banking_financials": [{"ticker": "BANKY"}],
}


def _record(**kw):
    return build_track_record(LEDGER, WATCHLIST, fetch=fake_fetch(), today=TODAY, **kw)


def _row(record, ticker):
    return next(r for r in record["decisions"] if r["ticker"] == ticker)


def test_a_relogged_pick_counts_once():
    kept = unique_decisions(LEDGER)
    assert [e["ticker"] for e in kept].count("WIN") == 1
    assert next(e for e in kept if e["ticker"] == "WIN")["date"] == "2026-07-10"


def test_each_pick_is_measured_against_the_nifty_over_its_own_days():
    r = _row(_record(), "WIN")
    assert r["return_pct"] == 30.0
    assert r["nifty_pct"] == 10.0
    assert r["vs_nifty_pct"] == 20.0
    assert r["days"] == 79 and r["still_held"]


def test_an_exited_pick_is_still_scored():
    # The old post-mortem recorded these as "Left Watchlist (unscored)".
    r = _row(_record(), "LOSE")
    assert r["still_held"] is False
    assert r["vs_nifty_pct"] == -20.0


def test_a_sector_index_is_used_where_one_matches():
    r = _row(_record(), "BANKY")
    assert r["index"] == "Nifty Bank"
    assert r["vs_index_pct"] == -5.0  # +10% against Nifty Bank's +15%
    assert "index" not in _row(_record(), "WIN")  # no FMCG series in the fake


def test_a_bse_only_listing_is_found():
    assert _row(_record(), "BSEONLY")["return_pct"] == 20.0


def test_what_cannot_be_priced_says_so():
    r = _row(_record(), "NEW")
    assert r["unmeasured"] == "no price history for the pick"


def test_the_summary_judges_only_old_enough_picks_and_counts_exits():
    s = _record()["summary"]
    assert s["n"] == 4
    assert s["beat_nifty"] == 2  # WIN +20, BSEONLY +10; BANKY level, LOSE -20
    assert s["median_vs_nifty_pct"] == 5.0
    assert s["exited"] == 1 and s["exited_mean_vs_nifty_pct"] == -20.0
    assert s["with_index"] == 1 and s["beat_index"] == 0


def test_young_picks_are_listed_but_not_summarised():
    rows = [
        {
            "vs_nifty_pct": 5.0,
            "return_pct": 6.0,
            "nifty_pct": 1.0,
            "days": 3,
            "still_held": True,
            "date": "2026-09-24",
        }
    ]
    assert summarise(rows) == {"n": 0, "too_recent": 1}


def test_a_split_between_ledger_and_history_is_flagged():
    ledger = [
        {
            "date": "2026-07-10",
            "sector": "fmcg",
            "ticker": "WIN",
            "price_at_decision": 500,
        }
    ]
    r = build_track_record(ledger, WATCHLIST, fetch=fake_fetch(), today=TODAY)[
        "decisions"
    ][0]
    assert "split or bonus" in r["price_check"]


def test_one_download_for_everything_nse_serves(monkeypatch):
    calls = []
    build_track_record(LEDGER, WATCHLIST, fetch=fake_fetch(calls), today=TODAY)
    first, start = calls[0]
    assert "^NSEI" in first and "^NSEBANK" in first and "WIN.NS" in first
    assert start == "2026-06-30"  # earliest decision minus the staleness margin
    # The second call asks BSE only for what NSE did not serve.
    assert set(calls[1][0]) == {"BSEONLY.BO", "NEW.BO"}


def test_a_stale_bar_is_not_the_decision_price(monkeypatch):
    monkeypatch.setattr(track_record, "MAX_STALENESS_DAYS", 7)
    ledger = [{"date": "2026-07-25", "sector": "fmcg", "ticker": "WIN"}]
    r = build_track_record(ledger, WATCHLIST, fetch=fake_fetch(), today=TODAY)[
        "decisions"
    ][0]
    # The last close before 25 July is 9 July — too old to stand for it.
    assert r["unmeasured"]


def test_a_failed_download_never_breaks_the_run():
    def boom(symbols, start):
        raise RuntimeError("yahoo down")

    record = build_track_record(LEDGER, WATCHLIST, fetch=boom, today=TODAY)
    assert record["decisions"] == [] and "yahoo down" in record["error"]


def test_the_email_block_states_the_count_and_includes_exits():
    from emails.mailer import _build_track_record_html

    html = _build_track_record_html(_record(), {"lists": 5})
    assert "2 of 4 picks at least 30 days old beat the Nifty 50" in html
    assert "1 have since left the watchlist and are still counted" in html
    assert "(exited)" in html
    assert "no Sharpe ratio" in html
    assert _build_track_record_html({"decisions": []}) == ""


def test_yahoo_frames_are_read_for_one_symbol_and_for_many(monkeypatch):
    import pandas as pd
    import yfinance as yf

    idx = pd.to_datetime(["2026-07-09", "2026-07-10"])
    many = pd.concat(
        {
            "WIN.NS": pd.DataFrame({"Close": [100.0, 101.0]}, index=idx),
            "^NSEI": pd.DataFrame({"Close": [1000.0, float("nan")]}, index=idx),
            "GONE.NS": pd.DataFrame({"Close": [float("nan")] * 2}, index=idx),
        },
        axis=1,
    )
    monkeypatch.setattr(yf, "download", lambda *a, **k: many)
    out = track_record.yahoo_closes(
        ["WIN.NS", "^NSEI", "GONE.NS", "ABSENT.NS"], "2026-07-01"
    )
    assert out["WIN.NS"] == [("2026-07-09", 100.0), ("2026-07-10", 101.0)]
    assert out["^NSEI"] == [("2026-07-09", 1000.0)]
    assert "GONE.NS" not in out and "ABSENT.NS" not in out

    one = pd.DataFrame({"Close": [50.0, 51.0]}, index=idx)
    monkeypatch.setattr(yf, "download", lambda *a, **k: one)
    assert track_record.yahoo_closes(["X.BO"], "2026-07-01") == {
        "X.BO": [("2026-07-09", 50.0), ("2026-07-10", 51.0)]
    }


def test_an_etf_stands_in_when_the_index_symbol_is_empty(monkeypatch):
    closes = dict(CLOSES)
    closes.pop("^NSEBANK")
    closes["BANKBEES.NS"] = _series(50, 57.5)  # +15%

    def fetch(symbols, start):
        return {s: closes[s] for s in symbols if s in closes}

    r = _row(build_track_record(LEDGER, WATCHLIST, fetch=fetch, today=TODAY), "BANKY")
    assert r["index"] == "Nifty Bank (via BANKBEES ETF)"
    assert r["vs_index_pct"] == -5.0


def test_a_missing_index_is_named_on_the_row_and_in_the_log(caplog):
    closes = dict(CLOSES)
    closes.pop("^NSEBANK")

    def fetch(symbols, start):
        return {s: closes[s] for s in symbols if s in closes}

    record = build_track_record(LEDGER, WATCHLIST, fetch=fetch, today=TODAY)
    r = _row(record, "BANKY")
    assert "index" not in r
    assert r["index_unmeasured"] == "Nifty Bank: no data from ^NSEBANK, BANKBEES.NS"
    # FMCG too: the fake has no series for it, and every judged FMCG pick
    # says so rather than silently lacking a comparison.
    assert record["index_failed"] == [
        "Nifty Bank (^NSEBANK, BANKBEES.NS)",
        "Nifty FMCG (^CNXFMCG)",
    ]
    assert record["summary"]["index_unmeasured"] == 4


def test_the_summary_counts_stocks_as_well_as_decisions():
    ledger = LEDGER + [
        # WIN picked again well after the first: a second decision, same stock.
        {
            "date": "2026-08-01",
            "sector": "fmcg",
            "ticker": "WIN",
            "price_at_decision": 115,
        },
    ]
    s = build_track_record(ledger, WATCHLIST, fetch=fake_fetch(), today=TODAY)[
        "summary"
    ]
    assert s["n"] == 5 and s["stocks"] == 4


def test_the_email_names_the_indices_it_could_not_get():
    from emails.mailer import _build_track_record_html

    closes = dict(CLOSES)
    closes.pop("^NSEBANK")

    def fetch(symbols, start):
        return {s: closes[s] for s in symbols if s in closes}

    html = _build_track_record_html(
        build_track_record(LEDGER, WATCHLIST, fetch=fetch, today=TODAY), {"lists": 5}
    )
    assert "No sector-index comparison for 4" in html
    assert "Nifty Bank (^NSEBANK, BANKBEES.NS)" in html


def test_a_short_index_series_falls_through_to_the_etf():
    # 30 September: ^CNXINFRA returned a series, but one starting after most
    # decisions, and the first-symbol-with-data rule never tried INFRABEES.
    closes = dict(CLOSES)
    closes["^NSEBANK"] = [("2026-09-20", 500.0), ("2026-09-26", 510.0)]
    closes["BANKBEES.NS"] = _series(50, 57.5)

    def fetch(symbols, start):
        return {s: closes[s] for s in symbols if s in closes}

    record = build_track_record(LEDGER, WATCHLIST, fetch=fetch, today=TODAY)
    r = _row(record, "BANKY")
    assert r["index"] == "Nifty Bank (via BANKBEES ETF)"
    assert r["vs_index_pct"] == -5.0
    assert record["index_failed"] == ["Nifty FMCG (^CNXFMCG)"]


def test_a_series_that_covers_nothing_says_where_it_looked():
    closes = dict(CLOSES)
    closes["^NSEBANK"] = [("2026-09-20", 500.0), ("2026-09-26", 510.0)]

    def fetch(symbols, start):
        return {s: closes[s] for s in symbols if s in closes}

    r = _row(build_track_record(LEDGER, WATCHLIST, fetch=fetch, today=TODAY), "BANKY")
    assert r["index_unmeasured"] == (
        "Nifty Bank: no close within 7 days before 2026-07-10 in ^NSEBANK"
    )
