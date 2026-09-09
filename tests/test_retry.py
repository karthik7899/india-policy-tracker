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
