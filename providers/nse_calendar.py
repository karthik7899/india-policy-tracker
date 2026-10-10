"""Upcoming board meetings and corporate actions, from NSE's own calendars.

The pipeline learned a holding had reported its results when a headline
said so, and learned nothing in advance: there was no date anywhere for when
a company would report, go ex-dividend, split its shares or hold its AGM.
NSE publishes both, from the same site and session as the announcements
feed (providers/nse_announcements.py), so this reuses that provider's
session and handshake rather than repeating them:

  * the event calendar -- board meetings ahead, each with its purpose
    ("Financial Results", "Dividend", "Fund Raising") and a description;
  * corporate actions -- ex-dates and record dates for dividends, bonuses,
    splits, rights and AGMs.

NOT MEASURED YET from a runner. The endpoints are the ones NSE's own pages
call, and the field names are the ones those pages read, but neither has been
probed from GitHub Actions the way the announcements API was. So:

  * every field is read through aliases (first_present), so a rename costs
    one field rather than the feed;
  * a request carrying date parameters that comes back empty is tried once
    without them, because NSE answers a parameter it does not take with an
    empty list rather than an error -- the announcements provider learned
    that with index=corporate;
  * fetch_calendar() cannot raise: every failure is logged with its cause
    and the calendar falls back on the board-meeting intimations already
    read from the announcements feed (analysis/event_calendar.py).

`python scripts/probe_upstream.py --source nse-calendar` prints the status,
content type, record count and field names of both endpoints.
"""

import datetime
import re
from typing import Any, Dict, Iterable, List, Optional

import requests

from logger import log
from providers import nse_announcements as nse
from providers.exchange_api import (
    ExchangeAPIError,
    first_present,
    parse_json,
    rows_from,
    validate_content_type,
    validate_http,
)
from utils import TransientNetworkError, retry_network

EVENTS_URL = f"{nse.BASE_URL}/api/event-calendar"
EVENTS_PAGE = f"{nse.BASE_URL}/companies-listing/corporate-filings-event-calendar"
ACTIONS_URL = f"{nse.BASE_URL}/api/corporates-corporateActions"
ACTIONS_PAGE = f"{nse.BASE_URL}/companies-listing/corporate-filings-actions"

# How far ahead to ask for, and how far back: an event a few days past is
# still worth showing beside the results it produced.
AHEAD_DAYS = 60
BACK_DAYS = 14

EVENT_ALIASES = {
    "symbol": ("symbol", "bm_symbol", "SYMBOL"),
    "company": ("company", "sm_name", "comp", "bm_company"),
    "purpose": ("purpose", "bm_purpose"),
    "detail": ("bm_desc", "desc", "description"),
    "date": ("date", "bm_date", "meetingDate"),
}
ACTION_ALIASES = {
    "symbol": ("symbol", "SYMBOL"),
    "company": ("comp", "company", "sm_name"),
    "subject": ("subject", "purpose"),
    "ex_date": ("exDate", "ex_date", "exdate"),
    "record_date": ("recDate", "record_date", "recdate"),
}

# What an event is about, read from its purpose or subject. First match wins,
# so "Financial Results/Dividend" is a results meeting that also declares a
# dividend, and is filed under results.
KINDS = (
    ("results", r"financial results|\bresults\b|audited|unaudited"),
    ("dividend", r"dividend"),
    ("bonus", r"\bbonus\b"),
    ("split", r"split|sub-?division"),
    ("buyback", r"buy ?-?back"),
    ("rights", r"\brights\b"),
    (
        "fund_raising",
        r"fund ?raising|raising of funds|\bqip\b|preferential|debentures|\bncds?\b",
    ),
    ("agm", r"annual general meeting|\bagm\b"),
    ("egm", r"extra-?ordinary general meeting|\begm\b"),
    ("merger", r"amalgamation|merger|demerger|scheme of arrangement"),
)
_KIND_RES = [(k, re.compile(p, re.I)) for k, p in KINDS]

_MAX_DETAIL = 200


def classify(text: str, default: str = "board") -> str:
    """The kind of event a purpose or subject line describes."""
    for kind, pattern in _KIND_RES:
        if pattern.search(text or ""):
            return kind
    return default


