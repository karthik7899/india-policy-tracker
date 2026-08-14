"""Probe which BSE endpoints are usable, and what they actually return.

BSE is blocked from the development sandbox (403 on CONNECT, same egress
policy as Screener and Yahoo), so every claim about these endpoints would
otherwise be from memory. This runs on the Actions runner, which reaches them,
and reports measured facts: status, content type, size, and enough of the
shape to design against.

It writes nothing into the pipeline and is never called by a briefing run.

MEASURED, 14 Aug 2026 (runs 1 and 2). Re-run before trusting any of it; these
are undocumented endpoints and BSE moves them.

  WORKS

  Bhavcopy — whole-market daily OHLCV, ONE request.
    https://www.bseindia.com/download/BhavCopy/Equity/
        BhavCopy_BSE_CM_0_0_0_<YYYYMMDD>_F_0000.CSV
    851 KB, 4,973 rows, application/octet-stream. Columns include TradDt,
    FinInstrmId (scrip code), ISIN, TckrSymb, OpnPric, HghPric, LwPric,
    ClsPric, LastPr and a traded-value column. Keyed by ISIN, which we hold
    for all 70 watchlist holdings.
    TRAP: asking for *today* before the file is published returns 200 with
    BSE's Angular shell, not a 404. Run 1 read that as a dead endpoint. Ask
    for the previous session, and treat an HTML body as a miss whatever the
    status says.

  ListofScripData — the scrip master, 4,975 active equity scrips.
    https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w
        ?Group=&Scripcode=&industry=&segment=Equity&status=Active
    1.75 MB JSON. SCRIP_CD, ISIN_NUMBER, scrip_id, Scrip_Name, GROUP,
    FACE_VALUE, Mktcap. Nearly twice the coverage of our NSE-derived ISIN
    master and it includes BSE-only listings.

  getScripHeaderData — per-scrip quote.
    https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w
        ?Debtflag=&scripcode=<code>&seriesid=
    Header carries PrevClose/Open/High/Low/LTP; CurrRate carries LTP/Chg/PcChg.

  DOES NOT WORK YET

  Shareholding / promoter pledge. Four endpoint names tried
  (ShareHoldingPattern, ShpPromoterNGroup with and without Flag,
  ComShpPromoterNGroup, ShpSecurities); every one returned the same 1,814-byte
  ASP.NET page, which is BSE's generic miss. The names are wrong rather than
  the data being absent. Next step is reading what bseindia.com's own
  shareholding page calls, not more guessing.

  Corporate announcements. AnnGetData answers with JSON but returns
  "No Record Found!" for every parameter set tried, including a single large
  scrip over a seven-day window. The endpoint is alive and the query is wrong
  — a better position than a rejection, and worth one more attempt with the
  parameter names BSE's own page sends.

  Msnew autocomplete returns HTML, not JSON.

  NSE ARCHIVES (nsearchives.nseindia.com) — measured 14 Aug 2026, run 3

  sec_bhavdata_full — the best find here.
    https://nsearchives.nseindia.com/products/content/
        sec_bhavdata_full_<DDMMYYYY>.csv
    376 KB, 3,308 rows, text/csv, no zip. Columns: SYMBOL, SERIES, DATE1,
    PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE,
    AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY,
    DELIV_PER. It carries TURNOVER and DELIVERY directly, which analysis/
    liquidity.py currently derives from Yahoo volume times price — and
    delivery percentage is a better tradeability signal than raw volume,
    because it excludes intraday churn. Keyed by SYMBOL, which is the ticker
    our watchlist already uses; no ISIN join needed.

  UDiFF bhavcopy — whole-market OHLCV, zipped.
    https://nsearchives.nseindia.com/content/cm/
        BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip
    196 KB zip (verified PK magic), one CSV inside, same UDiFF column set as
    BSE's: TradDt, FinInstrmId, ISIN, TckrSymb, OpnPric..ClsPric.

  The legacy path is GONE, not merely unfashionable:
    /content/historical/EQUITIES/<YYYY>/<MON>/cm<DDMONYYYY>bhav.csv.zip
    returns a genuine 404. Older URLs are not a way around anything here.

  THE BOT FILTER IS ON BOTH HOSTS. Measured directly, same URL twice:
    NSE archives, no headers  -> ReadTimeout after 20s
    NSE archives, browser UA  -> 200
    BSE api, no headers       -> 403 "Access Denied"
    BSE api, browser UA       -> 200
  So the archive host is not an unguarded back door; it just fails by hanging
  rather than by rejecting, which is the more expensive failure of the two —
  a bare request costs the full timeout. The User-Agent and Referer that
  providers/isin_master.py already sends are required, not decorative.

Each probe prints what it got, including the failures, because a probe that
hides its misses is worse than none. Bodies under 400 bytes print verbatim:
run 1 summarised an 18-byte response by its keys and hid the one detail that
said the query was wrong rather than the window empty.
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


def _get(label, url, params=None, expect="json", headers=HEADERS):
    """One probe. Reports what came back rather than raising.

    ``headers`` is overridable so the bot-filter question can be answered by
    measurement: pass {} to ask whether an endpoint needs the browser
    user-agent and Referer at all.
    """
    print(f"\n--- {label}")
    print(f"    {url}")
    if params:
        print(f"    params: {params}")
    try:
        r = requests.get(
            url, params=params, headers=headers, timeout=TIMEOUT, allow_redirects=True
        )
    except Exception as e:
        print(f"    FAILED: {e.__class__.__name__}: {e}")
        return None

    ctype = r.headers.get("content-type", "?")
    print(f"    status={r.status_code} type={ctype} bytes={len(r.content)}")
    if r.status_code != 200 or not r.content:
        print(f"    body[:200]={r.text[:200]!r}")
        return None

    if expect == "binary":
        # A zip starts PK\x03\x04. Anything else arriving under a .zip URL is
        # an error page wearing a 200, which is how BSE and NSE both answer a
        # request for a file that does not exist yet.
        head = r.content[:4]
        is_zip = head[:2] == b"PK"
        print(f"    magic={head!r} looks_like_zip={is_zip}")
        if is_zip:
            try:
                import io
                import zipfile

                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    names = z.namelist()
                    print(f"    zip contains: {names[:4]}")
                    if names:
                        with z.open(names[0]) as inner:
                            first = inner.readline().decode("utf-8", "replace")
                            print(f"    header: {first[:200].strip()}")
            except Exception as e:
                print(f"    could not read zip: {e.__class__.__name__}: {e}")
        else:
            print(f"    body[:160]={r.text[:160]!r}")
        return r.content if is_zip else None

    if expect == "json":
        try:
            data = r.json()
        except ValueError:
            print(f"    not JSON. body[:300]={r.text[:300]!r}")
            return None
        # A small body is the interesting case, not the boring one: the first
        # run reported an 18-byte 200 from the announcements endpoint and
        # described only its keys, hiding the one thing that would have said
        # whether the query was wrong or the window was genuinely empty.
        if len(r.content) < 400:
            print(f"    small body, verbatim: {r.text!r}")
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


# Run 1 result: the path below returned a 200 carrying BSE's Angular shell
# (13,850 bytes of HTML), not a CSV. A 200 that is really a SPA fallback is
# the shape a stale download path takes on this site, so the pattern is tried
# alongside the older EQ_ISINCODE form rather than trusted.
_BHAV_PATTERNS = [
    (
        "new F_0000",
        "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{ymd}_F_0000.CSV",
    ),
    ("legacy zip", "https://www.bseindia.com/download/BhavCopy/Equity/EQ{dmy}_CSV.ZIP"),
    ("legacy csv", "https://www.bseindia.com/download/BhavCopy/Equity/EQ{dmy}_CSV.csv"),
]


def probe_bhavcopy():
    """Whole-market daily OHLCV in one request.

    If this works it is the highest-value item here: one call replaces the
    per-holding price fetch, and carries the traded value that turnover and
    the 52-week range are computed from.
    """
    print("\n=== 1. BHAVCOPY (whole-market daily OHLCV) ===")
    today = datetime.date.today()
    for back in range(1, 5):
        d = today - datetime.timedelta(days=back)
        if d.weekday() >= 5:
            continue
        for label, pattern in _BHAV_PATTERNS:
            url = pattern.format(ymd=d.strftime("%Y%m%d"), dmy=d.strftime("%d%m%y"))
            got = _get(f"{label} {d.isoformat()}", url, expect="csv")
            # An HTML shell is a miss even though it arrived as 200.
            if got and not got.lstrip().lower().startswith("<!doctype"):
                print("    ^ looks like real CSV")
                return
    print("    no usable bhavcopy found")


def probe_shareholding():
    """The pledge figure — the gap Screener left at 0 of 69 holdings."""
    print("\n=== 2. SHAREHOLDING / PLEDGE ===")
    # Run 1: both of these returned HTML, not JSON — the first an ASP.NET
    # page, the second the SPA shell. So the names are wrong rather than the
    # data being absent. These are the remaining candidates.
    for label, path, params in [
        (
            "ShareHoldingPattern",
            "ShareHoldingPattern/w",
            {"scripcode": SAMPLE_SCRIP, "qtrid": "", "Type": "EQ"},
        ),
        (
            "ShpPromoterNGroup (flag)",
            "ShpPromoterNGroup/w",
            {"scripcode": SAMPLE_SCRIP, "qtrid": "", "Flag": "P"},
        ),
        (
            "ComShpPromoterNGroup",
            "ComShpPromoterNGroup/w",
            {"scripcode": SAMPLE_SCRIP, "qtrid": ""},
        ),
        ("ShpSecurities", "ShpSecurities/w", {"scripcode": SAMPLE_SCRIP, "qtrid": ""}),
    ]:
        _get(label, f"https://api.bseindia.com/BseIndiaAPI/api/{path}", params=params)


def probe_announcements():
    """Real filings with real dates, vs the current Google News stand-in."""
    print("\n=== 3. CORPORATE ANNOUNCEMENTS ===")
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    # Run 1: this returned JSON but only 18 bytes — an empty result set, not
    # a rejection. The endpoint works and the query was wrong, which is a much
    # better position than a 403. Varying the parameters most likely to be at
    # fault: the category flag and the scrip filter.
    base = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    common = {
        "strPrevDate": week_ago.strftime("%Y%m%d"),
        "strToDate": today.strftime("%Y%m%d"),
        "strType": "C",
        "pageno": "1",
    }
    _get(
        "AnnGetData strCat=-1, all scrips",
        base,
        params={**common, "strCat": "-1", "strSearch": "P", "strscrip": ""},
    )
    _get(
        "AnnGetData blank cat, one scrip",
        base,
        params={**common, "strCat": "", "strSearch": "P", "strscrip": SAMPLE_SCRIP},
    )
    _get(
        "AnnGetData subcat blank, one scrip",
        base,
        params={
            **common,
            "strCat": "",
            "strSearch": "",
            "strscrip": SAMPLE_SCRIP,
            "subcategory": "",
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


# --- Archive hosts -------------------------------------------------------
#
# nsearchives.nseindia.com is a static file host, not the www.nseindia.com API
# that needs a cookie/session handshake. providers/isin_master.py already
# fetches EQUITY_L.csv from it successfully on every production run, which is
# the evidence that the archive host is the tractable NSE route.

_NSE_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://www.nseindia.com/",
}


def probe_nse_archives():
    """NSE's static archive host — whole-market files, no session handshake."""
    print("\n=== 6. NSE ARCHIVES (nsearchives.nseindia.com) ===")

    # Control: the repo already fetches this every run. If it fails, the
    # problem is the runner or the host, not the URL patterns below.
    _get(
        "EQUITY_L.csv (known-good control)",
        "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
        expect="csv",
        headers=_NSE_HEADERS,
    )

    today = datetime.date.today()
    for back in range(1, 6):
        d = today - datetime.timedelta(days=back)
        if d.weekday() >= 5:
            continue
        ymd = d.strftime("%Y%m%d")
        ddmmyyyy = d.strftime("%d%m%Y")
        mon = d.strftime("%b").upper()
        ddmonyyyy = d.strftime("%d%b%Y").upper()

        hit = _get(
            f"UDiFF bhavcopy {d.isoformat()}",
            f"https://nsearchives.nseindia.com/content/cm/"
            f"BhavCopy_NSE_CM_0_0_0_{ymd}_F_0000.csv.zip",
            expect="binary",
            headers=_NSE_HEADERS,
        )
        legacy = _get(
            f"legacy bhavcopy {d.isoformat()}",
            f"https://nsearchives.nseindia.com/content/historical/EQUITIES/"
            f"{d.year}/{mon}/cm{ddmonyyyy}bhav.csv.zip",
            expect="binary",
            headers=_NSE_HEADERS,
        )
        # Security-wise delivery data: carries delivery quantity, which is a
        # better liquidity signal than raw traded volume.
        deliv = _get(
            f"sec_bhavdata_full {d.isoformat()}",
            f"https://nsearchives.nseindia.com/products/content/"
            f"sec_bhavdata_full_{ddmmyyyy}.csv",
            expect="csv",
            headers=_NSE_HEADERS,
        )
        if hit or legacy or deliv:
            return
    print("    no NSE bhavcopy retrieved")


