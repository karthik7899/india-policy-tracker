"""The book: valuation, limits, orders and risk (analysis/portfolio.py).

Prices are made up so every figure can be worked out by hand; nothing is
downloaded (the weekly fetch is replaced in every test that builds a book).
"""

import datetime
import math

import pytest

from analysis import portfolio as pf

TODAY = datetime.date(2026, 10, 10)


def _stock(ticker, price, advt=None, mcap=None, low=None, name=None):
    sc = {}
    if advt is not None:
        sc["advt_cr"] = advt
    if mcap is not None:
        sc["market_cap"] = mcap
    if low is not None:
        sc["week52_low"] = low
    return {
        "ticker": ticker,
        "name": name or ticker,
        "price": f"{price:.2f}",
        "screener": sc,
    }


WATCHLIST = {
    "aerospace_defence": [
        _stock("HAL", 100.0, advt=500.0, mcap=300000.0, low=80.0),
        _stock("BEL", 50.0, advt=400.0, mcap=250000.0, low=45.0),
    ],
    "semiconductors_equipment": [
        # Trades Rs 0.25 crore a day: a Rs 5 crore position is 100 days of it.
        _stock("SPELS", 10.0, advt=0.25, mcap=500.0, low=8.0),
    ],
    "macro_indicators": [_stock("MAKEINDIA", 150.0)],
}


def _weekly(start, moves, d0=datetime.date(2025, 10, 6)):
    """Weekly closes from a start price and a list of weekly returns."""
    out, level = [[d0.isoformat(), start]], start
    for i, m in enumerate(moves, 1):
        level *= 1 + m
        out.append([(d0 + datetime.timedelta(weeks=i)).isoformat(), round(level, 6)])
    return out


def _book(**over):
    book = {
        "id": "test",
        "name": "Test book",
        "benchmark": "NIFTY50",
        "cash_cr": 0.0,
        "targets": "equal_weight",
        "limits": {},
        "positions": [
            {"ticker": "HAL", "quantity": 500000, "avg_cost": 80.0},  # Rs 5 Cr
            {"ticker": "BEL", "quantity": 1000000, "avg_cost": 50.0},  # Rs 5 Cr
            {"ticker": "SPELS", "quantity": 5000000, "avg_cost": 10.0},  # Rs 5 Cr
        ],
    }
    book.update(over)
    return book


def _build(book=None, weekly=None, bench=None, prior=None, groups=None):
    fetched = {"^NSEI": bench} if bench else {}
    out = pf.build_portfolios(
        WATCHLIST,
        weekly or {},
        books=[book or _book()],
        groups=groups or {},
        fetch=lambda symbols: fetched,
        prior=prior,
        today=TODAY,
    )
    return out["books"][0]


def test_the_book_is_valued_at_todays_prices_with_cash():
    b = _build(_book(cash_cr=5.0))
    s = b["summary"]
    assert s["nav_cr"] == 20.0 and s["invested_cr"] == 15.0 and s["cash_pct"] == 25.0
    # HAL bought at 80, now 100: Rs 1 crore up; the others at cost.
    assert s["pnl_cr"] == 1.0 and s["pnl_pct"] == pytest.approx(7.14, abs=0.01)
    hal = next(p for p in b["positions"] if p["ticker"] == "HAL")
    assert hal["weight_pct"] == 25.0 and hal["pnl_pct"] == 25.0
    # Macro indicators are not holdings.
    assert {p["ticker"] for p in b["positions"]} == {"HAL", "BEL", "SPELS"}


def test_liquidity_is_measured_at_the_real_size():
    b = _build()
    spels = next(p for p in b["positions"] if p["ticker"] == "SPELS")
    # Rs 5 Cr against Rs 0.25 Cr a day: twenty days of trading, a hundred
    # days to sell at a fifth of each.
    assert spels["pct_of_adv"] == 2000.0 and spels["days_to_exit"] == 100.0
    assert spels["ownership_pct"] == 1.0
    liq = b["liquidity"]
    # In a day: all of HAL and BEL, and 0.05 Cr of SPELS, out of 15.
    one = next(e for e in liq["exitable"] if e["days"] == 1)
    assert one["pct"] == pytest.approx((10 + 0.05) / 15 * 100, abs=0.1)
    # Selling a quarter of everything waits on SPELS.
    quarter = next(p for p in liq["pro_rata"] if p["share_pct"] == 25)
    assert quarter["days"] == 25.0
    assert liq["slowest"][0]["ticker"] == "SPELS"


