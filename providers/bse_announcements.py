"""Corporate announcements from BSE, the second primary filings source.

The companion to providers/nse_announcements.py. Most holdings are dual
listed, so this is largely a cross-check — but BSE-only listings exist, and a
day when one exchange refuses us is a day the other still reports.

TWO THINGS DIFFER FROM NSE, both measured rather than assumed:

  1. BSE's API does not require the cookie handshake. api.bseindia.com served
     1.75 MB of scrip master to a plain requests call carrying only a UA and
     a Referer (probe runs 1-3). So the handshake here is best-effort: it can
     only help, and a failure must not stop the call the way it rightly does
     on NSE.
  2. BSE keys everything by numeric SCRIP_CD, not by ticker. Our watchlist
     speaks NSE symbols, so holdings are resolved through ISIN — the scrip
     master carries SCRIP_CD and ISIN_NUMBER together, and providers/
     isin_master.py already stamps ISINs on holdings. When that join is
     unavailable the announcements still flow, just labelled "Corporate".

Note what is NOT here: promoter pledge and shareholding. Those live on
www.bseindia.com's HTML pages, which Akamai refuses to any browser we can
drive (see scripts/probe_bse_network.py). This file covers the announcements
feed only, which is on the API host and reachable.

MEASURED from a GitHub Actions runner, 15 Aug 2026
(scripts/probe_bse_announcements.py — re-run it before trusting any of this):

  THE SCRIP MASTER WORKS. 4,975 active equity scrips carrying SCRIP_CD,
  ISIN_NUMBER, Scrip_Name, Issuer_Name, Mktcap and scrip_id. The ISIN join
  this provider needs is therefore real and available.

  ANNOUNCEMENTS RETURNED NOTHING ON THE str* VOCABULARY. Thirteen parameter
  sets across four probe runs — every one answered HTTP 200 with the bare
  JSON string "No Record Found!". Note what that rules out: there was no
  redirect, no cookie rejection and no 403 in any of them. The endpoint
  talks to us; it just does not like the query.

  So this layer now sends a DIFFERENT PARAMETER VOCABULARY —
  scrip_cd / categoryname / type / fdate / tdate — which is the one untested
  dimension left that is not a blind guess at an endpoint name. The str*
  form is kept as a documented fallback so one run measures both.

  Its empty answer is a BARE JSON STRING, not an envelope: an 18-byte body
  parsing to the str "No Record Found!". Guarding only for a dict turned
  that routine reply into a schema error.

  Consequence for the pipeline: this provider is wired in and costs one
  request per run. NSE carries the filings section today. The scrip master
  fetch is deferred until announcements actually return rows, so a dead
  query costs 1.75 MB of nothing.
"""

import datetime

from logger import log
from models.core import FilingEvent
from providers.exchange_api import (
    ExchangeAPIError,
    ExchangeBlockedError,
    ExchangeContentTypeError,
    ExchangeSchemaError,
    build_session,
    first_present,
    parse_json,
    polite_pause,
    rows_from,
    validate_content_type,
    validate_http,
)
from utils import retry_network

API_BASE = "https://api.bseindia.com/BseIndiaAPI/api"
ANNOUNCEMENTS_URL = f"{API_BASE}/AnnGetData/w"
SCRIP_MASTER_URL = f"{API_BASE}/ListofScripData/w"

# The apex host, deliberately: the disclosures frame is served from it and
# the API checks Referer/Origin against it. Requests to the apex are
# redirected to www by BSE itself, which is benign and must NOT be mistaken
# for a firewall intercept — see _validate_redirects.
HOME_URL = "https://bseindia.com/"
# The disclosures landing frame. Handshaking here rather than at the bare
# host establishes the cookie scope the announcements XHR is issued under.
REFERER_PAGE = "https://bseindia.com/corporates/ann.html"

# Attachments come back as a bare filename; this is the directory they live in.
ATTACHMENT_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"

