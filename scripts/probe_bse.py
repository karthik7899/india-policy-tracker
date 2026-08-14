"""Probe which BSE endpoints are usable, and what they actually return.

BSE is blocked from the development sandbox (403 on CONNECT, same egress
policy as Screener and Yahoo), so every claim about these endpoints would
otherwise be from memory. This runs on the Actions runner, which reaches them,
and reports measured facts: status, content type, size, and enough of the
shape to design against.

It writes nothing into the pipeline and is never called by a briefing run. It
exists to answer three questions the current data gaps turn on:

  1. Bhavcopy — can one request replace 70 per-holding Yahoo calls, and does
     it carry the volume needed for turnover and a 52-week range?
  2. Shareholding pattern — does BSE expose the promoter pledge figure that
     Screener's page did not yield for any of 69 holdings?
  3. Announcements — are these real filings with real dates, rather than the
     Google News RSS query that currently stands in for "Corporate Filings"?

Nothing here is asserted as working. Each probe prints what it got, including
the failures, because a probe that hides its misses is worse than none.
"""

import datetime
import json
import sys

import requests

# BSE rejects requests without a browser-ish UA and a same-site Referer. That
# is not an authentication boundary, just their bot filter; stating it here so
# a future reader does not conclude the endpoint is broken.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 20

# Reliance: a scrip every probe can use, large enough that no endpoint should
# legitimately return nothing for it.
SAMPLE_SCRIP = "500325"
SAMPLE_TICKER = "RELIANCE"


def _get(label, url, params=None, expect="json"):
    """One probe. Reports what came back rather than raising."""
    print(f"\n--- {label}")
    print(f"    {url}")
    if params:
        print(f"    params: {params}")
    try:
        r = requests.get(
            url, params=params, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True
        )
    except Exception as e:
        print(f"    FAILED: {e.__class__.__name__}: {e}")
        return None

    ctype = r.headers.get("content-type", "?")
    print(f"    status={r.status_code} type={ctype} bytes={len(r.content)}")
    if r.status_code != 200 or not r.content:
        print(f"    body[:200]={r.text[:200]!r}")
        return None

    if expect == "json":
        try:
            data = r.json()
        except ValueError:
            print(f"    not JSON. body[:300]={r.text[:300]!r}")
            return None
        _describe(data)
        return data

    # CSV / text
    lines = r.text.splitlines()
    print(f"    lines={len(lines)}")
    for line in lines[:3]:
        print(f"      {line[:160]}")
    return r.text


def _describe(data, indent="    "):
    """Enough shape to design against, without dumping a megabyte."""
    if isinstance(data, dict):
        print(f"{indent}dict keys: {list(data)[:12]}")
        for k, v in list(data.items())[:4]:
            if isinstance(v, list) and v:
                print(f"{indent}  {k}: list[{len(v)}], first item keys:")
                if isinstance(v[0], dict):
                    print(f"{indent}    {list(v[0])[:16]}")
                    print(f"{indent}    sample: {json.dumps(v[0])[:300]}")
            elif isinstance(v, dict):
                print(f"{indent}  {k}: dict keys {list(v)[:12]}")
    elif isinstance(data, list):
        print(f"{indent}list[{len(data)}]")
        if data and isinstance(data[0], dict):
            print(f"{indent}  first keys: {list(data[0])[:16]}")
            print(f"{indent}  sample: {json.dumps(data[0])[:300]}")


def probe_bhavcopy():
    """Whole-market daily OHLCV in one request.

    If this works it is the highest-value item here: one call replaces the
    per-holding price fetch, and carries the traded value that turnover and
    the 52-week range are computed from.
    """
    print("\n=== 1. BHAVCOPY (whole-market daily OHLCV) ===")
    # Walk back to the most recent weekday; a holiday still just 404s, which
    # is a fine answer.
    today = datetime.date.today()
    for back in range(0, 6):
        d = today - datetime.timedelta(days=back)
        if d.weekday() >= 5:
            continue
        stamp = d.strftime("%Y%m%d")
        got = _get(
            f"BhavCopy {d.isoformat()}",
            f"https://www.bseindia.com/download/BhavCopy/Equity/"
            f"BhavCopy_BSE_CM_0_0_0_{stamp}_F_0000.CSV",
            expect="csv",
        )
        if got:
            return
    print("    no bhavcopy retrieved in the last 6 days")


def probe_shareholding():
    """The pledge figure — the gap Screener left at 0 of 69 holdings."""
    print("\n=== 2. SHAREHOLDING / PLEDGE ===")
    _get(
        "ShpPromoterNGroup",
        "https://api.bseindia.com/BseIndiaAPI/api/ShpPromoterNGroup/w",
        params={"scripcode": SAMPLE_SCRIP, "qtrid": ""},
    )
    _get(
        "Shareholding summary page",
        "https://www.bseindia.com/corporates/shpPromoterNGroup.aspx",
        params={"scripcd": SAMPLE_SCRIP},
        expect="html",
    )


def probe_announcements():
    """Real filings with real dates, vs the current Google News stand-in."""
    print("\n=== 3. CORPORATE ANNOUNCEMENTS ===")
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    _get(
        "AnnGetData (all scrips, last 7d)",
        "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w",
        params={
            "strCat": "-1",
            "strPrevDate": week_ago.strftime("%Y%m%d"),
            "strToDate": today.strftime("%Y%m%d"),
            "strSearch": "P",
            "strscrip": "",
            "strType": "C",
            "pageno": "1",
        },
    )


def probe_quote():
    """Header quote — the direct alternative to Yahoo for a single scrip."""
    print("\n=== 4. SCRIP QUOTE ===")
    _get(
        "getScripHeaderData",
        "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w",
        params={"Debtflag": "", "scripcode": SAMPLE_SCRIP, "seriesid": ""},
    )


def probe_scrip_master():
    """Ticker -> scrip code. Every other endpoint is keyed by scrip code, so
    without this mapping none of them can be used from our watchlist."""
    print("\n=== 5. SCRIP MASTER (ticker -> code) ===")
    _get(
        "ListofScripData",
        "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w",
        params={
            "Group": "",
            "Scripcode": "",
            "industry": "",
            "segment": "Equity",
            "status": "Active",
        },
    )
    _get(
        "getScripName autocomplete",
        "https://api.bseindia.com/BseIndiaAPI/api/Msnew/w",
        params={"text": SAMPLE_TICKER},
    )


def main():
    print(f"BSE probe — {datetime.datetime.now().isoformat()}")
    print(f"requests {requests.__version__}")
    for probe in (
        probe_scrip_master,
        probe_bhavcopy,
        probe_quote,
        probe_shareholding,
        probe_announcements,
    ):
        try:
            probe()
        except Exception as e:  # noqa: BLE001 - a probe must report, not crash
            print(f"    PROBE CRASHED: {e.__class__.__name__}: {e}")
    print("\nProbe complete. Nothing was written; this run changes no data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
