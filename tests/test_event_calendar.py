"""The calendar and results (providers/nse_calendar.py,
analysis/event_calendar.py).

Nothing is fetched: NSE is a fake session, and the quarterly series are
written out so each scorecard figure can be checked by hand.
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from analysis import event_calendar as ec
from providers import exchange_api
from providers import nse_announcements as nse
from providers import nse_calendar as cal

TODAY = datetime.date(2026, 10, 10)


def _stock(ticker, sales=None, eps=None, opm=None, profit=None, name=None):
    sc = {}
    if sales is not None:
        sc["sales_trend"] = sales
    if eps is not None:
        sc["eps_trend"] = eps
    if opm is not None:
        sc["quarterly_ebitda_margin"] = opm
    if profit is not None:
        sc["q_net_profit"] = profit
    return {"ticker": ticker, "name": name or ticker, "screener": sc}


HAL_SALES = [5976.0, 6957.0, 13700.0, 4819.0, 6629.0, 7699.0, 13942.0, 5515.0]
WATCHLIST = {
    "aerospace_defence": [
        _stock("HAL", HAL_SALES, name="Hindustan Aeronautics"),
        _stock("BEL"),
    ],
    "fmcg": [_stock("ITC")],
    "macro_indicators": [_stock("MAKEINDIA")],
}


# --- the provider ----------------------------------------------------------


def test_purposes_and_subjects_are_sorted_into_kinds():
    assert cal.classify("Financial Results/Dividend") == "results"
    assert cal.classify("Fund Raising") == "fund_raising"
    assert cal.classify("Other business") == "board"
    assert (
        cal.classify("Interim Dividend - Rs 5 Per Share", "corporate_action")
        == "dividend"
    )
    assert (
        cal.classify("Face Value Split (Sub-Division) - From Rs 10/- To Rs 2/-")
        == "split"
    )
    assert cal.classify("Annual General Meeting") == "agm"
    assert cal.classify("Bonus 1:1") == "bonus"


def test_nse_dates_are_read_or_dropped_never_guessed():
    assert cal.parse_date("31-Oct-2026") == "2026-10-31"
    assert cal.parse_date("31-OCT-2026") == "2026-10-31"
    assert cal.parse_date("31-Oct-2026 17:30:00") == "2026-10-31"
    assert cal.parse_date("2026-10-31") == "2026-10-31"
    assert cal.parse_date("soon") is None and cal.parse_date("") is None


def test_rows_become_calendar_entries():
    e = cal.normalize_event(
        {
            "symbol": "hal",
            "purpose": "Financial Results",
            "bm_desc": "To consider the results for the quarter ended September 30, 2026",
            "date": "31-Oct-2026",
        }
    )
    assert (e["ticker"], e["date"], e["kind"]) == ("HAL", "2026-10-31", "results")
    assert e["title"] == "Board meeting: Financial Results"
    a = cal.normalize_action(
        {
            "symbol": "ITC",
            "subject": "Interim Dividend - Rs 6.50 Per Share",
            "exDate": "05-Nov-2026",
            "recDate": "05-Nov-2026",
        }
    )
    assert (a["date"], a["kind"]) == ("2026-11-05", "dividend")
    assert a["title"] == "Ex-date: Interim Dividend - Rs 6.50 Per Share"
    assert cal.normalize_event({"symbol": "HAL", "date": "someday"}) is None
    assert cal.normalize_action({"symbol": "ITC", "exDate": "05-Nov-2026"}) is None


def _response(payload, content_type="application/json", status=200):
    r = MagicMock()
    r.status_code = status
    r.headers = {"Content-Type": content_type}
    r.url = "https://www.nseindia.com/api/x"
    r.text = "" if payload is not None else "<html>challenge</html>"
    if payload is None:
        r.json.side_effect = ValueError("Expecting value")
    else:
        r.json.return_value = payload
    return r


class _Session:
    def __init__(self, answers, cookies=True):
        self.answers, self.calls = answers, []
        self.cookies = {"nsit": "x"} if cookies else {}

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params))
        if url in (nse.HOME_URL, nse.REFERER_PAGE):
            return _response({})
        key = (url, "from_date" in (params or {}))
        return self.answers[key] if key in self.answers else self.answers[url]

    def close(self):
        pass


@pytest.fixture(autouse=True)
def _no_sleeping():
    with patch.object(exchange_api.time, "sleep"):
        yield


def test_the_calendar_reads_both_endpoints_and_keeps_holdings_only():
    session = _Session(
        {
            cal.EVENTS_URL: _response(
                [
                    {
                        "symbol": "HAL",
                        "purpose": "Financial Results",
                        "date": "31-Oct-2026",
                    },
                    {
                        "symbol": "TCS",
                        "purpose": "Financial Results",
                        "date": "09-Oct-2026",
                    },
                ]
            ),
            cal.ACTIONS_URL: _response(
                {
                    "data": [
                        {
                            "symbol": "ITC",
                            "subject": "Dividend",
                            "exDate": "05-Nov-2026",
                        }
                    ]
                }
            ),
        }
    )
    out = cal.fetch_calendar(["HAL", "ITC"], today=TODAY, session=session)
    assert out["published"] == {"event_calendar": 2, "corporate_actions": 1}
    assert sorted(e["ticker"] for e in out["events"]) == ["HAL", "ITC"]
    assert out["errors"] == []
    # The date window was asked for.
    params = dict(c for c in session.calls if c[0] == cal.EVENTS_URL)[cal.EVENTS_URL]
    assert params == {
        "index": "equities",
        "from_date": "26-09-2026",
        "to_date": "09-12-2026",
    }


def test_a_window_answered_with_nothing_is_asked_again_without_it():
    session = _Session(
        {
            (cal.EVENTS_URL, True): _response([]),
            (cal.EVENTS_URL, False): _response(
                [
                    {
                        "symbol": "HAL",
                        "purpose": "Financial Results",
                        "date": "31-Oct-2026",
                    }
                ]
            ),
            cal.ACTIONS_URL: _response([]),
        }
    )
    out = cal.fetch_calendar(["HAL"], today=TODAY, session=session)
    assert [e["ticker"] for e in out["events"]] == ["HAL"]
    assert (cal.EVENTS_URL, {"index": "equities"}) in session.calls


def test_a_refusal_is_reported_and_never_raised():
    blocked = _Session(
        {
            cal.EVENTS_URL: _response(None, content_type="text/html"),
            cal.ACTIONS_URL: _response([]),
        }
    )
    out = cal.fetch_calendar(["HAL"], today=TODAY, session=blocked)
    assert (
        out["events"] == []
        and "event_calendar: NSEContentTypeError" in out["errors"][0]
    )
    assert out["published"] == {"corporate_actions": 0}
    cookieless = cal.fetch_calendar(
        ["HAL"], today=TODAY, session=_Session({}, cookies=False)
    )
    assert cookieless["errors"] == ["NSE handshake yielded no cookies"]


# --- dates from the filings and the merge ----------------------------------

FILINGS = [
    {
        "ticker": "HAL",
        "date": "2026-10-08",
        "text": "Hindustan Aeronautics Limited has informed the Exchange about Board "
        "Meeting to be held on 31-Oct-2026 to consider and approve the unaudited "
        "financial results for the quarter ended September 30, 2026.",
        "link": "https://nsearchives.nseindia.com/corporate/HAL_1.pdf",
    },
    {
        "ticker": "BEL",
        "date": "2026-10-09",
        "text": "Bharat Electronics Limited has informed the Exchange regarding Outcome "
        "of Board Meeting held on October 9, 2026.",
    },
    {
        "ticker": "BEL",
        "date": "2026-10-09",
        "text": "Bharat Electronics Limited has informed the Exchange about Board Meeting "
        "to be held on 06/11/2026 for fund raising.",
    },
    # Not a holding.
    {
        "ticker": "TCS",
        "text": "TCS has informed the Exchange about Board Meeting to be held on 09-Oct-2026",
    },
    {
        "ticker": "ITC",
        "text": "ITC has informed the Exchange regarding a newspaper ad.",
    },
]


def test_board_meeting_notices_in_the_filings_give_dates():
    held = ec._held(WATCHLIST)
    got = {
        (m["ticker"], m["date"], m["kind"])
        for m in ec.meetings_from_filings(FILINGS, held)
    }
    assert got == {
        ("HAL", "2026-10-31", "results"),
        ("BEL", "2026-10-09", "outcome"),
        ("BEL", "2026-11-06", "fund_raising"),
    }


def test_the_calendar_merges_sources_and_keeps_one_meeting_a_day():
    fetched = {
        "events": [
            # The same HAL meeting as the filing: one entry, NSE's.
            {
                "ticker": "HAL",
                "date": "2026-10-31",
                "kind": "results",
                "title": "Board meeting: Financial Results",
                "source": "NSE event calendar",
            },
            # A dividend ex-date the same day as a meeting is its own event.
            {
                "ticker": "ITC",
                "date": "2026-11-05",
                "kind": "dividend",
                "title": "Ex-date: Dividend",
                "source": "NSE corporate actions",
            },
            {
                "ticker": "ITC",
                "date": "2026-11-05",
                "kind": "board",
                "title": "Board meeting",
                "source": "NSE event calendar",
            },
            # Beyond the window.
            {
                "ticker": "HAL",
                "date": "2027-03-01",
                "kind": "agm",
                "title": "AGM",
                "source": "NSE event calendar",
            },
        ],
        "published": {"event_calendar": 30, "corporate_actions": 12},
        "errors": [],
    }
    prior = {
        "upcoming": [
            # Still ahead, not seen today: carried.
            {
                "ticker": "BEL",
                "date": "2026-10-20",
                "kind": "results",
                "title": "Board meeting",
                "source": "NSE event calendar",
            },
            # Passed: dropped.
            {
                "ticker": "BEL",
                "date": "2026-10-01",
                "kind": "results",
                "title": "x",
                "source": "NSE event calendar",
            },
        ]
    }
    macro = [
        {
            "date": "2026-10-14",
            "kind": "macro",
            "title": "RBI policy",
            "source": "macro_events.json",
        }
    ]
    c = ec.build_calendar(WATCHLIST, fetched, FILINGS, prior, macro, today=TODAY)
    ahead = [(e["ticker"], e["date"], e["kind"], e["source"]) for e in c["upcoming"]]
    assert ahead == [
        ("BEL", "2026-10-20", "results", "NSE event calendar"),
        ("HAL", "2026-10-31", "results", "NSE event calendar"),
        ("ITC", "2026-11-05", "board", "NSE event calendar"),
        ("ITC", "2026-11-05", "dividend", "NSE corporate actions"),
        ("BEL", "2026-11-06", "fund_raising", "NSE filing"),
    ]
    assert c["upcoming"][0]["carried"] is True
    assert c["upcoming"][1]["name"] == "Hindustan Aeronautics"
    assert c["recent"][0]["date"] == "2026-10-09"
    assert c["next_results"] == {"BEL": "2026-10-20", "HAL": "2026-10-31"}
    assert c["macro"][0]["title"] == "RBI policy"
    assert c["sources"] == {
        "nse": {"event_calendar": 30, "corporate_actions": 12},
        "nse_errors": [],
        "filings": 3,
        "carried": 1,
    }


def test_a_plain_board_meeting_takes_the_purpose_another_source_read():
    fetched = {
        "events": [
            {
                "ticker": "HAL",
                "date": "2026-10-31",
                "kind": "board",
                "title": "Board meeting",
                "source": "NSE event calendar",
            }
        ]
    }
    c = ec.build_calendar(WATCHLIST, fetched, FILINGS[:1], {}, [], today=TODAY)
    (hal,) = [e for e in c["upcoming"] if e["ticker"] == "HAL"]
    assert hal["kind"] == "results" and hal["source"] == "NSE event calendar"


def test_macro_dates_are_read_from_the_file_and_never_invented(tmp_path):
    p = tmp_path / "macro.json"
    p.write_text(
        '{"events": [{"date": "2026-12-05", "title": "RBI policy decision", '
        '"sectors": ["banking_financials"]}, {"title": "no date"}, "junk"]}'
    )
    assert ec.load_macro(str(p)) == [
        {
            "date": "2026-12-05",
            "kind": "macro",
            "title": "RBI policy decision",
            "detail": "",
            "sectors": ["banking_financials"],
            "source": "macro_events.json",
        }
    ]
    assert ec.load_macro(str(tmp_path / "none.json")) == []


def test_the_committed_macro_file_is_empty_until_someone_fills_it():
    import os

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert ec.load_macro(os.path.join(root, "macro_events.json")) == []


# --- results ---------------------------------------------------------------


def test_a_new_quarter_is_the_series_moved_along_by_one():
    old = HAL_SALES
    new = HAL_SALES[1:] + [7100.0]
    assert ec.new_quarter(old, new)
    # Nothing changed.
    assert not ec.new_quarter(old, list(old))
    # One quarter restated by a few percent still lines up.
    restated = list(new)
    restated[2] = new[2] * 1.05
    assert ec.new_quarter(old, restated)
    # The latest quarter restated, nothing new.
    assert not ec.new_quarter(old, HAL_SALES[:-1] + [5600.0])
    # Too short to tell.
    assert not ec.new_quarter([1.0, 2.0], [2.0, 3.0])


def test_flat_sales_with_a_restated_quarter_are_not_called_a_result():
    flat = [100.0, 100.2, 100.4, 100.6, 100.8, 101.0, 101.2, 101.4]
    assert not ec.new_quarter(flat, flat[:-1] + [103.0])


def test_the_quarter_is_the_last_to_end_before_the_result_appeared():
    assert ec._quarter_end(datetime.date(2026, 10, 25)) == datetime.date(2026, 9, 30)
    assert ec._quarter_end(datetime.date(2026, 2, 3)) == datetime.date(2025, 12, 31)
    assert ec._quarter_end(datetime.date(2026, 5, 20)) == datetime.date(2026, 3, 31)
    assert ec._quarter_end(datetime.date(2026, 3, 31)) == datetime.date(2025, 12, 31)


def test_the_scorecard_leads_with_a_year_earlier():
    new_sales = HAL_SALES[1:] + [7100.0]
    stock = _stock(
        "HAL",
        new_sales,
        eps=[21.53, 59.46, 20.69, 24.96, 27.91, 62.74, 23.77, 30.0],
        opm=[24.0, 36.0, 28.0, 25.5],
        profit=2000.0,
        name="Hindustan Aeronautics",
    )
    held = {
        "name": "Hindustan Aeronautics",
        "sector": "aerospace_defence",
        "stock": stock,
    }
    c = ec.scorecard("HAL", held, datetime.date(2026, 10, 30))
    assert c["quarter"] == "Sep 2026"
    # Year-ago quarter is four back: 6629.
    assert c["sales_yoy_pct"] == round((7100 / 6629 - 1) * 100, 1)
    assert c["sales_qoq_pct"] == round((7100 / 5515 - 1) * 100, 1)
    # 13,700, 7,699 and 13,942 were higher.
    assert c["sales_rank"] == 4
    assert c["eps_yoy_pct"] == round((30.0 / 24.96 - 1) * 100, 1)
    assert c["opm_change_pp"] == -2.5
    assert c["summary"].startswith(
        "Sales ₹7,100 Cr, +7.1% on a year ago (+28.7% on the quarter before)"
    )
    assert "operating margin 26%, -2.5 pts on the quarter before" in c["summary"]


def test_a_loss_a_year_ago_is_said_rather_than_given_a_percentage():
    stock = _stock("BEL", [1, 2, 3, 4, 5.0], eps=[-1.0, 1, 1, 1, 2.0])
    held = {"name": "BEL", "sector": "x", "stock": stock}
    c = ec.scorecard("BEL", held, TODAY)
    assert c["eps_yoy_pct"] is None and c["eps_year_ago"] == -1.0
    assert "EPS 2.00 against -1.00 a year ago" in c["summary"]
    assert "the highest of 5 quarters" in c["summary"]


def test_results_are_found_between_runs_and_kept_for_a_while():
    first = ec.update_results(WATCHLIST, None, today=TODAY)
    # The first run only records what it saw.
    assert first["scorecards"] == [] and first["seen"]["HAL"]["sales"] == HAL_SALES

    reported = {
        **WATCHLIST,
        "aerospace_defence": [_stock("HAL", HAL_SALES[1:] + [7100.0]), _stock("BEL")],
    }
    later = TODAY + datetime.timedelta(days=20)
    second = ec.update_results(reported, first, today=later)
    assert second["reported_today"] == ["HAL"]
    assert second["scorecards"][0]["detected"] == later.isoformat()

    # Screener failed for HAL the next day: its figures are empty, the series
    # to compare with is kept, and the scorecard stays.
    failed = {**WATCHLIST, "aerospace_defence": [_stock("HAL"), _stock("BEL")]}
    third = ec.update_results(failed, second, today=later + datetime.timedelta(days=1))
    assert third["seen"]["HAL"]["sales"] == HAL_SALES[1:] + [7100.0]
    assert third["reported_today"] == [] and len(third["scorecards"]) == 1

    # Gone after SCORECARD_DAYS.
    old = ec.update_results(
        reported, third, today=later + datetime.timedelta(days=ec.SCORECARD_DAYS + 1)
    )
    assert old["scorecards"] == []


def test_a_holding_that_left_the_watchlist_takes_its_results_with_it():
    prior = {
        "seen": {"OLDCO": {"sales": [1.0, 2.0, 3.0, 4.0]}},
        "scorecards": [{"ticker": "OLDCO", "detected": TODAY.isoformat()}],
    }
    out = ec.update_results(WATCHLIST, prior, today=TODAY)
    assert "OLDCO" not in out["seen"] and out["scorecards"] == []


# --- where it shows ---------------------------------------------------------


def test_since_last_run_lists_results_and_new_dates():
    from analysis.changes import build_changes

    data = {
        "results": {
            "reported_today": ["HAL"],
            "scorecards": [
                {"ticker": "HAL", "quarter": "Sep 2026", "summary": "Sales up."}
            ],
        },
        "event_calendar": {
            "upcoming": [
                {
                    "ticker": "BEL",
                    "date": "2026-10-20",
                    "kind": "results",
                    "source": "NSE filing",
                },
                {"ticker": "ITC", "date": "2026-11-05", "kind": "dividend"},
            ]
        },
    }
    prior = {"event_calendar": {"upcoming": []}}
    items = build_changes(data, prior)["items"]["results"]
    assert [(i["ticker"], i["text"]) for i in items] == [
        ("HAL", "reported the Sep 2026 quarter"),
        ("BEL", "results due 2026-10-20"),
    ]
    # Dates are only new against a run that had a calendar.
    assert len(build_changes(data, {"x": 1})["items"]["results"]) == 1


def test_the_email_lists_results_then_the_week_ahead():
    from emails.mailer import _build_calendar_html

    calendar = {
        "as_of": "2026-10-10",
        "ahead_days": 45,
        "upcoming": [
            {
                "ticker": "HAL",
                "date": "2026-10-12",
                "kind": "results",
                "title": "Board meeting: Financial Results",
            },
            {
                "ticker": "BEL",
                "date": "2026-10-30",
                "kind": "results",
                "title": "Board meeting",
            },
        ],
        "macro": [
            {"date": "2026-10-14", "kind": "macro", "title": "RBI policy decision"}
        ],
    }
    results = {
        "reported_today": ["ITC"],
        "scorecards": [
            {"ticker": "ITC", "quarter": "Sep 2026", "summary": "Sales ₹20,000 Cr."}
        ],
    }
    html = _build_calendar_html(calendar, results)
    assert "Reported since the last run (1)" in html and "Sales ₹20,000 Cr." in html
    assert "Mon 12 Oct" in html and "RBI policy decision" in html
    # Beyond the week: on the dashboard, not here.
    assert "2026-10-30" not in html and "Board meeting</li>" not in html
    assert "#/calendar" in html
    assert _build_calendar_html({"as_of": "2026-10-10", "upcoming": []}, {}) == ""


def test_the_comparison_series_stays_out_of_the_page():
    from dashboard.payload import build_display_payload

    out = build_display_payload({"results": {"seen": {"HAL": [1.0]}, "scorecards": []}})
    assert out["results"] == {"scorecards": []}


def test_eps_that_did_not_move_with_sales_is_left_out():
    eps = [22.59, 21.53, 59.46, 20.69, 24.96, 27.91, 62.74, 23.77]
    before = {**WATCHLIST, "aerospace_defence": [_stock("HAL", HAL_SALES, eps=eps)]}
    first = ec.update_results(before, None, today=TODAY)
    after = {
        **WATCHLIST,
        "aerospace_defence": [_stock("HAL", HAL_SALES[1:] + [7100.0], eps=eps)],
    }
    (card,) = ec.update_results(after, first, today=TODAY)["scorecards"]
    assert "eps" not in card and "EPS" not in card["summary"]
    moved = {
        **WATCHLIST,
        "aerospace_defence": [
            _stock("HAL", HAL_SALES[1:] + [7100.0], eps=eps[1:] + [30.0])
        ],
    }
    (card,) = ec.update_results(moved, first, today=TODAY)["scorecards"]
    assert card["eps"] == 30.0


def test_neither_step_can_break_the_run():
    c = ec.build_calendar({"x": "not a list"}, {"events": "nonsense"}, 5, today=TODAY)
    assert c["upcoming"] == [] and c["sources"]["filings"] == 0
    prior = {"seen": {"HAL": {"sales": HAL_SALES}}, "scorecards": [{"ticker": "HAL"}]}
    with patch.object(ec, "_held", side_effect=RuntimeError("boom")):
        r = ec.update_results(WATCHLIST, prior, today=TODAY)
        c = ec.build_calendar(WATCHLIST, today=TODAY)
    assert r["seen"] == prior["seen"] and r["scorecards"] == prior["scorecards"]
    assert r["error"] == "RuntimeError('boom')" and c["error"] == "RuntimeError('boom')"
