"""Publishers' own markets feeds: each article's direct link and its summary.

WHY. Every other news item the pipeline collects comes through Google News
search. Its links lead to the article only through the URL decoding this
project does not do, and its summaries repeat the headline. A brokerage's
call is a headline; why it made the call is in the article. Three publishers
serve their markets feeds, with a summary of each article and a direct link
to it, to the runner (the probe-upstream workflow's publisher-news source,
28 Oct): Economic Times, Livemint and Moneycontrol. Business Standard
refused (403) and is not asked.

Each feed is read only where the publisher's robots.txt allows it, with a
user agent that says who is asking. A refusal is logged and not asked again
until the next run; a server error or a timeout is retried as every other
fetch is (utils.fetch_text_async), since a day's items not read are mostly
gone from the feed by the next run. An item is kept when its headline names
a holding, attributed as the other feeds are
(analysis.parsing.title_matches_company).
"""

import asyncio
import html
import re
import unicodedata
import urllib.robotparser
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import feedparser
from bs4 import BeautifulSoup

from analysis.parsing import title_matches_company
from logger import log

FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Livemint": "https://www.livemint.com/rss/markets",
    "Moneycontrol": "https://www.moneycontrol.com/rss/buzzingstocks.xml",
}
# Said plainly: who is asking and where to find them.
USER_AGENT = (
    "india-policy-tracker/1.0 (+https://github.com/karthik7899/india-policy-tracker)"
)
TIMEOUT_S = 20
# A summary is the article's opening, often the reason behind a headline's
# call ("prompted brokerages such as Kotak … to downgrade the stock"). Enough
# for that, not the article.
SUMMARY_CHARS = 600
# Items kept across runs, newest first. The three feeds hold about 100
# items between them at a time (50, 35 and 15 on 28 Oct) and only those
# naming a holding are kept, so 400 is weeks of them: more than the fifteen
# newest a holding's thesis check reads (thesis_check.MAX_PER_HOLDING),
# while history.json, committed every run, does not carry a summary for
# every item of coverage's 120 days.
KEPT = 400

# Moneycontrol writes "day#39;s high" for "day's high": a character
# reference that has lost its ampersand (probe, 28 Oct). Put back only where
# it stands for punctuation, which is all a headline writes that way, so a
# Google News copy of the same story is recognised as one. The ampersand is
# optional because html.unescape decodes once, and "&amp;#39;" is left
# "&#39;".
_LOST_AMPERSAND = re.compile(r"&?#(\d{2,4});")


def _text(raw: Any) -> str:
    """Markup stripped, character references decoded, whitespace collapsed."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(raw or "")))

    def put_back(match: "re.Match[str]") -> str:
        char = chr(int(match.group(1)))
        return char if unicodedata.category(char).startswith("P") else match[0]

    return " ".join(_LOST_AMPERSAND.sub(put_back, text).split())


def robots_rules(status: int, text: str) -> urllib.robotparser.RobotFileParser:
    """A robots.txt response read as urllib.robotparser.read reads it: 401 or
    403 keeps everything out, another 4xx (no file) lets everything in, and a
    server error leaves the rules unread, which keeps everything out."""
    rules = urllib.robotparser.RobotFileParser()
    if status in (401, 403):
        rules.disallow_all = True
    elif 400 <= status < 500:
        rules.allow_all = True
    elif status < 400:
        rules.parse(text.splitlines())
    return rules


def _holdings(watchlist: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    return [
        (str(s["ticker"]).upper(), s.get("name") or "", sector)
        for sector, stocks in (watchlist or {}).items()
        if sector != "macro_indicators"
        for s in stocks or []
        if isinstance(s, dict) and s.get("ticker")
    ]


def items_from_feed(
    text: str, publisher: str, holdings: List[Tuple[str, str, str]]
) -> List[Dict[str, Any]]:
    """The feed's items whose headline names a holding, with their summary
    and the article's own link (``article_url``)."""
    out = []
    for entry in feedparser.parse(text).entries:
        title = _text(entry.get("title"))
        link = str(entry.get("link") or "").strip()
        if not title or not link:
            continue
        match = next(
            (
                (name, sector)
                for ticker, name, sector in holdings
                if title_matches_company(title, ticker, name)
            ),
            None,
        )
        if match is None:
            continue
        summary = _text(entry.get("summary"))
        out.append(
            {
                "company": match[0],
                "industry": match[1],
                "title": title,
                "link": link,
                "article_url": link,
                "date": entry.get("published") or entry.get("updated") or "",
                "source": publisher,
                # A summary that only repeats the headline says nothing more.
                **(
                    {"summary": summary[:SUMMARY_CHARS]}
                    if summary and summary != title
                    else {}
                ),
            }
        )
    return out