def parse_date(raw: str) -> Optional[str]:
    """NSE's '24-Oct-2026' (or a close cousin) as ISO; None when unreadable.

    Unlike a filing's timestamp, an event's date is what the calendar sorts
    and filters on, so an unreadable one is dropped rather than shown raw.
    """
    raw = (raw or "").strip()
    # A timestamp ("24-Oct-2026 17:30:00") is read by its date alone.
    candidates = [raw, raw.split()[0]] if " " in raw else [raw]
    for text in candidates:
        for fmt in (
            "%d-%b-%Y",
            "%d-%B-%Y",
            "%d %b %Y",
            "%d %B %Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
        ):
            try:
                return datetime.datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _trim(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= _MAX_DETAIL else text[: _MAX_DETAIL - 1].rstrip() + "…"


def normalize_event(record: Any) -> Optional[Dict[str, Any]]:
    """One event-calendar row as a calendar entry, or None."""
    if not isinstance(record, dict):
        return None
    symbol = first_present(record, EVENT_ALIASES["symbol"]).upper()
    date = parse_date(first_present(record, EVENT_ALIASES["date"]))
    if not symbol or not date:
        return None
    purpose = first_present(record, EVENT_ALIASES["purpose"])
    detail = first_present(record, EVENT_ALIASES["detail"])
    return {
        "ticker": symbol,
        "date": date,
        "kind": classify(f"{purpose} {detail}"),
        "title": f"Board meeting: {purpose}" if purpose else "Board meeting",
        "detail": _trim(detail),
        "source": "NSE event calendar",
        "link": EVENTS_PAGE,
    }


def normalize_action(record: Any) -> Optional[Dict[str, Any]]:
    """One corporate-action row, dated by its ex-date, or None."""
    if not isinstance(record, dict):
        return None
    symbol = first_present(record, ACTION_ALIASES["symbol"]).upper()
    subject = first_present(record, ACTION_ALIASES["subject"])
    ex_date = parse_date(first_present(record, ACTION_ALIASES["ex_date"]))
    record_date = parse_date(first_present(record, ACTION_ALIASES["record_date"]))
    date = ex_date or record_date
    if not symbol or not subject or not date:
        return None
    return {
        "ticker": symbol,
        "date": date,
        "kind": classify(subject, default="corporate_action"),
        "title": f"{'Ex-date' if ex_date else 'Record date'}: {_trim(subject)}",
        "detail": f"record date {record_date}" if ex_date and record_date else "",
        "source": "NSE corporate actions",
        "link": ACTIONS_PAGE,
    }


@retry_network(max_retries=2, base_delay=2.0)
def _get(session, url: str, referer: str, params: Optional[Dict[str, str]]):
    headers = {**nse.API_HEADERS, "Referer": referer}
    response = session.get(
        url, params=params, headers=headers, timeout=nse.REQUEST_TIMEOUT_S
    )
    validate_http(response, blocked_exc=nse.NSEBlockedError)
    validate_content_type(response, exc=nse.NSEContentTypeError)
    return rows_from(parse_json(response, exc=nse.NSESchemaError))


def _rows(session, url, referer, params) -> List[Any]:
    """Records for the date window; if it drew nothing, the same request with
    only the market named, then with no parameters at all."""
    attempts = [params, {k: v for k, v in params.items() if k == "index"}, None]
    rows: List[Any] = []
    for i, attempt in enumerate(attempts):
        if i:
            nse._polite_pause()
        rows = _get(session, url, referer, attempt or None)
        if rows:
            break
    return rows


def fetch_calendar(
    symbols: Iterable[str],
    today: Optional[datetime.date] = None,
    session=None,
) -> Dict[str, Any]:
    """Events for the given holdings. NEVER raises.

    Returns ``{"events": [...], "published": {source: n}, "errors": [...]}``;
    ``published`` counts every record NSE returned, held or not, so an empty
    calendar can be told apart from an endpoint that answered with nothing.
    """
    wanted = {str(s).upper() for s in symbols or ()}
    today = today or datetime.date.today()
    window = {
        "index": "equities",
        "from_date": (today - datetime.timedelta(days=BACK_DAYS)).strftime("%d-%m-%Y"),
        "to_date": (today + datetime.timedelta(days=AHEAD_DAYS)).strftime("%d-%m-%Y"),
    }
    out: Dict[str, Any] = {"events": [], "published": {}, "errors": []}
    owns = session is None
    try:
        session = session or nse.build_session()
        if not nse.handshake(session):
            out["errors"].append("NSE handshake yielded no cookies")
            return out
        for name, url, page, normalize in (
            ("event_calendar", EVENTS_URL, EVENTS_PAGE, normalize_event),
            ("corporate_actions", ACTIONS_URL, ACTIONS_PAGE, normalize_action),
        ):
            try:
                nse._polite_pause()
                rows = _rows(session, url, page, window)
            except (
                ExchangeAPIError,
                TransientNetworkError,
                requests.RequestException,
            ) as e:
                out["errors"].append(f"{name}: {type(e).__name__}: {str(e)[:160]}")
                continue
            out["published"][name] = len(rows)
            for r in rows:
                event = normalize(r)
                if event and event["ticker"] in wanted:
                    out["events"].append(event)
    except Exception as e:  # noqa: BLE001 - a calendar must never end a run
        out["errors"].append(f"{type(e).__name__}: {str(e)[:160]}")
    finally:
        if owns and session is not None:
            session.close()
    log.info(
        "NSE calendar: "
        + (
            ", ".join(
                f"{n} {k.replace('_', ' ')} record(s)"
                for k, n in out["published"].items()
            )
            or "nothing read"
        )
        + f"; {len(out['events'])} for holdings"
        + (f"; failed: {'; '.join(out['errors'])}" if out["errors"] else "")
        + "."
    )
    return out
