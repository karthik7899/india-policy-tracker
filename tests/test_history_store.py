import unittest
from unittest.mock import patch

import pytest

import history.store
import os
import tempfile
import json
from history.store import HistoryStore


class TestDeduplicateAndMerge(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w")
        json.dump({}, self.temp_file)
        self.temp_file.close()
        self.store = HistoryStore(filepath=self.temp_file.name)

    def tearDown(self):
        os.unlink(self.temp_file.name)

    def test_deduplicate_and_merge_no_history(self):
        self.store.data = {"briefing": {"test_cat": []}}

        new_events = [
            {"id": 1, "title": "A"},
            {"id": 2, "title": "B"},
            {"id": 1, "title": "A duplicate"},
        ]

        merged = self.store.deduplicate_and_merge("test_cat", new_events, ["id"])

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["title"], "A")
        self.assertEqual(merged[1]["title"], "B")

    def test_deduplicate_and_merge_with_history(self):
        self.store.data = {
            "briefing": {
                "test_cat": [
                    {"id": 1, "title": "A old"},
                    {"id": 3, "title": "C old"},
                ]
            }
        }

        new_events = [{"id": 1, "title": "A new"}, {"id": 2, "title": "B new"}]

        merged = self.store.deduplicate_and_merge("test_cat", new_events, ["id"])

        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[0]["title"], "A new")
        self.assertEqual(merged[1]["title"], "B new")
        self.assertEqual(merged[2]["title"], "C old")

    def test_deduplicate_and_merge_multiple_keys(self):
        self.store.data = {
            "briefing": {
                "test_cat": [
                    {"id": 1, "type": "T1", "title": "Old"},
                ]
            }
        }

        new_events = [
            {"id": 1, "type": "T2", "title": "Different type"},
            {"id": 1, "type": "T1", "title": "New"},
        ]

        merged = self.store.deduplicate_and_merge(
            "test_cat", new_events, ["id", "type"]
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["title"], "Different type")
        self.assertEqual(merged[1]["title"], "New")

    def test_deduplicate_and_merge_missing_keys(self):
        self.store.data = {
            "briefing": {
                "test_cat": [
                    {"id": 1, "title": "Old without optional_key"},
                ]
            }
        }

        new_events = [
            {"id": 2, "title": "New without optional_key"},
            {"id": 1, "title": "New duplicate because optional_key is None for both"},
        ]

        merged = self.store.deduplicate_and_merge(
            "test_cat", new_events, ["id", "optional_key"]
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["title"], "New without optional_key")
        self.assertEqual(
            merged[1]["title"], "New duplicate because optional_key is None for both"
        )


class TestGetHistoricalEvents(unittest.TestCase):
    """get_historical_events is a one-line getter, but it is the read side of
    every merge, so its behaviour on a missing category or a corpus with no
    "briefing" key is what keeps deduplicate_and_merge from raising on a
    first run or a truncated history file.

    Separate class from the merge tests above because that fixture writes a
    real temp file, and these deliberately never touch the disk.
    """

    def setUp(self):
        with patch("history.store.os.path.exists", return_value=False):
            self.store = HistoryStore(filepath="dummy.json")

    def test_existing_category(self):
        self.store.data = {
            "briefing": {
                "macro": [
                    {"title": "Event 1", "date": "2023-01-01"},
                    {"title": "Event 2", "date": "2023-01-02"},
                ],
                "sector": [{"title": "Sector Event"}],
            }
        }
        events = self.store.get_historical_events("macro")
        self.assertEqual([e["title"] for e in events], ["Event 1", "Event 2"])

    def test_unknown_category_is_empty_not_an_error(self):
        self.store.data = {"briefing": {"macro": [{"title": "Event 1"}]}}
        self.assertEqual(self.store.get_historical_events("unknown_category"), [])

    def test_missing_briefing_key_is_empty(self):
        self.store.data = {"some_other_key": {"macro": [{"title": "Event 1"}]}}
        self.assertEqual(self.store.get_historical_events("macro"), [])

    def test_empty_data_is_empty(self):
        self.store.data = {}
        self.assertEqual(self.store.get_historical_events("macro"), [])


class TestSave(unittest.TestCase):
    def test_save_nests_the_briefing_and_writes_the_file(self):
        """save() wraps whatever it is given under a "briefing" key. That
        nesting is the corpus format every reader assumes, including
        get_historical_events above."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test_history.json")
            store = HistoryStore(filepath=path)
            self.assertEqual(store.data, {})  # absent file starts empty

            brief_data = {
                "market_summary": [{"event": "Market went up"}],
                "corporate_actions": [{"event": "Dividend declared"}],
            }
            store.save(brief_data)

            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["briefing"], brief_data)


# --- load(), including the legacy-path fallback --------------------------
#
# pytest-style below because these need tmp_path and monkeypatch; the classes
# above predate them. Both run in the same file so the module has one home.

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
