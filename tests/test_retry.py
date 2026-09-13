import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from utils import fetch_text_async


@pytest.mark.anyio
async def test_fetch_text_async_success():
    session = MagicMock()

    class DummyResponse:
        def __init__(self):
            self.status = 200

        async def text(self):
            return "success_text"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    session.get.return_value = DummyResponse()

    status, text = await fetch_text_async(session, "http://example.com", timeout=1)
    assert status == 200
    assert text == "success_text"
    assert session.get.call_count == 1


@pytest.mark.anyio
async def test_fetch_text_async_retry_transient():
    session = MagicMock()

    class FailedResponse:
        def __init__(self):
            self.status = 503
            # Real responses carry headers, and the transient path reads
            # Retry-After off them. A double without headers would let this
            # test pass against code that raises in production.
            self.headers = {}

        async def text(self):
            return ""

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    class SuccessResponse:
        def __init__(self):
            self.status = 200

        async def text(self):
            return "success_after_retry"

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # First call returns 503, second returns 200
    session.get.side_effect = [FailedResponse(), SuccessResponse()]

    # We will override the decorator defaults in the test by mocking asyncio.sleep
    with pytest.MonkeyPatch.context() as m:
        m.setattr(asyncio, "sleep", AsyncMock())
        status, text = await fetch_text_async(session, "http://example.com", timeout=1)

    assert status == 200
    assert text == "success_after_retry"
    assert session.get.call_count == 2


# ---------------------------------------------------------------------------
# Retry-After
#
# A 429 is a service stating how long to wait. The pipeline used to ignore it
# and back off on its own schedule, which is both discourteous and self-
# defeating: the early retry is what earns the next 429. Screener returned six
# of them to the peer fetch on 13 Sep alone.
# ---------------------------------------------------------------------------


def test_parse_retry_after_reads_delta_seconds():
    from utils import parse_retry_after

    assert parse_retry_after("7") == 7.0
    assert parse_retry_after(" 12 ") == 12.0
    assert parse_retry_after(0) == 0.0


def test_parse_retry_after_reads_an_http_date():
    import datetime

    from utils import parse_retry_after

    soon = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=30)
    header = soon.strftime("%a, %d %b %Y %H:%M:%S GMT")
    value = parse_retry_after(header)
    assert value is not None
    assert 20 <= value <= 35, value


def test_parse_retry_after_returns_none_for_junk_rather_than_zero():
    """Unreadable must not become "wait zero" — that is a hot loop against a
    service that just asked us to stop."""
    from utils import parse_retry_after

    for junk in (None, "", "soon", "-", "NaN-ish"):
        assert parse_retry_after(junk) is None, junk


def test_a_past_http_date_clamps_to_zero_not_negative():
    from utils import parse_retry_after

    assert parse_retry_after("Wed, 01 Jan 2020 00:00:00 GMT") == 0.0


def test_backoff_prefers_the_longer_of_ours_and_theirs():
    """Honour the instruction, but never wait less than our own backoff: a
    Retry-After of 0 must not turn the retry into a hot loop."""
    from utils import TransientNetworkError, _backoff_delay

    ours = _backoff_delay(TransientNetworkError("x"), base_delay=2.0, retries=1)
    assert ours == 2.0

    theirs = TransientNetworkError("x", retry_after=9)
    assert _backoff_delay(theirs, base_delay=2.0, retries=1) == 9.0

    zero = TransientNetworkError("x", retry_after=0)
    assert _backoff_delay(zero, base_delay=2.0, retries=1) == 2.0


def test_backoff_caps_an_absurd_retry_after():
    from utils import MAX_RETRY_AFTER_S, TransientNetworkError, _backoff_delay

    hostile = TransientNetworkError("x", retry_after=86400)
    assert _backoff_delay(hostile, base_delay=1.0, retries=1) == MAX_RETRY_AFTER_S


def test_retry_after_of_tolerates_a_response_without_headers():
    """This runs on the error path. A response shaped differently than
    expected must not turn a recoverable 429 into an AttributeError."""
    from utils import retry_after_of

    class NoHeaders:
        status = 429

    assert retry_after_of(NoHeaders()) is None
    assert retry_after_of(object()) is None
