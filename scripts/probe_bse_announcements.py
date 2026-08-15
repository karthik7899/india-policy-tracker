"""Find the parameter set AnnGetData actually wants, by testing a matrix.

Eight guesses at BSE endpoint names have already failed, and three guesses at
this endpoint's parameters returned "No Record Found!" — an alive endpoint
answering a wrong query. Guess nine would be the same mistake again, so this
varies one dimension at a time and reports which combinations return records.

Two suspicions drive the matrix, both from evidence rather than memory:

  * ``subcategory`` was absent from every earlier attempt. The canonical call
    bseindia.com's own page makes includes subcategory=-1, and an ASP.NET
    action with an unbound parameter can quietly filter everything out.
  * no earlier attempt carried cookies. That is exactly what unlocked NSE,
    whose API had been assumed to be blocking cloud IPs when it was only
    refusing un-cookied sessions.

Also probes the scrip master, because the announcements feed keys by numeric
SCRIP_CD and holdings can only be resolved through the ISIN join it provides.

Writes nothing. Never called by a briefing run.
"""

import datetime
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from providers import bse_announcements as bse  # noqa: E402
from providers.exchange_api import build_session  # noqa: E402

SAMPLE_SCRIP = "500325"  # Reliance: always has filings.


def _try(session, label, params):
    """One combination. Reports records, or exactly why not."""
    print(f"\n--- {label}")
    print(f"    params: {params}")
    try:
        rows = bse._get(session, bse.ANNOUNCEMENTS_URL, params)
    except Exception as e:  # noqa: BLE001 - the failure IS the measurement
        print(f"    {type(e).__name__}: {str(e)[:300]}")
        return []

    print(f"    records: {len(rows)}")
    if rows:
        print(f"    FIELD NAMES: {sorted(rows[0].keys())}")
        print(f"    FIRST RECORD:\n{json.dumps(rows[0], indent=6)[:900]}")
        normalized = bse.normalize(rows[0])
        print(f"    NORMALIZED : {normalized}")
        empty = [k for k, v in (normalized or {}).items() if not v]
        if empty:
            print(f"    EMPTY FIELDS: {empty} — check the aliases")
    return rows


def probe_announcements(session):
    print("=== ANNOUNCEMENTS PARAMETER MATRIX")
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    canonical = bse.announcement_params(week_ago, today)
    winners = []

    # 1. The canonical set, which is the one this provider ships with.
    if _try(session, "canonical (subcategory=-1, 7d, all scrips)", canonical):
        winners.append("canonical")

    # 2. Isolate subcategory — the parameter every earlier attempt omitted.
    without = {k: v for k, v in canonical.items() if k != "subcategory"}
    if _try(session, "canonical MINUS subcategory", without):
        winners.append("no-subcategory")

    # 3. One scrip. If the all-scrips query is what BSE dislikes, this shows it.
    if _try(
        session,
        "canonical + one scrip",
        bse.announcement_params(week_ago, today, scrip=SAMPLE_SCRIP),
    ):
        winners.append("one-scrip")

    # 4. Today only. A wide window may itself be the rejection.
    if _try(session, "today only", bse.announcement_params(today, today)):
        winners.append("today-only")

    # 5. strType=A. C is "company"; if the feed wants "all", C filters it out.
    if _try(session, "strType=A", {**canonical, "strType": "A"}):
        winners.append("strType=A")

    print(f"\n=== COMBINATIONS THAT RETURNED RECORDS: {winners or 'NONE'}")
    if not winners:
        print(
            "    Every combination came back empty. The endpoint answers, so\n"
            "    this is still a query problem — but the next step is reading\n"
            "    the parameters off a real request, and BSE's HTML pages are\n"
            "    Akamai-blocked to any browser we can drive. Prefer NSE."
        )


def probe_scrip_master(session):
    """The ISIN join. Without it BSE announcements cannot name a holding."""
    print("\n=== SCRIP MASTER (the SCRIP_CD <-> ISIN join)")
    try:
        rows = bse._get(
            session,
            bse.SCRIP_MASTER_URL,
            {
                "Group": "",
                "Scripcode": "",
                "industry": "",
                "segment": "Equity",
                "status": "Active",
            },
        )
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
