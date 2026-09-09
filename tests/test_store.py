import os
import json
import pytest
import history.store
from history.store import HistoryStore

@pytest.fixture
def store_paths(tmp_path, monkeypatch):
    """Provides isolated history and legacy paths for testing."""
    history_path = tmp_path / "history.json"
    legacy_path = tmp_path / "dashboard_data.json"

    # Patch module level constants used in load()
    monkeypatch.setattr(history.store, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(history.store, "_LEGACY_PATH", str(legacy_path))

    return history_path, legacy_path

def test_load_from_existing_history(store_paths):
    """Test loading data normally when HISTORY_PATH is present."""
    history_path, legacy_path = store_paths

    test_data = {"key": "value"}
    history_path.write_text(json.dumps(test_data))

    store = HistoryStore(filepath=str(history_path))
    assert store.data == test_data

def test_load_fallback_to_legacy(store_paths):
    """Test fallback to _LEGACY_PATH when HISTORY_PATH is missing."""
    history_path, legacy_path = store_paths

    test_data = {"legacy": "data"}
    legacy_path.write_text(json.dumps(test_data))

    # filepath matches HISTORY_PATH, so the fallback should happen
    store = HistoryStore(filepath=str(history_path))
    assert store.data == test_data

def test_load_no_fallback_if_custom_path(store_paths):
    """Test that fallback only happens when filepath == HISTORY_PATH."""
    history_path, legacy_path = store_paths
    custom_path = history_path.parent / "custom.json"

    test_data = {"legacy": "data"}
    legacy_path.write_text(json.dumps(test_data))

    # Since filepath doesn't match HISTORY_PATH, it shouldn't fallback to _LEGACY_PATH
    store = HistoryStore(filepath=str(custom_path))
    assert store.data == {}

def test_load_file_not_found(store_paths):
    """Test behavior when no files exist."""
    history_path, legacy_path = store_paths

    # Neither history_path nor legacy_path exists
    store = HistoryStore(filepath=str(history_path))
    assert store.data == {}

def test_load_invalid_json(store_paths, caplog):
    """Test fallback when the file exists but contains invalid JSON."""
    history_path, legacy_path = store_paths

    # Create invalid JSON
    history_path.write_text("invalid json {")

    store = HistoryStore(filepath=str(history_path))

    # Data should be an empty dictionary because Exception was caught
    assert store.data == {}

    # Verify the error was logged
    assert any("Failed to load history" in record.message for record in caplog.records)
