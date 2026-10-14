"""Last known good (analysis/last_good.py): what a source failed to deliver
this run is kept for up to a week and marked, never lost and never passed
off as fresh."""

import datetime
import os
import re

import pytest

from analysis import last_good as lg

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UTC = datetime.timezone.utc
BEFORE = datetime.datetime(2026, 10, 13, 9, 30, tzinfo=UTC)
NOW = datetime.datetime(2026, 10, 14, 9, 30, tzinfo=UTC)


def _holding(**extra):
    stock = {
        "ticker": "HAL",
        "price": "4210.50",
        "growth_pct": "+12.0%",
        "screener": {
            "roce": 31.2,
            "roe": 24.0,
            "market_cap": 281000.0,
            "pledged_pct": 1.5,
            "q_sales": 7044.0,
            "advt_cr": 512.0,
            "week52_low": 3046.0,
            "deliv_pct": 48.0,
            # Computed later in every run; never kept.
            "graham_intrinsic_value": 1890.0,
            "isin": "INE066F01020",
        },
        "_fetched": {
            "price": "2026-10-13T09:31:00+00:00",
            "screener": "2026-10-13T09:40:00+00:00",
            "run": "2026-10-13T09:45:00+00:00",
        },
    }
    stock.update(extra)
    return stock


def _run(stock, *, price=False, screener=None, when=NOW):
    """One run: snapshot, the sources' results, restore."""
    watchlist = {"aerospace_defence": [stock]}
    prior = lg.snapshot(watchlist, when=when - datetime.timedelta(minutes=30))
    # Each run rebuilds the screener dict from what the sources deliver.
    stock["screener"] = dict(screener or {})
    stock["screener"]["isin"] = "INE066F01020"
    if price:
        stock["price"] = "4300.00"
        lg.mark(stock, "price", when=when - datetime.timedelta(minutes=20))
    if screener is not None:
        lg.mark(stock, "screener", when=when - datetime.timedelta(minutes=10))
    return lg.restore(watchlist, prior, when=when)


def test_a_failed_screener_fetch_keeps_the_fundamentals_marked():
    """A Screener timeout used to leave the holding with no fundamentals."""
    stock = _holding()
    report = _run(stock, price=True)
    sc = stock["screener"]
    assert sc["roce"] == 31.2 and sc["market_cap"] == 281000.0
    # The fetch failed, so a pledge row's absence says nothing: kept too.
    assert sc["pledged_pct"] == 1.5
    assert stock["_stale_fields"]["roce"] == "2026-10-13"
    # Computed later in the run, from the kept inputs; not kept itself.
    assert "graham_intrinsic_value" not in sc
    assert "graham_intrinsic_value" not in stock["_stale_fields"]
    # The price came in fresh, so it is not marked.
    assert stock["price"] == "4300.00" and "price" not in stock["_stale_fields"]
    assert report["holdings"] == 1 and report["dropped"] == 0
    assert report["oldest"] == "2026-10-13"


def test_a_partial_fetch_keeps_only_what_is_missing():
    stock = _holding()
    _run(stock, price=True, screener={"roe": 25.0, "market_cap": 290000.0})
    sc = stock["screener"]
    assert sc["roe"] == 25.0 and sc["roce"] == 31.2
    assert set(stock["_stale_fields"]) >= {"roce", "q_sales"}
    assert "roe" not in stock["_stale_fields"]
    # The fetch worked and printed no pledge row: the pledge is gone.
    assert "pledged_pct" not in sc


def test_a_value_older_than_a_week_is_dropped_not_shown_as_current():
    stock = _holding(_stale_fields={"roce": "2026-10-06", "price": "2026-10-05"})
    report = _run(stock)
    assert "roce" not in stock["screener"]
    # Kept since 13 Oct: still within the week.
    assert stock["screener"]["roe"] == 24.0
    # A price nine days old is not the price; its upside goes with it.
    assert "price" not in stock and "growth_pct" not in stock
    assert report["dropped"] == 2


def test_a_kept_value_keeps_the_day_it_was_fetched():
    stock = _holding(_stale_fields={"roce": "2026-10-10"})
    _run(stock)
    assert stock["_stale_fields"]["roce"] == "2026-10-10"
    assert stock["_stale_fields"]["roe"] == "2026-10-13"


