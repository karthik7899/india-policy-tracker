"""Capture what BSE's own pages call — the DevTools Network tab, scripted.

Guessing endpoint names has now failed eight times across two probe runs: four
shareholding candidates all returned the same generic ASP.NET page, and three
announcement parameter sets all returned "No Record Found!". That is the point
to stop guessing and read what the site itself does.

Runs only on the Actions runner: BSE refuses connections from the development
sandbox (403 on CONNECT). Writes nothing, and is never called by a briefing
run.

ANSWERED, run 5 — THIS APPROACH IS DEAD, AND THE SCRIPT IS KEPT ONLY AS THE
RECORD OF WHY. All five pages returned:

    landed: HTTP 403 | <the url asked for>
    title : 'Access Denied'
    dom   : ~250 chars, 0 tables, 0 rows
    head  : "Access Denied You don't have permission to access ... "
            "https://errors.edgesuite.net/"
    all hosts: {'www.bseindia.com': 1}

One response per page and no JS ever ran, so there was no XHR to capture: the
browser never received a page. Akamai (errors.edgesuite.net) refuses headless
Chromium outright.

The load-bearing comparison is with the endpoint probe, which runs on the SAME
runner and is served normally: plain `requests` carrying the UA and Referer
from providers/isin_master.py pulled 851 KB of bhavcopy and 1.75 MB of scrip
master from these hosts in runs 1-3. So the filter is on browser fingerprint,
not on the UA string or the IP — a spoofed user_agent and
--disable-blink-features=AutomationControlled changed nothing.

Defeating that means fingerprint-spoofing tooling, which is evasion of a
control the site is plainly asserting, and would be a fragile thing to hang a
daily briefing on besides. Do not do it. The shareholding and announcement
gaps stay open, to be closed from a source that will have us: see the WORKS
list in probe_bse.py.

Run 4 background, for why the diagnostics below exist: it reported "no API
calls captured" with no navigation error, which could not be told apart from
its own filter never matching. The 403 was invisible. This version resolves
that ambiguity before drawing any conclusion:

  * it prints the landing URL, title, top-level HTTP status and a DOM
    fingerprint, so BSE's Angular-shell miss (a 200 carrying no content — the
    trap that made probe run 1 call the bhavcopy dead) is visible as itself;
  * it counts EVERY response by host, not just api.bseindia.com, so "the page
    fired nothing" is distinguishable from "the filter matched nothing";
  * it drives the SPA the way a reader does — scrolling, and clicking whatever
    looks like a quarter/period control — since an XHR that only fires on
    interaction is invisible to a script that just waits.

Two questions it exists to answer, both currently blocking:

  1. Which endpoint serves the promoter pledge figure? Screener's page yielded
     it for 0 of 69 holdings, so BSE is the fallback and we cannot find the
     door by knocking on names.
  2. What parameters does AnnGetData actually want? It answers with JSON and
     "No Record Found!", so the endpoint is alive and only the query is wrong.
"""

import sys
from collections import Counter
from urllib.parse import urlsplit

# Reliance: large, always has filings, and its pledge row is a known quantity.
SAMPLE_SCRIP = "500325"

# Both URL shapes for each target. The SEO slug form is what a search result
# links to, but a wrong slug is exactly how run 1 got served a shell with a 200
# on it; the legacy .aspx form carries no slug to get wrong. If one shape works
# and the other does not, that difference is itself the finding.
PAGES = [
    (
        "shareholding (SEO slug)",
        f"https://www.bseindia.com/stock-share-price/reliance-industries-ltd/"
        f"reliance/{SAMPLE_SCRIP}/shareholding-pattern/",
    ),
    (
        "shareholding (legacy aspx)",
        f"https://www.bseindia.com/corporates/shpPromoterNGroup.aspx"
        f"?scripcd={SAMPLE_SCRIP}",
    ),
    (
        "quote page",
        f"https://www.bseindia.com/stock-share-price/reliance-industries-ltd/"
        f"reliance/{SAMPLE_SCRIP}/",
    ),
    (
        "corp announcements (SEO slug)",
        f"https://www.bseindia.com/stock-share-price/reliance-industries-ltd/"
        f"reliance/{SAMPLE_SCRIP}/corp-announcements/",
    ),
    (
        "announcements listing",
        "https://www.bseindia.com/corporates/ann.html",
    ),
]

# The page fires plenty of chrome, analytics and font requests. Only calls to
# the API host can carry the data, so everything else is noise — but the noise
# is counted, because silence there means the capture itself failed.
API_HOST = "api.bseindia.com"

