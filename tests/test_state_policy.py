"""State-government policy: the feed, whose measure it is, and where it flows."""

import asyncio
from unittest.mock import MagicMock

import pytest

from analysis.policy_impact import policy_impacts, prune_state_policy, state_of


@pytest.mark.parametrize(
    "headline, state",
    [
        (
            "Gujarat government notifies semiconductor policy with 40% capital subsidy",
            "Gujarat",
        ),
        ("Tamil Nadu's EV policy 2026 offers land at half price", "Tamil Nadu"),
        ("UP cabinet approves data centre policy", "Uttar Pradesh"),
        ("Maha govt clears Rs 50,000 cr investment proposals", "Maharashtra"),
        ("TN govt signs MoU with Foxconn", "Tamil Nadu"),
        ("Karnataka CM unveils aerospace policy", "Karnataka"),
        ("Telangana govt sets up centre of excellence for drones", "Telangana"),
        # A place, not an actor.
        ("Adani Green commissions 1 GW in Khavda, Gujarat", None),
        ("Stocks go up as Karnataka startup raises funds", None),
        # The Centre acting in a state is the Centre's measure.
        ("Centre approves Rs 3,000 crore semiconductor unit in Gujarat", None),
        ("Union Cabinet clears Maharashtra port project", None),
        # Two states' actions are not attributed to either.
        ("Maharashtra, Gujarat governments announce EV incentives", None),
        # Abbreviations are matched in capitals only.
        ("Power stocks gear up; government policy in focus", None),
        ("Govt cuts import duty on solar glass", None),
    ],
)
def test_state_of_reads_whose_measure_it_is(headline, state):
    assert state_of(headline) == state


def test_a_policy_impact_carries_its_state():
    readings = {
        "Gujarat government notifies semiconductor policy": {
            "policy_measure": "incentive_scheme",
            "policy_status": "in_force",
            "sector_effects": [
                {
                    "sector": "semiconductors_equipment",
                    "direction": "tailwind",
                    "because": "semiconductor policy",
                }
            ],
        },
        "Govt cuts import duty on solar glass": {
            "policy_measure": "duty_or_tariff",
            "policy_status": "in_force",
            "sector_effects": [
                {
                    "sector": "clean_energy",
                    "direction": "tailwind",
                    "because": "solar glass",
                }
            ],
        },
    }
    rows = {r["headline"]: r for r in policy_impacts(readings, today="2026-09-26")}
    assert (
        rows["Gujarat government notifies semiconductor policy"]["state"] == "Gujarat"
    )
    assert "state" not in rows["Govt cuts import duty on solar glass"]


def test_the_state_feed_keeps_the_window_newest_first_and_capped(monkeypatch):
    import analysis.policy_impact as pi

    monkeypatch.setattr(pi, "STATE_FEED_CAP", 2)
    items = [
        {"title": "old", "date": "2026-07-01"},
        {"title": "mid", "date": "Wed, 23 Sep 2026 10:00:00 GMT"},
        {"title": "new", "date": "25 Sep 2026"},
        {"title": "newer", "date": "2026-09-26"},
        {"title": "undated", "date": ""},
    ]
    kept = prune_state_policy(items, today="2026-09-26")
    assert [i["title"] for i in kept] == ["newer", "new"]