def test_limits_are_checked_and_breaches_say_why():
    b = _build(
        _book(
            limits={
                "max_stock_pct": 30,
                "max_days_to_exit": 5,
                "max_ownership_pct": 0.5,
            },
            exclusions=[{"ticker": "BEL", "reason": "tobacco"}],
        )
    )
    kinds = {(x["kind"], x["subject"]) for x in b["breaches"]}
    assert kinds == {
        ("stock", "HAL"),
        ("stock", "BEL"),
        ("stock", "SPELS"),
        ("excluded", "BEL"),
        ("liquidity", "SPELS"),
        ("ownership", "SPELS"),
    }
    msg = next(x["message"] for x in b["breaches"] if x["kind"] == "liquidity")
    assert msg.startswith("SPELS takes 100.0 days to exit")
    assert "excluded: tobacco" in next(
        x["message"] for x in b["breaches"] if x["kind"] == "excluded"
    )


def test_group_and_sector_limits_add_up_the_members():
    b = _build(
        _book(limits={"max_sector_pct": 60, "max_group_pct": 50}),
        groups={"HAL": "Government of India", "BEL": "Government of India"},
    )
    by = {(x["kind"], x["subject"]): x for x in b["breaches"]}
    assert by[("sector", "aerospace_defence")]["value"] == pytest.approx(66.67)
    assert "Aerospace" in by[("sector", "aerospace_defence")]["message"]
    assert by[("group", "Government of India")]["value"] == pytest.approx(66.67)
    groups = b["exposure"]["groups"]
    assert groups == [
        {"group": "Government of India", "weight_pct": 66.67, "tickers": ["BEL", "HAL"]}
    ]


def test_a_cap_cuts_the_target_and_hands_the_rest_on():
    targets, capped, left = pf.apply_caps(
        {"A": 30.0, "B": 30.0, "C": 40.0}, {"A": (10.0, "liquidity")}
    )
    assert targets["A"] == 10.0 and capped == {"A": (10.0, "liquidity")}
    # The 20 points A could not take go to B and C in proportion.
    assert targets["B"] == pytest.approx(30 + 20 * 30 / 70)
    assert targets["C"] == pytest.approx(40 + 20 * 40 / 70)
    assert left == 0.0
    # When every name is capped, what is left over stays in cash.
    targets, capped, left = pf.apply_caps(
        {"A": 50.0, "B": 50.0}, {"A": (10.0, "x"), "B": (20.0, "y")}
    )
    assert targets == {"A": 10.0, "B": 20.0} and left == pytest.approx(70.0)


def test_orders_cut_an_illiquid_position_and_reinvest_the_proceeds():
    b = _build(_book(limits={"max_days_to_exit": 5}))
    orders = {o["ticker"]: o for o in b["orders"]["rows"]}
    # SPELS may hold 5 days x 0.25 Cr x 20% = Rs 0.25 Cr of a Rs 15 Cr book.
    capped = b["orders"]["capped"][0]
    assert capped["ticker"] == "SPELS" and capped["target_pct"] == pytest.approx(
        1.67, abs=0.01
    )
    assert orders["SPELS"]["side"] == "SELL"
    assert orders["SPELS"]["quantity"] == 5000000 - 250000
    assert "over its cap" in orders["SPELS"]["reason"]
    # The Rs 4.75 Cr freed goes to HAL and BEL, now well under target.
    assert orders["HAL"]["side"] == orders["BEL"]["side"] == "BUY"
    assert b["orders"]["breaches_after"] == []
    assert 0 <= b["orders"]["cash_after_cr"] < 0.01
    # Whole shares only.
    assert all(isinstance(o["quantity"], int) for o in b["orders"]["rows"])