def test_a_price_the_run_did_not_refresh_is_marked_and_dated():
    stock = _holding()
    _run(stock, screener={"roce": 31.0, "roe": 24.0, "market_cap": 1.0})
    assert stock["price"] == "4210.50"
    assert stock["_stale_fields"]["price"] == "2026-10-13"


def test_turnover_dates_from_the_price_fetch_and_delivery_from_the_run():
    stock = _holding()
    stock["_fetched"]["price"] = "2026-10-12T09:31:00+00:00"
    _run(stock, price=True, screener={"roce": 31.0})
    assert stock["_stale_fields"]["advt_cr"] == "2026-10-12"
    assert stock["_stale_fields"]["week52_low"] == "2026-10-12"
    assert stock["_stale_fields"]["deliv_pct"] == "2026-10-13"


def test_records_from_before_this_existed_count_as_yesterdays():
    stock = _holding()
    del stock["_fetched"]
    _run(stock)
    assert stock["_stale_fields"]["roce"] == "2026-10-13"
    assert stock["_fetched"]["run"] == "2026-10-14T09:30:00+00:00"


def test_a_fully_fresh_holding_carries_no_marker():
    stock = _holding(_stale_fields={"roce": "2026-10-12"})
    full = {k: 1.0 for k in lg.KEPT_FIELDS}
    report = _run(stock, price=True, screener=full)
    assert "_stale_fields" not in stock
    assert report == {"kept": 0, "holdings": 0, "dropped": 0, "oldest": None}
    assert lg.describe(report) == (
        "Last known good: every holding's values were fetched this run."
    )


def test_a_new_holding_has_nothing_to_keep():
    watchlist = {"aerospace_defence": [_holding()]}
    prior = lg.snapshot({}, when=NOW)
    report = lg.restore(watchlist, prior, when=NOW)
    assert report["kept"] == 0
    assert "_stale_fields" not in watchlist["aerospace_defence"][0]


def test_the_log_line_says_what_was_kept_and_dropped():
    line = lg.describe({"kept": 5, "holdings": 2, "dropped": 1, "oldest": "2026-10-11"})
    assert line == (
        "Last known good: kept 5 value(s) a source did not deliver this run, "
        "for 2 holding(s), the oldest fetched 2026-10-11; dropped 1 older "
        "than 7 days rather than show them as current."
    )


# The field lists are what each source writes. A field added to a source and
# not to its list would be lost on a failed fetch again, silently.


def test_the_screener_fields_are_what_the_parser_writes():
    with open(os.path.join(ROOT, "providers", "screener.py"), encoding="utf-8") as f:
        parsed = set(re.findall(r'\bsc\["([a-z_0-9]+)"\]\s*=', f.read()))
    assert parsed == set(lg.SCREENER_FIELDS)


def test_the_liquidity_fields_are_what_the_price_download_writes():
    pd = pytest.importorskip("pandas")
    from analysis.growth import _range_from_frame
    from analysis.liquidity import assess

    written = set(assess([100.0] * 20, [1000.0] * 20))
    frame = pd.DataFrame({"Close": [90.0, 110.0, 100.0]})
    written |= set(_range_from_frame(frame))
    assert written == set(lg.LIQUIDITY_FIELDS)


def test_the_delivery_fields_are_what_delivery_writes():
    from providers.nse_delivery import apply_delivery

    watchlist = {"x": [{"ticker": "HAL", "screener": {}}]}
    row = {"deliv_pct": 48.0, "series": "EQ", "turnover_cr": 12.0}
    apply_delivery(watchlist, {"HAL": row})
    assert set(watchlist["x"][0]["screener"]) == set(lg.DELIVERY_FIELDS)


def test_a_live_price_is_stamped_as_fetched(monkeypatch):
    import providers.yahoo as yahoo
    from analysis.growth import update_single_stock

    monkeypatch.setattr(
        yahoo, "fetch_stock_data", lambda symbol, **kw: {"price": 101.0}
    )
    stock = {"ticker": "HAL"}
    assert update_single_stock(stock) is True
    assert stock["_fetched"]["price"] >= "2026"
    monkeypatch.setattr(yahoo, "fetch_stock_data", lambda symbol, **kw: {"price": None})
    stock = {"ticker": "HAL"}
    assert update_single_stock(stock) is False
    assert "_fetched" not in stock
