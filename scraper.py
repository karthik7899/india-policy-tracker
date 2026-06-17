import asyncio
import aiohttp
import feedparser
import datetime
from bs4 import BeautifulSoup
import urllib.parse
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from logger import log
from config import SECTOR_QUERIES

analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(title, summary):
    """Uses VADER sentiment analysis to determine positive/negative impact."""
    text = f"{title}. {summary}"
    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.2:
        return "Positive"
    elif compound <= -0.2:
        return "Negative"
    else:
        # Fallback to simple keyword checking if VADER is neutral but contains strong keywords
        text_lower = text.lower()
        if any(
            w in text_lower
            for w in [
                "hike",
                "scheme approved",
                "approved",
                "subsidy",
                "record profit",
                "expansion",
                "secures order",
                "order of",
                "invests",
                "joint venture",
                "launch",
                "semiconductor fab",
                "pli benefit",
            ]
        ):
            return "Positive"
        elif any(
            w in text_lower
            for w in [
                "delay",
                "investigation",
                "fine",
                "loss",
                "tariff hike negative",
                "penalty",
                "tax increase",
                "curb",
            ]
        ):
            return "Negative"
        return "Neutral"


def clean_news_item(entry, query_term):
    """Formats and cleans an RSS entry. Returns None if the article is older than 7 days."""
    # Use BeautifulSoup and attribute access based on instructions
    title = ""
    if hasattr(entry, "title") and entry.title:
        title = BeautifulSoup(entry.title, "html.parser").get_text(strip=True)
    elif entry.get("title"):
        title = BeautifulSoup(entry.get("title"), "html.parser").get_text(strip=True)

    title = title.split(" - ")[0]

    source = entry.get("source", {}).get("title", "Finance Media")
    if " - " in entry.get("title", ""):
        parts = entry.get("title", "").split(" - ")
        if len(parts) > 1:
            source = parts[-1]

    link = entry.get("link", "")

    pub_date_raw = entry.get("published", "")

    # Fallback to current date if published missing, as specified in the prompt
    published_dt = datetime.datetime.now()
    pub_date = published_dt.strftime("%d %b %Y")

    if pub_date_raw:
        try:
            parsed_t = entry.get("published_parsed")
            if parsed_t:
                article_date = datetime.date(*parsed_t[:3])
                age_days = (datetime.date.today() - article_date).days
                if age_days > 7:
                    return None
                pub_date = article_date.strftime("%d %b %Y")
        except Exception:
            pass

    summary = entry.get("summary", "")
    if summary:
        summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)
        # Remove trailing "..." or "Read more" typically found in RSS
        import re

        summary = re.sub(
            r"(\.\.\.|Read more.*)", "", summary, flags=re.IGNORECASE
        ).strip()

    impact = analyze_sentiment(title, summary)

    return {
        "title": title,
        "source": source,
        "link": link,
        "date": pub_date,
        "impact": impact,
        "relevance": query_term,
    }


async def fetch_query_feed_async(session, sector, query):
    """Asynchronously fetches news for a single query."""
    query_with_time = f"{query} when:7d"
    encoded_query = urllib.parse.quote(query_with_time)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    sector_news = []
    try:
        async with session.get(rss_url, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:3]:
                    cleaned = clean_news_item(entry, query)
                    if cleaned is not None:
                        sector_news.append(cleaned)
    except Exception as e:
        log.error(f"Error parsing feed for query '{query}': {e}")
    return sector, sector_news


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


