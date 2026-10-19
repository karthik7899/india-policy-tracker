import asyncio
import aiohttp
import feedparser
import datetime  # noqa: F401  (referenced via patch("scraper.datetime...") in tests)
from bs4 import BeautifulSoup
import urllib.parse
import re
from logger import log
from config import SECTOR_QUERIES, GLOBAL_EVENT_QUERIES
from providers.rss import fetch_query_feed_async
from providers.nse_announcements import fetch_filings as nse_fetch_filings
from providers import bse_announcements
from providers.bse_announcements import fetch_filings as bse_fetch_filings
from analysis.parsing import title_matches_company


async def fetch_all_feeds_async():
    """Fetches news from Google News RSS for all sectors asynchronously."""
    log.info("Initializing RSS Aggregation engine (Async)...")

    today_brief = {}
    tasks = []

    async with aiohttp.ClientSession() as session:
        for sector, queries in SECTOR_QUERIES.items():
            today_brief[sector] = []
            for query in queries:
                tasks.append(fetch_query_feed_async(session, sector, query))

        results = await asyncio.gather(*tasks)

    sector_results = {sector: [] for sector in SECTOR_QUERIES}
    for sec, news_list in results:
        sector_results[sec].extend(news_list)

    for sector in SECTOR_QUERIES:
        sector_news = []
        seen_titles = set()
        for cleaned in sector_results[sector]:
            title_lower = cleaned["title"].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                sector_news.append(cleaned)

        # Newest first. This used to sort "Positive" sentiment first before
        # keeping four, so an upbeat-sounding story displaced a newer, more
        # negative one before anyone saw it — a selection bias applied by a
        # tone score that is not even a reading of policy direction.
        from analysis.event_evidence import article_date

        sector_news.sort(key=lambda x: article_date(x.get("date")) or "", reverse=True)
        today_brief[sector] = sector_news[:4]  # Store top 4 articles per sector
        log.info(
            f"Aggregated {len(today_brief[sector])} feed items for sector: {sector}"
        )

    return today_brief


_NAVIGATION_MARKS = ("menu", "nav", "header", "footer", "breadcrumb")


def _is_navigation(li):
    """A list item that is a page's menu rather than a release's content.

    A real page lists its menus in the same tags as a release lists its
    beneficiaries, and every one of them would otherwise be read as a
    company. A menu item is a link, or sits in a nav, header, footer or menu
    block; a list of beneficiaries in a release is plain text. Decided on
    structure alone, because PIB's markup could not be checked: the
    development sandbox's proxy refuses pib.gov.in.
    """
    link = li.find("a")
    if link is not None and link.get_text(strip=True) == li.get_text(strip=True):
        return True
    for parent in li.parents:
        if parent.name in ("nav", "header", "footer"):
            return True
        marks = " ".join(
            [str(parent.get("id") or "")] + list(parent.get("class") or [])
        ).lower()
        if any(m in marks for m in _NAVIGATION_MARKS):
            return True
    return False


def _extract_pli_data_from_html(html, title, published_date=""):
    companies = []
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ")

    # 1. Sector extraction
    sector = "Manufacturing"
    title_lower = title.lower()
    # ⚡ Bolt Optimization: Slice first, then lower, outside the loop to avoid redundant O(N) operations
    text_prefix_lower = text[:500].lower()
    for s in [
        "automobile",
        "auto components",
        "white goods",
        "it hardware",
        "textile",
        "telecom",
        "solar",
        "drone",
        "pharmaceutical",
        "medical devices",
        "food processing",
        "specialty steel",
    ]:
        if s in title_lower or s in text_prefix_lower:
            sector = s.title()
            break

    # 2. Scheme extraction
    scheme = "PLI Scheme"
    if "2.0" in title_lower or "2.0" in text[:500]:
        scheme = "PLI 2.0"

    # 3. Extract companies from tables
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if cols:
                cell_text = cols[0].get_text(strip=True)
                # Filter out headers and junk
                if (
                    len(cell_text) > 3
                    and len(cell_text) < 100
                    and not cell_text.lower()
                    in [
                        "company",
                        "company name",
                        "s. no.",
                        "s.no",
                        "name",
                        "applicant",
                    ]
                ):
                    # Ensure it's not a multi-line chunk that regex failed on earlier
                    if "\n" not in cell_text:
                        companies.append(cell_text)

    # 4. Extract companies from lists, leaving out a page's navigation
    for ul in soup.find_all("ul"):
        for li in ul.find_all("li"):
            if _is_navigation(li):
                continue
            li_text = li.get_text(strip=True)
            if len(li_text) > 3 and len(li_text) < 100 and "\n" not in li_text:
                companies.append(li_text)

    # 5. Regex fallback on text
    corp_pattern = re.compile(
        r"\b([A-Z][a-zA-Z0-9&]+(?:\s+[A-Z][a-zA-Z0-9&]+)*)\s+(?:Ltd|Limited|Corp|Corporation|Enterprises|Solutions|Electronics|Industries|Apparels|Defence|Semiconductors|Company)\b"
    )
    for m in corp_pattern.finditer(text):
        companies.append(m.group(0))

    # Clean and deduplicate
    unique_companies = []
    seen_lower = set()
    for c in companies:
        c_clean = re.sub(r"^\d+[\.\)]\s*", "", c).strip()
        cl = c_clean.lower()
        if cl not in seen_lower and len(c_clean) > 3 and len(c_clean) < 80:
            seen_lower.add(cl)
            unique_companies.append(
                {
                    "name": c_clean,
                    "sector": sector,
                    "scheme": scheme,
                    "date": published_date,
                }
            )

    return unique_companies