async def _read_feed(
    session, publisher: str, url: str, holdings: List[Tuple[str, str, str]]
) -> Optional[List[Dict[str, Any]]]:
    """One publisher's items, or None where its feed was not read."""
    from utils import fetch_text_async

    headers = {"User-Agent": USER_AGENT}
    try:
        status, text = await fetch_text_async(
            session,
            f"https://{urlparse(url).netloc}/robots.txt",
            headers=headers,
            timeout=TIMEOUT_S,
        )
        rules = robots_rules(status, text)
    except Exception as e:  # noqa: BLE001 - unread rules keep the feed out
        log.info(f"Publisher news: {publisher}: robots.txt unread ({e!r}).")
        return None
    if not rules.can_fetch(USER_AGENT, url):
        log.info(
            f"Publisher news: {publisher}: robots.txt (HTTP {status}) keeps "
            "the feed out."
        )
        return None
    try:
        status, text = await fetch_text_async(
            session, url, headers=headers, timeout=TIMEOUT_S
        )
    except Exception as e:  # noqa: BLE001 - one feed must not stop the rest
        log.info(f"Publisher news: {publisher}: feed failed ({e!r}).")
        return None
    if status != 200:
        log.info(f"Publisher news: {publisher}: feed answered HTTP {status}.")
        return None
    try:
        return items_from_feed(text, publisher, holdings)
    except Exception as e:  # noqa: BLE001 - an unreadable feed is one not read
        log.info(f"Publisher news: {publisher}: feed unreadable ({e!r}).")
        return None


async def fetch_publisher_news_async(
    session, watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Items naming a holding from each publisher's markets feed. Never
    raises: a feed that refuses or fails is logged and the rest are read."""
    holdings = _holdings(watchlist)
    feeds = await asyncio.gather(
        *(
            _read_feed(session, publisher, url, holdings)
            for publisher, url in FEEDS.items()
        )
    )
    items = [item for feed in feeds if feed is not None for item in feed]
    read = sum(1 for feed in feeds if feed is not None)
    log.info(
        f"Publisher news: {len(items)} item(s) naming a holding from {read} of "
        f"{len(FEEDS)} feed(s)."
    )
    return items


# ---------------------------------------------------------------------------
# an article, for the reasons behind a brokerage's call
# ---------------------------------------------------------------------------

# The paragraphs kept from an article: from the first that names the company,
# which is where a story gives a brokerage's reasons.
ARTICLE_CHARS = 3000
# Shorter ones are captions, bylines and share buttons.
PARAGRAPH_CHARS = 40
# Each publisher's robots.txt, read once a run: (rules, read at all).
_ROBOTS: Dict[str, Tuple[urllib.robotparser.RobotFileParser, bool]] = {}


def article_paragraphs(page: str) -> List[str]:
    """An article page's paragraphs: the story's, without the page's
    navigation, scripts and footer, or its captions."""
    soup = BeautifulSoup(page, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "aside", "footer", "form"]):
        tag.decompose()
    paragraphs = [" ".join(p.get_text(" ").split()) for p in soup.find_all("p")]
    return [p for p in paragraphs if len(p) >= PARAGRAPH_CHARS]


def excerpt(paragraphs: List[str], ticker: str = "", name: str = "") -> str:
    """The paragraphs from the first that names the company, where one does,
    to ARTICLE_CHARS. Moneycontrol's pages open with advertising (probe,
    28 Oct), and a note on five stocks may reach this one only far down."""
    if name:
        first = next(
            (
                i
                for i, p in enumerate(paragraphs)
                if title_matches_company(p, ticker, name)
            ),
            0,
        )
        paragraphs = paragraphs[first:]
    return " ".join(paragraphs)[:ARTICLE_CHARS]


def _robots_for(host: str, get) -> Tuple[urllib.robotparser.RobotFileParser, bool]:
    if host not in _ROBOTS:
        try:
            response = get(
                f"https://{host}/robots.txt",
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT_S,
            )
            _ROBOTS[host] = (
                robots_rules(response.status_code, response.text),
                response.status_code < 500,
            )
        except Exception:  # noqa: BLE001 - unread rules keep every article out
            _ROBOTS[host] = (urllib.robotparser.RobotFileParser(), False)
    return _ROBOTS[host]


def fetch_article(url: str, get=None) -> Tuple[str, str, List[str]]:
    """``(outcome, detail, paragraphs)`` for one article, asked for once, of
    the three publishers' own hosts only, and only where robots.txt allows
    it.

    "ok" carries the article's paragraphs (article_paragraphs), for excerpt
    to cut each holding's part from: a note on several stocks is asked for
    once. "refused" is a publisher's no: robots.txt keeps the article out, it
    answered 4xx, or the page holds no story; "failed" is a request that got
    no page. "waiting" means the article was not asked for, because
    robots.txt could not be read today. Never raises.
    """
    if get is None:
        import requests

        get = requests.get
    parts = urlparse(str(url or ""))
    hosts = {urlparse(feed).netloc for feed in FEEDS.values()}
    if parts.scheme != "https" or parts.netloc not in hosts:
        return "refused", "not a publisher's address", []
    rules, read = _robots_for(parts.netloc, get)
    if not read:
        return "waiting", "robots.txt unread", []
    if not rules.can_fetch(USER_AGENT, url):
        return "refused", "robots.txt", []
    try:
        response = get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S)
    except Exception as e:  # noqa: BLE001 - the one request got no page
        return "failed", type(e).__name__, []
    if response.status_code != 200:
        outcome = "failed" if response.status_code >= 500 else "refused"
        return outcome, f"HTTP {response.status_code}", []
    if "html" not in str(response.headers.get("Content-Type", "")).lower():
        return "refused", "not a page", []
    paragraphs = article_paragraphs(response.text)
    if not paragraphs:
        return "refused", "no story on the page", []
    return "ok", "", paragraphs
