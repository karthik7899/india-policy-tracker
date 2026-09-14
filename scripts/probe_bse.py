"""Probe which BSE endpoints are usable, and what they actually return.

BSE is blocked from the development sandbox (403 on CONNECT, same egress
policy as Screener and Yahoo), so every claim about these endpoints would
otherwise be from memory. This runs on the Actions runner, which reaches them,
and reports measured facts: status, content type, size, and enough of the
shape to design against.

It writes nothing into the pipeline and is never called by a briefing run.

MEASURED 14 Sep 2026 (run 34807288884), re-confirming 14 Aug 2026. Re-run
before trusting any of it; these are undocumented endpoints and BSE moves
them. Nothing moved in that month: everything below that worked still works,
and everything dead is still dead.

  WORKS

  Bhavcopy — whole-market daily OHLCV, ONE request.
    https://www.bseindia.com/download/BhavCopy/Equity/
        BhavCopy_BSE_CM_0_0_0_<YYYYMMDD>_F_0000.CSV
    857,324 bytes, 5,008 lines, application/octet-stream (Aug: 851 KB,
    4,973). Columns include TradDt, FinInstrmId (scrip code), ISIN,
    TckrSymb, OpnPric, HghPric, LwPric, ClsPric, LastPr and a traded-value
    column. Keyed by ISIN, which we hold for all 70 watchlist holdings.
    TRAP: asking for *today* before the file is published returns 200 with
    BSE's Angular shell, not a 404. Run 1 read that as a dead endpoint. Ask
    for the previous session, and treat an HTML body as a miss whatever the
    status says.

  ListofScripData — the scrip master, 5,004 active equity scrips.
    https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w
        ?Group=&Scripcode=&industry=&segment=Equity&status=Active
    1,755,863 bytes JSON, a bare list (Aug: 1.75 MB, 4,975 scrips). Twelve
    keys, more than the Aug note recorded: SCRIP_CD, Scrip_Name, Status,
    GROUP, FACE_VALUE, ISIN_NUMBER, INDUSTRY, scrip_id, Segment, NSURL,
    Issuer_Name, Mktcap. INDUSTRY is null in the sample, so do not plan on
    it. Nearly twice the coverage of our NSE-derived ISIN master, and it
    includes BSE-only listings.

  getScripHeaderData — per-scrip quote. 1,183 bytes.
    https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w
        ?Debtflag=&scripcode=<code>&seriesid=
    Header carries PrevClose/Open/High/Low/LTP; CurrRate carries LTP/Chg/PcChg.

  AnnSubCategoryGetData — corporate announcements. THE PATH, and the only
  one. providers/bse_announcements.py has used it in production since 15 Aug.
    https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w
        ?pageno=1&strCat=-1&strPrevDate=<YYYYMMDD>&strScrip=&strSearch=P
        &strToDate=<YYYYMMDD>&strType=C&subcategory=-1

  DOES NOT WORK

  Shareholding / promoter pledge. Four endpoint names were tried
  (ShareHoldingPattern, ShpPromoterNGroup with and without Flag,
  ComShpPromoterNGroup, ShpSecurities); every one returns the same 1,814-byte
  ASP.NET page, which is BSE's generic miss. The names are wrong rather than
  the data being absent. Only ONE is still probed, as a tripwire — guessing
  names is what cost 32 attempts against the announcements feed.

  AnnGetData — a real endpoint, and the wrong one. It answers 200 with
  application/json and the 18-byte body "No Record Found!" for every
  parameter set, including the parameters that work against
  AnnSubCategoryGetData. Kept here as a labelled control precisely because
  the two side by side are the lesson: identical query, identical status and
  content type, one returns filings and one returns a polite empty string.

  The route to settle the shareholding gap was to read what bseindia.com's
  own pages call. Run 5 closed it: www.bseindia.com answers headless Chromium
  with an Akamai 403 "Access Denied" on every page, while plain requests
  carrying our UA and Referer are served normally from the same runner. The
  filter is on browser fingerprint, so the site cannot be read the way a
  person reads it without evasion tooling — which we are not going to build.
  See docs/upstream-findings.md. That gap needs a source that will have us,
  not another guess at BSE.

  Msnew autocomplete returns HTML, not JSON. Tripwire only.

  NSE ARCHIVES (nsearchives.nseindia.com) — re-measured 14 Sep 2026

  sec_bhavdata_full — the best find here.
    https://nsearchives.nseindia.com/products/content/
        sec_bhavdata_full_<DDMMYYYY>.csv
    394,927 bytes, 3,486 lines, text/csv, no zip (Aug: 376 KB, 3,308 rows).
    Columns: SYMBOL, SERIES, DATE1,
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
    204,525 bytes zip, verified PK magic (Aug: 196 KB), one CSV inside, same
    UDiFF column set as BSE's: TradDt, FinInstrmId, ISIN, TckrSymb,
    OpnPric..ClsPric.

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
                return True
    print("    no usable bhavcopy found")
    return False


def probe_shareholding():
    """The pledge figure — the gap Screener leaves at 0 of 70 holdings.

    ONE call, not the four this used to make. Four endpoint names were tried
    across three runs and every one returned the identical 1,814-byte ASP.NET
    page, which is BSE's generic miss — so the names are wrong rather than the
    data being absent. The way to learn the right name is to read what the
    site's own pages call, and that route is closed: Akamai refuses headless
    Chromium on browser fingerprint (docs/upstream-findings.md).

    Guessing endpoint names is precisely what this project has learned not to
    do — it cost 32 attempts against the announcements feed before someone
    checked the path. So the other three guesses are gone and this is a
    tripwire: if BSE ever serves JSON here, that is worth knowing, and one
    request a run is a fair price for finding out.
    """
    print("\n=== 2. SHAREHOLDING / PLEDGE (tripwire; expected to fail) ===")
    got = _get(
        "ShareHoldingPattern",
        "https://api.bseindia.com/BseIndiaAPI/api/ShareHoldingPattern/w",
        params={"scripcode": SAMPLE_SCRIP, "qtrid": "", "Type": "EQ"},
    )
    if got:
        print("    ^ THIS CHANGED. BSE is serving JSON here now; re-open the")
        print("      pledge question — analysis/pledging.py has no source.")
    return bool(got)


def probe_announcements():
    """Real filings with real dates, vs the Google News stand-in.

    Probes the path production actually uses. This used to fire three
    parameter variations at AnnGetData and report "No Record Found!" three
    times — a settled negative, re-litigated every run, while
    providers/bse_announcements.py had been pulling real filings from
    AnnSubCategoryGetData for a month. A catalogue whose verdict contradicts
    the running pipeline is worse than no catalogue.

    The dead path is kept as ONE labelled control, because the two side by
    side are the whole lesson: same parameters, same 200, same JSON
    content-type, and one returns filings while the other returns a polite
    empty string. That is the most expensive kind of wrong — it looks like a
    data problem for as long as you care to look.
    """
    print("\n=== 3. CORPORATE ANNOUNCEMENTS ===")

    # A SINGLE DAY, not a range, and a COMPLETED session rather than today.
    #
    # Both halves were learned the expensive way. The first version of this
    # asked strPrevDate=<7 days ago>&strToDate=<today>, inherited unexamined
    # from the old AnnGetData probe, and got back `{}` — two bytes. That
    # looked exactly like a regression and was reported as one, while
    # production was fetching filings normally: the captured browser request
    # this endpoint was found from sends strPrevDate == strToDate, one day.
    # Whatever this endpoint does with a range, it is not what a range means.
    #
    # And asking for TODAY conflates "the endpoint is broken" with "it is
    # 09:00 and nobody has filed yet" — the same trap probe_bhavcopy documents
    # for the BSE bhavcopy. Walk back to a finished weekday, where an empty
    # answer means something.
    day = datetime.date.today() - datetime.timedelta(days=1)
    while day.weekday() >= 5:
        day -= datetime.timedelta(days=1)
    ymd = day.strftime("%Y%m%d")
    common = {
        "strPrevDate": ymd,
        "strToDate": ymd,
        "strType": "C",
        "pageno": "1",
        "strCat": "-1",
        "strSearch": "P",
        "strScrip": "",
        "subcategory": "-1",
    }
    live = _get(
        f"AnnSubCategoryGetData (production's path, single day {day.isoformat()})",
        "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w",
        params=common,
    )
    _get(
        "AnnGetData (CONTROL: known-wrong path, identical parameters)",
        "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w",
        params=common,
    )

    # A string body is not a record list. "No Record Found!" parses as valid
    # JSON and is truthy, so a bare `if live:` would call this a success.
    rows = None
    if isinstance(live, dict):
        rows = next(
            (
                live[k]
                for k in ("Table", "data", "rows")
                if isinstance(live.get(k), list)
            ),
            None,
        )
    elif isinstance(live, list):
        rows = live
    ok = isinstance(rows, list) and bool(rows)
    if not ok:
        print(
            "    ^ no record list. Check the SHAPE before calling this a BSE\n"
            "      regression: an empty dict here has meant a malformed query\n"
            "      more often than a dead endpoint."
        )
    return ok


def probe_quote():
    """Header quote — the direct alternative to Yahoo for a single scrip."""
    print("\n=== 4. SCRIP QUOTE ===")
    got = _get(
        "getScripHeaderData",
        "https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w",
        params={"Debtflag": "", "scripcode": SAMPLE_SCRIP, "seriesid": ""},
    )
    return isinstance(got, dict) and bool(got.get("Header"))


def probe_scrip_master():
    """Ticker -> scrip code. Every other endpoint is keyed by scrip code, so
    without this mapping none of them can be used from our watchlist."""
    print("\n=== 5. SCRIP MASTER (ticker -> code) ===")
    got = _get(
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
    # Msnew has returned the generic ASP.NET page on every run since Aug 2026.
    # Kept as a one-request tripwire, not as a live candidate.
    _get(
        "getScripName autocomplete (tripwire; expected to fail)",
        "https://api.bseindia.com/BseIndiaAPI/api/Msnew/w",
        params={"text": SAMPLE_TICKER},
    )
    return isinstance(got, list) and bool(got)


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
            # deliv is the one production depends on (providers/nse_delivery.py),
            # so it decides the verdict. The other two are catalogue entries;
            # legacy is a confirmed 404 and its absence is not a regression.
            return bool(deliv)
    print("    no NSE bhavcopy retrieved")
    return False


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


# What each probe is EXPECTED to return, so the summary can tell the two
# interesting outcomes apart. A known-dead endpoint staying dead is not news;
# a known-good one going dead is the whole reason to re-run this. Without the
# expectation, both read as "False" and a regression hides among the four
# failures that are supposed to be there.
_EXPECTED = {
    "scrip master": True,
    "BSE bhavcopy": True,
    "scrip quote": True,
    "shareholding / pledge": False,
    "corporate announcements": True,
    "NSE archives (delivery)": True,
}


def main():
    print(f"BSE probe — {datetime.datetime.now().isoformat()}")
    print(f"requests {requests.__version__}")
    results = {}
    for name, probe in (
        ("scrip master", probe_scrip_master),
        ("BSE bhavcopy", probe_bhavcopy),
        ("scrip quote", probe_quote),
        ("shareholding / pledge", probe_shareholding),
        ("corporate announcements", probe_announcements),
        ("NSE archives (delivery)", probe_nse_archives),
    ):
        try:
            results[name] = bool(probe())
        except Exception as e:  # noqa: BLE001 - a probe must report, not crash
            results[name] = False
            print(f"    PROBE CRASHED: {e.__class__.__name__}: {e}")

    # Informational only: it answers "are the headers needed", not "does an
    # endpoint work", so it has no pass/fail and is kept out of the tally.
    try:
        probe_bot_filter()
    except Exception as e:  # noqa: BLE001
        print(f"    PROBE CRASHED: {e.__class__.__name__}: {e}")

    print(f"\n{'=' * 72}\nSUMMARY\n{'=' * 72}")

    # Nothing at all got through. Per-endpoint verdicts are then not merely
    # unhelpful, they are WRONG: every line would read "REGRESSED", and the
    # shareholding line would read "still dead (expected)" while being right
    # by coincidence — it failed at the local proxy, not at BSE's generic miss
    # page. From a development sandbox this is the egress policy every time.
    # Say so and stop, rather than raise five false alarms.
    if not any(results.values()):
        for name in results:
            print(f"  {'unreachable':24} {name}")
        print(f"\n0/{len(results)} endpoint(s) returned usable data.")
        print(
            "  EVERY endpoint failed, so no per-endpoint verdict is meaningful\n"
            "  here — a blocked CONNECT and a dead endpoint are indistinguishable\n"
            "  from this side. From a development sandbox that is normally the\n"
            "  egress policy rather than the upstream. Re-run this on the Actions\n"
            "  runner (workflow: probe-bse.yml), which can reach these hosts."
        )
        print("\nNothing was written; this run changes no data.")
        return 0

    regressions, fixed = [], []
    for name, ok in results.items():
        expected = _EXPECTED[name]
        if ok and expected:
            verdict = "WORKS"
        elif not ok and not expected:
            verdict = "still dead (expected)"
        elif ok and not expected:
            verdict = "NEWLY WORKING — investigate"
            fixed.append(name)
        else:
            verdict = "REGRESSED — was working"
            regressions.append(name)
        print(f"  {verdict:24} {name}")

    working = sum(1 for n, ok in results.items() if ok)
    print(f"\n{working}/{len(results)} endpoint(s) returned usable data.")
    if regressions:
        print(f"  REGRESSIONS: {', '.join(regressions)} — production may be affected.")
    if fixed:
        print(f"  NEWLY WORKING: {', '.join(fixed)} — a gap may now be closable.")
    if not regressions and not fixed:
        print("  Nothing moved since the last measurement.")
    print("\nNothing was written; this run changes no data.")
    # Always exit 0: a changed upstream is a FINDING, and failing the job would
    # make the tool look broken while it is doing its job.
    return 0


if __name__ == "__main__":
    sys.exit(main())