# Company names per search: few enough that one busy name (Apple, Google)
# does not take every result, enough to cover the graph in a few requests.
_COMPANY_BATCH = 8
# Results kept per company search; the vocabulary searches keep 5.
_COMPANY_RESULTS = 8
# What a company search looks for: its deals, and how its business is doing.
# Results and demand matter as much as deals — "Corning sales fall" is what
# reaches the Optiemus venture.
_COMPANY_TERMS = (
    "deal OR partnership OR investment OR order OR expansion OR supply OR "
    "sales OR revenue OR profit OR results OR guidance OR demand OR "
    "layoffs OR shutdown"
)


def watched_company_names(graph, holdings=(), extra=()):
    """Every company the graph ties to what we hold, plus ``extra``.

    The demand anchors, every holding's partners, and whoever else is being
    watched (new entrants the radar flagged). Holdings themselves are left
    out: their own news is searched for by sector.
    """
    held = {str(t).upper() for t in holdings}
    names = {str(n) for n in extra}
    for edge in (graph or {}).get("edges", []):
        if edge.get("type") == "anchor_demand":
            names.add(str(edge.get("src")))
        elif edge.get("type") == "partner":
            names |= {
                str(end)
                for end in (edge.get("src"), edge.get("dst"))
                if str(end).upper() not in held
            }
    unique = {}
    for name in names:
        name = name.strip()
        if len(name) >= 3:
            unique.setdefault(name.lower(), name)
    return sorted(unique.values(), key=str.lower)


def company_queries(names, batch=_COMPANY_BATCH):
    """News searches covering ``names``, ``batch`` to a search.

    There used to be one search, of the first 12 anchors alphabetically:
    Nvidia, TSMC, Samsung, Micron, Microsoft and Qualcomm were never searched,
    and no holding's partner was searched at all.
    """
    return [
        "("
        + " OR ".join(f'"{n}"' for n in names[i : i + batch])
        + f") AND ({_COMPANY_TERMS})"
        for i in range(0, len(names), batch)
    ]


async def fetch_global_event_feeds_async(session, holdings=(), watched=()):
    """Global market-event headlines: supply-chain shocks, big tie-ups, and
    the news of companies tied to our holdings, whose second-order impact
    lands on them.

    Queries are entity-free vocabulary from config plus company searches
    assembled at runtime from the entity graph (watched_company_names) — so
    which companies get watched is data, never code. Enhancement channel:
    fail-safe, capped, and never blocks the briefing.
    """
    from analysis.entity_graph import load_entity_graph
    from utils import fetch_text_async

    queries = [(q, 5) for q in GLOBAL_EVENT_QUERIES]
    names = watched_company_names(load_entity_graph(), holdings, watched)
    queries += [(q, _COMPANY_RESULTS) for q in company_queries(names)]

    items = []
    seen = set()

    async def _fetch_query(query):
        try:
            encoded = urllib.parse.quote(f"{query} when:3d")
            url = (
                f"https://news.google.com/rss/search?q={encoded}"
                f"&hl=en-IN&gl=IN&ceid=IN:en"
            )
            status, xml_data = await fetch_text_async(session, url, timeout=15)
            if status == 200:
                return feedparser.parse(xml_data)
        except Exception as e:
            log.error(f"Global event feed query failed: {e}")
        return None

    # ⚡ Bolt Optimization: Batch fetch global event feed queries concurrently to prevent event-loop blocking from sequential IO.
    feeds = await asyncio.gather(*(_fetch_query(q) for q, _ in queries))

    for feed, (_, keep) in zip(feeds, queries):
        if not feed:
            continue
        for entry in feed.entries[:keep]:
            title = entry.get("title", "").split(" - ")[0].strip()
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            items.append(
                {
                    "title": title,
                    "link": entry.get("link", ""),
                    "date": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "News"),
                }
            )

    log.info(
        f"Global event feed: {len(items)} headlines collected "
        f"({len(names)} companies searched in {len(queries) - len(GLOBAL_EVENT_QUERIES)} "
        f"batch(es))."
    )
    return items


