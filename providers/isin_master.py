"""Symbol→ISIN master: the automated identity source for entities.py.

Per-stock ISIN scrapes all failed from CI (Screener doesn't expose it,
Yahoo's experimental lookup can't handle .NS symbols, NSE's site 403s
GitHub runners) — but ISIN↔symbol is a *bulk* dataset, not a per-stock
lookup. NSE publishes one CSV of every listed equity with its ISIN
(EQUITY_L.csv on its archive host), and because an ISIN never changes for
the life of a listing, a committed snapshot cannot go stale the way
prices do — it can only lack listings newer than itself.

So this provider is offline-first:

  - ``isin_master.json`` (committed, ~2k symbols) resolves instantly with
    zero network — auto-discovered stocks get their ISIN the first run
    they appear, no manual seeding.
  - Once per run, a fail-safe fetch of the live archive CSV merges any
    NEW symbols into the master (existing entries are never overwritten —
    a transient bad row must not corrupt known-good identity data). If
    the archive host also blocks CI, the committed snapshot simply keeps
    serving; the auto-commit workflow persists whatever was learned.
"""

import csv
import io
import os

from logger import log
from utils import atomic_write_json

MASTER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "isin_master.json"
)

_NSE_EQUITY_LIST_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
}


def _valid_isin(isin):
    return isinstance(isin, str) and len(isin) == 12 and isin.startswith("IN")


def load_isin_master(path=MASTER_PATH):
    """Committed symbol→ISIN mapping; empty dict on any problem."""
    import json

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k).upper(): v for k, v in data.items() if _valid_isin(v)}
    except FileNotFoundError:
        log.warning("isin_master.json not found — ISIN features run uncovered.")
    except Exception as e:
        log.warning(f"Could not load isin_master.json: {e}")
    return {}


def parse_equity_csv(text):
    """Parses NSE's EQUITY_L.csv (SYMBOL, ..., ISIN NUMBER) into a
    symbol→ISIN dict. Header names carry stray spaces in the wild, so
    lookups are normalized."""
    mapping = {}
    if not text:
        return mapping
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            cleaned = {
                (k or "").strip().upper(): (v or "").strip() for k, v in row.items()
            }
            symbol = cleaned.get("SYMBOL", "").upper()
            isin = cleaned.get("ISIN NUMBER", "").upper()
            if symbol and _valid_isin(isin):
                mapping[symbol] = isin
    except Exception as e:
        log.warning(f"Could not parse NSE equity list CSV: {e}")
    return mapping


async def refresh_isin_master_async(session, master, path=MASTER_PATH):
    """Single fail-safe attempt to merge NEW listings from NSE's live
    equity list into the master. Mutates ``master`` in place and persists
    when anything was learned. Never raises; returns the count of added
    symbols. Existing entries are never overwritten — ISINs don't change,
    so a divergent live row is more likely a feed glitch than news.
    """
    try:
        async with session.get(
            _NSE_EQUITY_LIST_URL, headers=_HEADERS, timeout=15, allow_redirects=False
        ) as response:
            if response.status != 200:
                log.info(
                    f"ISIN master refresh skipped: NSE archive returned "
                    f"{response.status} (committed snapshot still serves)."
                )
                return 0
            text = await response.text()
        fetched = parse_equity_csv(text)
        added = 0
        for symbol, isin in fetched.items():
            if symbol not in master:
                master[symbol] = isin
                added += 1
        if added:
            atomic_write_json(dict(sorted(master.items())), path)
            log.info(f"ISIN master refreshed: {added} new listings added.")
        else:
            log.info("ISIN master refresh: no new listings.")
        return added
    except Exception as e:
        log.info(
            f"ISIN master refresh skipped ({type(e).__name__}: {str(e)[:120]}); "
            "committed snapshot still serves."
        )
        return 0


def annotate_watchlist_isins(watchlist, master):
    """Stamps ``screener.isin`` on every holding the master knows,
    powering entities.py (duplicate detection, rotation dedup guard).
    Idempotent; never overwrites an ISIN already present. Returns the
    number of holdings now carrying an ISIN."""
    covered = 0
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            screener = stock.setdefault("screener", {})
            if not isinstance(screener, dict):
                continue
            if not screener.get("isin"):
                isin = master.get(str(stock.get("ticker", "")).upper())
                if isin:
                    screener["isin"] = isin
            if screener.get("isin"):
                covered += 1
    return covered
