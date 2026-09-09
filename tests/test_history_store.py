import unittest
from history.store import HistoryStore


class TestHistoryStore(unittest.TestCase):
    def test_get_historical_events_with_existing_category(self):
        store = HistoryStore(filepath="non_existent_dummy_file.json")
        store.data = {"briefing": {"category1": [{"id": 1, "name": "Event 1"}]}}
        self.assertEqual(
            store.get_historical_events("category1"), [{"id": 1, "name": "Event 1"}]
        )

    def test_get_historical_events_missing_category(self):
        store = HistoryStore(filepath="non_existent_dummy_file.json")
        store.data = {"briefing": {"category1": [{"id": 1, "name": "Event 1"}]}}
        self.assertEqual(store.get_historical_events("category2"), [])

    def test_get_historical_events_no_briefing_key(self):
        store = HistoryStore(filepath="non_existent_dummy_file.json")
        store.data = {"other": "data"}
        self.assertEqual(store.get_historical_events("category1"), [])

    def test_get_historical_events_empty_data(self):
        store = HistoryStore(filepath="non_existent_dummy_file.json")
        store.data = {}
        self.assertEqual(store.get_historical_events("category1"), [])


if __name__ == "__main__":
    unittest.main()