def test_the_reader_and_coverage_see_the_state_feed():
    from analysis.competitive_intel import collect_headlines, collect_sources
    from analysis.coverage import build_coverage

    item = {
        "title": "AP Government and Suzlon break ground for 1,325 MW wind projects",
        "link": "https://news.test/ap",
        "date": "2026-09-25",
        "source": "Test",
        "feed_state": "Andhra Pradesh",
    }
    data = {"state_policy": [item]}
    watchlist = {"clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    assert item["title"] in collect_headlines(data, watchlist)
    assert (
        collect_sources(data, watchlist)[item["title"].lower()]["link"] == item["link"]
    )
    coverage = build_coverage(data, watchlist)
    assert [c["headline"] for c in coverage["SUZLON"]] == [item["title"]]


RSS = """<rss><channel>
<item><title>Gujarat government unveils solar policy - Times</title>
<link>https://n.test/1</link><pubDate>Thu, 24 Sep 2026 01:00:00 GMT</pubDate>
<source url="x">Times</source></item>
<item><title>Gujarat government unveils solar policy - Mint</title>
<link>https://n.test/2</link><pubDate>Thu, 24 Sep 2026 02:00:00 GMT</pubDate></item>
<item><title>Gujarat government old textile scheme - Old</title>
<link>https://n.test/old</link><pubDate>Mon, 01 Jun 2026 02:00:00 GMT</pubDate></item>
</channel></rss>"""


def test_the_state_feed_tags_where_it_looked_and_survives_a_failed_query(monkeypatch):
    import config
    from scraper import fetch_state_policy_async

    monkeypatch.setattr(
        config,
        "STATE_POLICY_QUERIES",
        {
            "Gujarat": ['"Gujarat government"', '"Gujarat cabinet"'],
            "Odisha": ['"Odisha government"'],
        },
    )
    monkeypatch.setattr(config, "STATE_INDUSTRY_QUERIES", {})
    urls = []

    async def fetch(session, url, **kwargs):
        urls.append(url)
        if "Odisha" in url:
            raise RuntimeError("connection reset")
        return 200, RSS

    monkeypatch.setattr("utils.fetch_text_async", fetch)
    import datetime

    items = asyncio.run(
        fetch_state_policy_async(MagicMock(), today=datetime.date(2026, 9, 26))
    )
    # One simple search per entry, each with the date filter appended.
    assert len(urls) == 3
    assert all("when%3A7d" in u for u in urls)
    assert all("%28" not in u for u in urls)  # no parenthesised OR groups
    # The same story from two outlets, or from both Gujarat searches, is one.
    assert [i["title"] for i in items] == ["Gujarat government unveils solar policy"]
    assert items[0]["feed_state"] == "Gujarat"
    assert items[0]["link"] == "https://n.test/1"
    # Google ignores "when:7d"; a June story must not take a slot.
    assert all("old textile" not in i["title"] for i in items)


INDUSTRY_RSS = """<rss><channel>
<item><title>Tamil Nadu unveils semiconductor policy with 50% capital subsidy - ET</title>
<link>https://n.test/sc</link><pubDate>Thu, 24 Sep 2026 03:00:00 GMT</pubDate>
<source url="x">ET</source></item>
</channel></rss>"""

POLITICS_RSS = (
    "<rss><channel>"
    + "".join(
        f"<item><title>Tamil Nadu government reshuffle story {n} - Daily</title>"
        f"<link>https://n.test/p{n}</link>"
        f"<pubDate>Fri, 25 Sep 2026 0{n}:00:00 GMT</pubDate></item>"
        for n in range(8)
    )
    + "</channel></rss>"
)


def test_industrial_policy_searches_have_slots_of_their_own(monkeypatch):
    """A day of cabinet politics fills a state's six general slots; the
    semiconductor policy still gets in, from its own search."""
    import config
    from scraper import fetch_state_policy_async

    monkeypatch.setattr(
        config, "STATE_POLICY_QUERIES", {"Tamil Nadu": ['"Tamil Nadu government"']}
    )
    monkeypatch.setattr(
        config,
        "STATE_INDUSTRY_QUERIES",
        {"Tamil Nadu": ['"Tamil Nadu" semiconductor policy']},
    )
    urls = []

    async def fetch(session, url, **kwargs):
        urls.append(url)
        return 200, INDUSTRY_RSS if "semiconductor" in url else POLITICS_RSS

    monkeypatch.setattr("utils.fetch_text_async", fetch)
    import datetime

    items = asyncio.run(
        fetch_state_policy_async(MagicMock(), today=datetime.date(2026, 9, 26))
    )
    assert len(urls) == 2
    industry = [i for i in items if i.get("feed_kind") == "industry"]
    assert [i["title"] for i in industry] == [
        "Tamil Nadu unveils semiconductor policy with 50% capital subsidy"
    ]
    assert industry[0]["feed_state"] == "Tamil Nadu"
    assert sum(1 for i in items if "feed_kind" not in i) == 6


def test_the_industry_searches_cover_the_five_states_simply():
    import config

    assert set(config.STATE_INDUSTRY_QUERIES) == {
        "Gujarat",
        "Maharashtra",
        "Tamil Nadu",
        "Karnataka",
        "Telangana",
    }
    for queries in config.STATE_INDUSTRY_QUERIES.values():
        # Short searches: a long ORed one returned mostly old articles.
        assert all(" OR " not in q and "(" not in q for q in queries)


def test_a_measure_says_how_binding_it_is():
    from analysis.policy_impact import policy_impacts

    effect = [{"sector": "semiconductors", "direction": "tailwind", "because": "x"}]
    readings = {
        "Gujarat notifies semiconductor subsidy": {
            "policy_measure": "subsidy_or_funding",
            "policy_status": "in_force",
            "sector_effects": effect,
        },
        "Karnataka cabinet approves data centre incentives": {
            "policy_measure": "incentive_scheme",
            "policy_status": "approved",
            "sector_effects": effect,
        },
        "Telangana proposes EV policy": {
            "policy_measure": "incentive_scheme",
            "policy_status": "proposed",
            "sector_effects": effect,
        },
    }
    rows = {r["headline"]: r["strength"] for r in policy_impacts(readings)}
    assert rows == {
        "Gujarat notifies semiconductor subsidy": "hard",
        "Karnataka cabinet approves data centre incentives": "hard",
        "Telangana proposes EV policy": "proposed",
    }


def test_a_governments_mou_is_a_soft_partnership():
    """12 Oct corpus: the reader recorded no measure for these, so they never
    became policy rows; they were tie-up events."""
    from analysis.policy_impact import government_party, government_partnerships

    events = [
        {
            "headline": "ReNew signs Rs 700 billion MoU with Maharashtra government "
            "to develop green integrated energy projects",
            "event_type": "tie_up",
            "date": "2026-10-10",
            "domains": ["clean_energy"],
            "actors": [],
            "certainty": "announced",
            "link": "https://n.test/renew",
        },
        {
            "headline": "Anant Raj signs MoU with Haryana Govt for data centre park",
            "event_type": "tie_up",
            "date": "2026-10-09",
            "domains": ["data_center_support"],
            "actors": ["ANANTRAJ"],
        },
        # Companies, not a government: a tie-up, not a partnership.
        {
            "headline": "NTPC signs MoU with NHPC, PTC and TCS",
            "event_type": "tie_up",
            "date": "2026-10-09",
        },
        # A government, but an order, not a pact.
        {
            "headline": "BEL bags order from Defence Ministry",
            "event_type": "order_win",
            "date": "2026-10-09",
        },
        # Older than the window.
        {
            "headline": "Gujarat government signs MoU with Tata",
            "event_type": "tie_up",
            "date": "2026-08-01",
        },
    ]
    rows = government_partnerships(events, today="2026-10-12")
    assert [(r["government"], r["strength"], r["tickers"]) for r in rows] == [
        ("Maharashtra", "soft", []),
        ("Haryana", "soft", ["ANANTRAJ"]),
    ]
    assert (
        rows[0]["sectors"] == ["clean_energy"]
        and rows[0]["link"] == "https://n.test/renew"
    )
    # A state is a party even beside the Centre.
    assert (
        government_party("Andhra govt, Centre, AM/NS India sign pact to upgrade ITIs")
        == "Andhra Pradesh"
    )
    assert government_party("Centre signs pact with Micron") == "Centre"
    assert government_party("Ministry of Steel signs MoU with SAIL") == "Government"
    assert government_party("NTPC signs MoU with NHPC") is None


def test_centre_stage_is_not_the_centre():
    from analysis.policy_impact import government_party, state_of

    assert (
        government_party(
            "ARVIND LIMITED IS SET TO TAKE CENTRE STAGE WITH ASHISH N SONI AT "
            "LAKME FASHION WEEK"
        )
        is None
    )
    assert (
        government_party("Semiconductors take centre-stage as Centre signs pact")
        == "Centre"
    )
    assert (
        state_of("Gujarat government takes centre stage with new EV policy")
        == "Gujarat"
    )
