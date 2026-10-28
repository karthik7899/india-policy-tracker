"""Ask one upstream source what it is actually serving, and say so.

Every upstream this pipeline depends on is denied by the development
environment's egress policy, so a question like "what does Screener's peers
endpoint return now?" cannot be answered locally. Twice this week it was
answered the slow way instead: change the code to log more, merge it, fire the
daily brief, read the log, repeat. Three round trips for the peer radar, and
six briefing emails sent to a human who did not ask for them.

This is the fast way. It runs in CI, where the hosts ARE reachable, and it:

  * makes ONE request per source, never a sweep;
  * feeds the response to the REAL parser, because a probe with its own
    parsing proves nothing about the pipeline — the peer-table bug was a
    parser bug, not a fetch bug;
  * prints a bounded description of what came back, and saves the raw sample
    as a workflow artifact so a fixture can be built from the genuine article
    rather than reconstructed by hand;
  * sends no email, writes no payload, commits nothing.

    python scripts/probe_upstream.py --source screener-peers --symbol HAL
    python scripts/probe_upstream.py --source all
"""

import argparse
import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_DIR = os.environ.get("PROBE_OUT", "probe-output")

# Samples are for building fixtures, not for archiving a website. Enough to
# see the shape of a response and no more.
SAMPLE_BYTES = 40000
SHOW_CHARS = 400


def _save(name, text):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(text)[:SAMPLE_BYTES])
    return path


def _report(title, status, content_type, body, parsed_summary, saved):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")
    print(f"  HTTP        : {status}")
    print(f"  Content-Type: {content_type or 'unstated'}")
    print(f"  Size        : {len(body or '')} bytes")
    print(f"  PARSED      : {parsed_summary}")
    if saved:
        print(f"  Sample      : {saved}")
    visible = " ".join(str(body or "").split())[:SHOW_CHARS]
    print(f"  First {SHOW_CHARS} chars:\n    {visible}")


async def probe_screener_peers(symbol):
    """The endpoint that returned a readable table nobody could read."""
    import aiohttp

    from providers.screener import fetch_screener_async, parse_peer_table

    async with aiohttp.ClientSession() as session:
        # The company page first, because the peers URL needs its warehouse id
        # — and that dependency is itself worth exercising.
        _t, sc, warehouse_id = await fetch_screener_async(session, symbol, "probe", 0.0)
        print(
            f"  company page: screener fields={len(sc or {})} "
            f"warehouse_id={warehouse_id!r}"
        )
        if not warehouse_id:
            print("  PARSED      : no warehouse id, so the peers URL cannot be built")
            return False

        url = f"https://www.screener.in/api/company/{warehouse_id}/peers/"
        async with session.get(
            url, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=15
        ) as response:
            body = await response.text()
            status = response.status
            ctype = response.headers.get("Content-Type", "")

    rows = parse_peer_table(body)
    summary = f"{len(rows)} peer row(s)"
    if rows:
        summary += f"; first = {json.dumps(rows[0])[:160]}"
    _report(
        f"SCREENER PEERS ({symbol}, warehouse {warehouse_id})",
        status,
        ctype,
        body,
        summary,
        _save("screener_peers.html", body),
    )
    return status == 200 and bool(rows)


def _row_labels(soup, section_id):
    """First-column labels of a Screener section's rows, as the parser sees them."""
    section = soup.find("section", id=section_id)
    if not section:
        return []
    labels = []
    for tr in section.find_all("tr"):
        tds = tr.find_all("td")
        if tds:
            labels.append(tds[0].get_text(" ", strip=True))
    return labels


def _watchlist_name(symbol):
    """The watchlist's name for a holding, which the pipeline checks a
    Screener search answer against; None outside the watchlist."""
    try:
        with open("watchlist.json", encoding="utf-8") as f:
            watchlist = json.load(f)
    except (OSError, ValueError):
        return None
    for rows in watchlist.values():
        for s in rows if isinstance(rows, list) else []:
            if isinstance(s, dict) and s.get("ticker") == symbol:
                return s.get("name")
    return None


