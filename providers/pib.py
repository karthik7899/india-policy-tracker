"""PIB's own pages: the list of a day's releases, and a release's text.

Google News is how the PLI scraper hears of a release, but its links lead to
Google's own page and never to pib.gov.in: from a runner on 19 October 2026,
a 584 KB page titled "Google News" that never names the bureau. PIB's RSS
feed is no way round that. Whatever the address asks for, it redirects to the
Hindi feed, and it holds the last 20 releases, a few hours of PIB's day.

What works is PIB's list of its releases, allRel.aspx: an ASP.NET form whose
day menu posts it back to itself. Posted with the day at "All", it lists a
whole month: 953 releases for October 2026 to the 19th, 1,429 for September.
A whole month, because Google dates a PIB page when Google saw it, which can
be weeks after PIB posted it. The list's links carry each release's PRID. The
release page itself is a shell around an iframe, and the shell's sidebar of
other releases is what the parser used to read as company names, so the
iframe's own page is read instead, and only the block that holds the
release's text.
"""

import datetime
import re
import urllib.parse
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from logger import log

# The www host: the bare one redirects, and a redirected POST comes back as
# a GET of today's list.
LIST_URL = "https://www.pib.gov.in/allRel.aspx?reg=3&lang=1"
RELEASE_URL = (
    "https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID={prid}&reg=3&lang=1"
)
# The block that holds a release's own text, spelt as PIB spells it.
BODY_CLASS = "innner-page-main-about-us-content-right-part"

_DAY = "ctl00$ContentPlaceHolder1$ddlday"
_MONTH = "ctl00$ContentPlaceHolder1$ddlMonth"
_YEAR = "ctl00$ContentPlaceHolder1$ddlYear"
_IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
_PRID_RE = re.compile(r"PRID=(\d+)", re.I)
# What Google News appends to a PIB headline.
_SITE_RE = re.compile(
    r"\s+[-–|]\s+(?:press information bureau|(?:www\.)?pib(?:\.gov\.in|\.nic\.in)?)"
    r"\s*$",
    re.I,
)
_POSTED_RE = re.compile(r"Posted On:\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})", re.I)


def form_fields(html):
    """What a browser would post back from the page's form, as it stands."""
    form = BeautifulSoup(html or "", "lxml").find("form")
    if form is None:
        return {}
    fields = {}
    for field in form.find_all(["input", "select"]):
        name = field.get("name")
        kind = (field.get("type") or "").lower()
        if not name or kind in ("image", "submit", "button", "reset"):
            continue
        if kind in ("checkbox", "radio") and not field.has_attr("checked"):
            continue
        if field.name == "select":
            chosen = field.find("option", selected=True) or field.find("option")
            fields[name] = chosen.get("value", "") if chosen else ""
        else:
            fields[name] = field.get("value") or ""
    return fields


def shown_month(fields):
    """The month a page lists in full, read from its own menus, or None
    when it lists a single day or says nothing."""
    try:
        if str(fields[_DAY]) != "0":
            return None
        return datetime.date(int(fields[_YEAR]), int(fields[_MONTH]), 1)
    except (KeyError, TypeError, ValueError):
        return None


def months_to(today, count):
    """The first day of ``today``'s month and of each of the ``count - 1``
    months before it, newest first."""
    months = [today.replace(day=1)]
    while len(months) < count:
        months.append((months[-1] - datetime.timedelta(days=1)).replace(day=1))
    return months


def today_in_india():
    return datetime.datetime.now(_IST).date()


def release_links(html):
    """``(title, prid, link)`` for every release a list page links to."""
    links, seen = [], set()
    for a in BeautifulSoup(html or "", "lxml").find_all("a", href=True):
        match = _PRID_RE.search(a["href"])
        title = a.get_text(" ", strip=True) or a.get("title", "").strip()
        if not match or not title or match.group(1) in seen:
            continue
        seen.add(match.group(1))
        links.append((title, match.group(1), urllib.parse.urljoin(LIST_URL, a["href"])))
    return links


