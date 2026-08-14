"""Corporate announcements from NSE's own disclosure API — the primary source.

scraper.fetch_exchange_filings_async has never read a filing. It searches
Google News for articles *about* filings, which means the pipeline learns
what a journalist chose to write up, a day late, with the company name
recovered by fuzzy title matching. This reads the disclosure feed the
exchange itself publishes: every announcement, keyed by the exact SYMBOL our
watchlist already uses, with the PDF attachment the company filed.

WHY THIS FILE IS SO DEFENSIVE

NSE fronts its site with bot protection, and cloud egress is its least
trusted traffic. It does not fail cleanly:

  * the API answers an un-cookied request with 401/403, so the session must
    be established through the HTML site first, exactly as a browser does;
  * when the bot filter trips it serves an HTML challenge page with HTTP
    200, so status alone proves nothing and a naive json() call dies on
    "Expecting value: line 1 column 1" — a parse error that reads like a
    code bug and is actually a network verdict;
  * the JSON schema is undocumented and its field names have moved before.

So every layer is checked separately and each failure names itself. And the
whole thing is wrapped by fetch_filings(), which cannot raise: NSE is an
upgrade to the filings section, never a precondition for the briefing
running.

MEASURED from a GitHub Actions runner, 14 Aug 2026
(scripts/probe_nse_announcements.py, re-run it before trusting this):

  The handshake works and NSE serves us. It set AKA_A2, _abck and bm_sz —
  Akamai bot-manager cookies — and the API then answered HTTP 200 with
  Content-Type: application/json and 44,674 bytes for a single day of
  equity announcements. The note in providers/isin_master.py that "NSE's
  site 403s GitHub runners" holds for per-stock page scraping, not for this
  endpoint reached through a cookie handshake.

  The first probe still failed, and instructively: BROWSER_HEADERS asked for
  "gzip, deflate, br", NSE honoured the br, and urllib3 cannot decode Brotli
  unless the brotli package is installed. Content-type validation passed —
  it really was JSON — and the schema layer then reported "not valid JSON",
  blaming the parser for a header we sent. Hence no Accept-Encoding here at
  all, and a schema error that names the Content-Encoding.

  Shape, once readable: a bare list (no envelope), 520 records and 361 KB for
  one day. Fields:

    an_dt attFileSize attchmntFile attchmntText bflag csvName desc difference
    dt exchdisstime fileSize hasXbrl old_new orgid seq_id smIndustry sm_isin
    sm_name sort_date symbol

  Two of those are traps. ``desc`` is a coarse CATEGORY ("Updates"), not a
  subject — the readable sentence is in ``attchmntText``, so that is read
  first. And 520 records into a ten-row section means ordering decides
  everything: holdings are sorted ahead of the rest, or the section fills
  with whoever filed earliest.
"""

import datetime
import random
import time

import requests

from logger import log
from models.core import FilingEvent
from utils import TransientNetworkError, retry_network

BASE_URL = "https://www.nseindia.com"

# The handshake path. Hitting the API cold yields 401/403 because the oscar
# and nsit cookies are only minted by the HTML site; requesting the
# announcements page too (not just the home page) is what a real reader's
# browser does before the XHR fires, and it is cheap insurance.
HOME_URL = f"{BASE_URL}/"
REFERER_PAGE = f"{BASE_URL}/companies-listing/corporate-filings-announcements"
API_URL = f"{BASE_URL}/api/corporate-announcements"

# NSE's own announcements page sends index=equities for the equity market.
# "corporate" is the section name in the site's navigation, not a value this
# endpoint accepts, and passing it returns an empty result rather than an
# error — a silent miss, which is the worst kind.
DEFAULT_INDEX = "equities"

# A full desktop Chrome header set. The point is not disguise — it is that
# NSE's edge rejects requests missing the headers every browser sends, and a
# bare python-requests fingerprint is refused outright.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en-GB;q=0.9,en;q=0.8",
    # NO Accept-Encoding. requests sets it from what urllib3 can actually
    # decode, and overriding it is how the first CI probe broke: this header
    # read "gzip, deflate, br", NSE honoured the br, and urllib3 handed back
    # 44 KB of undecodable Brotli. Content-type said application/json and was
    # telling the truth, so the failure surfaced as "not valid JSON" — a
    # parse error blamed on the parser, from a header we sent. Never
    # advertise an encoding this client cannot decode.
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

