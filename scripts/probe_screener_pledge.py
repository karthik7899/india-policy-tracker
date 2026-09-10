"""Find where Screener actually serves the promoter pledge figure.

analysis/pledging.py has been complete and correct for months and has never
graded a single holding. Production run 147 (08 Sep 2026) reports:

    Promoter pledging: 0 alert(s) from 0 holding(s) with a disclosed
    pledge; 70 not disclosed or not parsed.

The cause is settled, and it is not the regex. The diagnostic already in
providers/screener.py printed the rows the shareholding section actually
carries:

    Pledge row not matched for HAL. Shareholding rows present:
    ['Promoters +', 'FIIs +', 'DIIs +', 'Government +', 'Public +',
     'No. of Shareholders', ... repeated for the yearly tab]

CAUTION about that output, and about the first reading of it. The diagnostic
is once-per-run and fired on HAL — a government-owned company, which has no
promoter pledge and structurally cannot have one. Its missing pledge row is
CORRECT output. Concluding from it that "Screener has no pledge row" was a
generalisation from n=1, on the least informative sample the watchlist
contains, and it may well be wrong: Screener is understood to print the row
only for companies that actually carry a pledge.

So this script now dumps the shareholding row labels for SEVERAL holdings,
chosen so that a null result would mean something. If a promoter-led
smallcap also lacks the row, the expander theory stands. If any company
shows it, the fix is a parser change after all and the whole JS chase below
was solving a problem that did not exist.

So the question this script answers is narrow: WHAT URL does that expander
call? It does not guess. Guessing endpoints is what cost 32 failed attempts
against BSE before a DevTools capture showed the answer was a path we had
never tried. Here the markup is already in our hands, so the method is to
READ the expander's attributes and follow whatever they name.

The expander turned out to be neither an HTMX attribute nor a link but a JS
call, and the function it names does not hold a URL either. So the chase is
three hops, each one measured rather than assumed:

  1. The promoter row's attributes. MEASURED (run 1):
     ``onclick="Company.showShareholders('promoters', 'quarterly', this)"``
     — a handler, so there is no URL to fetch here.
  2. The function, in the scripts the page loads. MEASURED (run 2), in
     company.customisation.*.js:
     ``_loadRows(Utils.getUrl("getShareholders", context), ...)``
     — still no URL, but it names a registry key.
  3. That key in the URL registry. MEASURED (run 4), in utils.*.js:
     ``getShareholders: "/api/3/{companyId}/investors/{classification}/{period}/"``
     — the path, at last, and formatted by Screener's own code rather than
     invented by ours.

The script now CALLS that template first and reports what comes back, which
settles the two questions left. The template wants ``companyId``, but the
peers table uses ``warehouseId`` and providers/screener.py only extracts the
latter — so every id on the page is tried and the response says which is
right. And the expander buttons carry ``plausible-event-user=unregistered``,
so a 401/403 would mean the path is correct and the account is the obstacle:
a different problem, and one to raise rather than route around.

No guessed paths remain. A guess that returns 200 proves the path exists,
not that it is the one the page uses, and the registry has made guessing
unnecessary.

Also reported: the HTTP status of every request. Screener answered this
pipeline with 429s throughout run 147 ("Peer radar: 0 industry table(s)
fetched for 66 holding(s)"), so a fix that costs one extra request per
holding would trade the pledge figure for the peer radar. If this probe
gets rate-limited too, that IS the finding, and the answer is a batched or
cached fetch rather than a per-holding one.

Manual only. Writes nothing, commits nothing. Read the job log.
"""

import re
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 2)[0])

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402

BASE = "https://www.screener.in"

