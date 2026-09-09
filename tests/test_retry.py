import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from utils import fetch_text_async, fetch_text_sync


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


def test_fetch_text_sync_retry_transient(monkeypatch):
    import time

    session = MagicMock()

    class DummyResp:
        def __init__(self, status_code, text):
            self.status_code = status_code
            self.text = text

    session.get.side_effect = [DummyResp(502, "bad gateway"), DummyResp(200, "ok")]

    monkeypatch.setattr(time, "sleep", MagicMock())

    status, text = fetch_text_sync(session, "http://example.com")
    assert status == 200
    assert text == "ok"
    assert session.get.call_count == 2


def test_sync_wrapper_success():
    from utils import retry_network

    @retry_network(max_retries=2, base_delay=0.1)
    def dummy_func():
        return "success"

    assert dummy_func() == "success"


def test_sync_wrapper_retry_transient_then_success(monkeypatch):
    import time
    from utils import retry_network, TransientNetworkError

    mock_sleep = MagicMock()
    monkeypatch.setattr(time, "sleep", mock_sleep)

    call_count = 0

    @retry_network(max_retries=2, base_delay=0.1)
    def dummy_func():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TransientNetworkError("temporary failure")
        return "success_after_retry"

    result = dummy_func()
    assert result == "success_after_retry"
    assert call_count == 2
    mock_sleep.assert_called_once_with(0.1)


def test_sync_wrapper_max_retries_exceeded(monkeypatch):
    import time
    import requests
    from utils import retry_network

    mock_sleep = MagicMock()
    monkeypatch.setattr(time, "sleep", mock_sleep)

    call_count = 0

    @retry_network(max_retries=2, base_delay=0.1)
    def dummy_func():
        nonlocal call_count
        call_count += 1
        raise requests.exceptions.ConnectionError("connection failed")

    with pytest.raises(requests.exceptions.ConnectionError):
        dummy_func()

    assert call_count == 3  # 1 initial call + 2 retries
    assert mock_sleep.call_count == 2
