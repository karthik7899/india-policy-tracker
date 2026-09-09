from utils import safe_float, safe_int, safe_percentage  # noqa: E402


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


from unittest.mock import MagicMock, patch  # noqa: E402
import pytest  # noqa: E402
from utils import fetch_text_sync, TransientNetworkError  # noqa: E402


def test_fetch_text_sync_success():
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "success"
    mock_session.get.return_value = mock_response

    status, text = fetch_text_sync(mock_session, "http://example.com")
    assert status == 200
    assert text == "success"
    mock_session.get.assert_called_once_with(
        "http://example.com", headers=None, timeout=15
    )


@patch("utils.time.sleep")
def test_fetch_text_sync_transient_error(mock_sleep):
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_session.get.return_value = mock_response

    with pytest.raises(TransientNetworkError) as exc_info:
        fetch_text_sync(mock_session, "http://example.com")

    assert "HTTP 500 for http://example.com" in str(exc_info.value)
    # 1 initial call + 3 retries = 4 calls total
    assert mock_session.get.call_count == 4
    assert mock_sleep.call_count == 3


@patch("utils.time.sleep")
def test_fetch_text_sync_transient_error_recovery(mock_sleep):
    mock_session = MagicMock()

    bad_response = MagicMock()
    bad_response.status_code = 502

    good_response = MagicMock()
    good_response.status_code = 200
    good_response.text = "recovered"

    mock_session.get.side_effect = [bad_response, good_response]

    status, text = fetch_text_sync(mock_session, "http://example.com")

    assert status == 200
    assert text == "recovered"
    assert mock_session.get.call_count == 2
    assert mock_sleep.call_count == 1