# The API host wants a same-site Referer. Not an auth boundary, just their bot
# filter — stated so a future reader does not conclude the endpoint is broken.
API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    # Referer AND Origin. The API host is a different subdomain from the page
    # the XHR is issued from, so a browser sends both; sending only Referer
    # leaves the request looking unlike anything the site itself makes.
    "Referer": HOME_URL,
    "Origin": "https://bseindia.com",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# Paths BSE bounces unauthenticated or filtered traffic to. Landing on one of
# these means we were intercepted, whatever status code came back.
_INTERCEPT_MARKERS = ("showinterest.aspx", "/members", "login.aspx")

REQUEST_TIMEOUT_S = 20

_BLOCKED_HINT = (
    "Check, in order: (1) the Referer is bseindia.com, (2) the UA is a "
    "browser string, (3) whether this IP is refused outright. Note the API "
    "host has served us without cookies before, so a 403 here is a change."
)


class BSEAnnouncementsError(ExchangeAPIError):
    """Base for every way this provider decides it has no usable data."""


class BSEBlockedError(ExchangeBlockedError, BSEAnnouncementsError):
    """BSE refused us."""


class BSEContentTypeError(ExchangeContentTypeError, BSEAnnouncementsError):
    """Served something other than JSON."""


class BSESchemaError(ExchangeSchemaError, BSEAnnouncementsError):
    """Parsed, but not the shape written against."""


class BSEFirewallIntercept(BSEBlockedError):
    """We were redirected away from the data endpoint.

    Distinct from a 403: the request was not refused, it was *diverted*, and
    the response body will look like a perfectly valid page from somewhere
    else entirely. Parsing that as data is how a block becomes a silent
    wrong answer rather than a loud failure.
    """


class BSEStructuralError(BSESchemaError):
    """JSON arrived and parsed, but carries no 'Table' payload key."""


# Undocumented and prone to renaming, so every spelling seen is listed.
# HEADLINE before NEWSSUB: NEWSSUB is often the coarse category, the same trap
# NSE's `desc` turned out to be.
_ALIASES = {
    "scrip": ("SCRIP_CD", "scrip_cd", "Scripcode", "scripcode"),
    "company": ("SLONGNAME", "sLongName", "COMPANYNAME", "Scrip_Name"),
    "subject": ("HEADLINE", "NEWSSUB", "MORE", "SUBCATNAME", "CATEGORYNAME"),
    "date": ("NEWS_DT", "News_submission_dt", "DissemDT", "DT_TM"),
    "attachment": ("ATTACHMENTNAME", "Attachmentname", "NSURL"),
    "category": ("CATEGORYNAME", "SUBCATNAME", "ANNOUNCEMENT_TYPE"),
}

# BSE wraps its rows in Table, with a row count alongside in Table1.
_ENVELOPE_KEYS = ("Table", "data", "rows")

# Long headlines trim for the table cell, with an ellipsis so a cut reads as
# a cut.
_MAX_SUBJECT_CHARS = 240


def handshake(session):
    """Establish domain-aware tracking from the disclosures frame itself.

    Points at corporates/ann.html rather than the bare host: that is the page
    the announcements XHR is issued from, so it is the scope any cookie the
    API cares about gets minted under. The apex host is requested first so
    domain-level cookies land before the path-level ones.

    Best-effort by design. Unlike NSE this is not a precondition — the API
    host has served us with no cookies at all — so a failure is logged and
    the call proceeds anyway.
    """
    for url in (HOME_URL, REFERER_PAGE):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT_S)
            log.debug(
                f"BSE handshake {url} -> {response.status_code} "
                f"(landed {response.url})"
            )
            polite_pause()
        except Exception as e:  # noqa: BLE001 - best effort by definition
            log.info(
                f"BSE handshake step {url} skipped ({type(e).__name__}); the "
                "API host has served us without cookies before, so continuing."
            )
    return bool(session.cookies)