# The XHR announces itself differently from a page load: JSON, same-origin,
# and refered from the page a reader would be looking at.
API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": REFERER_PAGE,
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# Human-paced. Two requests fired back to back from a datacentre IP is the
# signature rate limiters look for, and the whole fetch happens once per run
# so a few seconds costs nothing.
MIN_PAUSE_S = 2.0
MAX_PAUSE_S = 5.0

REQUEST_TIMEOUT_S = 20

# Retried by the exchange's own admission that it is having a moment.
_TRANSIENT_STATUSES = (408, 429, 500, 502, 503, 504)
# Not transient — the session is wrong, and only a fresh handshake can fix it.
_AUTH_STATUSES = (401, 403)


class NSEAnnouncementsError(Exception):
    """Base for every way this provider can decide it has no usable data."""


class NSEBlockedError(NSEAnnouncementsError):
    """NSE refused us. Carries what to check, because from a CI log this is
    indistinguishable from a code fault otherwise."""


class NSEContentTypeError(NSEAnnouncementsError):
    """Served something other than JSON — a bot-challenge page, typically,
    delivered with HTTP 200. Raised BEFORE any parse is attempted."""


class NSESchemaError(NSEAnnouncementsError):
    """Parsed as JSON but is not the shape this provider was written against."""


def _polite_pause():
    """Random, not fixed: a constant interval is itself a fingerprint."""
    time.sleep(random.uniform(MIN_PAUSE_S, MAX_PAUSE_S))


def build_session():
    """A session, because the cookies NSE mints must persist across requests.

    Kept separate from the handshake so tests can inject a fake.
    """
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    return session


def handshake(session):
    """Harvest the cookies the API requires by visiting the HTML site first.

    Returns True when the exchange gave us cookies. A handshake that returns
    200 but sets nothing means the edge served a challenge page; the caller
    is told so it can report that specifically instead of blaming the API.
    """
    for url in (HOME_URL, REFERER_PAGE):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT_S)
            log.debug(f"NSE handshake {url} -> {response.status_code}")
        except requests.RequestException as e:
            log.warning(f"NSE handshake failed at {url}: {type(e).__name__}: {e}")
            return False
        _polite_pause()

    if not session.cookies:
        log.warning(
            "NSE handshake returned no cookies — the edge served a challenge "
            "page rather than the site."
        )
        return False
    return True


def _validate_http(response):
    """Status first: an auth refusal and a rate limit need opposite reactions."""
    status = response.status_code
    if status in _AUTH_STATUSES:
        raise NSEBlockedError(
            f"NSE returned HTTP {status} for {response.url}. This is the bot "
            "filter, not a bad query. Check, in order: (1) the handshake ran "
            "and cookies were set, (2) the Referer is the announcements page, "
            "(3) whether this IP is a cloud range NSE refuses outright — "
            "GitHub-hosted runners have been blocked before, in which case no "
            "amount of header work will help and the data needs another source."
        )
    if status in _TRANSIENT_STATUSES:
        # Handed to retry_network, which owns the exponential backoff.
        raise TransientNetworkError(f"HTTP {status} for {response.url}")
    if status != 200:
        raise NSEAnnouncementsError(f"NSE returned HTTP {status} for {response.url}")


def _validate_content_type(response):
    """The check that matters most: a block arrives as HTML with a 200 on it.

    Stopping here means the log says "served text/html" instead of a
    JSONDecodeError pointing at column 1, which has sent people looking for a
    parser bug that was never there.
    """
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "application/json" not in content_type:
        body = (response.text or "")[:200].replace("\n", " ")
        raise NSEContentTypeError(
            f"Expected application/json, got {content_type or 'no Content-Type'} "
            f"(HTTP {response.status_code}). First 200 bytes: {body!r}"
        )


