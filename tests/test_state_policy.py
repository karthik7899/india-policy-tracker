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
</channel></rss>"""


def test_the_state_feed_tags_where_it_looked_and_survives_a_failed_query(monkeypatch):
    import config
    from scraper import fetch_state_policy_async

    monkeypatch.setattr(
        config,
        "STATE_POLICY_QUERIES",
        {"Gujarat": '"Gujarat government"', "Odisha": '"Odisha government"'},
    )
    urls = []

    async def fetch(session, url, **kwargs):
        urls.append(url)
        if "Odisha" in url:
            raise RuntimeError("connection reset")
        return 200, RSS

    monkeypatch.setattr("utils.fetch_text_async", fetch)
    items = asyncio.run(fetch_state_policy_async(MagicMock()))
    assert len(urls) == 2
    # The same story from two outlets is one item.
    assert [i["title"] for i in items] == ["Gujarat government unveils solar policy"]
    assert items[0]["feed_state"] == "Gujarat"
    assert items[0]["link"] == "https://n.test/1"