def _parse_date(raw):
    """BSE stamps '2026-08-14T15:41:54.000Z' or '14 Aug 2026 15:41:54'.
    Normalised to the '%d %b %Y' the pipeline renders; returned verbatim when
    unrecognised, because an odd date is information and a guessed one is
    not."""
    if not raw:
        return ""
    cleaned = raw.replace("T", " ").split(".")[0].replace("Z", "").strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d %b %Y %H:%M:%S",
        "%d %b %Y",
        "%d-%b-%Y %H:%M:%S",
        "%d/%m/%Y",
    ):
        try:
            return datetime.datetime.strptime(cleaned, fmt).strftime("%d %b %Y")
        except ValueError:
            continue
    return raw


def _attachment_url(name):
    """Attachments arrive as a bare filename; some records already carry a
    full URL. Both must end up as something a reader can click."""
    if not name:
        return REFERER_PAGE
    if name.startswith("http://") or name.startswith("https://"):
        return name
    return ATTACHMENT_BASE + name


def normalize(record, scrip_index=None):
    """One raw announcement -> the FilingEvent shape the pipeline renders.

    ``scrip_index`` maps SCRIP_CD -> (display name, sector). Announcements
    from companies we do not hold are still returned, labelled "Corporate" —
    the competitive-intel pass reads peers' filings too.
    """
    if not isinstance(record, dict):
        return None

    scrip = first_present(record, _ALIASES["scrip"])
    subject = first_present(record, _ALIASES["subject"])
    if not scrip or not subject:
        return None
    if len(subject) > _MAX_SUBJECT_CHARS:
        subject = subject[: _MAX_SUBJECT_CHARS - 1].rstrip() + "…"

    name, industry = (scrip_index or {}).get(scrip, ("", "Corporate"))
    return FilingEvent(
        company=name or first_present(record, _ALIASES["company"]) or f"BSE {scrip}",
        industry=industry,
        filing=subject,
        date=_parse_date(first_present(record, _ALIASES["date"])),
        source="BSE",
        link=_attachment_url(first_present(record, _ALIASES["attachment"])),
    ).model_dump()


def _validate_redirects(response):
    """Catch a diversion, and only a diversion.

    A literal "any redirect is an intercept" rule cannot be used here: we
    address the apex host deliberately, and BSE redirects apex -> www on
    every single request. That hop is benign and firing on it would mean the
    module never completes a call.

    What actually matters is WHERE we landed. A hop onto an interstitial —
    showinterest.aspx, /members, a login page — or off the bseindia.com
    domain entirely means the response body is some other page, and parsing
    it as data turns a block into a silent wrong answer.
    """
    landed = (response.url or "").lower()

    for marker in _INTERCEPT_MARKERS:
        if marker in landed:
            hops = " -> ".join(r.url for r in response.history) or "(none)"
            raise BSEFirewallIntercept(
                f"Redirected to an interstitial: {response.url!r} matches "
                f"{marker!r}. Redirect chain: {hops}. The body is that page, "
                "not announcement data, so it is refused rather than parsed."
            )

    if "bseindia.com" not in landed:
        hops = " -> ".join(r.url for r in response.history) or "(none)"
        raise BSEFirewallIntercept(
            f"Redirected off the BSE domain entirely, to {response.url!r}. "
            f"Redirect chain: {hops}."
        )

    if response.history:
        # Benign, and worth seeing exactly once when diagnosing: the apex to
        # www hop is expected and is not an interception.
        hops = " -> ".join(r.url for r in response.history)
        log.debug(f"BSE redirect (benign, still on-domain): {hops} -> {response.url}")


