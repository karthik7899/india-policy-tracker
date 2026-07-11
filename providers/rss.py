import datetime
import feedparser
import re
import urllib.parse
import html
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from logger import log

analyzer = SentimentIntensityAnalyzer()


def _strip_tags(text):
    if not text:
        return text
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def clean_news_item(entry, query_term):
    """Formats and cleans an RSS entry. Returns None if the article is older than 7 days."""
    title = ""
    if hasattr(entry, "title") and entry.title:
        title = _strip_tags(entry.title)
    elif entry.get("title"):
        title = _strip_tags(entry.get("title"))

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
        summary = _strip_tags(summary)
        # Remove trailing "..." or "Read more" typically found in RSS
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