async def _screener_search(session, symbol):
    """What Screener's own search calls a company it has no page for under
    the ticker: by the ticker, then by the watchlist's name for it."""
    from urllib.parse import quote

    for query in [symbol, _watchlist_name(symbol)]:
        if not query:
            continue
        url = (
            "https://www.screener.in/api/company/search/" f"?q={quote(query)}&v=3&fts=1"
        )
        async with session.get(url, timeout=20) as response:
            body = await response.text()
            status = response.status
            ctype = response.headers.get("Content-Type", "")
        try:
            hits = [(h.get("name"), h.get("url")) for h in json.loads(body)][:6]
        except (ValueError, AttributeError, TypeError):
            hits = "unreadable"
        _report(
            f"SCREENER SEARCH ({query!r})",
            status,
            ctype,
            body,
            f"results={hits}",
            _save(f"screener_search_{symbol}_{len(query)}.json", body),
        )
        await asyncio.sleep(1.5)


async def probe_screener_accounts(symbols):
    """Each company's consolidated and standalone pages, side by side.

    On 14 Oct SCHNEIDER, PAGEIND and RELAXO came back from the consolidated
    page with their shareholding and no figures, and ASMTEC with nothing.
    This reads both views of each company (comma-separated symbols) through
    the real parser, then what the pipeline's fetch returns.
    """
    import re

    import aiohttp
    from bs4 import BeautifulSoup

    from providers.screener import (
        ACCOUNTS,
        company_url,
        fetch_screener_async,
        has_figures,
        parse_company_page,
    )

    found = False
    async with aiohttp.ClientSession() as session:
        for symbol in [s.strip().upper() for s in symbols.split(",") if s.strip()]:
            for accounts in ACCOUNTS:
                # Screener limits by rate; one request every 1.5 s stays clear.
                await asyncio.sleep(1.5)
                url = company_url(symbol, accounts)
                async with session.get(url, timeout=20) as response:
                    body = await response.text()
                    status = response.status
                    ctype = response.headers.get("Content-Type", "")
                    final = str(response.url)
                sc, warehouse_id = parse_company_page(body, symbol, "probe")
                core = {
                    k: sc.get(k) for k in ("market_cap", "pe_ratio", "roce", "q_sales")
                }
                _report(
                    f"SCREENER {accounts.upper()} ({symbol})",
                    status,
                    ctype,
                    body,
                    f"figures={has_figures(sc)} {core}; {len(sc)} field(s); "
                    f"warehouse={warehouse_id}; final URL {final}",
                    _save(f"screener_{symbol}_{accounts}.html", body),
                )
                soup = BeautifulSoup(body, "lxml")
                text = " ".join(soup.get_text(" ").split())
                mentions = re.findall(
                    r"[^.]{0,90}\b(?:consolidated|standalone)\b[^.]{0,90}", text, re.I
                )
                print(f"  Mentions    : {mentions[:3] or 'none'}")
                # The labels the parser matches against: a bank's page names
                # its rows differently from a manufacturer's.
                for section in ("quarters", "profit-loss", "ratios"):
                    print(
                        f"  Rows {section:<11}: {_row_labels(soup, section) or 'none'}"
                    )
                if status == 404 and accounts == ACCOUNTS[-1]:
                    await asyncio.sleep(1.5)
                    await _screener_search(session, symbol)
            await asyncio.sleep(1.5)
            _t, sc, _w = await fetch_screener_async(
                session, symbol, "probe", 0.0, name=_watchlist_name(symbol)
            )
            shown = {
                k: (sc or {}).get(k)
                for k in ("accounts", "slug", "q_sales", "q_opm", "q_fin_margin")
            }
            print(
                f"  PIPELINE    : {symbol} -> {shown} "
                f"figures={has_figures(sc)} fields={len(sc or {})}"
            )
            found = found or has_figures(sc)
    return found