def test_proceeds_too_small_to_pass_the_band_are_still_reinvested():
    """An equal-weight book of 40 names where one is cut back: every other
    name is under target by less than the band, so only the settling pass
    puts the proceeds to work -- without it they would sit in cash."""
    rows, info = [], {}
    for i in range(40):
        t = f"S{i:02d}"
        rows.append(
            {
                "ticker": t,
                "name": t,
                "price": 100.0,
                "quantity": 25000,
                "value_cr": 0.25,
                "weight_pct": 2.5,
                "in_watchlist": True,
            }
        )
        info[t] = {"name": t, "sector": "x", "price": 100.0, "advt_cr": 10.0}
    targets = {r["ticker"]: 2.5 for r in rows}
    targets["S00"] = 0.5
    for t in targets:
        if t != "S00":
            targets[t] = 2.5 + 2.0 / 39
    capped = {"S00": (0.5, "a test cap")}
    orders = pf.rebalance(rows, targets, 10.0, info, 0.25, {}, capped, 0.0, 0.0)
    by = {o["ticker"]: o for o in orders}
    assert by["S00"]["side"] == "SELL" and by["S00"]["quantity"] == 20000
    buys = [o for o in orders if o["side"] == "BUY"]
    assert len(buys) == 39
    assert {o["reason"] for o in buys} == {"reinvests the proceeds of the sales"}
    spent = sum(o["quantity"] * o["price"] for o in buys) / 1e7
    assert 0.19 < spent <= 0.2


def test_a_name_off_the_watchlist_is_sold_and_a_new_one_bought():
    book = _book(
        positions=[
            {"ticker": "HAL", "quantity": 500000},
            {"ticker": "BEL", "quantity": 1000000},
            {"ticker": "OLDCO", "quantity": 1000},
        ]
    )
    weekly = {"HAL": _weekly(100.0, [0.0] * 3)}
    b = pf.build_portfolios(
        WATCHLIST,
        weekly,
        books=[book],
        groups={},
        # OLDCO left the watchlist; its price comes from the weekly download.
        fetch=lambda symbols: {"OLDCO.NS": _weekly(200.0, [0.0] * 3)},
        today=TODAY,
    )["books"][0]
    orders = {o["ticker"]: o for o in b["orders"]["rows"]}
    assert orders["OLDCO"]["side"] == "SELL" and orders["OLDCO"]["quantity"] == 1000
    assert orders["OLDCO"]["reason"] == "no longer on the watchlist"
    assert (
        orders["SPELS"]["side"] == "BUY"
        and orders["SPELS"]["reason"] == "new to the targets"
    )
    old = next(p for p in b["positions"] if p["ticker"] == "OLDCO")
    assert old["in_watchlist"] is False and old["price"] == 200.0


def test_drift_inside_the_band_is_left_alone():
    # Equal weights to within a few basis points: nothing to trade.
    book = _book(
        positions=[
            {"ticker": "HAL", "quantity": 500000},
            {"ticker": "BEL", "quantity": 1000000},
            {"ticker": "SPELS", "quantity": 5010000},
        ]
    )
    assert _build(book)["orders"]["rows"] == []


def test_a_cash_shortfall_is_raised_from_the_overweights():
    # A new name must be bought with no cash: HAL, the overweight, pays.
    book = _book(
        positions=[
            {"ticker": "HAL", "quantity": 1000000},  # Rs 10 Cr
            {"ticker": "BEL", "quantity": 1000000},  # Rs 5 Cr
        ]
    )
    b = _build(book)
    orders = {o["ticker"]: o for o in b["orders"]["rows"]}
    assert orders["SPELS"]["side"] == "BUY"
    assert orders["HAL"]["side"] == "SELL"
    assert b["orders"]["cash_after_cr"] >= 0


