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
  - BSE's scrip master is merged after NSE's, for the same reason and under
    the same rule. It carries ~4,975 active equity scrips against NSE's
    ~2,000 and includes BSE-only listings, so it is the larger source of
    new identities.

A CAUTION ABOUT THE BSE MERGE. NSE's SYMBOL and BSE's scrip_id are both
ticker-like codes and usually agree for a dual-listed company, but they are
different namespaces: nothing guarantees that a BSE-only scrip_id is not
also some other company's NSE symbol. NSE is merged first and existing
entries are never overwritten, so a collision cannot corrupt a mapping we
already trust — it can only decline to add one. Collisions are counted and
logged rather than assumed rare, because that count is the only evidence of
whether the risk is real.
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


def fetch_scrip_master_sync():
    """Indirection so tests can stub the network at one obvious seam, rather
    than reaching the real exchange from a unit test."""
    from providers.bse_announcements import fetch_scrip_master

    return fetch_scrip_master()


def parse_bse_scrip_rows(rows):
    """BSE scrip master rows -> scrip_id→ISIN. Keyed on scrip_id because that
    is BSE's ticker; SCRIP_CD is a numeric code the watchlist never uses."""
    mapping = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("scrip_id") or "").strip().upper()
        isin = str(row.get("ISIN_NUMBER") or "").strip().upper()
        if symbol and _valid_isin(isin):
            mapping[symbol] = isin
    return mapping


def merge_new_symbols(master, fetched, source):
    """Adds only symbols the master lacks. Returns (added, conflicts).

    A conflict is the same symbol carrying a different ISIN. It is never
    applied — ISINs do not change, so a divergent row is more likely a feed
    glitch or a cross-namespace ticker collision than news — but it is
    counted, because that number is the only way to learn whether merging a
    second exchange's ticker namespace is safe.
    """
    added = conflicts = 0
    for symbol, isin in fetched.items():
        existing = master.get(symbol)
        if existing is None:
            master[symbol] = isin
            added += 1
        elif existing != isin:
            conflicts += 1
    if conflicts:
        log.warning(
            f"ISIN master: {conflicts} symbol(s) from {source} disagree with "
            "the existing mapping and were NOT applied. A high count here "
            "means the two ticker namespaces collide and this merge needs "
            "rethinking."
        )
    return added, conflicts


async def refresh_bse_scrips(master):
    """Merge BSE's scrip master. Never raises; returns the count added.

    to_thread because the BSE provider is sync requests (it needs cookie-jar
    persistence) and this must not block the event loop.
    """
    import asyncio

    try:
        rows = await asyncio.to_thread(fetch_scrip_master_sync)
        added, _conflicts = merge_new_symbols(master, parse_bse_scrip_rows(rows), "BSE")
        log.info(f"ISIN master: {added} new listings from BSE ({len(rows)} scrips).")
        return added
    except Exception as e:  # noqa: BLE001 - an enrichment must not end a run
        log.info(
            f"BSE ISIN merge skipped ({type(e).__name__}: {str(e)[:120]}); "
            "the NSE-derived master still serves."
        )
        return 0


async def refresh_isin_master_async(session, master, path=MASTER_PATH):
    """Merge NEW listings from NSE's equity list and BSE's scrip master.

    Mutates ``master`` in place and persists once, after both sources, so a
    run costs a single write rather than one per exchange. Never raises;
    returns the total count added. Existing entries are never overwritten —
    ISINs don't change, so a divergent live row is more likely a feed glitch
    than news.

    NSE goes first deliberately: it is the namespace the watchlist speaks, so
    where the two exchanges disagree on a ticker, the NSE mapping is the one
    that must survive.
    """
    added = 0
    try:
        async with session.get(
            _NSE_EQUITY_LIST_URL, headers=_HEADERS, timeout=15, allow_redirects=False
        ) as response:
            if response.status != 200:
                log.info(
                    f"ISIN master: NSE archive returned {response.status} "
                    "(committed snapshot still serves)."
                )
            else:
                text = await response.text()
                nse_added, _ = merge_new_symbols(master, parse_equity_csv(text), "NSE")
                added += nse_added
                log.info(f"ISIN master: {nse_added} new listings from NSE.")
    except Exception as e:
        log.info(
            f"ISIN master NSE refresh skipped ({type(e).__name__}: "
            f"{str(e)[:120]}); committed snapshot still serves."
        )

    added += await refresh_bse_scrips(master)

    if added:
        atomic_write_json(dict(sorted(master.items())), path)
        log.info(
            f"ISIN master refreshed: {added} new listings added, {len(master)} total."
        )
    else:
        log.info(f"ISIN master refresh: no new listings ({len(master)} total).")
    return added


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
