"""Capture what BSE's own pages call — the DevTools Network tab, scripted.

Guessing endpoint names has now failed eight times across two probe runs: four
shareholding candidates all returned the same generic ASP.NET page, and three
announcement parameter sets all returned "No Record Found!". That is the point
to stop guessing and read what the site itself does.

This loads BSE pages in headless Chromium and records every XHR they fire,
with the query string intact. Whatever the shareholding page calls to render
the promoter pledge row is, by definition, in that list.

Runs only on the Actions runner: BSE refuses connections from the development
sandbox (403 on CONNECT). Writes nothing, and is never called by a briefing
run.

Two questions it exists to answer, both currently blocking:

  1. Which endpoint serves the promoter pledge figure? Screener's page yielded
     it for 0 of 69 holdings, so BSE is the fallback and we cannot find the
     door by knocking on names.
  2. What parameters does AnnGetData actually want? It answers with JSON and
     "No Record Found!", so the endpoint is alive and only the query is wrong.
"""

import sys

# Reliance: large, always has filings, and its pledge row is a known quantity.
SAMPLE_SCRIP = "500325"

PAGES = [
    (
        "shareholding pattern",
        f"https://www.bseindia.com/stock-share-price/reliance-industries-ltd/"
        f"reliance/{SAMPLE_SCRIP}/shareholding-pattern/",
    ),
    (
        "corp announcements",
        f"https://www.bseindia.com/stock-share-price/reliance-industries-ltd/"
        f"reliance/{SAMPLE_SCRIP}/corp-announcements/",
    ),
    (
        "announcements listing",
        "https://www.bseindia.com/corporates/ann.html",
    ),
]

# The page fires plenty of chrome, analytics and font requests. Only calls to
# the API host can carry the data, so everything else is noise.
API_HOST = "api.bseindia.com"


def capture(browser, label, url):
    print(f"\n=== {label}")
    print(f"    {url}")

    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
        )
    )
    page = context.new_page()

    seen = []
    # Recorded on response rather than request, so the status is available:
    # an endpoint the page calls and which then 404s is a different finding
    # from one that returns data, and both are worth seeing.
    page.on(
        "response",
        lambda r: (
            seen.append((r.status, r.request.method, r.url))
            if API_HOST in r.url
            else None
        ),
    )

    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
    except Exception as e:
        # A timeout still leaves whatever was captured before it, which is
        # usually the interesting part. Report and carry on.
        print(f"    (navigation: {e.__class__.__name__} — reporting what was seen)")

    # Shareholding sits behind a quarter selector on some layouts; give any
    # lazily-fired follow-up call a moment to land.
    page.wait_for_timeout(3000)

    if not seen:
        print("    no API calls captured")
    for status, method, u in seen:
        print(f"    {status} {method} {u}")

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
        browser = p.chromium.launch()
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
        print("    none — the pages may render server-side, or navigation failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
