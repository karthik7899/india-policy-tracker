import json
import os
from typing import Dict, List, Any
from logger import log


class HistoryStore:
    def __init__(self, filepath: str = "dashboard_data.json"):
        self.filepath = filepath
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                log.error(f"Failed to load history from {self.filepath}: {e}")
                self.data = {}
        else:
            self.data = {}

    def get_historical_events(self, category: str) -> List[Dict[str, Any]]:
        """Returns the list of historical events for a given category in the briefing."""
        return self.data.get("briefing", {}).get(category, [])

    def deduplicate_and_merge(
        self, category: str, new_events: List[Dict[str, Any]], unique_keys: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Merges new events with historical events, keeping the newest first,
        and deduplicating based on the combination of `unique_keys`.
        """
        historical = self.get_historical_events(category)

        seen = set()
        merged = []

        # Add new events first
        for event in new_events:
            key = tuple(event.get(k) for k in unique_keys)
            if key not in seen:
                seen.add(key)
                merged.append(event)

        # Add historical events if not seen
        for event in historical:
            key = tuple(event.get(k) for k in unique_keys)
            if key not in seen:
                seen.add(key)
                merged.append(event)

        return merged