async def probe_nse_isin():
    """EQUITY_L.csv — the source that settles an ISIN disagreement."""
    import aiohttp

    from providers.isin_master import (
        _HEADERS,
        _NSE_EQUITY_LIST_URL,
        load_isin_master,
        parse_equity_csv,
        parse_equity_names,
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(
            _NSE_EQUITY_LIST_URL, headers=_HEADERS, timeout=20, allow_redirects=False
        ) as response:
            body = await response.text()
            status, ctype = response.status, response.headers.get("Content-Type", "")

    live = parse_equity_csv(body)
    master = load_isin_master()
    disagree = {
        s: (master[s], i) for s, i in live.items() if s in master and master[s] != i
    }
    missing = [s for s in live if s not in master]

    summary = (
        f"{len(live)} symbol(s) parsed; {len(missing)} absent from the master; "
        f"{len(disagree)} disagree"
    )
    _report(
        "NSE EQUITY_L.csv", status, ctype, body, summary, _save("nse_equity.csv", body)
    )

    if disagree:
        print(
            f"\n  DISAGREEMENTS ({len(disagree)}) — the question a log cannot answer:"
        )
        same_issuer = sum(1 for o, n in disagree.values() if o[:9] == n[:9])
        print(
            f"    same issuer, different issue series (a corporate action): {same_issuer}"
        )
        print(
            f"    genuinely different issuer (a real collision):           "
            f"{len(disagree) - same_issuer}"
        )
        for sym, (old, new) in sorted(disagree.items())[:15]:
            kind = "series" if old[:9] == new[:9] else "ISSUER"
            print(f"      {sym:14} {old} -> {new}   [{kind}]")

    _report_names(parse_equity_names(body))
    return bool(live)


def _report_names(names):
    """How the holdings' and competitors' stored names compare with the names
    NSE registers, and what analysis/company_names.py would store instead.
    Tab-separated: who, ticker, registered name, stored name, repaired name
    ("=" when the stored one stands)."""
    from analysis.company_names import tidy_name

    rows = {}
    with open("watchlist.json", encoding="utf-8") as f:
        for sector, stocks in json.load(f).items():
            if sector == "macro_indicators" or not isinstance(stocks, list):
                continue
            for s in stocks:
                if isinstance(s, dict) and s.get("ticker"):
                    rows[str(s["ticker"]).upper()] = ("holding", s.get("name") or "")
    for path in ("data/peer_competitors.json", "data/candidate_screen.json"):
        try:
            with open(path, encoding="utf-8") as f:
                body = json.load(f)
        except (OSError, ValueError):
            continue
        for peers in (body.get("value") or {}).values():
            for p in peers if isinstance(peers, list) else []:
                ticker = str((p or {}).get("ticker") or "").upper()
                if ticker and ticker not in rows:
                    rows[ticker] = ("competitor", p.get("name") or "")

    print(f"\n  REGISTERED NAMES: {len(names)} parsed")
    repaired = 0
    for ticker, (who, stored) in sorted(rows.items()):
        registered = names.get(ticker)
        new = tidy_name(stored, registered)
        repaired += new != stored
        print(
            f"  NAME\t{who}\t{ticker}\t{registered or '-'}\t{stored}\t"
            f"{new if new != stored else '='}"
        )
    print(f"  {repaired} of {len(rows)} stored name(s) would be repaired.")


def probe_bse_scrips():
    """BSE's scrip master — the other half of the ISIN namespace question."""
    from providers.bse_announcements import fetch_scrip_master
    from providers.isin_master import load_isin_master, parse_bse_scrip_rows

    rows = fetch_scrip_master()
    mapping = parse_bse_scrip_rows(rows)
    master = load_isin_master()
    disagree = {
        s: (master[s], i) for s, i in mapping.items() if s in master and master[s] != i
    }

    print(f"\n{'=' * 72}\nBSE SCRIP MASTER\n{'=' * 72}")
    print(f"  rows returned : {len(rows or [])}")
    print(f"  parsed        : {len(mapping)} scrip_id -> ISIN")
    print(f"  disagree with the master: {len(disagree)}")
    if rows:
        _save("bse_scrips_sample.json", json.dumps(rows[:50], indent=2))
        print(f"  Sample        : {OUT_DIR}/bse_scrips_sample.json")
    if disagree:
        same_issuer = sum(1 for o, n in disagree.values() if o[:9] == n[:9])
        print(f"    same issuer (corporate action): {same_issuer}")
        print(f"    different issuer (collision)  : {len(disagree) - same_issuer}")
        for sym, (old, new) in sorted(disagree.items())[:15]:
            kind = "series" if old[:9] == new[:9] else "ISSUER"
            print(f"      {sym:14} {old} -> {new}   [{kind}]")
    return bool(mapping)


async def probe_nse_delivery():
    import aiohttp

    from providers.nse_delivery import fetch_delivery_async

    async with aiohttp.ClientSession() as session:
        delivery = await fetch_delivery_async(session)
    print(f"\n{'=' * 72}\nNSE DELIVERY BHAVCOPY\n{'=' * 72}")
    print(f"  securities parsed: {len(delivery or {})}")
    if delivery:
        sym = next(iter(delivery))
        print(f"  sample           : {sym} -> {json.dumps(delivery[sym])[:200]}")
    return bool(delivery)


def probe_nse_announcements():
    """Is NSE's disclosure API the primary filings source, or the fallback?

    providers/nse_announcements.py is written to survive a refusal, so the
    pipeline cannot tell you which of the two it is currently living as. Only
    a runner can.

    Each layer is reported separately because they fail for different reasons
    and a single pass/fail would hide which one moved: the handshake mints
    cookies or does not; the API answers 200 or the 401/403 that means the IP
    is refused; the body is JSON or the challenge page served WITH a 200; and
    the field names are the part most likely to have quietly drifted. The
    provider reads through aliases so a rename degrades one field rather than
    emptying the feed, which is exactly why a rename would otherwise go
    unnoticed until it cost a section.
    """
    import datetime

    from providers import nse_announcements as nse
    from providers.screener import describe_fragment

    print(f"\n{'=' * 72}\nNSE CORPORATE ANNOUNCEMENTS\n{'=' * 72}")
    session = nse.build_session()
    try:
        ok = nse.handshake(session)
        cookies = sorted(session.cookies.keys()) if session.cookies else []
        print(f"  handshake   : {ok} -> cookies {cookies}")
        if not ok:
            # Deliberately does NOT name a cause. handshake() swallows its
            # exception and returns a bare False, which covers two different
            # worlds: the edge answered and challenged us, or the request
            # never reached the edge at all. This line used to assert the
            # first, and said so on a run where the agent proxy had refused
            # the CONNECT — blaming NSE for a local egress policy. The log
            # line immediately above carries the real reason; read it.
            print(
                "  no cookies minted, so the API call will be refused. Cause "
                "is NOT established here — the WARNING above says whether the "
                "edge challenged us or the request never left this machine."
            )

        today = datetime.date.today()
        params = {
            "index": nse.DEFAULT_INDEX,
            "from_date": today.strftime("%d-%m-%Y"),
            "to_date": today.strftime("%d-%m-%Y"),
        }
        response = session.get(
            nse.API_URL,
            params=params,
            headers=nse.API_HEADERS,
            timeout=nse.REQUEST_TIMEOUT_S,
        )
        ctype = response.headers.get("Content-Type", "")
        body = response.text or ""
        print(f"  url         : {nse.API_URL}")
        print(f"  params      : {params}")
        print(f"  status      : {response.status_code}")
        print(f"  content-type: {ctype or 'unstated'}")
        print(f"  bytes       : {len(body)}")

        if "application/json" not in ctype.lower():
            # Short bodies print verbatim. An earlier BSE probe described an
            # 18-byte response by its keys alone and hid the answer in doing so.
            print(f"  body        : {describe_fragment(body, ctype)}")
            print("  VERDICT     : refused — HTML where JSON was asked for.")
            return False

        try:
            payload = json.loads(body)
        except ValueError as e:
            print(f"  body        : {describe_fragment(body, ctype)}")
            print(f"  VERDICT     : JSON declared but undecodable: {e}")
            return False

        if isinstance(payload, dict):
            print(f"  envelope    : dict, keys {sorted(payload.keys())[:12]}")
            rows = payload.get("data", payload.get("rows", []))
        else:
            print(f"  envelope    : {type(payload).__name__}")
            rows = payload

        count = len(rows) if isinstance(rows, list) else 0
        print(f"  records     : {count}")
        _save("nse_announcements.json", body)
        print(f"  Sample      : {OUT_DIR}/nse_announcements.json")

        if not (isinstance(rows, list) and rows):
            # Empty is not the same as refused, and saying so matters: on a
            # holiday or before the day's first filing this is correct output.
            print(
                "  VERDICT     : reachable but empty. Before concluding the "
                "endpoint moved, check this is a trading day and that "
                "announcements have been published yet today."
            )
            return False

        print(f"  FIELD NAMES : {sorted(rows[0].keys())}")
        normalized = nse.normalize(rows[0])
        print(f"  NORMALIZED  : {json.dumps(normalized, default=str)[:300]}")
        empty = [k for k, v in (normalized or {}).items() if not v]
        if empty:
            print(f"  EMPTY FIELDS: {empty} — check the aliases")
        print("  VERDICT     : reachable. NSE can serve as the primary source.")
        return True
    finally:
        session.close()


def probe_nse_calendar():
    """Do NSE's event calendar and corporate actions answer a runner, and in
    what shape?

    providers/nse_calendar.py was written against the fields NSE's own pages
    read, not against a measured response. This prints, per endpoint, what
    came back and the field names, and saves the bodies, so the aliases can
    be checked against the genuine article.
    """
    import datetime

    from providers import nse_announcements as nse
    from providers import nse_calendar as cal
    from providers.screener import describe_fragment

    print(f"\n{'=' * 72}\nNSE EVENT CALENDAR AND CORPORATE ACTIONS\n{'=' * 72}")
    session = nse.build_session()
    ok_all = True
    try:
        ok = nse.handshake(session)
        print(f"  handshake   : {ok} -> cookies {sorted(session.cookies.keys())}")
        today = datetime.date.today()
        window = {
            "index": "equities",
            "from_date": (today - datetime.timedelta(days=cal.BACK_DAYS)).strftime(
                "%d-%m-%Y"
            ),
            "to_date": (today + datetime.timedelta(days=cal.AHEAD_DAYS)).strftime(
                "%d-%m-%Y"
            ),
        }
        for name, url, page, normalize in (
            ("event-calendar", cal.EVENTS_URL, cal.EVENTS_PAGE, cal.normalize_event),
            (
                "corporate-actions",
                cal.ACTIONS_URL,
                cal.ACTIONS_PAGE,
                cal.normalize_action,
            ),
        ):
            for params in (window, None):
                nse._polite_pause()
                response = session.get(
                    url,
                    params=params,
                    headers={**nse.API_HEADERS, "Referer": page},
                    timeout=nse.REQUEST_TIMEOUT_S,
                )
                ctype = response.headers.get("Content-Type", "")
                body = response.text or ""
                print(f"\n  {name} params={params}")
                print(f"    status      : {response.status_code}")
                print(f"    content-type: {ctype or 'unstated'}")
                print(f"    bytes       : {len(body)}")
                if "json" not in ctype.lower():
                    print(f"    body        : {describe_fragment(body, ctype)}")
                    ok_all = False
                    continue
                try:
                    payload = json.loads(body)
                except ValueError as e:
                    print(f"    VERDICT     : JSON declared but undecodable: {e}")
                    ok_all = False
                    continue
                rows = (
                    payload.get("data", payload.get("rows", []))
                    if isinstance(payload, dict)
                    else payload
                )
                count = len(rows) if isinstance(rows, list) else 0
                print(f"    records     : {count}")
                _save(f"nse_{name}{'' if params else '_bare'}.json", body)
                if count:
                    print(f"    FIELD NAMES : {sorted(rows[0].keys())}")
                    normalized = [normalize(r) for r in rows]
                    usable = [n for n in normalized if n]
                    print(f"    usable      : {len(usable)} of {count}")
                    if usable:
                        print(f"    SAMPLE      : {json.dumps(usable[0])[:300]}")
                    break
            else:
                ok_all = False
        return ok_all
    finally:
        session.close()


async def probe_pib_pli():
    """The PLI scraper's own path, a step at a time, against the live sites.

    Google News for the stories; PIB's lists of this month's and last month's
    releases for each story's release, and for the releases PIB titles as a
    scheme's; each release's own page for the names, with the scheme each was
    read under, before the scraper keeps those under a scheme a holding works
    in; then the scraper itself, end to end, on today's watchlist. What the
    probes that built it found is in docs/upstream-findings.md.
    """
    import re

    import aiohttp
    import feedparser
    from bs4 import BeautifulSoup

    import scraper
    from config import load_watchlist
    from providers import pib
    from providers.isin_master import load_registered_names
    from utils import fetch_text_async

    async with aiohttp.ClientSession() as session:
        print(f"\n{'=' * 72}\nGOOGLE NEWS: which releases there were\n{'=' * 72}")
        status, xml = await fetch_text_async(session, scraper.pli_search_url())
        entries = feedparser.parse(xml).entries if status == 200 else []
        stories = scraper._stories(entries)
        print(f"  HTTP {status}: {len(entries)} result(s), {len(stories)} release(s)")

        print(
            f"\n{'=' * 72}\nPIB: its lists of this month's and last month's releases\n{'=' * 72}"
        )
        index = pib.MonthIndex(session)
        ranked, unfound, general = await scraper._locate_on_pib(
            stories, index, pib.today_in_india()
        )
        print(f"  {general} found that are about no scheme, not read")
        for first, links in index.months.items():
            print(f"  {first:%B %Y}: {len(links)} release(s)")
        if index.failed:
            print(f"  {index.failed}")
        for item in ranked:
            source = "Google" if "story" in item else "PIB title"
            print(
                f"    {scraper._relevance(item['title'])} PRID {item['prid']} "
                f"({source}): {item['title'][:85]}"
            )
        listed = [
            (t, prid, set(pib.title_words(t)))
            for links in index.months.values()
            for t, prid, _ in links
        ]
        for story in unfound:
            want = set(pib.title_words(story["title"]))
            near = max(
                ((len(want & w) / len(want | w), prid, t) for t, prid, w in listed),
                default=(0, "", ""),
            )
            print(f"    not on the lists: {story['title'][:90]}")
            if want and near[0] >= 0.3:
                print(f"      nearest ({near[0]:.2f}) PRID {near[1]}: {near[2][:90]}")

        print(f"\n{'=' * 72}\nPIB: what each release to be read names\n{'=' * 72}")
        for item in ranked[: scraper.MAX_PLI_RELEASES]:
            status, page = await fetch_text_async(
                session, pib.release_url(item["prid"]), timeout=20
            )
            release = pib.read_release(page) if status == 200 else None
            print(f"  PRID {item['prid']}: HTTP {status}, {len(page)} bytes")
            if release is None:
                print("    no release text on the page")
                continue
            print(f"    {release['date']} {release['title'][:90]}")
            names = scraper._extract_pli_data_from_html(
                release["html"], release["title"], release["date"]
            )
            for c in names:
                print(f"    > {c['name']} | {c['sector']} | {c['scheme_sectors']}")
            if not names:
                # Where names might be that the parser does not take.
                body = BeautifulSoup(release["html"], "lxml")
                for t, table in enumerate(body.find_all("table")[:4]):
                    for row in table.find_all("tr")[:4]:
                        cells = [
                            c.get_text(" ", strip=True)[:30]
                            for c in row.find_all(["td", "th"])
                        ]
                        print(f"      table {t}: {cells[:5]}")
                lines = scraper._text_lines(body)
                hits = [
                    ln for ln in lines if re.search(r"Limited|Ltd|Pvt|LLP|Private", ln)
                ]
                print(f"      {len(lines)} line(s); {len(hits)} with a legal word")
                for ln in hits[:6]:
                    print(f"      | {ln[:150]}")
                for ln in lines[:6]:
                    print(f"      : {ln[:150]}")

        print(f"\n{'=' * 72}\nTHE SCRAPER, end to end\n{'=' * 72}")
        found = await scraper.scrape_pib_pli_approvals_async(
            session, load_watchlist(), registered=load_registered_names()
        )
        for c in found:
            print(
                f"    * {c['name']} ({c['status']}, {c.get('ticker')}) | "
                f"{c['sector']} | {c['found_in']} | {c['announcement'][:60]}"
            )
    return bool(index.read)


# Publishers' own markets feeds. Every news item the pipeline collects comes
# through Google News search, whose links lead to the article only through
# the URL decoding this project does not do; a publisher's own feed links to
# its article directly and often carries the opening paragraph.
PUBLISHER_FEEDS = {
    "Economic Times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Livemint": "https://www.livemint.com/rss/markets",
    "Business Standard": "https://www.business-standard.com/rss/markets-106.rss",
    "Moneycontrol": "https://www.moneycontrol.com/rss/buzzingstocks.xml",
}
# Said plainly: who is asking and where to find them.
PROBE_AGENT = (
    "india-policy-tracker-probe/1.0 "
    "(+https://github.com/karthik7899/india-policy-tracker)"
)
_BROKERAGE_CALL = re.compile(
    r"upgrad|downgrad|target|\bbuy\b|\bsell\b|outperform|brokerage|top pick",
    re.IGNORECASE,
)


def probe_publisher_news():
    """Can the pipeline read why a brokerage made a call, not only that it did?

    The thesis check counts a brokerage's upgrade for a thesis and a
    downgrade against it, but a headline seldom says why, and the reason is
    what tells an owner whether the call touches the thesis. For each
    publisher this asks three things, one request each, with a plain client
    that says who it is and takes no for an answer:

      * robots.txt: may an automated reader fetch its articles at all;
      * its markets feed: how many items, how many carry a summary, and
        whether their links lead to the article itself;
      * one article from that feed (a brokerage call if there is one): what
        the page returns and how much of it is readable paragraph text.

    A refusal is reported as a refusal and not retried.
    """
    import urllib.robotparser
    from urllib.parse import urlparse

    import feedparser
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": PROBE_AGENT}
    readable = []
    for name, feed_url in PUBLISHER_FEEDS.items():
        print(f"\n{'=' * 72}\nPUBLISHER: {name}\n{'=' * 72}")
        host = urlparse(feed_url).netloc
        robots = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(f"https://{host}/robots.txt", headers=headers, timeout=20)
            # As urllib.robotparser reads it: refused means keep out, missing
            # (another 4xx) means no rules, and a server error leaves the
            # rules unread, which keeps out as well (can_fetch is False until
            # rules are read).
            if r.status_code in (401, 403):
                robots.disallow_all = True
            elif 400 <= r.status_code < 500:
                robots.allow_all = True
            elif r.status_code < 400:
                robots.parse(r.text.splitlines())
            print(f"  robots.txt  : HTTP {r.status_code}")
        except requests.RequestException as e:
            print(f"  robots.txt  : request failed: {e!r}"[:200])
        try:
            r = requests.get(feed_url, headers=headers, timeout=20)
        except requests.RequestException as e:
            print(f"  feed        : request failed: {e!r}"[:200])
            continue
        print(
            f"  feed        : HTTP {r.status_code} {r.headers.get('Content-Type', '')}"
        )
        if r.status_code != 200:
            print(f"  body        : {' '.join(r.text.split())[:200]}")
            continue
        _save(f"feed_{host}.xml", r.text)
        entries = feedparser.parse(r.content).entries
        summaries = [
            " ".join(BeautifulSoup(e.get("summary", ""), "lxml").get_text(" ").split())
            for e in entries
        ]
        direct = [e for e in entries if host.split(".", 1)[-1] in e.get("link", "")]
        print(
            f"  items       : {len(entries)}, {sum(1 for t in summaries if len(t) > 40)} "
            f"with a summary, {len(direct)} linking to the article itself"
        )
        if not direct:
            continue
        pick = next(
            (e for e in direct if _BROKERAGE_CALL.search(e.get("title", ""))),
            direct[0],
        )
        i = entries.index(pick)
        print(f"  article     : {pick.get('title', '')[:110]}")
        print(f"  summary     : {summaries[i][:300] or '(none)'}")
        link = pick.get("link", "")
        allowed = robots.can_fetch(PROBE_AGENT, link)
        print(f"  robots allow: {allowed}")
        if not allowed:
            continue
        try:
            r = requests.get(link, headers=headers, timeout=20)
        except requests.RequestException as e:
            print(f"  page        : request failed: {e!r}"[:200])
            continue
        _save(f"article_{host}.html", r.text)
        page = BeautifulSoup(r.text, "lxml")
        text = " ".join(
            t
            for t in (p.get_text(" ", strip=True) for p in page.find_all("p"))
            if len(t) > 60
        )
        print(
            f"  page        : HTTP {r.status_code} {r.headers.get('Content-Type', '')}, "
            f"{len(text)} characters of paragraph text"
        )
        print(f"  text        : {text[:400] or '(none)'}")
        if r.status_code == 200 and len(text) > 500:
            readable.append(name)
    print(f"\n  ARTICLES READABLE FROM: {', '.join(readable) or 'none'}")
    return bool(readable)


SOURCES = {
    "pib-pli": ("async-noarg", probe_pib_pli),
    "screener-peers": ("async", probe_screener_peers),
    "screener-accounts": ("async", probe_screener_accounts),
    "nse-isin": ("async-noarg", probe_nse_isin),
    "bse-scrips": ("sync", probe_bse_scrips),
    "nse-delivery": ("async-noarg", probe_nse_delivery),
    "nse-announcements": ("sync", probe_nse_announcements),
    "nse-calendar": ("sync", probe_nse_calendar),
    "publisher-news": ("sync", probe_publisher_news),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default="all", choices=[*SOURCES, "all"])
    ap.add_argument("--symbol", default="HAL", help="for the per-company probes")
    args = ap.parse_args()

    chosen = list(SOURCES) if args.source == "all" else [args.source]

    # "Did not raise" is not "answered". Every probe reports whether it came
    # back with data anyone could use, because a summary that counts absence
    # of exceptions is the exact failure this tool was built to stop: the
    # first version of this line said "4/4 source(s) answered" on a run where
    # all four were blocked at the proxy.
    results = {}
    for name in chosen:
        kind, fn = SOURCES[name]
        try:
            if kind == "async":
                results[name] = bool(asyncio.run(fn(args.symbol)))
            elif kind == "async-noarg":
                results[name] = bool(asyncio.run(fn()))
            else:
                results[name] = bool(fn())
        except Exception as e:  # noqa: BLE001 - one dead source must not hide the rest
            results[name] = False
            print(f"\n{'=' * 72}\n{name.upper()}\n{'=' * 72}")
            print(f"  FAILED: {type(e).__name__}: {str(e)[:300]}")

    usable = [n for n, ok in results.items() if ok]
    print(f"\n{'=' * 72}\nSUMMARY\n{'=' * 72}")
    for name, ok in results.items():
        print(f"  {'DATA  ' if ok else 'NOTHING'} {name}")
    print(f"\n{len(usable)}/{len(chosen)} source(s) returned usable data.")
    if not usable:
        print(
            "  Every source came back empty. From a development sandbox that is\n"
            "  normally the egress policy rather than the upstream — the proxy\n"
            "  says so in the body ('Host not in allowlist'). From CI it means\n"
            "  the sources really are down or have changed."
        )
    # Always exit 0: a blocked or changed upstream is a FINDING, and failing
    # the job would make the tool feel broken when it is doing its job.
    return 0


if __name__ == "__main__":
    sys.exit(main())
