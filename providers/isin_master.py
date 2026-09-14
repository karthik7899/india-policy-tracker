"""Symbol→ISIN master: the automated identity source for entities.py.

Per-stock ISIN scrapes all failed from CI (Screener doesn't expose it,
Yahoo's experimental lookup can't handle .NS symbols, NSE's site 403s
GitHub runners) — but ISIN↔symbol is a *bulk* dataset, not a per-stock
lookup. NSE publishes one CSV of every listed equity with its ISIN
(EQUITY_L.csv on its archive host), so a committed snapshot serves without
network.

IT CAN GO STALE, THOUGH. This module used to say an ISIN "never changes for
the life of a listing", and therefore that the snapshot "cannot go stale the
way prices do — it can only lack listings newer than itself". That is not
true, and the whole never-overwrite rule was built on it. A corporate action
that changes the share itself — a split, a face-value change — issues a NEW
ISIN for the same company: the issuer prefix stays, the issue-series digits
increment, the check digit follows. INE814H01011 and INE814H01029 are both
Adani Power, before and after.

So the snapshot drifts every time a holding splits, and a rule that refused
to overwrite guaranteed the drift was permanent. See the caution below for
how that was measured.

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
also some other company's NSE symbol. Collisions are counted and logged
rather than assumed rare, because that count is the only evidence of whether
the risk is real.

The count answered, and the answer was not the collision it was watching for.

It sat at exactly 140 NSE and 130 BSE on every run for days — too stable to
be feed noise. Letting NSE apply its 140 and reading the resulting git diff
settled what they were: in all 140, the ISIN's first nine characters were
unchanged and only the issue-series digits moved, always upward. Not one was a
different issuer. They were the SAME companies after a corporate action, and
the master was holding pre-split values — including six live holdings
(ADANIPOWER, COFORGE, DIACABS, PERSISTENT, PGIL, VBL).

So the cross-namespace risk this caution was written about remains
unmeasured; what the counter actually caught was staleness, and the rule
meant to protect identity data was the thing preserving the stale copy.

Precedence is therefore explicit rather than positional: NSE merges as an
AUTHORITATIVE source and corrects what it disagrees with, because a symbol in
NSE's equity list is an NSE listing and NSE publishes its current ISIN. BSE
keeps never-overwrite, so its 130 remain an honest measure of how much the
two namespaces really do disagree — now that NSE's side is current, that
number is worth watching again from a clean baseline.

A bound on how much of a feed may be corrected at once keeps the protection
the old rule was reaching for: a corrupt fetch still must not rewrite the
snapshot wholesale.
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


# A source with authority may correct entries it disagrees with, but not
# without limit. An exchange's ISINs do not change wholesale overnight, so a
# fetch that wants to rewrite more than this fraction of what it carries is a
# corrupt feed rather than news, and applying it would destroy good identity
# data that the committed snapshot cannot get back.
#
# The observed real figure is ~7% (140 of ~2,000 NSE symbols), which is
# exactly the cross-namespace collision this guard must NOT block.
MAX_CORRECTION_FRACTION = 0.25

# ...and a fraction is only meaningful once there is enough feed to judge.
# One row disagreeing out of one is 100% and says nothing; the corruption this
# guards against is a mass rewrite of a full exchange listing. Below this size
# the blast radius is small enough that NSE re-asserting the right value on the
# next run is adequate protection on its own.
MIN_FETCH_FOR_CORRECTION_GUARD = 50


def merge_new_symbols(master, fetched, source, authoritative=False):
    """Merge a source into the master. Returns (added, conflicts, corrected).

    A conflict is the same symbol carrying a different ISIN.

    For a NON-authoritative source it is never applied: it has no standing to
    say which of two values is current, so the incumbent stays and the
    disagreement is counted.

    For an AUTHORITATIVE source it is corrected, and that distinction is the
    point of this function. The module has always intended NSE to win:

        "NSE goes first deliberately: it is the namespace the watchlist
         speaks, so where the two exchanges disagree on a ticker, the NSE
         mapping is the one that must survive."

    Ordering alone cannot deliver that, because the master is committed and
    reloaded. Going first only helps while it is empty, which is true exactly
    once — afterwards "never overwrite" means the NSE value can never land.

    That mattered more than a tie-break, because ISINs DO change: a split or
    face-value change issues a new one for the same company. All 140 symbols
    NSE was being refused turned out to be exactly that — same issuer, later
    issue series — so the rule was not protecting identity data, it was
    pinning it to a pre-split value.

    A symbol present in NSE's equity list IS an NSE listing and NSE publishes
    its current ISIN, so NSE is authoritative for it by construction. BSE
    keeps never-overwrite: it cannot arbitrate which value is current either.
    """
    added = conflicts = corrected = 0
    divergent = {}
    for symbol, isin in fetched.items():
        existing = master.get(symbol)
        if existing is None:
            master[symbol] = isin
            added += 1
        elif existing != isin:
            conflicts += 1
            divergent[symbol] = (existing, isin)

    if authoritative and divergent:
        share = len(divergent) / max(len(fetched), 1)
        if (
            len(fetched) >= MIN_FETCH_FOR_CORRECTION_GUARD
            and share > MAX_CORRECTION_FRACTION
        ):
            log.warning(
                f"ISIN master: {source} disagrees on {len(divergent)} of "
                f"{len(fetched)} symbols ({share:.0%}). That is too much of the "
                "feed to be real; declining the whole correction and keeping "
                "the committed mapping."
            )
        else:
            for symbol, (_old, new) in divergent.items():
                master[symbol] = new
            corrected = len(divergent)
            sample = ", ".join(
                f"{s} {old}->{new}"
                for s, (old, new) in list(sorted(divergent.items()))[:5]
            )
            log.warning(
                f"ISIN master: corrected {corrected} symbol(s) to {source}'s "
                f"mapping — {source} is authoritative for its own namespace and "
                f"these were held by another. e.g. {sample}"
            )
            conflicts = 0

    if conflicts:
        log.warning(
            f"ISIN master: {conflicts} symbol(s) from {source} disagree with "
            "the existing mapping and were NOT applied. Expected where a BSE "
            "scrip_id collides with a different company's NSE symbol; NSE "
            "holds the key and BSE yields."
        )
    return added, conflicts, corrected


async def refresh_bse_scrips(master):
    """Merge BSE's scrip master. Never raises; returns the count added.

    to_thread because the BSE provider is sync requests (it needs cookie-jar
    persistence) and this must not block the event loop.
    """
    import asyncio

    try:
        rows = await asyncio.to_thread(fetch_scrip_master_sync)
        added, _conflicts, _corrected = merge_new_symbols(
            master, parse_bse_scrip_rows(rows), "BSE"
        )
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
    corrected = 0
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
                nse_added, _conflicts, corrected = merge_new_symbols(
                    master, parse_equity_csv(text), "NSE", authoritative=True
                )
                added += nse_added
                log.info(f"ISIN master: {nse_added} new listings from NSE.")
    except Exception as e:
        log.info(
            f"ISIN master NSE refresh skipped ({type(e).__name__}: "
            f"{str(e)[:120]}); committed snapshot still serves."
        )

    added += await refresh_bse_scrips(master)

    # A correction changes the file even when nothing was added, and once the
    # master is saturated "nothing added" is every run. Persisting only on
    # `added` would compute the corrected mapping and then throw it away
    # daily — the fix would appear to work in the log and never reach disk.
    if added or corrected:
        atomic_write_json(dict(sorted(master.items())), path)
        log.info(
            f"ISIN master refreshed: {added} new listing(s) added, "
            f"{corrected} corrected, {len(master)} total."
        )
    else:
        log.info(f"ISIN master refresh: no changes ({len(master)} total).")
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