# Chosen so a null result would MEAN something. HAL is government-owned and
# structurally cannot carry a promoter pledge, so its missing row is expected
# and uninformative — exactly the trap the production diagnostic fell into by
# sampling it alone. It is kept as the control. The rest are promoter-led
# companies where a pledge is at least possible, including smallcaps where it
# is common.
TICKERS = ("HAL", "SUZLON", "ANANTRAJ", "OPTIEMUS", "ADSL", "FAZE3Q")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Attributes that carry a URL on an expander. Listed rather than pattern
# matched so the output says which one hit.
#
# onclick is deliberately NOT here. Run 1 of this probe included it, and
# Screener's expander turned out to be `Company.showShareholders('promoters',
# 'quarterly', this)` — a JS call, not a URL. Fetching it produced three
# ConnectionErrors against a hostname made of the function name, which read
# like a finding and was not. A handler goes to _handlers, not _URL_ATTRS.
_URL_ATTRS = (
    "hx-get",
    "hx-post",
    "data-url",
    "data-src",
    "data-hx-get",
    "href",
    "action",
)

# JS handlers, reported separately: these name the function to chase through
# the bundle rather than a URL to fetch.
_HANDLER_ATTRS = ("onclick", "@click", "x-on:click")

_PLEDGE_RE = re.compile(r"pledg", re.I)

PAUSE_S = 3.0


def _get(session, url, label):
    """One request, with its status reported whatever happens."""
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
    except Exception as e:
        print(f"      {label}: FAILED {type(e).__name__}: {str(e)[:120]}")
        return None
    size = len(r.content or b"")
    note = ""
    if r.status_code == 429:
        note = "  <-- RATE LIMITED; see the module docstring"
    print(f"      {label}: HTTP {r.status_code}, {size:,} bytes{note}")
    return r if r.status_code == 200 else None


def _describe_promoter_row(soup):
    """Print every URL-bearing attribute on the promoter expander.

    This is the part that answers the question. Everything below it is
    fallback for the case where Screener renders the expander some other way.
    """
    section = soup.find("section", id="shareholding")
    if not section:
        print("      no #shareholding section on the page")
        return [], []

    # Every row label, per ticker. The production diagnostic in
    # providers/screener.py is once-per-run and happened to fire on HAL — a
    # government-owned PSU, which has no promoter pledge and never will. Its
    # missing pledge row is correct output, not evidence about the other 69
    # holdings, and reading it as "Screener has no pledge row" was a
    # conclusion from n=1 drawn on the least informative sample available.
    labels = []
    for tr in section.find_all("tr"):
        cells = tr.find_all("td")
        if cells:
            text = cells[0].get_text(" ", strip=True)
            if text:
                labels.append(text)
    print(f"      shareholding rows: {labels}")
    pledge_rows = [x for x in labels if _PLEDGE_RE.search(x)]
    print(f"      pledge row present: {bool(pledge_rows)} {pledge_rows or ''}")

    urls, handlers = [], []
    for row in section.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        label = cells[0].get_text(" ", strip=True)
        if "promoter" not in label.lower():
            continue

        print(f"      row: {label!r}")
        # The expander is usually a button or anchor inside the first cell.
        for el in cells[0].find_all(["button", "a", "span", "div"]):
            attrs = dict(el.attrs)
            if not attrs:
                continue
            for key in _URL_ATTRS:
                if attrs.get(key):
                    print(f"        URL   {key}={attrs[key]}")
                    urls.append(str(attrs[key]))
            for key in _HANDLER_ATTRS:
                if attrs.get(key):
                    print(f"        JS    {key}={attrs[key]}")
                    handlers.append(str(attrs[key]))
    return urls, handlers


_FUNC_RE = re.compile(r"([A-Za-z_$][\w$]*)\s*\(")
# A URL literal or template inside the bundle, including `/api/${id}/...`
# forms, which is how the path is normally assembled.
_URL_IN_JS_RE = re.compile(r"""["'`](/[^"'`\s]{4,120})["'`]""")
# Utils.getUrl("getShareholders", ...) — the registry key to chase next.
_GETURL_RE = re.compile(r"""getUrl\s*\(\s*["'`]([\w.-]+)["'`]""")


