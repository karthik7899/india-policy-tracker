import os
import json
import pytest
from unittest import mock
from history import store
from history.store import write_coverage_sidecars


@pytest.fixture
def temp_news_dir(tmp_path, monkeypatch):
    news_dir = str(tmp_path / "news")
    monkeypatch.setattr(store, "NEWS_DIR", news_dir)
    return news_dir


def test_write_coverage_sidecars_success(temp_news_dir):
    coverage = {
        "AAPL": [{"headline": "Apple News 1"}],
        "MSFT": [{"headline": "Microsoft News 1"}, {"headline": "Microsoft News 2"}],
    }

    written = write_coverage_sidecars(coverage)

    assert written == 2
    assert os.path.exists(temp_news_dir)

    aapl_file = os.path.join(temp_news_dir, "AAPL.json")
    assert os.path.exists(aapl_file)
    with open(aapl_file, "r") as f:
        data = json.load(f)
        assert data["ticker"] == "AAPL"
        assert len(data["items"]) == 1

    msft_file = os.path.join(temp_news_dir, "MSFT.json")
    assert os.path.exists(msft_file)
    with open(msft_file, "r") as f:
        data = json.load(f)
        assert data["ticker"] == "MSFT"
        assert len(data["items"]) == 2


def test_write_coverage_sidecars_removes_stale(temp_news_dir):
    os.makedirs(temp_news_dir, exist_ok=True)
    stale_file = os.path.join(temp_news_dir, "OLDTICKER.json")
    with open(stale_file, "w") as f:
        json.dump({"ticker": "OLDTICKER", "items": []}, f)

    other_file = os.path.join(temp_news_dir, "not_json.txt")
    with open(other_file, "w") as f:
        f.write("hello")

    coverage = {"NEWTICKER": [{"headline": "New"}]}

    written = write_coverage_sidecars(coverage)

    assert written == 1
    assert os.path.exists(os.path.join(temp_news_dir, "NEWTICKER.json"))
    assert not os.path.exists(stale_file)
    assert os.path.exists(other_file)  # Should not remove non-json files


def test_write_coverage_sidecars_none_coverage(temp_news_dir):
    os.makedirs(temp_news_dir, exist_ok=True)
    stale_file = os.path.join(temp_news_dir, "OLDTICKER.json")
    with open(stale_file, "w") as f:
        json.dump({"ticker": "OLDTICKER", "items": []}, f)

    written = write_coverage_sidecars(None)

    assert written == 0
    assert not os.path.exists(stale_file)


def test_write_coverage_sidecars_sanitizes_ticker(temp_news_dir):
    coverage = {
        "bad/ticker": [{"headline": "test1"}],
        "good-ticker_1": [{"headline": "test2"}],
        "?!?": [{"headline": "test3"}],  # Will become empty and should be skipped
    }

    written = write_coverage_sidecars(coverage)

    assert written == 2
    assert os.path.exists(os.path.join(temp_news_dir, "BADTICKER.json"))
    assert os.path.exists(os.path.join(temp_news_dir, "GOOD-TICKER_1.json"))

    files = [f for f in os.listdir(temp_news_dir) if f.endswith(".json")]
    assert len(files) == 2


@mock.patch("history.store.os.makedirs")
def test_write_coverage_sidecars_exception_handled(
    mock_makedirs, temp_news_dir, caplog
):
    mock_makedirs.side_effect = Exception("Disk full")

    coverage = {"AAPL": [{"headline": "Apple News 1"}]}

    written = write_coverage_sidecars(coverage)

    assert written == 0
    assert "Coverage sidecar write failed safely" in caplog.text
    assert "Disk full" in caplog.text
