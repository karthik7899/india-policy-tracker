import unittest
import os
import tempfile
import json
from history.store import HistoryStore


class TestHistoryStore(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