def _chase_handler_through_js(session, soup, handlers):
    """Follow the expander to the URL, one indirection at a time.

    Run 2 got as far as the function and stopped, because the function does
    not contain a URL either:

        function showShareholders(classification, period, target) {
          const context = {companyId: info.companyId, classification, period};
          _loadRows(Utils.getUrl("getShareholders", context), target, ...);
        }

    So the path lives in a URL registry under the key "getShareholders", in
    another bundle. Every script is fetched ONCE into memory and then searched
    for each hop, rather than refetching per name — Screener rate-limits this
    pipeline, and a probe that costs a request per lookup is the same mistake
    the eventual fix has to avoid.
    """
    names = set()
    for h in handlers:
        for m in _FUNC_RE.finditer(h):
            names.add(m.group(1))
    names.discard("")
    if not names:
        print("      no function name parsed out of the handler")
        return
    print(f"      chasing: {sorted(names)}")

    srcs = []
    for tag in soup.find_all("script", src=True):
        src = tag["src"]
        srcs.append(src if src.startswith("http") else BASE + src)
    print(f"      page loads {len(srcs)} script(s); fetching each once")

    bundles = {}
    for src in dict.fromkeys(srcs):
        time.sleep(PAUSE_S)
        r = _get(session, src, src.rsplit("/", 1)[-1][:60])
        if r is not None:
            bundles[src] = r.text

    def _report(term, label, require_url=False, limit=3):
        """Print the source around occurrences of term, and any URLs.

        ``require_url`` skips windows with no URL literal in them. Run 3
        needed it: searching for the key "getShareholders" matched the CALL
        SITE first — Utils.getUrl("getShareholders", context) — and filled
        the hit limit inside company.customisation.js before ever reaching
        the registry in utils.js. The call site is the thing we already knew.
        Only a window containing a path is new information.
        """
        hits = 0
        for src, body in bundles.items():
            start = 0
            while True:
                idx = body.find(term, start)
                if idx == -1:
                    break
                start = idx + len(term)
                window = body[max(0, idx - 400) : idx + 800]
                paths = sorted(set(_URL_IN_JS_RE.findall(window)))
                if require_url and not paths:
                    continue
                hits += 1
                print(f"        {label} in {src.rsplit('/', 1)[-1][:50]}")
                if paths:
                    print(f"          URL literals: {paths[:8]}")
                print(f"          {window[:600]}")
                if hits >= limit:
                    return hits
        return hits

    keys = set()
    for name in names:
        _report(name, f"[{name}]", limit=1)
        # Second hop: whatever registry key the function asks the URL for.
        for body in bundles.values():
            for m in re.finditer(rf"{re.escape(name)}[\s\S]{{0,400}}", body):
                keys.update(_GETURL_RE.findall(m.group(0)))

    if not keys:
        print("      function names no getUrl key; the URL may be inline above")
        return

    print(f"      registry key(s) named by the function: {sorted(keys)}")
    for key in sorted(keys):
        found = _report(f'"{key}"', f"[key {key}]", require_url=True)
        if not found:
            found = _report(f"'{key}'", f"[key {key}]", require_url=True)
        if not found:
            print(f"        no URL-bearing window for {key!r}")

    # Belt and braces: dump the registry itself. If the key lookup above
    # found nothing, the map is still the place the answer lives, and
    # printing it is cheaper than another run.
    print("      [3] the URL registry (getUrl definition)")
    if not _report("getUrl", "[getUrl def]", require_url=True, limit=2):
        print("        getUrl not found with a URL nearby in any bundle")


def _looks_like_pledge(text):
    """Does this response actually carry the number we want?"""
    if not text:
        return False
    return bool(_PLEDGE_RE.search(text))


# MEASURED (run 4), from Screener's own URL registry in utils.*.js:
#
#     getShareholders: "/api/3/{companyId}/investors/{classification}/{period}/"
#
# Not a guess. This is the template the page itself formats and fetches.
SHAREHOLDERS_TEMPLATE = "/api/3/{company_id}/investors/{classification}/{period}/"


