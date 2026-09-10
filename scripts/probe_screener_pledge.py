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

There is no pledge row on the page at all. The ``+`` on ``Promoters +`` is
the tell: it is an expander, and "Pledged percentage" is a child row that
only exists once expanded. No amount of tuning a row-label pattern will
find something the document does not contain.

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
  3. That key in the URL registry, which is where the path finally lives.

If a URL-bearing attribute ever does appear at step 1, it is fetched
directly and the rest is skipped. Conventional paths are tried only when
nothing at all is found, and are labelled as guesses: a 200 from a guessed
path proves the path exists, not that it is the one the page uses.

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

# Real holdings, chosen to span the cases. A promoter-heavy PSU, a private
# group company, and a smallcap: if pledge disclosure differs by company
# type, one ticker would not show it.
TICKERS = ("HAL", "RELIANCE", "SUZLON")

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

    def _report(term, label):
        """Print the source around every occurrence of term, and any URLs."""
        hits = 0
        for src, body in bundles.items():
            start = 0
            while True:
                idx = body.find(term, start)
                if idx == -1:
                    break
                hits += 1
                window = body[max(0, idx - 300) : idx + 700]
                paths = sorted(set(_URL_IN_JS_RE.findall(window)))
                print(f"        {label} in {src.rsplit('/', 1)[-1][:50]}")
                if paths:
                    print(f"          URL literals: {paths[:8]}")
                print(f"          {window[:500]}")
                start = idx + len(term)
                if hits >= 3:
                    return hits
        return hits

    keys = set()
    for name in names:
        if not _report(name, f"[{name}]"):
            continue
        # Second hop: whatever registry key the function asks the URL for.
        for body in bundles.values():
            for m in re.finditer(rf"{re.escape(name)}[\s\S]{{0,400}}", body):
                keys.update(_GETURL_RE.findall(m.group(0)))

    if keys:
        print(f"      registry key(s) named by the function: {sorted(keys)}")
        for key in sorted(keys):
            if not _report(f'"{key}"', f"[key {key}]"):
                _report(f"'{key}'", f"[key {key}]")
    else:
        print("      function names no getUrl key; the URL may be inline above")


def _looks_like_pledge(text):
    """Does this response actually carry the number we want?"""
    if not text:
        return False
    return bool(_PLEDGE_RE.search(text))


def probe(session, ticker):
    print(f"\n  {ticker}")
    page = _get(session, f"{BASE}/company/{ticker}/consolidated/", "company page")
    if page is None:
        return

    soup = BeautifulSoup(page.text, "html.parser")

    warehouse_el = soup.find(attrs={"data-warehouse-id": True})
    warehouse_id = warehouse_el.get("data-warehouse-id") if warehouse_el else None
    print(f"      warehouse id: {warehouse_id}")

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

    print("    [2] markup named no URL and no handler")
    print("    [3] conventional paths — GUESSES, a 200 here proves little")
    guesses = [f"/company/{ticker}/shareholding/"]
    if warehouse_id:
        guesses += [
            f"/api/company/{warehouse_id}/shareholding/",
            f"/api/company/{warehouse_id}/shareholders/",
        ]
    for path in guesses:
        time.sleep(PAUSE_S)
        r = _get(session, BASE + path, path)
        if r is not None and _looks_like_pledge(r.text):
            print("        *** PLEDGE FIGURE PRESENT ***")
            print(f"        {r.text[:600]}")


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