# Headlines kept per state per run. The query is broad on purpose (any policy
# word, any of our sector words), so the reader, not the query, decides what
# is policy.
STATE_ITEMS_PER_QUERY = 6
# Google News ignores "when:7d" for these queries: the first live run got 54
# headlines, 39 of them older than the 45-day retention, so stale stories took
# the slots meant for new ones. Age is checked here, before the slots fill.
STATE_MAX_AGE_DAYS = 14


async def fetch_state_policy_async(session, today=None):
    """State-government headlines, a few simple Google News searches per state.

    Each item carries ``feed_state``: the state whose search found it. That is
    where the search looked, not whose policy it is — the article can mention
    a state the headline does not — so jurisdiction is read from the headline
    itself (analysis/policy_impact.state_of). Items from a state's industrial
    policy searches (config.STATE_INDUSTRY_QUERIES) also carry
    ``feed_kind: "industry"``. Fail-safe like every feed: a search that fails
    contributes nothing and the run continues.
    """
    from analysis.event_evidence import article_date
    from config import STATE_INDUSTRY_QUERIES, STATE_POLICY_QUERIES
    from utils import fetch_text_async

    today = today or datetime.date.today()
    cutoff = (today - datetime.timedelta(days=STATE_MAX_AGE_DAYS)).isoformat()

    async def _fetch(state, kind, query):
        try:
            url = (
                "https://news.google.com/rss/search?q="
                f"{urllib.parse.quote(query + ' when:7d')}&hl=en-IN&gl=IN&ceid=IN:en"
            )
            status, xml_data = await fetch_text_async(session, url, timeout=15)
            if status == 200:
                return state, kind, feedparser.parse(xml_data)
            log.info(f"State policy feed ({state}, {query}): HTTP {status}.")
        except Exception as e:
            log.error(f"State policy feed ({state}, {query}) failed: {e}")
        return state, kind, None

    searches = [
        (state, kind, query)
        for kind, table in (
            ("general", STATE_POLICY_QUERIES),
            ("industry", STATE_INDUSTRY_QUERIES),
        )
        for state, queries in table.items()
        for query in queries
    ]
    results = await asyncio.gather(*(_fetch(*s) for s in searches))
    # One pool per state and kind, so a state's searches share its slots and
    # its industrial-policy searches have their own.
    pools: dict = {}
    for state, kind, feed in results:
        if feed:
            pools.setdefault((state, kind), []).extend(feed.entries)
    items, seen, per_state, stale, industry = [], set(), {}, 0, 0
    for (state, kind), entries in pools.items():
        fresh = []
        for entry in entries:
            date = article_date(entry.get("published")) or ""
            if date >= cutoff:
                fresh.append((date, entry))
            else:
                stale += 1
        fresh.sort(key=lambda d: d[0], reverse=True)
        taken = 0
        for _, entry in fresh:
            if taken >= STATE_ITEMS_PER_QUERY:
                break
            title = entry.get("title", "").split(" - ")[0].strip()
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            taken += 1
            per_state[state] = per_state.get(state, 0) + 1
            if kind == "industry":
                industry += 1
            items.append(
                {
                    "title": title,
                    "link": entry.get("link", ""),
                    "date": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "News"),
                    "feed_state": state,
                    **({"feed_kind": "industry"} if kind == "industry" else {}),
                }
            )
    states = dict.fromkeys([*STATE_POLICY_QUERIES, *STATE_INDUSTRY_QUERIES])
    log.info(
        f"State policy feed: {len(items)} headline(s), {industry} from "
        "industrial-policy searches — "
        + ", ".join(f"{s} {per_state.get(s, 0)}" for s in states)
        + f"; {stale} older than {STATE_MAX_AGE_DAYS} days skipped."
    )
    return items


