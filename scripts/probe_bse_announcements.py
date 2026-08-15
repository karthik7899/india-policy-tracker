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
        rows = bse._get(
            session, bse.ANNOUNCEMENTS_URL, params, validator=bse._validate_table
        )
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

    winners = []

    # The whole point of this run: the two vocabularies over the SAME window.
    # Announcement volume varies enough day to day that comparing yesterday's
    # result to today's would prove nothing.
    #
    # 1-4: the disclosure vocabulary (scrip_cd / categoryname / type), which
    # is the untested dimension. If the parameter NAMES were the problem all
    # along, one of these returns records where thirteen str* sets did not.
    if _try(
        session,
        "disclosure vocab, all categories, 7d",
        bse.announcement_params(week_ago, today),
    ):
        winners.append("disclosure-all")

    if _try(
        session,
        "disclosure vocab, categoryname=Result",
        bse.announcement_params(week_ago, today, category="Result"),
    ):
        winners.append("disclosure-result")

    if _try(
        session,
        "disclosure vocab, one scrip",
        bse.announcement_params(week_ago, today, scrip=SAMPLE_SCRIP),
    ):
        winners.append("disclosure-one-scrip")

    if _try(
        session,
        "disclosure vocab, today only",
        bse.announcement_params(today, today),
    ):
        winners.append("disclosure-today")

    # 5: the str* baseline, so this run says whether the difference is the
    # vocabulary or the day.
    legacy = bse.legacy_announcement_params(week_ago, today)
    if _try(session, "legacy str* vocab (measured baseline)", legacy):
        winners.append("legacy")

    # 6: date format. Every attempt so far sent YYYYMMDD; if BSE wants
    # DD/MM/YYYY then all of them matched nothing while answering politely,
    # which is exactly the behaviour observed.
    if _try(
        session,
        "disclosure vocab, DD/MM/YYYY dates",
        {
            **bse.announcement_params(week_ago, today),
            "fdate": week_ago.strftime("%d/%m/%Y"),
            "tdate": today.strftime("%d/%m/%Y"),
        },
    ):
        winners.append("dd/mm/yyyy")

    print(f"\n=== COMBINATIONS THAT RETURNED RECORDS: {winners or 'NONE'}")
    if not winners:
        print(
            "    Every combination came back empty. Twenty-five attempts now\n"
            "    span endpoint names, parameter names and values, date\n"
            "    formats, cookies, Referer host and path, and Origin. The\n"
            "    endpoint answers politely every time and yields nothing.\n"
            "    Do not add another guess: the only thing left is the query\n"
            "    BSE's own page sends, and that needs a capture from an\n"
            "    ordinary desktop browser. NSE carries filings meanwhile."
        )


_SCRIP_PARAMS = {
    "Group": "",
    "Scripcode": "",
    "industry": "",
    "segment": "Equity",
    "status": "Active",
}


def probe_header_variants():
    """Which Referer/Origin form does BSE accept? Decided in ONE run.

    The scrip master is the control: it returned 4,975 records with
    Referer=https://www.bseindia.com/ and no Origin, then began redirecting to
    /members/showinterest after the header set changed to the apex form. That
    is a causal claim, so it gets tested rather than assumed — same endpoint,
    same parameters, same minute, only the headers differ.
    """
    print("\n=== HEADER VARIANTS (control: the scrip master, known to work)")
    variants = [
        (
            "www Referer, no Origin (the form that returned 4,975)",
            {"Referer": "https://www.bseindia.com/"},
        ),
        (
            "apex Referer + apex Origin (the current header set)",
            {"Referer": "https://bseindia.com/", "Origin": "https://bseindia.com"},
        ),
        (
            "www Referer + www Origin",
            {
                "Referer": "https://www.bseindia.com/",
                "Origin": "https://www.bseindia.com",
            },
        ),
        ("apex Referer, no Origin", {"Referer": "https://bseindia.com/"}),
    ]

    for label, headers in variants:
        print(f"\n--- {label}")
        session = build_session()
        try:
            # Rebuilt from scratch, not merged over API_HEADERS: "no Origin"
            # has to mean the header is absent, and merging would leave the
            # module's own Origin in place and test nothing.
            merged = {
                k: v
                for k, v in bse.API_HEADERS.items()
                if k not in ("Referer", "Origin")
            }
            merged.update(headers)
            response = session.get(
                bse.SCRIP_MASTER_URL,
                params=_SCRIP_PARAMS,
                headers=merged,
                timeout=bse.REQUEST_TIMEOUT_S,
            )
            print(f"    status : {response.status_code}")
            print(f"    landed : {response.url[:120]}")
            print(f"    hops   : {len(response.history)}")
            body = response.text or ""
            if "showinterest" in (response.url or ""):
                print("    VERDICT: INTERCEPTED")
            elif response.status_code == 200 and body.startswith("["):
                print(f"    VERDICT: OK — {len(body)} bytes of JSON list")
            else:
                print(f"    VERDICT: unexpected — first 120 bytes {body[:120]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"    {type(e).__name__}: {str(e)[:200]}")
        finally:
            session.close()


def probe_referer_paths():
    """Does AnnGetData care WHICH PAGE the request claims to come from?

    Nineteen parameter sets have now returned "No Record Found!" with a clean
    200, and the header work established that this host checks the Referer's
    HOST (apex diverts, www serves). What no attempt has varied is the
    Referer's PATH: every one sent the bare host root.

    If BSE gates this endpoint on the referring page rather than the origin,
    the observed behaviour is exactly what you would expect — a polite empty
    answer to a request that did not come from the announcements screen.
    That is cheap to test and is the last dimension available without
    capturing a real request.

    Each variant handshakes through the page it then claims to come from,
    because a Referer naming a page the session never visited is not what a
    browser produces.
    """
    print("\n=== REFERER PATH VARIANTS (the last untested dimension)")
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)

    referers = [
        ("host root (every attempt so far)", "https://www.bseindia.com/"),
        ("the announcements page", "https://www.bseindia.com/corporates/ann"),
        ("announcements page, .html", "https://www.bseindia.com/corporates/ann.html"),
    ]
    param_sets = [
        ("disclosure vocab", bse.announcement_params(week_ago, today)),
        ("legacy str* vocab", bse.legacy_announcement_params(week_ago, today)),
    ]

    for ref_label, referer in referers:
        for param_label, params in param_sets:
            print(f"\n--- Referer={referer}  |  {param_label}")
            session = build_session()
            try:
                # Visit the page first: a Referer naming somewhere the session
                # has never been is not a state a browser can be in.
                if referer != "https://www.bseindia.com/":
                    session.get(referer, headers=bse.API_HEADERS, timeout=15)
                headers = {**bse.API_HEADERS, "Referer": referer}
                response = session.get(
                    bse.ANNOUNCEMENTS_URL,
                    params=params,
                    headers=headers,
                    timeout=bse.REQUEST_TIMEOUT_S,
                )
                body = (response.text or "")[:160]
                print(
                    f"    status : {response.status_code}  hops: {len(response.history)}"
                )
                if "showinterest" in (response.url or ""):
                    print("    VERDICT: INTERCEPTED")
                elif "No Record Found" in body:
                    print(f"    VERDICT: empty — {body!r}")
                else:
                    print(
                        f"    VERDICT: *** DIFFERENT *** {len(response.text or '')} bytes"
                    )
                    print(f"    body   : {body!r}")
            except Exception as e:  # noqa: BLE001
                print(f"    {type(e).__name__}: {str(e)[:200]}")
            finally:
                session.close()


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
    probe_header_variants()
    probe_referer_paths()
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