def _validate_schema(response):
    """Parse, then confirm the shape before anything downstream trusts it."""
    try:
        payload = response.json()
    except ValueError as e:  # json.JSONDecodeError subclasses ValueError
        # Name the encoding. When this fired in CI the body was Brotli we had
        # asked for and could not decode, and the bare message ("Expecting
        # value: line 1 column 1") pointed at the parser instead of at the
        # request headers. Anything undecodable here should say what arrived.
        encoding = response.headers.get("Content-Encoding") or "none"
        head = repr((response.text or "")[:80])
        raise NSESchemaError(
            f"Content-Type claimed JSON but the body did not parse: {e} "
            f"(Content-Encoding: {encoding}, first bytes: {head}). If the "
            "encoding is one this client cannot decode, that is the bug — "
            "check Accept-Encoding, not the parser."
        ) from e

    # NSE has served both a bare list and a {"data": [...]} envelope for this
    # endpoint at different times. Accept either rather than break on a
    # wrapper change.
    if isinstance(payload, dict):
        rows = payload.get("data", payload.get("rows", []))
    elif isinstance(payload, list):
        rows = payload
    else:
        raise NSESchemaError(f"Expected a dict or list, got {type(payload).__name__}")

    if not isinstance(rows, list):
        raise NSESchemaError(f"Expected a list of records, got {type(rows).__name__}")
    return rows


# The API is undocumented and its keys have moved. Each logical field lists
# every spelling seen in the wild, most recent first; reading through aliases
# means a rename degrades one field instead of emptying the feed.
_FIELD_ALIASES = {
    "symbol": ("symbol", "SYMBOL", "sym"),
    "company": ("sm_name", "companyName", "comp", "company"),
    # attchmntText FIRST, and this order is load-bearing. Measured: desc is a
    # coarse category ("Updates"), not a subject line — the sentence a reader
    # needs ("... has informed the Exchange regarding 'quarterly financial
    # results of 30062026'") is in attchmntText. Reading desc first rendered
    # every filing as "Updates", which also collapsed the feed, since filings
    # are deduped by their text.
    "subject": ("attchmntText", "desc", "subject", "descriptor"),
    "date": ("an_dt", "an_date", "exchdisstime", "sort_date", "dt"),
    "attachment": ("attchmntFile", "attachment", "attchmntfile", "fileName"),
    # NSE's own sector label. Better than the "Corporate" placeholder for a
    # company we do not hold, and it is the exchange's classification rather
    # than one we inferred.
    "industry": ("smIndustry", "industry"),
}

# attchmntText runs long on occasion. Trimmed for the table cell it renders
# into, with an ellipsis so a cut is visible as a cut.
_MAX_SUBJECT_CHARS = 240


def _first_present(record, field):
    """Safe .get() across every known alias; '' when the field is absent."""
    for key in _FIELD_ALIASES[field]:
        value = record.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _parse_date(raw):
    """NSE stamps '14-Aug-2026 17:30:00'. Normalised to the '%d %b %Y' the
    rest of the pipeline renders, and returned verbatim when unrecognised —
    an odd-looking date is information; a fabricated one is not."""
    if not raw:
        return ""
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(raw, fmt).strftime("%d %b %Y")
        except ValueError:
            continue
    return raw


def normalize(record, symbol_index=None):
    """One raw announcement -> the FilingEvent shape the pipeline already
    renders. Returns None for anything without a symbol and a subject, since
    a filing that identifies neither the company nor the event is noise.

    ``symbol_index`` maps SYMBOL -> (display name, sector) from the watchlist.
    An announcement from a company we do not hold is still returned, labelled
    'Corporate' — the competitive-intel pass reads filings from peers too.
    """
    if not isinstance(record, dict):
        return None

    symbol = _first_present(record, "symbol").upper()
    subject = _first_present(record, "subject")
    if not symbol or not subject:
        return None
    if len(subject) > _MAX_SUBJECT_CHARS:
        subject = subject[: _MAX_SUBJECT_CHARS - 1].rstrip() + "…"

    # A holding keeps OUR sector, so the filings table agrees with the rest of
    # the dashboard. Anything else falls back to NSE's label, then the
    # placeholder.
    default_industry = _first_present(record, "industry") or "Corporate"
    name, industry = (symbol_index or {}).get(symbol, ("", default_industry))

    attachment = _first_present(record, "attachment")
    return FilingEvent(
        company=name or _first_present(record, "company") or symbol,
        industry=industry,
        filing=subject,
        date=_parse_date(_first_present(record, "date")),
        source="NSE",
        # Falls back to the announcements page rather than an empty href: the
        # dashboard renders this as a "View filing" link either way.
        link=attachment or REFERER_PAGE,
    ).model_dump()


