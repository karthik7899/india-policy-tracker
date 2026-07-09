import asyncio
import aiohttp
import feedparser
import datetime  # noqa: F401  (referenced via patch("scraper.datetime...") in tests)
from bs4 import BeautifulSoup
import urllib.parse
import re
from logger import log
from config import SECTOR_QUERIES
from providers.rss import fetch_query_feed_async
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

        # Sort so Positive impacts are highlighted first
        sector_news.sort(
            key=lambda x: (
                1
                if x["impact"] == "Positive"
                else (3 if x["impact"] == "Negative" else 2)
            )
        )
        today_brief[sector] = sector_news[:4]  # Store top 4 articles per sector
        log.info(
            f"Aggregated {len(today_brief[sector])} feed items for sector: {sector}"
        )

    return today_brief


def _extract_pli_data_from_html(html, title, published_date=""):
    companies = []
    soup = BeautifulSoup(html, "html.parser")
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

    # 4. Extract companies from lists
    for ul in soup.find_all("ul"):
        for li in ul.find_all("li"):
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


async def scrape_pib_pli_approvals_async(session, watchlist):
    log.info("Scraping PIB for PLI approval announcements (Async)...")
    query = 'site:pib.gov.in "PLI" AND ("provisionally selected" OR "approved" OR "incentive scheme" OR "applications approved")'
    encoded_query = urllib.parse.quote(f"{query} when:30d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    emerging_pli_competitors = []

    from utils import fetch_text_async

    try:
        status, xml_data = await fetch_text_async(session, rss_url, timeout=15)
        if status == 200:
            feed = feedparser.parse(xml_data)

            # We process at most 5 entries to limit network calls
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")

                # Fetch actual article HTML (assuming session handles redirects if possible,
                # or if Google News RSS returns direct HTML fallback)
                try:
                    art_status, art_html = await fetch_text_async(
                        session, link, timeout=15
                    )
                    if art_status == 200:
                        extracted = _extract_pli_data_from_html(
                            art_html, title, published
                        )
                        for comp in extracted:
                            comp["announcement"] = title.split(" - ")[0]
                            comp["link"] = link
                            emerging_pli_competitors.append(comp)
                except Exception as ex:
                    log.error(f"Failed to fetch article for PLI extraction: {ex}")
                    # Fallback to extracting from RSS title/summary
                    extracted = _extract_pli_data_from_html(
                        title + " " + entry.get("summary", ""), title, published
                    )
                    for comp in extracted:
                        comp["announcement"] = title.split(" - ")[0]
                        comp["link"] = link
                        emerging_pli_competitors.append(comp)

    except Exception as e:
        log.error(f"Error scraping PIB PLI approvals: {e}")

    # Deduplicate before returning (can have same company in different RSS entries)
    deduped = []
    seen = set()
    from analysis.parsing import resolve_ticker_from_name_async

    # Existing names in watchlist to ignore
    existing_names = set()
    for sector, stocks in watchlist.items():
        for s in stocks:
            existing_names.add(s["name"].lower())
            if s.get("ticker"):
                existing_names.add(s["ticker"].lower())

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
                    agreements.append(
                        {
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


async def fetch_exchange_filings_async(session, watchlist):
    log.info("Fetching NSE/BSE corporate filings (Async)...")
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