# Releases read per run, to limit requests.
MAX_PLI_RELEASES = 5

# Every PIB release page names the bureau; Google News's own page for the same
# story does not. Names are read from a fetched page only when it is the
# release, because the parser takes every table cell and list item on a page
# for a company name.
_PIB_MARKER = "press information bureau"


def _is_pib_release(html):
    return _PIB_MARKER in (html or "")[:200_000].lower()


def _headline_text(title, summary):
    """The headline and summary as plain text.

    Google News summaries are HTML, and for a story several outlets carried
    they hold a list of the related headlines, each of which the parser
    would read as a company. Without the markup only the parser's
    company-suffix match ("... Ltd", "... Limited") can find a name.
    """
    plain = BeautifulSoup(summary, "lxml").get_text(" ") if summary else ""
    return f"{title} {plain}".strip()


async def scrape_pib_pli_approvals_async(session, watchlist):
    """PLI beneficiaries named in PIB releases from the last 30 days.

    Releases are found through Google News, and a Google News link can lead
    to Google's own page rather than to pib.gov.in. That page came back as an
    ordinary success, so the fallback to the headline -- which ran only when
    the fetch raised -- never ran, and this returned nothing on every run from
    at least mid-September 2026 without saying so. Names are now read from
    the release when the link leads there and from the headline and summary
    otherwise, and every step is counted in one log line. A headline names a
    company only now and then; a beneficiary list lives in the release.
    """
    log.info("Scraping PIB for PLI approval announcements (Async)...")
    query = 'site:pib.gov.in "PLI" AND ("provisionally selected" OR "approved" OR "incentive scheme" OR "applications approved")'
    encoded_query = urllib.parse.quote(f"{query} when:30d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    emerging_pli_competitors = []
    tally = {"releases": 0, "release page": 0, "headline": 0, "elsewhere": 0}
    failed = 0
    search_note = ""

    from utils import fetch_text_async

    try:
        status, xml_data = await fetch_text_async(session, rss_url, timeout=15)
        if status != 200:
            search_note = f"search returned HTTP {status}"
        else:
            feed = feedparser.parse(xml_data)
            entries = feed.entries[:MAX_PLI_RELEASES]
            tally["releases"] = len(entries)
            for entry in entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")

                extracted, source = [], "headline"
                try:
                    art_status, art_html = await fetch_text_async(
                        session, link, timeout=15
                    )
                    if art_status == 200 and _is_pib_release(art_html):
                        extracted = _extract_pli_data_from_html(
                            art_html, title, published
                        )
                        source = "release page"
                    else:
                        tally["elsewhere"] += 1
                except Exception as ex:
                    failed += 1
                    log.warning(f"PLI release fetch failed: {type(ex).__name__}: {ex}")
                if not extracted:
                    extracted = _extract_pli_data_from_html(
                        _headline_text(title, entry.get("summary", "")),
                        title,
                        published,
                    )
                    source = "headline"
                tally[source] += len(extracted)
                for comp in extracted:
                    comp["announcement"] = title.split(" - ")[0]
                    comp["link"] = link
                    comp["found_in"] = source
                    emerging_pli_competitors.append(comp)

    except Exception as e:
        log.error(f"Error scraping PIB PLI approvals: {e}")
        search_note = f"search failed ({type(e).__name__})"

    # Deduplicate before returning (can have same company in different RSS entries)
    deduped = []
    seen = set()
    from analysis.parsing import resolve_ticker_from_name_async

    # Existing names in watchlist to ignore
    existing_names = set()
    for sector, stocks in watchlist.items():
        for s in stocks:
            if s.get("name"):
                existing_names.add(str(s["name"]).lower())
            if s.get("ticker"):
                existing_names.add(str(s["ticker"]).lower())

    unique_candidates = []
    for comp in emerging_pli_competitors:
        name_lower = comp["name"].lower()
        if name_lower not in seen and name_lower not in existing_names:
            seen.add(name_lower)
            unique_candidates.append(comp)

    # Concurrently resolve tickers using asyncio.gather
    resolution_tasks = [
        resolve_ticker_from_name_async(comp["name"], session)
        for comp in unique_candidates
    ]
    resolution_results = await asyncio.gather(*resolution_tasks)

    for comp, result in zip(unique_candidates, resolution_results):
        ticker, _ = result
        comp["ticker"] = ticker
        comp["status"] = "Listed Peer" if ticker else "Unlisted"
        deduped.append(comp)
        log.info(
            f"PIB PLI approval competitor detected: {comp['name']} ({comp['status']})"
        )

    # One line that says where an empty result came from.
    log.info(
        "PLI approvals: "
        + (search_note or f"{tally['releases']} release(s) in the last 30 days")
        + f"; {tally['release page']} name(s) from release pages, "
        f"{tally['headline']} from headlines"
        + (
            f"; {tally['elsewhere']} link(s) led to a page that was not the release"
            if tally["elsewhere"]
            else ""
        )
        + (f"; {failed} fetch(es) failed" if failed else "")
        + f"; {len(deduped)} new candidate(s) after removing duplicates and "
        "holdings."
    )
    return deduped


async def fetch_advanced_rss_feeds_async(session, watchlist):
    log.info(
        "Fetching advanced RSS feeds for agreements and product launches (Async)..."
    )
    agreements = []
    launches = []

    all_tickers = []
    for sector, stocks in watchlist.items():
        for s in stocks:
            all_tickers.append(s["ticker"])

    # Combine queries in chunks of 4 to be polite to RSS service
    ticker_chunks = [all_tickers[i : i + 4] for i in range(0, len(all_tickers), 4)]

    # Pre-flatten watchlist once; matching itself is word-boundary + person-
    # name-guarded (see analysis.parsing.title_matches_company) — bare
    # substring checks mis-attributed "IBM CEO Arvind Krishna ..." to Arvind
    # Ltd and let ticker LT match any headline containing "Ltd".
    flat_watchlist = [
        (s["ticker"], s["name"], sector_name)
        for sector_name, stocks in watchlist.items()
        for s in stocks
    ]

    async def process_chunk(chunk):
        ticker_query = " OR ".join([f'"{t}"' for t in chunk])

        # Agreements
        agree_q = f'({ticker_query}) AND ("joint venture" OR "strategic partnership" OR "agreement" OR "collaboration" OR "MoU" OR "acquisition" OR "stake purchase")'
        encoded_agree = urllib.parse.quote(f"{agree_q} when:7d")
        rss_agree_url = f"https://news.google.com/rss/search?q={encoded_agree}&hl=en-IN&gl=IN&ceid=IN:en"

        from utils import fetch_text_async

        try:
            status, xml_data = await fetch_text_async(
                session, rss_agree_url, timeout=15
            )
            if status == 200:
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:3]:
                    title = entry.get("title", "")

                    # Attribute to a holding, exactly as launches and filings
                    # already do. Without this the record carried no company
                    # field at all, so dashboard/builder.py keyed all forty
                    # agreements under "" and none of them ever reached the
                    # holding they were about — a third of the policy-event
                    # corpus scoring nothing, silently.
                    matched_company = "Unknown"
                    matched_industry = "Corporate"
                    for ticker_sym, s_name, sector_name in flat_watchlist:
                        if title_matches_company(title, ticker_sym, s_name):
                            matched_company = s_name
                            matched_industry = sector_name
                            break

                    agreements.append(
                        {
                            "company": matched_company,
                            "industry": matched_industry,
                            "title": title.split(" - ")[0],
                            "link": entry.get("link", ""),
                            "date": entry.get("published", ""),
                            "source": entry.get("source", {}).get("title", "News"),
                        }
                    )
        except Exception as e:
            log.error(f"Error fetching agreements chunk: {e}")

        # Launches
        launch_q = f'({ticker_query}) AND ("product launch" OR "unveils" OR "commercial production" OR "production starts" OR "new facility" OR "new plant" OR "pilot production")'
        encoded_launch = urllib.parse.quote(f"{launch_q} when:7d")
        rss_launch_url = f"https://news.google.com/rss/search?q={encoded_launch}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with session.get(rss_launch_url, timeout=15) as resp:
                if resp.status == 200:
                    xml_data = await resp.text()
                    feed = feedparser.parse(xml_data)
                    for entry in feed.entries[:3]:
                        title = entry.get("title", "")

                        matched_company = "Unknown"
                        matched_industry = "Manufacturing"
                        for ticker_sym, s_name, sector_name in flat_watchlist:
                            if title_matches_company(title, ticker_sym, s_name):
                                matched_company = s_name
                                matched_industry = sector_name
                                break

                        launches.append(
                            {
                                "company": matched_company,
                                "product": title.split(" - ")[0],
                                "industry": matched_industry,
                                "date": entry.get("published", ""),
                                "source": entry.get("source", {}).get("title", "News"),
                                "link": entry.get("link", ""),
                            }
                        )
        except Exception as e:
            log.error(f"Error fetching launches chunk: {e}")

    await asyncio.gather(*[process_chunk(chunk) for chunk in ticker_chunks])

    unique_agreements = {a["title"]: a for a in agreements}.values()
    unique_launches = {launch["product"]: launch for launch in launches}.values()

    return list(unique_agreements)[:10], list(unique_launches)[:10]


