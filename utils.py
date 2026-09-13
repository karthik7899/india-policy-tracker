from typing import Optional, Union  # noqa: E402


def to_float(value: Union[str, int, float, None]) -> Optional[float]:
    """Canonical tolerant numeric coercion for stock-record fields.

    Accepts numbers as-is and strings in every format this pipeline has
    historically produced ("482.95", "+23.0%", "1,840.00", "N/A", "-", "—"),
    returning None for anything non-numeric. This is THE coercion helper —
    five modules used to carry private copies of it, which meant a parsing
    fix in one never reached the others.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace("+", "").replace(",", "")
        if not cleaned or cleaned.upper() in {"N/A", "NA", "-", "—", "NONE"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


import json  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402


def atomic_write_json(data, filepath, indent=2):
    """
    Writes data to a JSON file atomically.
    1. Writes to a temporary file.
    2. Flushes and fsyncs the file to ensure data is on disk.
    3. Atomically replaces the target file with the temporary file.
    """
    directory = os.path.dirname(os.path.abspath(filepath))
    fd, temp_path = tempfile.mkstemp(dir=directory, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, filepath)
    except Exception:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


import asyncio  # noqa: E402
import datetime  # noqa: E402
import functools  # noqa: E402
import logging  # noqa: E402
import time  # noqa: E402

log = logging.getLogger(__name__)


class TransientNetworkError(Exception):
    """Raised when a network operation fails temporarily (e.g. HTTP 429/502/503).

    ``retry_after`` carries the server's own instruction when it sent one. A
    429 is a service telling us how long to wait; guessing a shorter backoff
    and retrying anyway is both rude and counterproductive, because the early
    retry is what earns the next 429.
    """

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


# A hostile or mistaken Retry-After must not be able to stall a run for hours.
MAX_RETRY_AFTER_S = 30.0


def retry_after_of(response):
    """Retry-After from a response, tolerating one that carries no headers.

    Defensive on purpose: this runs on the *error* path, so a response object
    that does not look the way we expect would otherwise turn a recoverable
    429 into an AttributeError and take down the whole fetch.
    """
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        return parse_retry_after(headers.get("Retry-After"))
    except Exception:  # noqa: BLE001 - a header lookup must not break a retry
        return None


def parse_retry_after(value):
    """Seconds from a Retry-After header, or None.

    The header is either delta-seconds or an HTTP date; both are in the wild.
    Anything unreadable returns None so the caller falls back to its own
    backoff rather than treating a malformed header as "wait zero".
    """
    # Explicitly None/empty rather than falsy: a Retry-After of 0 is a real
    # instruction ("retry immediately") and is not the same as no header at
    # all. _backoff_delay clamps it up to our own backoff either way, but the
    # two should not be conflated here.
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime

        when = parsedate_to_datetime(text)
        if when is None:
            return None
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        delta = (when - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
        return max(0.0, delta)
    except Exception:  # noqa: BLE001 - a bad header is not worth an exception
        return None


def _backoff_delay(error, base_delay, retries):
    """Exponential backoff, overridden by the server's own Retry-After."""
    delay = base_delay * (2 ** (retries - 1))
    hinted = getattr(error, "retry_after", None)
    if hinted is not None:
        # Honour the instruction, but never wait less than our own backoff —
        # a Retry-After of 0 should not become a hot loop.
        delay = max(delay, min(float(hinted), MAX_RETRY_AFTER_S))
    return delay


def retry_network(max_retries=3, base_delay=1.0):
    """
    Decorator for retrying network operations with exponential backoff.
    Retries only on transient network failures, not on parsing/logic errors.
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                import aiohttp
                import requests

                transient_exceptions = (
                    TransientNetworkError,
                    aiohttp.ClientConnectionError,
                    aiohttp.ClientPayloadError,
                    aiohttp.ServerDisconnectedError,
                    asyncio.TimeoutError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError,
                )
                retries = 0
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except transient_exceptions as e:
                        retries += 1
                        if retries > max_retries:
                            log.error(
                                f"Async network operation failed after {max_retries} retries: {e}"
                            )
                            raise
                        delay = _backoff_delay(e, base_delay, retries)
                        log.warning(
                            f"Transient network error in {func.__name__}: {e}. Retrying in {delay}s (Attempt {retries}/{max_retries})"
                        )
                        await asyncio.sleep(delay)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                import requests
                import urllib3

                transient_exceptions = (
                    TransientNetworkError,
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.ChunkedEncodingError,
                    urllib3.exceptions.ProtocolError,
                )
                retries = 0
                while True:
                    try:
                        return func(*args, **kwargs)
                    except transient_exceptions as e:
                        retries += 1
                        if retries > max_retries:
                            log.error(
                                f"Sync network operation failed after {max_retries} retries: {e}"
                            )
                            raise
                        delay = _backoff_delay(e, base_delay, retries)
                        log.warning(
                            f"Transient network error in {func.__name__}: {e}. Retrying in {delay}s (Attempt {retries}/{max_retries})"
                        )
                        time.sleep(delay)

            return sync_wrapper

    return decorator


@retry_network(max_retries=3, base_delay=2.0)
async def fetch_text_async(session, url, headers=None, timeout=15):
    async with session.get(url, headers=headers, timeout=timeout) as response:
        if response.status in (408, 429, 500, 502, 503, 504):
            raise TransientNetworkError(
                f"HTTP {response.status} for {url}",
                retry_after=retry_after_of(response),
            )
        return response.status, await response.text()


import threading  # noqa: E402

_THREAD_SESSIONS = threading.local()


def thread_local_session():
    """A ``requests.Session`` owned by the calling thread.

    requests documents Session as NOT thread-safe. Sharing one across a
    ThreadPoolExecutor races on the cookie jar and on per-adapter state, and
    the failure mode is the bad kind: not a crash, but occasional wrong or
    dropped responses under load, which look like the remote host being
    flaky.

    Per-thread rather than per-call so connection pooling — the only reason
    to hold a Session at all — still applies. Pools here are small and
    bounded, and a thread's session is collected with the thread.
    """
    import requests

    session = getattr(_THREAD_SESSIONS, "session", None)
    if session is None:
        session = requests.Session()
        _THREAD_SESSIONS.session = session
    return session