def test_risk_is_read_from_weekly_returns_against_the_benchmark():
    bench_moves = [0.01 * math.sin(i) for i in range(52)]
    bench = _weekly(20000.0, bench_moves)
    # HAL moves twice as far as the market every week; BEL exactly with it.
    weekly = {
        "HAL": _weekly(100.0, [2 * m for m in bench_moves]),
        "BEL": _weekly(50.0, bench_moves),
    }
    book = _book(
        positions=[
            {"ticker": "HAL", "quantity": 500000},
            {"ticker": "BEL", "quantity": 1000000},
        ],
        targets={"HAL": 50, "BEL": 50},
    )
    b = _build(book, weekly=weekly, bench=bench)
    risk = b["risk"]
    assert risk["weeks"] == 52
    # Half at beta 2, half at beta 1 (rebalanced weekly).
    assert risk["beta"] == pytest.approx(1.5, abs=0.01)
    assert risk["correlation"] == pytest.approx(1.0, abs=0.001)
    hal = next(p for p in b["positions"] if p["ticker"] == "HAL")
    assert hal["beta"] == pytest.approx(2.0, abs=0.01)
    # HAL carries two thirds of the risk: weight 1/2, beta 2, against 1.5.
    shares = {c["ticker"]: c["risk_share_pct"] for c in risk["contributors"]}
    assert shares["HAL"] == pytest.approx(66.7, abs=0.1)
    assert shares["BEL"] == pytest.approx(33.3, abs=0.1)
    # The active return is half the market's, so the tracking error is half
    # the market's volatility.
    assert risk["tracking_error_pct"] == pytest.approx(
        risk["benchmark_vol_pct"] * 0.5, abs=0.15
    )
    # Historical VaR: the 5% quantile of the 52 weekly returns.
    book_rets = [1.5 * m for m in bench_moves]
    xs = sorted(book_rets)
    pos = 0.05 * 51
    q = xs[2] + (xs[3] - xs[2]) * (pos - 2)
    assert risk["var_95"]["pct"] == pytest.approx(-q * 100, abs=0.01)
    assert risk["worst_4_weeks"]["pct"] < 0
    assert risk["worst_4_weeks"]["contributors"][0]["ticker"] == "HAL"
    pair = risk["correlated_pairs"][0]
    assert {pair["a"], pair["b"]} == {"HAL", "BEL"} and pair["correlation"] == 1.0
    # A Nifty fall of 10% costs 15% through the betas.
    fall = next(s for s in b["scenarios"] if s["key"] == "market_fall")
    assert fall["pct"] == pytest.approx(-15.0, abs=0.1)


def test_returns_are_a_backcast_whose_contributions_add_up():
    bench = _weekly(20000.0, [0.01] * 52)
    weekly = {
        "HAL": _weekly(100.0 / 1.02**52, [0.02] * 52),
        "BEL": _weekly(50.0, [0.0] * 52),
        # Listed eight weeks ago: left out of the longer windows.
        "SPELS": _weekly(10.0, [0.0] * 8, d0=datetime.date(2026, 8, 10)),
    }
    b = _build(weekly=weekly, bench=bench)
    windows = {w["label"]: w for w in b["returns"]["windows"]}
    assert set(windows) == {"1 month", "3 months", "6 months", "1 year"}
    year = windows["1 year"]
    assert year["unpriced"] == ["SPELS"]
    # HAL and BEL reweighted to half each; HAL rose 1.02^52 - 1.
    hal = 1.02**52 - 1
    assert year["portfolio_pct"] == pytest.approx(hal / 2 * 100, abs=0.01)
    assert year["benchmark_pct"] == pytest.approx((1.01**52 - 1) * 100, abs=0.01)
    parts = b["returns"]["best"] + b["returns"]["worst"]
    assert sum({p["ticker"]: p["pct"] for p in parts}.values()) == pytest.approx(
        year["portfolio_pct"], abs=0.02
    )
    month = windows["1 month"]
    assert month["unpriced"] == []


def test_the_year_is_shortened_to_the_download_not_left_out():
    bench = _weekly(20000.0, [0.0] * 30)
    weekly = {
        t: _weekly(p, [0.0] * 30)
        for t, p in (("HAL", 100.0), ("BEL", 50.0), ("SPELS", 10.0))
    }
    b = _build(weekly=weekly, bench=bench)
    labels = [w["label"] for w in b["returns"]["windows"]]
    assert labels == ["1 month", "3 months", "6 months", "30 weeks"]
    assert b["returns"]["contribution_window"] == "30 weeks"