def holding_names(watchlist):
    """Display names of everything we hold.

    Both exchange providers set ``company`` to the watchlist name when they
    match a holding, so an exact hit here means the filing is about a stock
    in the book. That is the only holdings signal that survives the merge —
    each provider sorts its own output holdings-first, but that ordering is
    invisible once the lists are concatenated.
    """
    return {
        s.get("name")
        for stocks in (watchlist or {}).values()
        for s in (stocks or [])
        if isinstance(s, dict) and s.get("name")
    }


def _interleave(*sources):
    """Round-robin across sources, preserving each one's internal order.

    Concatenation is what starved BSE: NSE alone returns hundreds of records,
    so `nse + bse` followed by a ten-row cap meant BSE never reached the
    section at all. Measured in production on 2026-09-09 — 40 filings, every
    one from NSE, on a pipeline where the BSE provider was working fine.
    """
    from itertools import zip_longest

    out = []
    for group in zip_longest(*sources):
        out.extend(item for item in group if item is not None)
    return out


async def fetch_exchange_filings_async(session, watchlist, cap=10, held_out=None):
    """Corporate filings from both exchanges and the press.

    The exchange APIs give the filing itself — exact identifier, the
    company's own subject line, the attached PDF. The news search below is
    what we had before them and is kept as the fallback, because either
    exchange can refuse a cloud IP on any given day: a block must degrade the
    section, not empty it.

    Ordering decides the whole result, because a full trading day produces
    hundreds of filings for a section that shows ten. Two rules, in order:

      1. Holdings before everything else. A filing about a stock we own is
         worth more than one about a company we have never heard of, whoever
         published it.
      2. Within each tier, round-robin across sources rather than
         concatenating. Concatenation lets whichever source answers first
         consume every slot — which is exactly what happened to BSE.
    """
    log.info(
        "Fetching NSE/BSE corporate filings (Async)..."
        if bse_announcements.BSE_ENABLED
        else "Fetching NSE corporate filings (Async); BSE is switched off..."
    )

    async def no_filings():
        return []

    # to_thread because both providers are sync requests (they need cookie-jar
    # persistence across the handshake) and this coroutine must not block the
    # event loop while they sleep out their rate-limit pauses. Gathered so the
    # two exchanges' pauses overlap instead of adding up.
    nse_filings, bse_filings, news_filings = await asyncio.gather(
        asyncio.to_thread(nse_fetch_filings, watchlist),
        (
            asyncio.to_thread(bse_fetch_filings, watchlist)
            if bse_announcements.BSE_ENABLED
            else no_filings()
        ),
        _fetch_filing_news_async(session, watchlist),
    )

    held = holding_names(watchlist)

    def split(filings):
        ours = [f for f in filings if f.get("company") in held]
        theirs = [f for f in filings if f.get("company") not in held]
        return ours, theirs

    nse_held, nse_rest = split(nse_filings)
    bse_held, bse_rest = split(bse_filings)
    news_held, news_rest = split(news_filings)

    # Every exchange filing by a holding, uncapped, for event confirmation
    # (analysis/event_evidence.confirm_with_filings). The section below keeps
    # ten; the check needs all of them — the one that confirms an order win is
    # rarely among the day's first ten. Exchange filings only: the news path
    # is somebody's account of a filing, which is what gets checked.
    if held_out is not None:
        ticker_of = {
            s.get("name"): str(s.get("ticker", "")).upper()
            for key, stocks in (watchlist or {}).items()
            if key != "macro_indicators"
            for s in stocks or []
            if isinstance(s, dict) and s.get("ticker")
        }
        from analysis.event_evidence import article_date

        for f in nse_held + bse_held:
            ticker = ticker_of.get(f.get("company"))
            if not ticker:
                continue
            held_out.append(
                {
                    "ticker": ticker,
                    "date": article_date(f.get("date")) or "",
                    "text": str(f.get("filing") or "")[:240],
                    "source": f.get("source"),
                    "link": f.get("link") or "",
                }
            )

    # Exchanges lead each tier: they carry the filing itself, where the news
    # path carries somebody's account of it and identifies the company by a
    # fuzzy title match.
    ordered = (
        _interleave(nse_held, bse_held)
        + news_held
        + _interleave(nse_rest, bse_rest)
        + news_rest
    )

    # Keyed on (company, filing), not filing alone. Two companies file the
    # same subject constantly — NSE stamps a coarse category on many records
    # — so a text-only key silently collapses a whole day into one row. This
    # matches the key main.py already dedupes the merged history on.
    #
    # setdefault, not a dict comprehension: the comprehension idiom used
    # elsewhere in this file keeps the LAST record for a duplicate key, which
    # here would hand every reported filing back to the weaker news version.
    unique = {}
    for filing in ordered:
        unique.setdefault((filing["company"], filing["filing"]), filing)
    result = list(unique.values())[:cap]

    kept = {}
    for f in result:
        kept[f.get("source", "?")] = kept.get(f.get("source", "?"), 0) + 1
    log.info(
        f"Corporate filings: {len(nse_filings)} from NSE, "
        + (
            f"{len(bse_filings)} from BSE, "
            if bse_announcements.BSE_ENABLED
            else "BSE off, "
        )
        + f"{len(news_filings)} from news; kept {len(result)} — {kept}. "
        f"{len(nse_held) + len(bse_held) + len(news_held)} concerned holdings."
    )
    return result


