from typing import Optional, Union  # noqa: E402


def _clean_str(val: Union[str, int, float, None]) -> str:
    if val is None:
        return ""
    return str(val).strip()


def safe_float(
    val: Union[str, int, float, None], default: Optional[float] = None
) -> Optional[float]:
    """Safely converts a value to float, handling common string artifacts."""
    s = _clean_str(val)
    if not s or s in ("-", "N/A", "NA", "None"):
        return default
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return default


def safe_int(
    val: Union[str, int, float, None], default: Optional[int] = None
) -> Optional[int]:
    """Safely converts a value to int, handling common string artifacts."""
    s = _clean_str(val)
    if not s or s in ("-", "N/A", "NA", "None"):
        return default
    s = s.replace(",", "")
    try:
        return int(float(s))
    except ValueError:
        return default


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


def safe_percentage(
    val: Union[str, int, float, None], default: Optional[float] = None
) -> Optional[float]:
    """Safely converts a percentage string (e.g. '12.5%') to a float."""
    s = _clean_str(val)
    if not s or s in ("-", "N/A", "NA", "None"):
        return default
    s = s.replace("%", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return default


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
import functools  # noqa: E402
import logging  # noqa: E402
import time  # noqa: E402

log = logging.getLogger(__name__)


class TransientNetworkError(Exception):
    """Exception raised when a network operation fails temporarily (e.g. HTTP 502/503/504)."""

    pass


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
                        delay = base_delay * (2 ** (retries - 1))
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
                        delay = base_delay * (2 ** (retries - 1))
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
            raise TransientNetworkError(f"HTTP {response.status} for {url}")
        return response.status, await response.text()


@retry_network(max_retries=3, base_delay=2.0)
def fetch_text_sync(session_or_module, url, headers=None, timeout=15):
    response = session_or_module.get(url, headers=headers, timeout=timeout)
    if response.status_code in (408, 429, 500, 502, 503, 504):
        raise TransientNetworkError(f"HTTP {response.status_code} for {url}")
    return response.status_code, response.text
