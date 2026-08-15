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

MEASURED: see scripts/probe_bse_announcements.py. AnnGetData has answered
"No Record Found!" to every parameter set tried so far, so the parameters
below are the canonical ones the site itself uses and the probe tests a
matrix around them. Re-run it before trusting this.
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

HOME_URL = "https://www.bseindia.com/"
REFERER_PAGE = "https://www.bseindia.com/corporates/ann.html"

# Attachments come back as a bare filename; this is the directory they live in.
ATTACHMENT_BASE = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/"

# The API host wants a same-site Referer. Not an auth boundary, just their bot
# filter — stated so a future reader does not conclude the endpoint is broken.
API_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Referer": HOME_URL,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

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
    """Best-effort cookie harvest. Unlike NSE this is not a precondition —
    the API host has served us with no cookies at all — so a failure is logged
    and the call proceeds anyway."""
    try:
        response = session.get(HOME_URL, timeout=REQUEST_TIMEOUT_S)
        log.debug(f"BSE handshake {HOME_URL} -> {response.status_code}")
        polite_pause()
        return bool(session.cookies)
    except Exception as e:  # noqa: BLE001 - best effort by definition
        log.info(
            f"BSE handshake skipped ({type(e).__name__}); the API host has "
            "served us without cookies before, so continuing."
        )
        return False


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


@retry_network(max_retries=3, base_delay=2.0)
def _get(session, url, params):
    """One validated API call. Backoff belongs to the decorator, which already
    separates transient failures from real ones."""
    response = session.get(
        url, params=params, headers=API_HEADERS, timeout=REQUEST_TIMEOUT_S
    )
    validate_http(response, blocked_hint=_BLOCKED_HINT, blocked_exc=BSEBlockedError)
    validate_content_type(response, exc=BSEContentTypeError)
    payload = parse_json(response, exc=BSESchemaError)

    # "No Record Found!" is BSE's empty answer, not an error. Reported as an
    # empty list so the caller logs a miss rather than raising — the endpoint
    # is alive and the query simply matched nothing.
    if isinstance(payload, dict) and not any(
        isinstance(payload.get(k), list) for k in _ENVELOPE_KEYS
    ):
        message = str(payload)[:200]
        log.info(f"BSE returned no records: {message}")
        return []
    return rows_from(payload, envelope_keys=_ENVELOPE_KEYS, exc=BSESchemaError)


def announcement_params(from_date, to_date, scrip="", page=1):
    """The parameter set bseindia.com's own announcements page sends.

    Every field is required. Earlier probes omitted ``subcategory`` and got
    "No Record Found!" back for a window that certainly had filings in it,
    which is the single likeliest cause of that miss.
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


def fetch_announcements(session=None, from_date=None, to_date=None, scrip=""):
    """Raw announcement records for a date window. Raises on failure."""
    today = datetime.date.today()
    params = announcement_params(from_date or today, to_date or today, scrip)

    owns_session = session is None
    session = session or build_session()
    try:
        handshake(session)
        polite_pause()
        return _get(session, ANNOUNCEMENTS_URL, params)
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
        scrip_index = build_scrip_index(watchlist, session=session)
        raw = fetch_announcements(session=session, from_date=from_date, to_date=to_date)
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
