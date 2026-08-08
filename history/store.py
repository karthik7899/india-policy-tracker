import json
import os
from typing import Dict, List, Any
from logger import log

HISTORY_PATH = "history.json"
# Where the corpus used to live, before payload and history were separated.
_LEGACY_PATH = "dashboard_data.json"


class HistoryStore:
    """The pipeline's accumulated corpus, kept apart from what the browser gets.

    These two things want opposite sizes. Every run merges new headlines into
    running lists, and four consumers read them afterwards — the event engine,
    entity-graph harvesting, new-entrant detection and per-stock coverage — so
    the corpus wants depth. The dashboard downloads its file whole on every
    page load, so the payload wants brevity. While both lived in
    dashboard_data.json, trimming one damaged the other.

    So the corpus lives here and is never fetched by the page, and
    dashboard/payload.py trims a display copy. Computation is unaffected by
    anything done for the dashboard's sake.
    """

    def __init__(self, filepath: str = HISTORY_PATH):
        self.filepath = filepath
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        source = self.filepath
        # First run after the split: seed from the old combined file rather
        # than starting empty, which would silently lose a run's worth of
        # deduplication.
        if not os.path.exists(source) and self.filepath == HISTORY_PATH:
            if os.path.exists(_LEGACY_PATH):
                log.info(
                    f"No {HISTORY_PATH} yet — seeding the corpus from "
                    f"{_LEGACY_PATH}."
                )
                source = _LEGACY_PATH
        if os.path.exists(source):
            try:
                with open(source, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                log.error(f"Failed to load history from {source}: {e}")
                self.data = {}
        else:
            self.data = {}

    def save(self, brief_data: Dict[str, Any]) -> None:
        """Persist the full corpus for the next run. Never served to a browser."""
        from utils import atomic_write_json

        atomic_write_json({"briefing": brief_data}, self.filepath)

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


# Per-ticker news sidecars.
#
# The drawer needs the full audit — counted, merged and excluded items with
# their reasons — which is roughly 111 records today and grows with the
# watchlist. Putting that in dashboard_data.json would undo the payload/corpus
# split: the browser downloads that file whole on every page load, and nobody
# reads 111 audit rows on arrival. One file per ticker, fetched on first open.
NEWS_DIR = "news"


def write_coverage_sidecars(coverage: Dict[str, List[Dict[str, Any]]]) -> int:
    """Write ``news/<TICKER>.json`` per holding. Returns files written.

    Stale sidecars are removed rather than left behind: a holding rotated out
    of the watchlist would otherwise keep serving its last coverage forever,
    and a drawer showing month-old news as current is worse than an empty one.
    """
    from utils import atomic_write_json

    written = 0
    try:
        os.makedirs(NEWS_DIR, exist_ok=True)
        current = set()
        for ticker, items in (coverage or {}).items():
            safe = "".join(c for c in str(ticker).upper() if c.isalnum() or c in "-_")
            if not safe:
                continue
            current.add(f"{safe}.json")
            atomic_write_json(
                {"ticker": safe, "items": items}, os.path.join(NEWS_DIR, f"{safe}.json")
            )
            written += 1

        for stale in os.listdir(NEWS_DIR):
            if stale.endswith(".json") and stale not in current:
                os.remove(os.path.join(NEWS_DIR, stale))

        log.info(f"Coverage sidecars: {written} written to {NEWS_DIR}/.")
    except Exception as e:  # noqa: BLE001 - a sidecar must never break a run
        log.warning(f"Coverage sidecar write failed safely: {e!r}")
    return written