def test_too_little_history_is_said_rather_than_guessed():
    bench = _weekly(20000.0, [0.01] * 10)
    weekly = {"HAL": _weekly(100.0, [0.01] * 10)}
    b = _build(weekly=weekly, bench=bench)
    assert "insufficient" in b["risk"] and "beta" not in b["risk"]
    assert b["risk"]["no_history"] == ["BEL", "HAL", "SPELS"]
    fall = next(s for s in b["scenarios"] if s["key"] == "market_fall")
    # Every holding taken at beta 1 and said to be.
    assert fall["pct"] == pytest.approx(-10.0) and "taken at 1.0" in fall["basis"]


def test_the_52_week_low_scenario_never_counts_a_gain():
    stocks = {
        "x": [
            _stock("HAL", 100.0, low=80.0),
            # Already under its weekly-close low.
            _stock("BEL", 50.0, low=55.0),
        ]
    }
    book = _book(
        positions=[
            {"ticker": "HAL", "quantity": 100000},
            {"ticker": "BEL", "quantity": 200000},
        ]
    )
    b = pf.build_portfolios(
        stocks, {}, books=[book], groups={}, fetch=lambda s: {}, today=TODAY
    )["books"][0]
    lows = next(s for s in b["scenarios"] if s["key"] == "week52_lows")
    assert lows["pct"] == pytest.approx(-10.0)


def test_new_breaches_are_marked_against_the_last_run():
    book = _book(limits={"max_days_to_exit": 5, "max_stock_pct": 30})
    prior = {
        "books": [
            {"id": "test", "breaches": [{"kind": "liquidity", "subject": "SPELS"}]}
        ]
    }
    b = _build(book, prior=prior)
    new = {(x["kind"], x["subject"]): x["new"] for x in b["breaches"]}
    assert new[("liquidity", "SPELS")] is False
    assert new[("stock", "HAL")] is True
    # Without a previous run nothing is called new.
    assert all("new" not in x for x in _build(book)["breaches"])


def test_nothing_breaks_the_run():
    def boom(symbols):
        raise RuntimeError("yahoo down")

    out = pf.build_portfolios(
        WATCHLIST, {}, books=[_book()], groups={}, fetch=boom, today=TODAY
    )
    b = out["books"][0]
    # Priced from the watchlist alone; no benchmark, said so.
    assert b["summary"]["nav_cr"] == 15.0
    assert b["benchmark"]["missing"] == "no weekly closes for ^NSEI"
    bad = pf.build_portfolios(
        WATCHLIST,
        {},
        books=[{"id": "x", "positions": "nonsense"}],
        groups={},
        fetch=lambda s: {},
        today=TODAY,
    )
    assert bad["books"][0]["error"]
    assert pf.build_portfolios(WATCHLIST, {}, books=[], today=TODAY) == {
        "as_of": "2026-10-10",
        "books": [],
    }


def test_portfolio_files_load(tmp_path):
    p = tmp_path / "portfolios.json"
    p.write_text('{"portfolios": [{"id": "a"}, "junk"]}')
    assert pf.load_portfolios(str(p)) == [{"id": "a"}]
    assert pf.load_portfolios(str(tmp_path / "none.json")) == []
    g = tmp_path / "groups.json"
    g.write_text('{"groups": {"Tata": ["tcs", "INDHOTEL"]}}')
    assert pf.load_groups(str(g)) == {"TCS": "Tata", "INDHOTEL": "Tata"}


def test_the_committed_model_book_and_groups_are_well_formed():
    import json
    import os

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    books = pf.load_portfolios(os.path.join(root, "portfolios.json"))
    model = next(b for b in books if b["id"] == "model")
    assert model["kind"] == "model" and model["positions"]
    assert all(
        isinstance(p["quantity"], int) and p["quantity"] > 0 for p in model["positions"]
    )
    groups = pf.load_groups(os.path.join(root, "business_groups.json"))
    with open(os.path.join(root, "business_groups.json")) as f:
        raw = json.load(f)["groups"]
    # A company belongs to one group at most.
    assert len(groups) == sum(len(v) for v in raw.values())


