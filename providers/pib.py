"""PIB's own pages: the list of a day's releases, and a release's text.

Google News is how the PLI scraper hears of a release, but its links lead to
Google's own page and never to pib.gov.in: from a runner on 19 October 2026,
a 584 KB page titled "Google News" that never names the bureau. PIB's RSS
feed is no way round that. Whatever the address asks for, it redirects to the
Hindi feed, and it holds the last 20 releases, a few hours of PIB's day.

What works is PIB's list of every release on a given day, allRel.aspx: an
ASP.NET form that its day menu posts back to itself, here posted with the day
wanted. Its links carry each release's PRID. The release page itself is a
shell around an iframe, and the shell's sidebar of other releases is what the
parser used to read as company names, so the iframe's own page is read
instead, and only the block that holds the release's text.
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


def shown_day(fields):
    """The day the list on a page is for, read from its own day menus."""
    try:
        return datetime.date(int(fields[_YEAR]), int(fields[_MONTH]), int(fields[_DAY]))
    except (KeyError, TypeError, ValueError):
        return None


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
    short, full = sorted((title_words(a), title_words(b)), key=len)
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


class DayIndex:
    """PIB's lists of releases, a day at a time, each asked for once a run.

    The list page is fetched once, for its form and for today's list. Every
    other day is that form posted back with the day, month and year changed,
    which is what the page's own day menu does. The first failure stops any
    further asking, so an unreachable site costs one timeout, not one a day.
    """

    def __init__(self, session):
        self.session = session
        self.fields = None
        self.days = {}
        self.read = 0
        self.failed = ""

    async def releases_on(self, day):
        """``release_links`` for ``day``, or None if PIB did not answer."""
        if day in self.days:
            return self.days[day]
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
                self.read += 1
                self.fields = form_fields(html)
                if _DAY not in self.fields:
                    return self._stop("the list of releases has no day menu")
                today = shown_day(self.fields)
                if today is not None:
                    self.days[today] = release_links(html)
                if day in self.days:
                    return self.days[day]
            data = dict(self.fields)
            data.update(
                {
                    _DAY: str(day.day),
                    _MONTH: str(day.month),
                    _YEAR: str(day.year),
                    "__EVENTTARGET": _DAY,
                    "__EVENTARGUMENT": "",
                }
            )
            status, html = await post_form_async(
                self.session, LIST_URL, data, timeout=30
            )
        except Exception as e:
            return self._stop(f"the list of releases failed ({type(e).__name__})")
        if status != 200:
            return self._stop(f"the list of releases returned HTTP {status}")
        self.read += 1
        if shown_day(form_fields(html)) != day:
            # The page came back with some other day: the form no longer
            # does what its menu did, and every other ask would do the same.
            self.days[day] = []
            self._stop(f"the list of releases would not show {day.isoformat()}")
            return []
        self.days[day] = release_links(html)
        return self.days[day]

    def _stop(self, why):
        self.failed = why
        log.warning(f"PIB: {why}; no more of its lists asked for this run.")
        return None
