"""Verify the two newest data sources against the live hosts.

Both were built and unit-tested but never run against the real thing:

  1. NSE delivery (sec_bhavdata_full) — does it still publish, with the
     columns the parser expects, and how many of OUR holdings appear in it?
  2. BSE scrip master merged into the ISIN master — how many identities does
     it actually add, and, the question that decides whether the merge is
     safe at all, how many symbols does it DISAGREE with?

That second number is the point of this script. NSE's SYMBOL and BSE's
scrip_id are ticker-like codes in different namespaces, and nothing
guarantees a BSE-only scrip_id is not also some other company's NSE symbol.
The merge already refuses to overwrite, so a collision cannot corrupt a
mapping we trust — but "cannot corrupt" is not the same as "is fine", and
until this is counted the risk is an assumption. A high count means the
merge needs rethinking rather than tuning.

Runs against a COPY of the committed master and writes nothing.
"""

import asyncio
import datetime
import json
import os
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])

import aiohttp  # noqa: E402

from providers import isin_master as im  # noqa: E402
from providers import nse_delivery as nd  # noqa: E402

_ROOT = __file__.rsplit("/", 2)[0]


def watchlist_tickers():
    """Every ticker we hold, so coverage is measured against the real book
    rather than against a sample that flatters it."""
    try:
        with open(os.path.join(_ROOT, "watchlist.json"), encoding="utf-8") as f:
            watchlist = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"    could not read watchlist.json: {e}")
        return []
    return [
        str(s.get("ticker") or "").upper()
        for stocks in watchlist.values()
        for s in (stocks or [])
        if isinstance(s, dict) and s.get("ticker")
    ]


async def probe_delivery(tickers):
    print("=== NSE DELIVERY (sec_bhavdata_full)")
    async with aiohttp.ClientSession() as session:
        rows = await nd.fetch_delivery_async(session)

    if not rows:
        print("    NO DATA. Either the file moved or the archive refused us.")
        return

    print(f"    securities (EQ only): {len(rows)}")

    covered = [t for t in tickers if t in rows]
    print(f"    watchlist coverage  : {len(covered)} of {len(tickers)} holdings")
    missing = [t for t in tickers if t not in rows]
    if missing:
        # Named, not counted: a BSE-only listing legitimately absent from an
        # NSE file is a different problem from a ticker we have spelled wrong.
        print(f"    NOT in the file     : {missing[:15]}")
        await explain_missing(missing)

    # Does the parser actually populate the fields, or silently produce Nones?
    with_pct = [t for t in covered if rows[t].get("deliv_pct") is not None]
    print(f"    delivery reported   : {len(with_pct)} of {len(covered)} covered")

    print("\n    SAMPLE (first 8 holdings):")
    for ticker in covered[:8]:
        row = rows[ticker]
        band = nd.classify_delivery(row.get("deliv_pct"))
        print(
            f"      {ticker:<14} deliv={row.get('deliv_pct')!s:>7}%  "
            f"turnover={row.get('turnover_cr')!s:>9} Cr  band={band}"
        )

    churn = [
        t for t in covered if nd.classify_delivery(rows[t]["deliv_pct"]) == "churn"
    ]
    print(f"\n    CHURN band ({len(churn)} holdings) — turnover flatters these:")
    for ticker in churn[:10]:
        print(f"      {ticker}: {nd.delivery_note(rows[ticker])}")


async def explain_missing(missing):
    """Why is each missing holding missing? Answered from the file, not guessed.

    Three possibilities with different fixes: the symbol trades under a
    non-EQ series (widen the filter), it is BSE-only (expected, no fix), or
    the ticker is wrong in the watchlist (a data bug worth finding).
    """
    print("\n    WHY THEY ARE MISSING (re-read with no series filter):")
    async with aiohttp.ClientSession() as session:
        for offset in range(nd.MAX_LOOKBACK_DAYS + 1):
            day = datetime.date.today() - datetime.timedelta(days=offset)
            try:
                async with session.get(
                    nd.url_for(day), headers=nd.HEADERS, timeout=nd.REQUEST_TIMEOUT_S
                ) as response:
                    if response.status != 200:
                        continue
                    text = await response.text()
            except Exception:  # noqa: BLE001
                continue
            everything = nd.parse_delivery_csv(text, series=None)
            for ticker in missing:
                row = everything.get(ticker)
                if row:
                    print(
                        f"      {ticker:<12} present under SERIES={row['series']!r} "
                        "— widen the filter, or accept the exclusion"
                    )
                else:
                    print(
                        f"      {ticker:<12} absent under EVERY series "
                        "— BSE-only listing, or the watchlist ticker is wrong"
                    )
            return
    print("      could not re-read the file")


def probe_isin_merge():
    print("\n=== BSE SCRIP MASTER -> ISIN MASTER")
    master = im.load_isin_master()
    print(f"    committed master    : {len(master)} symbols")

    rows = im.fetch_scrip_master_sync()
    if not rows:
        print("    NO DATA from the BSE scrip master.")
        return
    print(f"    BSE scrips fetched  : {len(rows)}")

    fetched = im.parse_bse_scrip_rows(rows)
    print(f"    with a valid ISIN   : {len(fetched)}")

    # A COPY: this is a measurement, not a migration.
    trial = dict(master)
    added, conflicts = im.merge_new_symbols(trial, fetched, "BSE")
    print(f"    would ADD           : {added} new symbols -> {len(trial)} total")
    print(f"    DISAGREEMENTS       : {conflicts}")

    if conflicts:
        print("\n    The disagreements, which decide whether this merge is safe:")
        shown = 0
        for symbol, isin in fetched.items():
            if symbol in master and master[symbol] != isin:
                print(f"      {symbol:<14} NSE={master[symbol]}  BSE={isin}")
                shown += 1
                if shown >= 20:
                    break
        rate = 100.0 * conflicts / max(1, len(fetched))
        print(f"\n    collision rate: {rate:.2f}% of BSE symbols")
        print(
            "    A few are dual-listing quirks. A lot means the two ticker\n"
            "    namespaces genuinely collide and this merge needs rethinking."
        )
    else:
        print("    No symbol disagrees. The namespaces align on the overlap.")


async def main():
    tickers = watchlist_tickers()
    print(f"watchlist holdings: {len(tickers)}\n")
    await probe_delivery(tickers)
    probe_isin_merge()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except Exception as e:  # noqa: BLE001 - a probe reports, it does not crash
        print(f"    PROBE FAILED: {type(e).__name__}: {e}")
        sys.exit(0)
