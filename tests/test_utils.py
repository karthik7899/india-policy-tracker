import asyncio  # noqa: E402
import pytest  # noqa: E402
import requests  # noqa: E402

from utils import (  # noqa: E402
    TransientNetworkError,
    retry_network,
    safe_float,
    safe_int,
    safe_percentage,
    to_float,
)


def test_safe_float():
    assert safe_float(None) is None
    assert safe_float("") is None
    assert safe_float("-") is None
    assert safe_float("N/A") is None
    assert safe_float("NA") is None
    assert safe_float("123.45") == 123.45
    assert safe_float("1,234.56") == 1234.56
    assert safe_float(10) == 10.0
    assert safe_float("invalid") is None
    assert safe_float("invalid", default=0.0) == 0.0
    assert safe_float("", default=1.5) == 1.5


def test_safe_int():
    assert safe_int(None) is None
    assert safe_int("") is None
    assert safe_int("-") is None
    assert safe_int("N/A") is None
    assert safe_int("123") == 123
    assert safe_int("1,234") == 1234
    assert safe_int("123.45") == 123
    assert safe_int(10) == 10
    assert safe_int("invalid") is None
    assert safe_int("invalid", default=0) == 0
    assert safe_int("", default=-1) == -1


def test_safe_percentage():
    assert safe_percentage(None) is None
    assert safe_percentage("") is None
    assert safe_percentage("-") is None
    assert safe_percentage("N/A") is None
    assert safe_percentage("12.5%") == 12.5
    assert safe_percentage("1,234.5%") == 1234.5
    assert safe_percentage("12.5") == 12.5
    assert safe_percentage(10) == 10.0
    assert safe_percentage("invalid") is None
    assert safe_percentage("invalid", default=0.0) == 0.0
    assert safe_percentage("", default=0.0) == 0.0


import json  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402

from utils import atomic_write_json  # noqa: E402


def test_atomic_write_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        target_file = os.path.join(tmpdir, "test.json")
        data = {"key": "value"}
        atomic_write_json(data, target_file)

        assert os.path.exists(target_file)
        with open(target_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data


def test_to_float():
    # None and booleans
    assert to_float(None) is None
    assert to_float(True) is None
    assert to_float(False) is None

    # Ints and floats
    assert to_float(10) == 10.0
    assert to_float(12.5) == 12.5

    # Strings that are valid numbers
    assert to_float("482.95") == 482.95
    assert to_float("1,840.00") == 1840.0
    assert to_float(" 42 ") == 42.0

    # Strings with formatting
    assert to_float("+23.0%") == 23.0
    assert to_float("12.5%") == 12.5

    # "None"-like and empty strings
    assert to_float("") is None
    assert to_float(" ") is None
    assert to_float("N/A") is None
    assert to_float("na") is None
    assert to_float("NA") is None
    assert to_float("-") is None
    assert to_float("—") is None
    assert to_float("none") is None
    assert to_float("NONE") is None

    # Invalid strings
    assert to_float("invalid") is None
    assert to_float("12.34 abc") is None
def test_retry_network_sync_success(monkeypatch):
    import time

    monkeypatch.setattr(time, "sleep", lambda x: None)

    @retry_network(max_retries=2, base_delay=0)
    def my_func():
        return "success"

    assert my_func() == "success"


def test_retry_network_sync_transient_retry(monkeypatch):
    import time

    monkeypatch.setattr(time, "sleep", lambda x: None)

    attempts = 0

    @retry_network(max_retries=2, base_delay=0)
    def my_func():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise requests.exceptions.ConnectionError("transient")
        return "success"

    assert my_func() == "success"
    assert attempts == 2


def test_retry_network_sync_transient_failure(monkeypatch):
    import time

    monkeypatch.setattr(time, "sleep", lambda x: None)

    attempts = 0

    @retry_network(max_retries=2, base_delay=0)
    def my_func():
        nonlocal attempts
        attempts += 1
        raise requests.exceptions.ConnectionError("transient")

    with pytest.raises(requests.exceptions.ConnectionError):
        my_func()
    assert attempts == 3  # 1 initial + 2 retries


def test_retry_network_sync_non_transient_failure():
    attempts = 0

    @retry_network(max_retries=2, base_delay=0)
    def my_func():
        nonlocal attempts
        attempts += 1
        raise ValueError("fatal")

    with pytest.raises(ValueError):
        my_func()
    assert attempts == 1


@pytest.mark.anyio
async def test_retry_network_async_success(monkeypatch):
    async def mock_sleep(delay):
        pass

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    @retry_network(max_retries=2, base_delay=0)
    async def my_func():
        return "success"

    assert await my_func() == "success"


@pytest.mark.anyio
async def test_retry_network_async_transient_retry(monkeypatch):
    async def mock_sleep(delay):
        pass

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    attempts = 0

    @retry_network(max_retries=2, base_delay=0)
    async def my_func():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            import aiohttp

            raise aiohttp.ClientConnectionError("transient")
        return "success"

    assert await my_func() == "success"
    assert attempts == 2


@pytest.mark.anyio
async def test_retry_network_async_transient_failure(monkeypatch):
    async def mock_sleep(delay):
        pass

    monkeypatch.setattr(asyncio, "sleep", mock_sleep)

    attempts = 0

    @retry_network(max_retries=2, base_delay=0)
    async def my_func():
        nonlocal attempts
        attempts += 1
        raise TransientNetworkError("transient")

    with pytest.raises(TransientNetworkError):
        await my_func()
    assert attempts == 3


@pytest.mark.anyio
async def test_retry_network_async_non_transient_failure():
    attempts = 0

    @retry_network(max_retries=2, base_delay=0)
    async def my_func():
        nonlocal attempts
        attempts += 1
        raise ValueError("fatal")

    with pytest.raises(ValueError):
        await my_func()
    assert attempts == 1