@retry_network(max_retries=3, base_delay=2.0)
def _get_announcements(session, params):
    """The API call itself, with validation. Backoff belongs to the decorator
    — it already distinguishes transient failures from real ones, and a second
    retry implementation here would fight it."""
    response = session.get(
        API_URL, params=params, headers=API_HEADERS, timeout=REQUEST_TIMEOUT_S
    )
    _validate_http(response)
    _validate_content_type(response)
    return _validate_schema(response)


def fetch_announcements(
    session=None, index=DEFAULT_INDEX, from_date=None, to_date=None, handshakes=2
):
    """Raw announcement records for a date window. Raises on failure.

    Defaults to today only, which is what a daily briefing wants. Retries the
    whole handshake-then-call sequence, because the common failure is an
    expired session rather than a dead endpoint, and only a fresh handshake
    fixes that — the transport-level retry inside _get_announcements cannot.
    """
    today = datetime.date.today()
    from_date = from_date or today
    to_date = to_date or today
    params = {
        "index": index,
        "from_date": from_date.strftime("%d-%m-%Y"),
        "to_date": to_date.strftime("%d-%m-%Y"),
    }

    owns_session = session is None
    last_error = NSEAnnouncementsError("No attempt was made (handshakes < 1).")
    try:
        for attempt in range(1, handshakes + 1):
            if session is None:
                session = build_session()
            try:
                if not handshake(session):
                    raise NSEBlockedError(
                        "NSE handshake did not yield cookies; the API call "
                        "would be refused. See the handshake warning above."
                    )
                _polite_pause()
                return _get_announcements(session, params)
            except (NSEBlockedError, NSEContentTypeError) as e:
                # Both mean "this session is not trusted". A fresh one is the
                # only move that can change the answer; a schema error, by
                # contrast, would repeat forever and is left to propagate.
                last_error = e
                log.warning(
                    f"NSE announcements attempt {attempt}/{handshakes} refused: "
                    f"{type(e).__name__}: {str(e)[:200]}"
                )
                if owns_session:
                    session.close()
                    session = None
                if attempt < handshakes:
                    _polite_pause()
        raise last_error
    finally:
        # One exit point for the socket, whether we returned data, gave up, or
        # raised. Sessions we were handed are the caller's to close.
        if owns_session and session is not None:
            session.close()


def fetch_filings(watchlist=None, index=DEFAULT_INDEX, from_date=None, to_date=None):
    """Announcements as FilingEvent dicts. NEVER raises.

    This is the pipeline-facing entry point. NSE improves the filings
    section; it must not be able to take the briefing down, so every failure
    is logged with its specific cause and returns an empty list, leaving the
    existing news-derived filings to serve alone.
    """
    symbol_index = build_symbol_index(watchlist)
    try:
        raw = fetch_announcements(index=index, from_date=from_date, to_date=to_date)
    except NSEAnnouncementsError as e:
        log.warning(f"NSE announcements unavailable ({type(e).__name__}): {e}")
        return []
    except Exception as e:  # noqa: BLE001 - a provider must not end the run
        log.warning(
            f"NSE announcements failed unexpectedly ({type(e).__name__}): "
            f"{str(e)[:200]}"
        )
        return []

    # Holdings first. A full trading day is ~520 announcements and the filings
    # section shows ten, so insertion order would spend every slot on whichever
    # companies happened to file first — quite possibly none of ours. Relative
    # order is preserved within each group, so NSE's own recency ranking still
    # decides who leads.
    held, others = [], []
    for record in raw:
        normalized = normalize(record, symbol_index)
        if not normalized:
            continue
        symbol = _first_present(record, "symbol").upper()
        (held if symbol in symbol_index else others).append(normalized)

    log.info(
        f"NSE announcements: {len(raw)} published, {len(held) + len(others)} "
        f"usable, {len(held)} from watchlist holdings."
    )
    return held + others


def build_symbol_index(watchlist):
    """SYMBOL -> (display name, sector). NSE keys announcements by the same
    symbol our watchlist uses, so holdings are matched exactly rather than by
    the fuzzy title matching the news-derived path has to fall back on."""
    index = {}
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            ticker = str(stock.get("ticker") or "").upper()
            if ticker:
                index[ticker] = (stock.get("name") or ticker, sector)
    return index