def strip_site(title):
    """A Google News headline without the " - Press Information Bureau"."""
    return _SITE_RE.sub("", str(title or "")).strip()


def title_words(title):
    return re.findall(r"[a-z0-9]+", strip_site(title).lower())


def same_title(a, b):
    """Whether two headlines are one release's, either perhaps cut short.

    Short titles must match whole: "PLI Scheme" begins a dozen releases.
    """
    return same_words(title_words(a), title_words(b))


def same_words(a, b):
    """``same_title`` for titles already split by ``title_words``."""
    short, full = sorted((a, b), key=len)
    if not short or short == full:
        return bool(short)
    n = len(short)
    # A title cut short can end mid-word: "... Bulk Drugs and Medical De".
    return n >= 6 and short[:-1] == full[: n - 1] and full[n - 1].startswith(short[-1])


def ist_day(published):
    """The day in India a feed timestamp falls on, or None.

    PIB files a release under India's date. A release posted at 00:30 in
    Delhi is the previous day in GMT, which is how Google stamps it.
    """
    try:
        when = parsedate_to_datetime(str(published or ""))
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    return when.astimezone(_IST).date()


def release_url(prid):
    return RELEASE_URL.format(prid=prid)


def read_release(html):
    """A release page's title, the day PIB posted it, and the HTML of its text.

    None when the page has no release text, so a page of anything else is
    never read for names.
    """
    body = BeautifulSoup(html or "", "lxml").find("div", class_=BODY_CLASS)
    if body is None:
        return None
    heading = body.find(id="Titleh2")
    posted = body.find(id="PrDateTime")
    day = None
    match = _POSTED_RE.search(posted.get_text(" ", strip=True)) if posted else None
    if match:
        try:
            day = datetime.datetime.strptime(match.group(1), "%d %b %Y").date()
        except ValueError:
            day = None
    return {
        "title": " ".join(heading.get_text(" ").split()) if heading else "",
        "date": day.isoformat() if day else "",
        "html": str(body),
    }


class MonthIndex:
    """PIB's lists of every release in a month, each asked for once a run.

    The list page is fetched once, for its form. Each month is that form
    posted back with the day menu at "All" and the month and year set, as the
    page's own menus would. The first failure stops any further asking, so an
    unreachable site costs one timeout, not one a month.
    """

    def __init__(self, session):
        self.session = session
        self.fields = None
        self.months = {}
        self.read = 0
        self.failed = ""

    async def releases_in(self, first):
        """``release_links`` for the month ``first`` begins, or None if PIB
        did not answer."""
        if first in self.months:
            return self.months[first]
        if self.failed:
            return None
        from utils import fetch_text_async, post_form_async

        try:
            if self.fields is None:
                status, html = await fetch_text_async(
                    self.session, LIST_URL, timeout=20
                )
                if status != 200:
                    return self._stop(f"the list of releases returned HTTP {status}")
                self.fields = form_fields(html)
                if _DAY not in self.fields:
                    return self._stop("the list of releases has no day menu")
            data = dict(self.fields)
            data.update(
                {
                    _DAY: "0",
                    _MONTH: str(first.month),
                    _YEAR: str(first.year),
                    "__EVENTTARGET": _DAY,
                    "__EVENTARGUMENT": "",
                }
            )
            # A month's list is a megabyte or more.
            status, html = await post_form_async(
                self.session, LIST_URL, data, timeout=60
            )
        except Exception as e:
            return self._stop(f"the list of releases failed ({type(e).__name__})")
        if status != 200:
            return self._stop(f"the list of releases returned HTTP {status}")
        if shown_month(form_fields(html)) != first:
            # The page came back with something else: the form no longer
            # does what its menus did, and every other ask would do the same.
            self.months[first] = []
            self._stop(f"the list of releases would not show {first:%B %Y}")
            return []
        self.read += 1
        self.months[first] = release_links(html)
        return self.months[first]

    def _stop(self, why):
        self.failed = why
        log.warning(f"PIB: {why}; no more of its lists asked for this run.")
        return None
