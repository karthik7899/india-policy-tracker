"""Event evidence: the article's date, story grouping, exchange confirmation.

Each test pins a finding from the 2026-09-25 corpus.
"""

import datetime

import pytest

from analysis.event_engine import classify_headlines, refresh_merged_events
from analysis.event_evidence import (
    article_date,
    cluster_stories,
    confirm_with_filings,
    evidence_level,
    prune_filings,
)

TODAY = datetime.date.today().isoformat()
WATCHLIST = {
    "clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}],
    "manufacturing_electronics": [{"ticker": "SYRMA", "name": "Syrma SGS Tech."}],
}


# ---------------------------------------------------------------------------
# dates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Thu, 30 Jul 2026 07:44:28 GMT", "2026-07-30"),
        ("24 Sep 2026", "2026-09-24"),
        ("2026-09-24", "2026-09-24"),
        ("", None),
        ("sometime last week", None),
    ],
)
def test_the_three_date_shapes_the_feeds_use(raw, expected):
    assert article_date(raw) == expected


def test_an_event_is_dated_by_its_article_not_by_the_run():
    """All 120 stored events read "today" while their median age was 56 days."""
    data = {
        "corporate_agreements": [
            {
                "title": "Suzlon wins its maiden 200 MW wind energy order from Ayana",
                "link": "https://x.test/1",
                "date": "Tue, 08 Sep 2026 06:00:00 GMT",
            }
        ]
    }
    (event,) = classify_headlines(data, WATCHLIST)
    assert event["date"] == "2026-09-08"
    assert event["first_seen"] == TODAY


def test_a_stored_event_is_re_dated_and_then_ages_out():
    old = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%d %b %Y")
    headline = "Suzlon wins its maiden 200 MW wind energy order from Ayana"
    stored = {
        "headline": headline,
        "event_type": "order_win",
        "phrase": "wins its maiden 200 mw wind energy order",
        "domains": [],
        "actors": ["SUZLON"],
        "external": [],
        "date": TODAY,  # the old, wrong stamp
    }
    sources = {headline.lower(): {"link": "x", "date": old}}
    assert refresh_merged_events([stored], WATCHLIST, sources=sources) == []


# ---------------------------------------------------------------------------
# stories
# ---------------------------------------------------------------------------


def _event(headline, source, **kw):
    base = {
        "headline": headline,
        "event_type": "tie_up",
        "actors": ["SYRMA"],
        "counterparties": [],
        "date": TODAY,
        "source": source,
    }
    base.update(kw)
    return base


def test_re_reports_of_one_story_are_counted_as_outlets():
    events = [
        _event(
            "Syrma SGS Forms PCB Joint Venture With Kaga Electronics",
            "Equitypandit",
            counterparties=["Kaga Electronics"],
        ),
        _event(
            "Syrma SGS, Kaga Electronics Form ₹250 Million EMS Joint Venture",
            "EFY",
            counterparties=["Kaga Electronics"],
        ),
        _event(
            "Syrma SGS Tech Forms JV With Kaga Electronics India",
            "Equitypandit",
            counterparties=["Kaga Electronics"],
        ),
    ]
    assert cluster_stories(events) == 1
    # Three headlines, two outlets: one site's two versions are one report.
    assert {e["reports"] for e in events} == {2}
    assert evidence_level(events[0]) == "multi-source"


def test_different_deals_of_one_company_stay_apart():
    events = [
        _event(
            "Syrma SGS forms JV with Kaga Electronics",
            "A",
            counterparties=["Kaga Electronics"],
        ),
        _event(
            "Syrma SGS and Elemaster inaugurate joint venture facility",
            "B",
            counterparties=["Elemaster"],
        ),
    ]
    assert cluster_stories(events) == 2
    assert evidence_level(events[0]) == "single report"


def test_the_same_words_a_month_apart_are_two_stories():
    earlier = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    events = [
        _event(
            "Suzlon bags 400 MW wind order from Tata Power",
            "A",
            actors=["SUZLON"],
            event_type="order_win",
        ),
        _event(
            "Suzlon bags 400 MW wind order from Tata Power",
            "B",
            actors=["SUZLON"],
            event_type="order_win",
            date=earlier,
        ),
    ]
    assert cluster_stories(events) == 2


# ---------------------------------------------------------------------------
# exchange confirmation
# ---------------------------------------------------------------------------


def _filing(text, days_from_story=0, ticker="SUZLON", source="NSE"):
    date = (
        datetime.date.today() + datetime.timedelta(days=days_from_story)
    ).isoformat()
    return {
        "ticker": ticker,
        "date": date,
        "text": text,
        "source": source,
        "link": "https://nse.test/f",
    }


def _order():
    return _event(
        "Suzlon wins its maiden 200 MW wind energy order from Ayana",
        "A",
        actors=["SUZLON"],
        event_type="order_win",
    )


def test_the_companys_own_filing_confirms_the_story():
    event = _order()
    n = confirm_with_filings(
        [event],
        [
            _filing(
                "Suzlon Energy Limited has informed the Exchange about Bagging/Receiving of orders/contracts",
                -1,
            )
        ],
    )
    assert n == 1 and evidence_level(event) == "confirmed"
    assert event["confirmation"]["source"] == "NSE"


@pytest.mark.parametrize(
    "filing",
    [
        _filing(
            "Bagging/Receiving of orders/contracts", -1, ticker="SYRMA"
        ),  # another company
        _filing("Resignation of Company Secretary", -1),  # another kind
        _filing("Bagging/Receiving of orders/contracts", -20),  # too early
        _filing("Bagging/Receiving of orders/contracts", 5),  # too late
        _filing(
            "Bagging/Receiving of orders/contracts", -1, source="news"
        ),  # not the exchange
    ],
)
def test_a_filing_confirms_only_the_same_company_kind_and_time(filing):
    event = _order()
    assert confirm_with_filings([event], [filing]) == 0
    assert "confirmation" not in event


def test_old_filings_are_pruned_from_the_record():
    old = (datetime.date.today() - datetime.timedelta(days=40)).isoformat()
    kept = prune_filings([{"date": old}, {"date": TODAY}, {"date": ""}])
    assert kept == [{"date": TODAY}]
