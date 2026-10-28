"""Publishers' own markets feeds (providers/publisher_feeds.py): what is kept
from a feed, when a feed is asked for at all, and where its items go."""

import asyncio
from unittest.mock import MagicMock

import pytest

from analysis.competitive_intel import collect_headlines, collect_sources
from analysis.stock_topics import build_stock_topics
from providers import publisher_feeds as pf
from utils import TransientNetworkError

WATCHLIST = {
    "manufacturing_electronics": [{"ticker": "DIXON", "name": "Dixon Technologies"}],
    "clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}],
    "macro_indicators": [{"ticker": "NIFTY", "name": "Nifty"}],
}
HOLDINGS = pf._holdings(WATCHLIST)

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Markets</title>
<item><title>Dixon Technologies shares jump as Motilal Oswal raises target</title>
<link>https://pub.test/markets/dixon-target.cms</link>
<pubDate>Tue, 27 Oct 2026 09:15:00 +0530</pubDate>
<description><![CDATA[<a href="https://pub.test/markets/dixon-target.cms"><img
src="https://pub.test/i.jpg" /></a><p>The brokerage sees mobile exports &amp;
the display fab lifting earnings.</p>]]></description></item>
<item><title>Gujarat State Petronet falls from day#39;s high as tariff cut triggers
downgrades</title><link>https://pub.test/gspl.html</link>
<pubDate>Tue, 27 Oct 2026 10:00:00 +0530</pubDate>
<description>Brokerages cut their targets.</description></item>
<item><title>Suzlon Energy falls from day#39;s high</title>
<link>https://pub.test/suzlon.html</link>
<pubDate>Tue, 27 Oct 2026 11:00:00 +0530</pubDate>
<description>Suzlon Energy falls from day#39;s high</description></item>
<item><title>Suzlon Energy wins an order, with no link to it</title>
<pubDate>Tue, 27 Oct 2026 12:00:00 +0530</pubDate></item>
</channel></rss>"""


def test_a_feed_keeps_the_items_naming_a_holding_with_their_link_and_summary():
    items = pf.items_from_feed(FEED, "Economic Times", HOLDINGS)
    # Petronet names no holding; the last item has nowhere to read it.
    assert [i["title"] for i in items] == [
        "Dixon Technologies shares jump as Motilal Oswal raises target",
        "Suzlon Energy falls from day's high",
    ]
    dixon, suzlon = items
    assert dixon == {
        "company": "Dixon Technologies",
        "industry": "manufacturing_electronics",
        "title": "Dixon Technologies shares jump as Motilal Oswal raises target",
        "link": "https://pub.test/markets/dixon-target.cms",
        "article_url": "https://pub.test/markets/dixon-target.cms",
        "date": "Tue, 27 Oct 2026 09:15:00 +0530",
        "source": "Economic Times",
        # The markup and the image link are gone, the ampersand decoded.
        "summary": "The brokerage sees mobile exports & the display fab "
        "lifting earnings.",
    }
    # A summary that only repeats the headline is not kept.
    assert "summary" not in suzlon


def test_a_summary_is_the_article_s_opening_not_the_article():
    long = "Suzlon Energy rallies. " + "The brokerage expects more orders. " * 40
    feed = (
        "<rss><channel><item><title>Suzlon Energy rallies</title>"
        f"<link>https://pub.test/s</link><description>{long}</description>"
        "</item></channel></rss>"
    )
    (item,) = pf.items_from_feed(feed, "Livemint", HOLDINGS)
    assert len(item["summary"]) == pf.SUMMARY_CHARS
    assert item["summary"].startswith("Suzlon Energy rallies. The brokerage")


@pytest.mark.parametrize(
    "raw, text",
    [
        # Moneycontrol's references with no ampersand (probe, 28 Oct).
        ("GSPL#39;s financial performance", "GSPL's financial performance"),
        ("a #34;buy#34; call", 'a "buy" call'),
        # Escaped twice: html.unescape takes off one layer.
        ("day&amp;#39;s high", "day's high"),
        ("  Q2 <b>results</b>\n beat  ", "Q2 results beat"),
        # Only punctuation is put back: neither is a lost reference.
        ("Nifty at #10; for a week", "Nifty at #10; for a week"),
        ("up #100; today", "up #100; today"),
    ],
)
def test_a_feed_s_text_is_read_as_its_reader_would(raw, text):
    assert pf._text(raw) == text


URL = "https://pub.test/rss/markets"


@pytest.mark.parametrize(
    "status, robots, allowed",
    [
        (200, "User-agent: *\nDisallow: /rss/\n", False),
        (200, "User-agent: *\nDisallow: /private/\n", True),
        # Rules for this agent by name apply to it, not the ones for anyone.
        (
            200,
            "User-agent: india-policy-tracker\nDisallow: /\n\n"
            "User-agent: *\nAllow: /\n",
            False,
        ),
        (401, "", False),
        (403, "", False),
        # No file: nothing is kept out.
        (404, "", True),
        # A server error leaves the rules unread, and unread keeps all out.
        (501, "", False),
        (503, "", False),
    ],
)
def test_robots_txt_is_read_as_urllib_reads_it(status, robots, allowed):
    assert pf.robots_rules(status, robots).can_fetch(pf.USER_AGENT, URL) is allowed


def _serve(monkeypatch, pages):
    """utils.fetch_text_async answering from ``pages``, by URL: a (status,
    text) pair, or an exception to raise. Returns the requests made."""
    asked = []

    async def fetch(session, url, headers=None, timeout=15):
        asked.append((url, headers))
        answer = pages[url]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr("utils.fetch_text_async", fetch)
    return asked


ET, MINT, MC = (
    pf.FEEDS["Economic Times"],
    pf.FEEDS["Livemint"],
    pf.FEEDS["Moneycontrol"],
)
ET_ROBOTS = "https://economictimes.indiatimes.com/robots.txt"
MINT_ROBOTS = "https://www.livemint.com/robots.txt"
MC_ROBOTS = "https://www.moneycontrol.com/robots.txt"


def test_a_feed_is_asked_for_only_where_robots_txt_allows_it(monkeypatch):
    asked = _serve(
        monkeypatch,
        {
            ET_ROBOTS: (200, "User-agent: *\nDisallow: /markets/rssfeeds/\n"),
            # Still failing after utils' own retries: the rules are unread.
            MINT_ROBOTS: TransientNetworkError(f"HTTP 503 for {MINT_ROBOTS}"),
            MC_ROBOTS: (200, "User-agent: *\nDisallow: /private/\n"),
            MC: (200, FEED),
        },
    )
    items = asyncio.run(pf.fetch_publisher_news_async(MagicMock(), WATCHLIST))
    assert sorted(url for url, _ in asked) == sorted(
        [ET_ROBOTS, MINT_ROBOTS, MC_ROBOTS, MC]
    )
    # Every request says who is asking.
    assert {h["User-Agent"] for _, h in asked} == {pf.USER_AGENT}
    assert [(i["source"], i["company"]) for i in items] == [
        ("Moneycontrol", "Dixon Technologies"),
        ("Moneycontrol", "Suzlon Energy"),
    ]


def test_a_feed_that_fails_or_refuses_leaves_the_others_read(monkeypatch):
    _serve(
        monkeypatch,
        {
            ET_ROBOTS: (200, ""),
            ET: RuntimeError("connection reset"),
            MINT_ROBOTS: (200, ""),
            MINT: (403, "Access Denied"),
            # No robots.txt at all: nothing is kept out.
            MC_ROBOTS: (404, ""),
            MC: (200, FEED),
        },
    )
    items = asyncio.run(pf.fetch_publisher_news_async(MagicMock(), WATCHLIST))
    assert {i["source"] for i in items} == {"Moneycontrol"}
    assert len(items) == 2


def test_publisher_news_is_attributed_like_the_other_feeds():
    """Listed last, so where another feed carried the same headline, its copy
    and citation stand, and the topics view's eight slots are not taken from
    the feeds it showed before."""
    headline = "Suzlon Energy shares rally as brokerage upgrades the stock"
    data = {
        "global_market_news": [{"title": headline, "link": "https://news.test/g"}],
        "publisher_news": [
            {"title": headline, "link": "https://pub.test/a", "source": "Livemint"},
            {
                "title": "Dixon Technologies falls as Jefferies cuts its target",
                "link": "https://pub.test/b",
                "source": "Economic Times",
            },
        ],
    }
    headlines = collect_headlines(data, WATCHLIST)
    assert headlines == [
        headline,
        "Dixon Technologies falls as Jefferies cuts its target",
    ]
    sources = collect_sources(data, WATCHLIST)
    assert sources[headline.lower()]["link"] == "https://news.test/g"
    assert sources[headlines[1].lower()]["link"] == "https://pub.test/b"

    topics = build_stock_topics(data, WATCHLIST)
    assert [t["kind"] for t in topics["SUZLON"]] == ["Global"]
    assert [(t["kind"], t["link"]) for t in topics["DIXON"]] == [
        ("Markets news", "https://pub.test/b")
    ]
