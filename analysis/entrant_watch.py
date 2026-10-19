"""New entrants the radar flagged, kept in view after their headline ages out.

The radar reads only the last 45 days of news (competitive_intel.
RADAR_MAX_AGE_DAYS). Amber's move on mobile manufacturing was real, and an
alert about it should stop once the article is old — but that left nothing
watching Amber at all: it is not in Screener's peer table for any of our
electronics holdings. So a flagged challenger is kept here for WATCH_DAYS
after it was last flagged, and while it is:

  * its news is searched for every run, beside the holdings' partners and
    the demand anchors (scraper.watched_company_names), so a fresh move
    raises a fresh alert;
  * if it is a listed company, its Screener row joins the sector's peer
    comparison (providers/screener.py), so a challenger growing faster than
    our holdings keeps showing as a Competitive Threat.
"""

import datetime
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

from analysis.company_names import clean_registered_name
from logger import log
from utils import atomic_write_json

WATCH_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "watched_entrants.json",
)

# How long a challenger stays watched after the radar last flagged it.
WATCH_DAYS = 180


def load_watched(path: str = WATCH_PATH) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
        return [r for r in rows if isinstance(r, dict) and r.get("name")]
    except FileNotFoundError:
        return []
    except Exception as e:  # noqa: BLE001 - a watch list must never break a run
        log.warning(f"Could not load {os.path.basename(path)}: {e!r}")
        return []


def save_watched(rows: List[Dict[str, Any]], path: str = WATCH_PATH) -> bool:
    try:
        atomic_write_json(rows, path)
        return True
    except OSError as e:
        log.error(f"Failed to save {os.path.basename(path)}: {e}")
        return False


def listed_as(name: str, registered: Dict[str, str]) -> Optional[Tuple[str, str]]:
    """``(symbol, registered name)`` of the one NSE company whose registered
    name begins with ``name``, word for word; None when none does or several
    do. "Amber" is Amber Enterprises India; "Reliance" is several companies
    and so none of them."""
    words = str(name or "").lower().split()
    if not words:
        return None
    found = [
        (symbol, clean)
        for symbol, raw in (registered or {}).items()
        for clean in [clean_registered_name(raw)]
        if clean.lower().split()[: len(words)] == words
    ]
    return found[0] if len(found) == 1 else None


def update_watched(
    rows: List[Dict[str, Any]],
    entrants: Iterable[Dict[str, Any]],
    registered: Dict[str, str],
    today: str = "",
) -> List[Dict[str, Any]]:
    """This run's radar entrants added or refreshed; any not flagged for
    WATCH_DAYS dropped."""
    today = today or datetime.date.today().isoformat()
    by_key = {(r.get("sector"), str(r.get("name")).lower()): r for r in rows or []}
    for entrant in entrants or []:
        name = str(entrant.get("challenger") or "").strip()
        sector = entrant.get("sector")
        if not name or not sector:
            continue
        row = by_key.get((sector, name.lower()))
        if row is None:
            listed = listed_as(name, registered)
            row = {
                "name": name,
                "sector": sector,
                "ticker": listed[0] if listed else None,
                "registered_name": listed[1] if listed else None,
                "first_seen": today,
            }
            by_key[(sector, name.lower())] = row
        row["last_seen"] = today
        row["headline"] = str(entrant.get("headline") or "")[:180]
    cutoff = (
        datetime.date.fromisoformat(today) - datetime.timedelta(days=WATCH_DAYS)
    ).isoformat()
    kept = [r for r in by_key.values() if str(r.get("last_seen", "")) >= cutoff]
    return sorted(kept, key=lambda r: (str(r.get("sector")), str(r.get("name"))))


def search_names(rows: Iterable[Dict[str, Any]]) -> List[str]:
    """What to search the news for: the registered name where there is one
    ("Amber Enterprises", not a bare "Amber"), else the name as flagged."""
    names = []
    for row in rows or []:
        name = str(row.get("registered_name") or row.get("name") or "").strip()
        # "Amber Enterprises India": headlines drop the country.
        if name.lower().endswith(" india") and len(name.split()) > 2:
            name = name[: -len(" india")]
        if name:
            names.append(name)
    return names


def screener_entrants(rows: Iterable[Dict[str, Any]]) -> List[Tuple[str, str, str]]:
    """``(ticker, name, sector)`` for the listed ones: their Screener row joins
    that sector's peer comparison."""
    return [
        (r["ticker"], r.get("registered_name") or r["name"], r["sector"])
        for r in rows or []
        if r.get("ticker") and r.get("sector")
    ]