async def _fetch_filing_news_async(session, watchlist):
    """Filings as reported by the press. The original implementation, now the
    fallback: it recovers the company by fuzzy title match, so it is strictly
    weaker identification than NSE's symbol, but it survives an IP block."""
    filings = []

    all_tickers = []
    for sector, stocks in watchlist.items():
        for s in stocks:
            all_tickers.append(s["ticker"])

    ticker_chunks = [all_tickers[i : i + 4] for i in range(0, len(all_tickers), 4)]

    flat_watchlist = [
        (s["ticker"], s["name"], sector_name)
        for sector_name, stocks in watchlist.items()
        for s in stocks
    ]

    async def process_chunk(chunk):
        ticker_query = " OR ".join([f'"{t}"' for t in chunk])
        filing_q = f'({ticker_query}) AND ("NSE" OR "BSE" OR "Exchange Filing" OR "Regulatory Filing") AND ("Agreement" OR "MoU" OR "Acquisition" OR "Expansion" OR "Capacity" OR "Capex" OR "Joint Venture" OR "Technology Transfer")'
        encoded_filing = urllib.parse.quote(f"{filing_q} when:3d")
        rss_url = f"https://news.google.com/rss/search?q={encoded_filing}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with session.get(rss_url, timeout=15) as resp:
                if resp.status == 200:
                    xml_data = await resp.text()
                    feed = feedparser.parse(xml_data)
                    for entry in feed.entries[:3]:
                        title = entry.get("title", "")

                        matched_company = "Unknown"
                        matched_industry = "Corporate"
                        for ticker_sym, s_name, sector_name in flat_watchlist:
                            if title_matches_company(title, ticker_sym, s_name):
                                matched_company = s_name
                                matched_industry = sector_name
                                break

                        filings.append(
                            {
                                "company": matched_company,
                                "filing": title.split(" - ")[0],
                                "industry": matched_industry,
                                "date": entry.get("published", ""),
                                "source": entry.get("source", {}).get(
                                    "title", "Exchange"
                                ),
                                "link": entry.get("link", ""),
                            }
                        )
        except Exception as e:
            log.error(f"Error fetching filings chunk: {e}")

    await asyncio.gather(*[process_chunk(chunk) for chunk in ticker_chunks])

    # Deduped here as well as in the caller: this half can repeat a headline
    # across chunks, and the cap keeps a chatty news day from crowding out
    # the exchange records it gets merged with.
    unique_filings = {f["filing"]: f for f in filings}.values()
    return list(unique_filings)[:10]


