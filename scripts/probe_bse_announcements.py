"""Verify BSE's announcements feed, and report what its records look like.

This started as a search: thirty-two attempts across endpoint names,
parameter names and values, date formats, cookies, Referer host and path,
and Origin. All of them returned "No Record Found!" from
BseIndiaAPI/api/AnnGetData/w.

The search ended when the real request was captured from Chrome's Network
tab on the live announcements page:

    https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
      ?pageno=1&strCat=-1&strPrevDate=20260815&strScrip=&strSearch=P
      &strToDate=20260815&strType=C&subcategory=-1

The parameters were right the whole time. The PATH was wrong, and it was
always an assumption rather than a measurement — DevTools' Name column shows
only the last segment, and every BSE endpoint ends in /w, so AnnGetData and
AnnSubCategoryGetData are indistinguishable in that list. AnnGetData is a
real endpoint that answers this exact query with a polite empty result,
which is the most expensive kind of wrong: it looks like a data problem for
as long as you care to look.

So this file is now a verification tool, not a search. It confirms the feed
still answers, reports the record shape so alias drift is visible, and
checks the scrip master that resolves holdings.

Writes nothing. Never called by a briefing run.
"""

import datetime
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from providers import bse_announcements as bse  # noqa: E402
from providers.exchange_api import build_session  # noqa: E402

_SCRIP_PARAMS = {
    "Group": "",
    "Scripcode": "",
    "industry": "",
    "segment": "Equity",
    "status": "Active",
}


def probe_announcements(session):
    """The captured query, against the captured endpoint."""
    print("=== ANNOUNCEMENTS")
    today = datetime.date.today()

    for label, day_from, day_to in [
        ("today", today, today),
        ("yesterday", today - datetime.timedelta(days=1), today),
    ]:
        params = bse.announcement_params(day_from, day_to)
        print(f"\n--- {label}")
        print(f"    {bse.ANNOUNCEMENTS_URL}")
        print(f"    params: {params}")
        try:
            rows = bse._get(
                session, bse.ANNOUNCEMENTS_URL, params, validator=bse._validate_table
            )
        except Exception as e:  # noqa: BLE001 - the failure IS the measurement
            print(f"    {type(e).__name__}: {str(e)[:300]}")
            continue

        print(f"    records: {len(rows)}")
        if not rows:
            continue

        print(f"\n    FIELD NAMES: {sorted(rows[0].keys())}")
        print(f"    FIRST RECORD:\n{json.dumps(rows[0], indent=6)[:1000]}")
        normalized = bse.normalize(rows[0])
        print(f"\n    NORMALIZED : {normalized}")
        empty = [k for k, v in (normalized or {}).items() if not v]
        if empty:
            print(f"    EMPTY FIELDS: {empty} — the aliases need updating")
        else:
            print("    All fields populated.")
        return rows
    return []


def probe_scrip_master(session):
    """The ISIN join. Without it BSE announcements cannot name a holding."""
    print("\n=== SCRIP MASTER (the SCRIP_CD <-> ISIN join)")
    try:
        rows = bse._get(session, bse.SCRIP_MASTER_URL, _SCRIP_PARAMS)
    except Exception as e:  # noqa: BLE001
        print(f"    {type(e).__name__}: {str(e)[:300]}")
        return

    print(f"    records: {len(rows)}")
    if rows:
        print(f"    FIELD NAMES: {sorted(rows[0].keys())}")
        print(f"    SAMPLE     : {json.dumps(rows[0])[:400]}")


def main():
    session = build_session(bse.API_HEADERS)
    try:
        got_cookies = bse.handshake(session)
        print(
            f"=== HANDSHAKE: cookies={got_cookies} -> {sorted(session.cookies.keys())}"
        )
        probe_announcements(session)
        probe_scrip_master(session)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001 - a probe reports, it does not crash
        print(f"    PROBE FAILED: {type(e).__name__}: {e}")
        sys.exit(0)