def probe_bot_filter():
    """Do these hosts actually need the browser user-agent?

    The premise worth testing rather than assuming: static archive paths are
    often served by a plain file host with no bot filter in front, while the
    JSON APIs sit behind one. If the archives answer a bare request, the
    fetching code gets simpler and stops depending on a spoofed header that
    could be tightened at any time.
    """
    print("\n=== 7. IS THE BROWSER HEADER ACTUALLY NEEDED? ===")
    for label, url, expect in [
        (
            "NSE EQUITY_L.csv",
            "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
            "csv",
        ),
        (
            "BSE scrip master",
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
            "?Group=&Scripcode=&industry=&segment=Equity&status=Active",
            "json",
        ),
    ]:
        _get(f"{label} — NO custom headers", url, expect=expect, headers={})
        _get(f"{label} — with browser headers", url, expect=expect)


def main():
    print(f"BSE probe — {datetime.datetime.now().isoformat()}")
    print(f"requests {requests.__version__}")
    for probe in (
        probe_scrip_master,
        probe_bhavcopy,
        probe_quote,
        probe_shareholding,
        probe_announcements,
        probe_nse_archives,
        probe_bot_filter,
    ):
        try:
            probe()
        except Exception as e:  # noqa: BLE001 - a probe must report, not crash
            print(f"    PROBE CRASHED: {e.__class__.__name__}: {e}")
    print("\nProbe complete. Nothing was written; this run changes no data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