async def scrape_pib_pli_approvals_async(session, watchlist):
    log.info("Scraping PIB for PLI approval announcements (Async)...")
    query = 'site:pib.gov.in "PLI" AND ("provisionally selected" OR "approved" OR "incentive scheme" OR "applications approved")'
    encoded_query = urllib.parse.quote(f"{query} when:30d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    emerging_pli_competitors = []
    seen = set()

    try:
        async with session.get(rss_url, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                corp_pattern = re.compile(
                    r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+(?:Ltd|Limited|Corp|Corporation|Enterprises|Solutions|Electronics|Industries|Apparels|Defence|Semiconductors)\b"
                )

                # General watchlist IDs to filter out
                existing_names = set()
                for sector, stocks in watchlist.items():
                    for s in stocks:
                        existing_names.add(s["name"].lower())
                        existing_names.add(s["ticker"].lower())

                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    for m in corp_pattern.finditer(title):
                        company_name = m.group(0)
                        name_key = company_name.lower()
                        if name_key not in existing_names and name_key not in seen:
                            seen.add(name_key)
                            from metrics import resolve_ticker_from_name

                            ticker, _ = resolve_ticker_from_name(company_name)
                            status = "Unlisted" if not ticker else "Listed Peer"
                            emerging_pli_competitors.append(
                                {
                                    "name": company_name,
                                    "ticker": ticker,
                                    "status": status,
                                    "announcement": title.split(" - ")[0],
                                    "link": entry.get("link", "https://pib.gov.in"),
                                }
                            )
                            log.info(
                                f"PIB PLI approval competitor detected: {company_name} ({status})"
                            )
    except Exception as e:
        log.error(f"Error scraping PIB PLI approvals: {e}")

    return emerging_pli_competitors


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

    async def process_chunk(chunk):
        ticker_query = " OR ".join([f'"{t}"' for t in chunk])

        # Agreements
        agree_q = f'({ticker_query}) AND ("joint venture" OR "strategic partnership" OR "market share" OR "agreement" OR "MoU")'
        encoded_agree = urllib.parse.quote(f"{agree_q} when:7d")
        rss_agree_url = f"https://news.google.com/rss/search?q={encoded_agree}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with session.get(rss_agree_url, timeout=15) as resp:
                if resp.status == 200:
                    xml_data = await resp.text()
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
        launch_q = f'({ticker_query}) AND ("product launch" OR "unveils" OR "commercial production" OR "new factory")'
        encoded_launch = urllib.parse.quote(f"{launch_q} when:7d")
        rss_launch_url = f"https://news.google.com/rss/search?q={encoded_launch}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with session.get(rss_launch_url, timeout=15) as resp:
                if resp.status == 200:
                    xml_data = await resp.text()
                    feed = feedparser.parse(xml_data)
                    for entry in feed.entries[:3]:
                        title = entry.get("title", "")
                        launches.append(
                            {
                                "title": title.split(" - ")[0],
                                "link": entry.get("link", ""),
                                "date": entry.get("published", ""),
                                "source": entry.get("source", {}).get("title", "News"),
                            }
                        )
        except Exception as e:
            log.error(f"Error fetching launches chunk: {e}")

    await asyncio.gather(*[process_chunk(chunk) for chunk in ticker_chunks])

    unique_agreements = {a["title"]: a for a in agreements}.values()
    unique_launches = {launch["title"]: launch for launch in launches}.values()

    return list(unique_agreements)[:10], list(unique_launches)[:10]


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


async def fetch_institutional_activity_async(session, watchlist):
    log.info(
        "Fetching institutional activity block deals and mutual fund buying trends (Async)..."
    )
    query = '"block deal" OR "bulk deal" OR "mutual fund buys" OR "FII buying" India'
    encoded_query = urllib.parse.quote(f"{query} when:7d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    activity = []
    try:
        async with session.get(rss_url, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:8]:  # Get top 8 entries
                    headline = entry.get("title", "").split(" - ")[0].strip()

                    # Parse block deal headline
                    buyer = "Institutional Investor"
                    action = "Buy"
                    company = "Listed Company"
                    details = "Block Deal"

                    if any(
                        w in headline.lower()
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
                        w in headline.lower()
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

                    # Match against watchlist stocks
                    matched_company = None
                    matched_ticker = None
                    for sector, stocks in watchlist.items():
                        for s in stocks:
                            if (
                                s["ticker"].lower() in headline.lower()
                                or s["name"].lower() in headline.lower()
                            ):
                                matched_company = s["name"]
                                matched_ticker = s["ticker"]
                                break
                        if matched_company:
                            break

                    if matched_company:
                        company = f"{matched_company} ({matched_ticker})"

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