def test_since_last_run_lists_new_and_cleared_breaches():
    from analysis.changes import build_changes

    now = {
        "books": [
            {
                "id": "m",
                "name": "Model",
                "breaches": [
                    {
                        "kind": "liquidity",
                        "subject": "SPELS",
                        "message": "SPELS takes 9 days",
                    }
                ],
            }
        ]
    }
    before = {
        "books": [
            {
                "id": "m",
                "name": "Model",
                "breaches": [
                    {"kind": "ownership", "subject": "ADSL", "message": "owns 1.1%"}
                ],
            }
        ]
    }
    c = build_changes({"portfolio": now}, {"portfolio": before})
    texts = [i["text"] for i in c["items"]["portfolio"]]
    assert texts == [
        "SPELS takes 9 days",
        "ADSL: share of the company owned back within the limit",
    ]
    # A book the last run did not measure is not all new.
    assert build_changes({"portfolio": now}, {"x": 1})["counts"]["portfolio"] == 0


def test_the_email_section_leads_with_value_risk_and_breaches():
    from emails.mailer import _build_portfolio_html

    bench = _weekly(20000.0, [0.01 * math.sin(i) for i in range(52)])
    weekly = {
        "HAL": _weekly(100.0, [0.02 * math.sin(i) for i in range(52)]),
        "BEL": _weekly(50.0, [0.01 * math.sin(i) for i in range(52)]),
    }
    out = pf.build_portfolios(
        WATCHLIST,
        weekly,
        books=[_book(limits={"max_days_to_exit": 5}, kind="model")],
        groups={},
        fetch=lambda s: {"^NSEI": bench},
        today=TODAY,
    )
    html = _build_portfolio_html(out)
    assert "₹15.0 Cr in 3 positions" in html
    assert "An illustrative model book" in html
    assert "SPELS takes 100.0 days to exit" in html
    assert "Nifty 50 falls 10%" in html and "-₹" in html and "₹-" not in html
    assert "would restore the targets" in html and "leaving every limit met" in html
    assert "#/portfolio" in html
    assert _build_portfolio_html({"books": []}) == ""
    assert _build_portfolio_html(None) == ""


def test_a_single_symbol_download_is_read_in_either_shape():
    import pandas as pd

    idx = pd.to_datetime(["2026-09-28", "2026-10-05"])
    flat = pd.DataFrame({"Close": [25000.0, 25100.0]}, index=idx)
    levels = pd.DataFrame(
        [[1.0, 25000.0], [1.0, 25100.0]],
        index=idx,
        columns=pd.MultiIndex.from_tuples([("^NSEI", "Open"), ("^NSEI", "Close")]),
    )
    want = [["2026-09-28", 25000.0], ["2026-10-05", 25100.0]]
    from analysis.growth import _weekly_closes

    assert _weekly_closes(pf._frame_for(flat, "^NSEI")) == want
    assert _weekly_closes(pf._frame_for(levels, "^NSEI")) == want
    assert pf._frame_for(levels, "^CRSLDX") is None


def test_two_lots_of_one_ticker_are_one_position():
    book = _book(
        positions=[
            {"ticker": "HAL", "quantity": 300000, "avg_cost": 80.0},
            {"ticker": "hal", "quantity": 200000, "avg_cost": 90.0},
            {"ticker": "BEL", "quantity": 1000000, "avg_cost": 50.0},
            {"ticker": "SPELS", "quantity": 5000000, "avg_cost": 10.0},
        ]
    )
    b = _build(book)
    hal = [p for p in b["positions"] if p["ticker"] == "HAL"]
    assert len(hal) == 1
    assert hal[0]["quantity"] == 500000 and hal[0]["avg_cost"] == 84.0
    assert b["summary"]["nav_cr"] == 15.0
    assert "market_cap_cr" not in hal[0] and "week52_low" not in hal[0]