def _validate_table(payload):
    """The payload contract: a dict carrying 'Table'.

    Three outcomes, deliberately distinguished, because they call for
    different reactions and a single "no data" would hide which one happened:
      * bare string       -> BSE's measured empty answer, a miss, not a fault
      * 'Table' missing   -> structural failure, the contract changed
      * 'Table' empty     -> the query matched nothing
    """
    if isinstance(payload, str):
        log.info(f"BSE data payload empty: {payload[:200]!r} (query matched nothing)")
        return []

    if not isinstance(payload, dict):
        raise BSEStructuralError(
            f"Expected a dict carrying 'Table', got {type(payload).__name__}"
        )

    if "Table" not in payload:
        raise BSEStructuralError(
            "DATA PAYLOAD STRUCTURAL FAILURE: no 'Table' key. Top-level keys "
            f"were {sorted(payload.keys())[:12]}. The response parsed as JSON, "
            "so this is a contract change at BSE, not a transport problem."
        )

    table = payload["Table"]
    if isinstance(table, str):
        log.info(f"BSE data payload empty: Table={table[:200]!r}")
        return []
    if not isinstance(table, list):
        raise BSEStructuralError(
            f"'Table' should hold a list of records, got {type(table).__name__}"
        )
    if not table:
        log.info("BSE data payload structural note: 'Table' present but empty.")
    return table


def _default_rows(payload):
    """Envelope-tolerant record extraction, for endpoints that are not the
    announcements feed. The scrip master returns a BARE LIST, so the strict
    'Table' contract cannot be applied to every call on this host."""
    if isinstance(payload, str):
        log.info(f"BSE returned no records: {payload[:200]!r}")
        return []
    if isinstance(payload, dict) and not any(
        isinstance(payload.get(k), list) for k in _ENVELOPE_KEYS
    ):
        log.info(f"BSE returned no records: {str(payload)[:200]}")
        return []
    return rows_from(payload, envelope_keys=_ENVELOPE_KEYS, exc=BSESchemaError)


@retry_network(max_retries=3, base_delay=2.0)
def _get(session, url, params, validator=None):
    """One validated API call. Backoff belongs to the decorator, which already
    separates transient failures from real ones.

    ``validator`` turns the parsed body into rows. Injected rather than fixed
    because the announcements feed owes us a 'Table' envelope while the scrip
    master answers with a bare list, and holding both to one contract would
    break whichever endpoint lost the argument.
    """
    response = session.get(
        url, params=params, headers=API_HEADERS, timeout=REQUEST_TIMEOUT_S
    )
    # Diversion is checked FIRST. An intercepted response can carry a 200 and
    # a perfectly valid body, so every check after this one would pass while
    # describing the wrong page.
    _validate_redirects(response)
    validate_http(response, blocked_hint=_BLOCKED_HINT, blocked_exc=BSEBlockedError)
    validate_content_type(response, exc=BSEContentTypeError)
    payload = parse_json(response, exc=BSESchemaError)
    return (validator or _default_rows)(payload)


def announcement_params(from_date, to_date, scrip="", category="Select", type_="A"):
    """The disclosure-endpoint vocabulary: scrip_cd / categoryname / type.

    Thirteen attempts on the str* vocabulary below returned "No Record
    Found!" with no redirect and no refusal, which points at the parameter
    NAMES rather than their values — an ASP.NET action binds what it
    recognises and quietly filters on the rest.

    Defaults: all companies, all categories, all update types, today.
    ``categoryname="Result"`` narrows to results; "Select" is the site's
    own all-categories sentinel.
    """
    return {
        "scrip_cd": scrip,
        "categoryname": category,
        "type": type_,
        "fdate": from_date.strftime("%Y%m%d"),
        "tdate": to_date.strftime("%Y%m%d"),
    }


def legacy_announcement_params(from_date, to_date, scrip="", page=1):
    """The str* vocabulary, kept because it is the measured baseline.

    Retained so a single probe run compares both against the same window
    rather than across days — announcement volume varies enough that
    comparing yesterday's result to today's proves nothing.
    """
    return {
        "pageno": str(page),
        "strCat": "-1",
        "strPrevDate": from_date.strftime("%Y%m%d"),
        "strToDate": to_date.strftime("%Y%m%d"),
        "strScrip": scrip,
        "strSearch": "P",
        "strType": "C",
        "subcategory": "-1",
    }


