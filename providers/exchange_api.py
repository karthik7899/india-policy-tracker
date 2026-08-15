"""Shared plumbing for reading JSON APIs off NSE and BSE.

Both exchanges front their APIs with bot protection and both fail in the same
dishonest ways, so the defences belong in one place rather than copied into
each provider — every one of the rules below was learned from a measured CI
failure, and a second copy is a second thing to re-learn:

  * a block arrives as HTML with HTTP 200, so content-type is checked BEFORE
    anything is parsed. Calling .json() on a challenge page raises "Expecting
    value: line 1 column 1", which reads like a parser bug and is actually a
    network verdict;
  * never advertise an Accept-Encoding this client cannot decode. Asking for
    "br" got us 44 KB of Brotli that urllib3 could not read, delivered with a
    truthful application/json content-type, and the failure surfaced as
    invalid JSON — a header we sent, blamed on the parser;
  * the API is refused without cookies from the HTML site, so a handshake
    runs first;
  * 401/403 means the session is not trusted and only a fresh handshake can
    change the answer; 429/5xx is the host having a moment and belongs to
    utils.retry_network's backoff. They are not the same failure and must not
    share a code path.

Exceptions are typed so a caller can tell "they refused us" from "they sent
something unexpected" without string matching.
"""

import random
import time

import requests

from utils import TransientNetworkError

# Retried: the host's own admission that it is struggling.
TRANSIENT_STATUSES = (408, 429, 500, 502, 503, 504)
# Not transient: the session or the caller is not trusted.
AUTH_STATUSES = (401, 403)

# Deliberately carries NO Accept-Encoding. requests derives it from what
# urllib3 can actually decode; pinning it here is how the NSE provider first
# broke. Providers add their own Referer and Accept.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en-GB;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Human-paced. Back-to-back requests from a datacentre IP are the signature
# rate limiters look for, and these fetches happen once per run.
MIN_PAUSE_S = 2.0
MAX_PAUSE_S = 5.0


class ExchangeAPIError(Exception):
    """Base: any reason a provider decided it has no usable data."""


class ExchangeBlockedError(ExchangeAPIError):
    """The exchange refused us. Carries what to check — from a CI log this is
    otherwise indistinguishable from a code fault."""


class ExchangeContentTypeError(ExchangeAPIError):
    """Served something other than JSON, typically a bot-challenge page
    delivered with HTTP 200. Raised BEFORE any parse is attempted."""


class ExchangeSchemaError(ExchangeAPIError):
    """Parsed, but not the shape the provider was written against."""


def polite_pause():
    """Random, not fixed: a constant interval is itself a fingerprint."""
    time.sleep(random.uniform(MIN_PAUSE_S, MAX_PAUSE_S))


def build_session(extra_headers=None):
    """A session, because the cookies these sites mint must persist across
    requests. Separate from the handshake so tests can inject a fake."""
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    if extra_headers:
        session.headers.update(extra_headers)
    return session


def validate_http(response, blocked_hint="", blocked_exc=ExchangeBlockedError):
    """Status first: an auth refusal and a rate limit need opposite reactions."""
    status = response.status_code
    if status in AUTH_STATUSES:
        raise blocked_exc(
            f"HTTP {status} for {response.url}. This is the bot filter, not a "
            f"bad query. {blocked_hint}".strip()
        )
    if status in TRANSIENT_STATUSES:
        # Handed to retry_network, which owns the exponential backoff.
        raise TransientNetworkError(f"HTTP {status} for {response.url}")
    if status != 200:
        raise ExchangeAPIError(f"HTTP {status} for {response.url}")


def validate_content_type(response, exc=ExchangeContentTypeError):
    """The check that matters most: a block arrives as HTML with a 200 on it."""
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "json" not in content_type:
        body = (response.text or "")[:200].replace("\n", " ")
        raise exc(
            f"Expected JSON, got {content_type or 'no Content-Type'} "
            f"(HTTP {response.status_code}). First 200 bytes: {body!r}"
        )


def parse_json(response, exc=ExchangeSchemaError):
    """Parse, naming the encoding when the body will not decode.

    A bare JSONDecodeError points at the parser. When this fired in CI the
    body was Brotli we had asked for and could not read, so the message says
    what arrived and where to look.
    """
    try:
        return response.json()
    except ValueError as e:  # json.JSONDecodeError subclasses ValueError
        encoding = response.headers.get("Content-Encoding") or "none"
        head = repr((response.text or "")[:80])
        raise exc(
            f"Content-Type claimed JSON but the body did not parse: {e} "
            f"(Content-Encoding: {encoding}, first bytes: {head}). If the "
            "encoding is one this client cannot decode, that is the bug — "
            "check Accept-Encoding, not the parser."
        ) from e


def rows_from(payload, envelope_keys=("data", "rows"), exc=ExchangeSchemaError):
    """The list of records, whatever wrapper it arrived in.

    NSE has served both a bare list and a {"data": [...]} envelope for the
    same endpoint; BSE wraps its rows in {"Table": [...]} alongside a row
    count. Accepting either shape means a wrapper change degrades to a clear
    error rather than an exception deep in a loop.
    """
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = next(
            (payload[k] for k in envelope_keys if isinstance(payload.get(k), list)),
            None,
        )
        if rows is None:
            raise exc(
                f"No record list found under {envelope_keys}; "
                f"top-level keys were {sorted(payload.keys())[:12]}"
            )
    else:
        raise exc(f"Expected a dict or list, got {type(payload).__name__}")

    if not isinstance(rows, list):
        raise exc(f"Expected a list of records, got {type(rows).__name__}")
    return rows


def first_present(record, aliases):
    """Safe .get() across every known spelling of a field; '' when absent.

    These APIs are undocumented and their key names have moved. Reading
    through aliases means a rename degrades one field instead of emptying the
    feed.
    """
    for key in aliases:
        value = record.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""