async def check_sebi_sid_filings_async(session):
    log.info("Checking SEBI filings for thematic funds (Incoming Capital) (Async)...")
    query = 'site:sebi.gov.in "Scheme Information Document" AND ("manufacturing" OR "semiconductors" OR "defence" OR "logistics" OR "technology")'
    encoded_query = urllib.parse.quote(f"{query} when:30d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    filings = []
    try:
        async with session.get(rss_url, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    theme = "Manufacturing & PLI"
                    if "defence" in title.lower() or "defense" in title.lower():
                        theme = "Defence & Aerospace"
                    elif "semiconductor" in title.lower() or "chip" in title.lower():
                        theme = "Semiconductors & Tech"
                    elif "logistics" in title.lower():
                        theme = "Logistics & Infra"

                    filings.append(
                        {
                            "fund_name": title.split(" - ")[0].replace("SEBI | ", ""),
                            "theme": theme,
                            "status": "Incoming Institutional Capital",
                            "date": entry.get("published", ""),
                            "link": entry.get("link", "https://www.sebi.gov.in"),
                        }
                    )
                    log.info(f"SEBI MF SID filing detected: {title} [{theme}]")
    except Exception as e:
        log.error(f"Error checking SEBI filings: {e}")

    return filings


def _parse_block_deal_headline(headline, flat_watchlist, headline_lower):
    buyer = "Institutional Investor"
    action = "Buy"
    company = "Listed Company"
    details = "Block Deal"

    if any(
        w in headline_lower
        for w in [
            "sells",
            "dumped",
            "exits",
            "offloads",
            "reduces stake",
        ]
    ):
        action = "Sell"
    elif any(
        w in headline_lower
        for w in [
            "buys",
            "acquires",
            "purchases",
            "picks up",
            "increases stake",
        ]
    ):
        action = "Buy"

    buyer_match = re.search(
        r"^([A-Z0-9][A-Za-z0-9\s\.\&]+?)\s+(?:buys|acquires|sells|purchases|picks up|offloads|exits|increases|decreases|shares|block|bulk|mutual)",
        headline,
    )
    if buyer_match:
        buyer = buyer_match.group(1).strip()

    details_match = re.search(
        r"(\d+(?:\.\d+)?%\s*stake|\d+\s*(?:lakh|million|crore)?\s*shares|worth\s*(?:Rs\s*)?\d+\s*(?:cr|crore|crores)?)",
        headline,
        re.IGNORECASE,
    )
    if details_match:
        details = details_match.group(1).strip()

    company_match = re.search(
        r"(?:in|of|shares of|stake in|shares in)\s+([A-Z][A-Za-z0-9\s\&]+?)(?:\s+via|\s+worth|\s+for|\s+at|\s+through|\s+block|\s+bulk|$)",
        headline,
    )
    if company_match:
        company = company_match.group(1).strip()

    # Match against watchlist stocks (word-boundary + person-name guard)
    matched_company = None
    matched_ticker = None
    for ticker_sym, s_name, _sector in flat_watchlist:
        if title_matches_company(headline, ticker_sym, s_name):
            matched_company = s_name
            matched_ticker = ticker_sym
            break

    if matched_company:
        company = f"{matched_company} ({matched_ticker})"

    return buyer, action, company, details


async def fetch_institutional_activity_async(session, watchlist):
    log.info(
        "Fetching institutional activity block deals and mutual fund buying trends (Async)..."
    )
    query = '"block deal" OR "bulk deal" OR "mutual fund buys" OR "FII buying" India'
    encoded_query = urllib.parse.quote(f"{query} when:7d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    flat_watchlist = [
        (s["ticker"], s["name"], None) for stocks in watchlist.values() for s in stocks
    ]

    activity = []
    try:
        async with session.get(rss_url, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:8]:  # Get top 8 entries
                    headline = entry.get("title", "").split(" - ")[0].strip()
                    headline_lower = headline.lower()

                    buyer, action, company, details = _parse_block_deal_headline(
                        headline, flat_watchlist, headline_lower
                    )

                    activity.append(
                        {
                            "headline": headline,
                            "link": entry.get("link", ""),
                            "source": entry.get("source", {}).get(
                                "title", "Finance Media"
                            ),
                            "date": entry.get("published", ""),
                            "buyer": buyer,
                            "action": action,
                            "company": company,
                            "details": details,
                        }
                    )
    except Exception as e:
        log.error(f"Error fetching institutional activity: {e}")

    return activity