def fetch_announcements(
    session=None, from_date=None, to_date=None, scrip="", params=None
):
    """Raw announcement records for a date window. Raises on failure.

    The 'Table' contract is enforced here specifically — this endpoint is the
    one that owes us that envelope.
    """
    today = datetime.date.today()
    params = params or announcement_params(from_date or today, to_date or today, scrip)

    owns_session = session is None
    session = session or build_session()
    try:
        handshake(session)
        polite_pause()
        return _get(session, ANNOUNCEMENTS_URL, params, validator=_validate_table)
    finally:
        if owns_session:
            session.close()


def build_scrip_index(watchlist, session=None):
    """SCRIP_CD -> (display name, sector) for holdings, joined through ISIN.

    BSE speaks scrip codes and our watchlist speaks NSE symbols; the scrip
    master is the only thing that connects them. Returns an empty index on
    any failure — announcements are still worth having unlabelled, so this
    never raises.
    """
    wanted = {}
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            screener = stock.get("screener") or {}
            isin = screener.get("isin") if isinstance(screener, dict) else None
            if isin:
                wanted[str(isin).upper()] = (
                    stock.get("name") or stock.get("ticker"),
                    sector,
                )
    if not wanted:
        log.info("BSE scrip index skipped: no holding carries an ISIN yet.")
        return {}

    owns_session = session is None
    session = session or build_session()
    try:
        rows = _get(
            session,
            SCRIP_MASTER_URL,
            {
                "Group": "",
                "Scripcode": "",
                "industry": "",
                "segment": "Equity",
                "status": "Active",
            },
        )
    except Exception as e:  # noqa: BLE001 - the index is an enrichment
        log.info(
            f"BSE scrip index unavailable ({type(e).__name__}: {str(e)[:120]}); "
            "announcements will be labelled Corporate."
        )
        return {}
    finally:
        if owns_session:
            session.close()

    index = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        isin = first_present(row, ("ISIN_NUMBER", "isin", "ISIN")).upper()
        code = first_present(row, ("SCRIP_CD", "Scrip_Cd", "scrip_cd"))
        if isin in wanted and code:
            index[code] = wanted[isin]

    log.info(f"BSE scrip index: {len(index)} of {len(wanted)} holdings resolved.")
    return index


def fetch_filings(watchlist=None, from_date=None, to_date=None):
    """Announcements as FilingEvent dicts. NEVER raises.

    The pipeline-facing entry point. BSE improves the filings section; it must
    not be able to take the briefing down, so every failure is logged with its
    cause and returns an empty list.
    """
    session = build_session()
    try:
        # Announcements FIRST, and the scrip master only if there is something
        # to name. That join costs 1.75 MB, and AnnGetData currently answers
        # "No Record Found!" to every parameter set tried (13 across four probe
        # runs), so paying for it up front would buy nothing on most days.
        raw = fetch_announcements(session=session, from_date=from_date, to_date=to_date)
        if not raw:
            log.info("BSE announcements: none returned; skipping the ISIN join.")
            return []
        scrip_index = build_scrip_index(watchlist, session=session)
    except BSEAnnouncementsError as e:
        log.warning(f"BSE announcements unavailable ({type(e).__name__}): {e}")
        return []
    except Exception as e:  # noqa: BLE001 - a provider must not end the run
        log.warning(
            f"BSE announcements failed unexpectedly ({type(e).__name__}): "
            f"{str(e)[:200]}"
        )
        return []
    finally:
        session.close()

    # Holdings first: a full day runs to hundreds of announcements and the
    # filings section shows ten, so source order would spend every slot on
    # whoever filed earliest.
    held, others = [], []
    for record in raw:
        normalized = normalize(record, scrip_index)
        if not normalized:
            continue
        scrip = first_present(record, _ALIASES["scrip"])
        (held if scrip in scrip_index else others).append(normalized)

    log.info(
        f"BSE announcements: {len(raw)} published, {len(held) + len(others)} "
        f"usable, {len(held)} from watchlist holdings."
    )
    return held + others
