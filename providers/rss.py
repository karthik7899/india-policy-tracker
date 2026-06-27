from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()
import datetime
from bs4 import BeautifulSoup

import feedparser
import urllib.parse
from logger import log
from utils import fetch_text_async
import re

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