def _company_ids(soup, page_text):
    """Every id on the page that could be the {companyId} the template wants.

    Worth being careful here: the JS passes info.companyId to this endpoint
    but info.warehouseId to the peers table, so they are not necessarily the
    same number, and providers/screener.py only ever extracts the warehouse
    one. Rather than assume, collect the candidates and let the request say
    which is right.
    """
    ids = {}
    for attr in ("data-company-id", "data-warehouse-id"):
        el = soup.find(attrs={attr: True})
        if el and el.get(attr):
            ids[attr] = el.get(attr)
    # getInfo() reads these off the DOM; the inline bootstrap sometimes
    # carries them as plain JS instead.
    for m in re.finditer(r"companyId\s*[:=]\s*[\"']?(\d{3,12})", page_text):
        ids.setdefault("inline companyId", m.group(1))
    return ids


def _try_shareholders_endpoint(session, ids):
    """Call the endpoint the registry named, for each candidate id.

    This is the step that settles the two open questions at once: whether we
    have the right id, and whether the view is gated. The buttons carry
    plausible-event-user=unregistered, so a 401/403 here would mean the path
    is correct and the account is the obstacle — a different problem, and one
    to raise rather than work around.
    """
    for label, cid in ids.items():
        path = SHAREHOLDERS_TEMPLATE.format(
            company_id=cid, classification="promoters", period="quarterly"
        )
        time.sleep(PAUSE_S)
        r = _get(session, BASE + path, f"{label}={cid} -> {path}")
        if r is None:
            continue
        if _looks_like_pledge(r.text):
            print("        *** PLEDGE FIGURE PRESENT — this is the endpoint ***")
            print(f"        {r.text[:700]}")
            return True
        print(
            f"        200 but no pledge text; first 300 chars:\n        {r.text[:300]}"
        )
    return False


def probe(session, ticker):
    print(f"\n  {ticker}")
    page = _get(session, f"{BASE}/company/{ticker}/consolidated/", "company page")
    if page is None:
        return

    soup = BeautifulSoup(page.text, "html.parser")

    ids = _company_ids(soup, page.text)
    print(f"      id candidates: {ids}")

    print("    [0] calling the endpoint the registry named")
    if _try_shareholders_endpoint(session, ids):
        return

    # Does the flat page carry it after all? Cheap to check and it would
    # make everything below unnecessary.
    if _looks_like_pledge(page.text):
        print("      NOTE: 'pledg' appears in the page source — check the context,")
        print("            the current parser may be looking in the wrong section.")

    print("    [1] promoter expander attributes")
    urls, handlers = _describe_promoter_row(soup)

    if urls:
        print(f"    [2] following {len(urls)} URL(s) the markup names")
        for raw in dict.fromkeys(urls):
            url = raw if raw.startswith("http") else BASE + raw
            time.sleep(PAUSE_S)
            r = _get(session, url, raw[:70])
            if r is not None and _looks_like_pledge(r.text):
                print("        *** PLEDGE FIGURE PRESENT — this is the endpoint ***")
                print(f"        {r.text[:600]}")
        return

    if handlers:
        print("    [2] expander is a JS handler; reading the bundle it lives in")
        _chase_handler_through_js(session, soup, handlers)
        return

    # No guessed paths any more. Step [0] calls the template Screener's own
    # registry gave us, so if that fails the answer is a changed registry —
    # which the JS chase above will show — not a path we have not thought of.
    print("    [2] markup named no URL and no handler; nothing further to follow")


def main():
    print("Screener promoter-pledge endpoint discovery")
    print("=" * 60)
    print(__doc__.strip().split("\n")[0])
    with requests.Session() as session:
        for i, ticker in enumerate(TICKERS):
            if i:
                time.sleep(PAUSE_S)
            probe(session, ticker)
    print("\nDone. If every request returned 429, that is the finding:")
    print("the fix must batch or cache, not add a request per holding.")


if __name__ == "__main__":
    main()