# Anything that might reveal a period-scoped XHR. BSE puts the quarter behind a
# select on some layouts and a link on others, so try both shapes and accept
# that most of these match nothing.
INTERACTION_SELECTORS = [
    "select",
    "a:has-text('Quarterly')",
    "a:has-text('Shareholding')",
    "a:has-text('Promoter')",
]


def fingerprint(page):
    """What actually landed: enough to tell a real page from BSE's shell."""
    try:
        return page.evaluate("""() => ({
                title: document.title,
                url: location.href,
                bodyChars: (document.body ? document.body.innerText : '').trim().length,
                tables: document.querySelectorAll('table').length,
                rows: document.querySelectorAll('tr').length,
                head: (document.body ? document.body.innerText : '')
                    .trim().slice(0, 200).replace(/\\s+/g, ' '),
            })""")
    except Exception as e:  # noqa: BLE001 - a fingerprint failure must not end the page
        return {"title": f"<unreadable: {e.__class__.__name__}>"}


def capture(browser, label, url):
    print(f"\n=== {label}")
    print(f"    {url}")

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 900},
        locale="en-IN",
    )
    page = context.new_page()

    seen = []
    hosts = Counter()

    def record(r):
        # Recorded on response rather than request, so the status is available:
        # an endpoint the page calls and which then 404s is a different finding
        # from one that returns data, and both are worth seeing.
        hosts[urlsplit(r.url).netloc] += 1
        if API_HOST in r.url:
            seen.append((r.status, r.request.method, r.url))

    page.on("response", record)
    page.on(
        "requestfailed", lambda r: hosts.update({f"FAILED {urlsplit(r.url).netloc}": 1})
    )

    status = None
    try:
        resp = page.goto(url, wait_until="networkidle", timeout=45000)
        status = resp.status if resp else None
    except Exception as e:
        # A timeout still leaves whatever was captured before it, which is
        # usually the interesting part. Report and carry on.
        print(f"    (navigation: {e.__class__.__name__} — reporting what was seen)")

    page.wait_for_timeout(3000)

    fp = fingerprint(page)
    print(f"    landed: HTTP {status} | {fp.get('url')}")
    print(f"    title : {fp.get('title')!r}")
    print(
        f"    dom   : {fp.get('bodyChars')} chars of text, "
        f"{fp.get('tables')} tables, {fp.get('rows')} rows"
    )
    print(f"    head  : {fp.get('head')!r}")

    # Drive it. An XHR fired only on interaction is invisible to a script that
    # merely waits, and that is a live explanation for run 4's silence.
    before = len(seen)
    try:
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(1500)
        for sel in INTERACTION_SELECTORS:
            loc = page.locator(sel).first
            if loc.count():
                loc.click(timeout=2500)
                page.wait_for_timeout(1500)
    except Exception as e:  # noqa: BLE001 - most selectors match nothing; that is fine
        print(f"    (interaction: {e.__class__.__name__})")
    if len(seen) > before:
        print(f"    +{len(seen) - before} API call(s) appeared only after interaction")

    print(f"    all hosts: {dict(hosts.most_common(8))}")
    if not seen:
        print("    no api.bseindia.com calls captured")
    for st, method, u in seen:
        print(f"    {st} {method} {u}")

    context.close()
    return seen


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "playwright not installed; run: pip install playwright && "
            "playwright install --with-deps chromium"
        )
        return 1

    all_seen = []
    with sync_playwright() as p:
        # Headless Chrome announces itself through navigator.webdriver whatever
        # the UA string says, and BSE demonstrably filters on client identity
        # (run 3: the api host answers a bare request with 403 Access Denied).
        browser = p.chromium.launch(
            args=["--disable-blink-features=AutomationControlled"]
        )
        try:
            for label, url in PAGES:
                try:
                    all_seen += capture(browser, label, url)
                except Exception as e:  # noqa: BLE001 - one page must not end the run
                    print(f"    PAGE FAILED: {e.__class__.__name__}: {e}")
        finally:
            browser.close()

    # The distinct endpoint paths, which is the actual deliverable — the query
    # strings above show the parameter names, and this shows the surface.
    print("\n=== DISTINCT ENDPOINTS ===")
    paths = sorted({u.split("?")[0] for _s, _m, u in all_seen})
    for path in paths:
        print(f"    {path}")
    if not paths:
        print("    none — read the per-page 'all hosts' and 'dom' lines above:")
        print("      hosts empty      -> the capture was blind, not the page silent")
        print("      dom ~0 chars     -> BSE served its shell, the URL is wrong")
        print("      dom full, 0 API  -> the page really is server-rendered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
