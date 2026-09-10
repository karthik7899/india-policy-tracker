"""Split the heavy payload keys into files the browser fetches on demand.

MEASURED on the committed payload (2026-09-10): dashboard_data.json is 642 KB
of JSON, and two keys are 28% of it —

    stock_topics       120,527 bytes   27.7%   (54 holdings)
    buffett_valuation   58,646 bytes   13.5%   (70 holdings)

Neither renders on the first screen. stock_topics opens inside a holding's
drawer; buffett_valuation is one lens on the valuation view. Every visitor
pays for both on every load regardless.

This follows history/store.write_coverage_sidecars, which already does exactly
this for the per-ticker news audit and has been in production for months. The
same three rules apply, and each is there for a reason:

  * Stale files are removed, not left. A holding rotated out of the watchlist
    would otherwise keep serving its last figures forever, and a drawer
    showing month-old data as current is worse than an empty one.
  * Ticker names are sanitised before they touch a path. Coverage sidecars
    have a test for `../../etc/passwd`; the same input reaches here.
  * A failure is swallowed. A sidecar is a convenience — losing one costs a
    drawer, losing the run costs the briefing.

What is NOT done here: dropping keys that are merely empty. payload.py draws a
deliberate distinction between a key that is absent (the step never ran) and
one that is `[]` (it ran and found nothing), and the seven empty keys in the
current payload total about 14 bytes. They are information, not weight.
"""

import os
from typing import Any, Dict, List, Tuple

from logger import log

# Sibling of news/, and named for what it holds rather than which view reads
# it — views get reorganised, the data does not.
DATA_DIR = "data"

# Keys moved out of the payload, with how each is split.
#
# "per_ticker" writes data/<key>/<TICKER>.json from a {ticker: value} dict, so
# a drawer fetches one holding rather than all of them. "whole" writes a single
# data/<key>.json, for a key one view needs in full.
SPLIT_PER_TICKER = ("stock_topics",)
SPLIT_WHOLE = ("buffett_valuation",)


def _safe_ticker(ticker: Any) -> str:
    """A ticker reduced to what may appear in a filename.

    Same rule as the coverage sidecars: anything not alphanumeric, hyphen or
    underscore is dropped, so a hostile or malformed ticker cannot climb out
    of the directory. Returns "" for a ticker with nothing usable left, and
    the caller skips it rather than writing a file named for nothing.
    """
    return "".join(c for c in str(ticker or "").upper() if c.isalnum() or c in "-_")


def _prune(directory: str, keep: set) -> int:
    """Delete .json files in directory that are not in keep. Returns removed."""
    removed = 0
    if not os.path.isdir(directory):
        return 0
    for name in os.listdir(directory):
        if name.endswith(".json") and name not in keep:
            os.remove(os.path.join(directory, name))
            removed += 1
    return removed


def write_sidecars(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Write the heavy keys to data/ and return (lightened payload, files).

    The payload is copied, never mutated: the caller's dict is also what the
    email and the corpus were built from, and quietly emptying a key it still
    reads is the class of bug this repo keeps finding.

    Each split key is replaced by a manifest the browser can act on without a
    round trip — for a per-ticker split, the list of tickers that have a file;
    for a whole split, just the path. A missing manifest means the split did
    not happen, and the frontend falls back to treating the data as absent,
    which is the same handling as a key that was never computed.
    """
    from utils import atomic_write_json

    lightened = dict(payload or {})
    written = 0

    try:

        for key in SPLIT_PER_TICKER:
            source = lightened.get(key)
            if not isinstance(source, dict) or not source:
                continue
            # Created here, not up front: a run with nothing to split must
            # not leave an empty data/ implying there is something in it.
            directory = os.path.join(DATA_DIR, key)
            os.makedirs(directory, exist_ok=True)
            current, tickers = set(), []
            for ticker, value in source.items():
                safe = _safe_ticker(ticker)
                if not safe:
                    continue
                atomic_write_json(
                    {"ticker": safe, "value": value},
                    os.path.join(directory, f"{safe}.json"),
                )
                current.add(f"{safe}.json")
                tickers.append(safe)
                written += 1
            _prune(directory, current)
            # The manifest replaces the data. Sorted so the committed payload
            # does not churn on dict ordering between runs.
            lightened[key] = {
                "sidecar": f"{DATA_DIR}/{key}",
                "tickers": sorted(tickers),
            }

        for key in SPLIT_WHOLE:
            source = lightened.get(key)
            if source in (None, [], {}):
                continue
            os.makedirs(DATA_DIR, exist_ok=True)
            path = os.path.join(DATA_DIR, f"{key}.json")
            atomic_write_json({"value": source}, path)
            written += 1
            count = len(source) if hasattr(source, "__len__") else 1
            lightened[key] = {"sidecar": path, "count": count}

        if written:
            log.info(f"Payload sidecars: {written} file(s) written to {DATA_DIR}/.")
    except Exception as e:  # noqa: BLE001 - a sidecar must never break a run
        log.warning(f"Sidecar split failed safely: {e!r}")
        return dict(payload or {}), 0

    return lightened, written


def deduplicate_sector_news(payload: Dict[str, Any], sector_keys: List[str]) -> int:
    """Drop per-sector news lists whose items already ride in sector_blocks.

    MEASURED: 49 of 70 items across the 18 per-sector keys also appear inside
    sector_blocks, which the sectors view renders from. Only a key that is
    ENTIRELY duplicated is dropped — a partial overlap means the key still
    carries something the blocks do not, and removing it would lose it.

    Returns the number of keys dropped.
    """
    import json

    blocks = payload.get("sector_blocks")
    if not blocks:
        return 0
    blob = json.dumps(blocks)

    dropped = 0
    for key in sector_keys:
        items = payload.get(key)
        if not isinstance(items, list) or not items:
            continue
        titles = [str(i.get("title", "")) for i in items if isinstance(i, dict)]
        if len(titles) != len(items):
            continue  # a non-dict row: leave the key alone
        if all(t and t[:60] in blob for t in titles):
            del payload[key]
            dropped += 1
    return dropped
