"""Per-holding coverage: what has actually been written about this company.

Every headline the pipeline collects is filed by *sector* — the sector feeds,
the agreements list, product launches, filings, market events, the global feed.
Picking a company therefore told you nothing about that company; you got the
whole sector's news and had to spot the relevant lines yourself.

Attribution reuses ``title_matches_company`` rather than substring search. That
matcher already carries the hard-won rules: whole-token matching, parenthetical
aliases, and the person guard that stopped "CEO Arvind" being filed under
Arvind Ltd. Reimplementing any of that in the browser would mean maintaining
two versions of the same judgement, so the mapping is computed once here and
shipped as data.

Market events are the exception: the event engine has already resolved their
actors to tickers, so those are read straight off rather than re-matched.
"""

from typing import Any, Dict, List

from analysis.parsing import title_matches_company
from logger import log

# Headline lists that are not sector-scoped, as (kind, data key, text field).
# The text field differs per source because each was built by a different
# scraper — launches carry `product`, filings carry `filing`.
_GLOBAL_SOURCES = (
    ("Agreement", "corporate_agreements", "title"),
    ("Launch", "product_launches", "product"),
    ("Filing", "corporate_filings", "filing"),
    ("Global", "global_market_news", "title"),
)

# Enough to show the current picture without turning the card into a feed.
MAX_TOPICS_PER_STOCK = 8


def _entry(kind: str, text: str, item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "kind": kind,
        "title": text,
        "link": item.get("link") or "",
        "date": item.get("date") or "",
        "source": item.get("source") or "",
        "impact": item.get("impact") or "",
    }


def build_stock_topics(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """{ticker: [topic, ...]} — the coverage that actually names each holding.

    Never raises: coverage is an enrichment, and a briefing without it is far
    better than no briefing.
    """
    topics: Dict[str, List[Dict[str, Any]]] = {}
    try:
        holdings = [
            (str(s.get("ticker", "")).upper(), s.get("name") or "", sector)
            for sector, stocks in (watchlist or {}).items()
            if sector != "macro_indicators"
            for s in stocks or []
            if isinstance(s, dict) and s.get("ticker")
        ]
        seen: Dict[str, set] = {t: set() for t, _, _ in holdings}

        def add(ticker: str, entry: Dict[str, Any]) -> None:
            key = entry["title"].strip().lower()
            if not key or key in seen[ticker]:
                return
            seen[ticker].add(key)
            topics.setdefault(ticker, []).append(entry)

        # Sector feeds match only against that sector's holdings: the query
        # that produced them was sector-scoped, so a match elsewhere is far
        # more likely to be a coincidence than a mention.
        for ticker, name, sector in holdings:
            for item in data.get(sector) or []:
                if not isinstance(item, dict):
                    continue
                text = item.get("title") or ""
                if text and title_matches_company(text, ticker, name):
                    add(ticker, _entry("Sector news", text, item))

        for kind, key, field in _GLOBAL_SOURCES:
            for item in data.get(key) or []:
                if not isinstance(item, dict):
                    continue
                text = item.get(field) or item.get("title") or ""
                if not text:
                    continue
                for ticker, name, _ in holdings:
                    if title_matches_company(text, ticker, name):
                        add(ticker, _entry(kind, text, item))

        # The event engine already resolved these to tickers.
        known = {t for t, _, _ in holdings}
        for item in data.get("market_events") or []:
            if not isinstance(item, dict):
                continue
            text = item.get("headline") or ""
            for actor in item.get("actors") or []:
                actor = str(actor).upper()
                if actor in known and text:
                    entry = _entry("Event", text, item)
                    entry["kind"] = (
                        (item.get("event_type") or "event").replace("_", " ").title()
                    )
                    add(actor, entry)

        for ticker in list(topics):
            topics[ticker] = topics[ticker][:MAX_TOPICS_PER_STOCK]

        if topics:
            covered = len(topics)
            total = sum(len(v) for v in topics.values())
            log.info(
                f"Stock coverage: {total} item(s) attributed to "
                f"{covered}/{len(holdings)} holdings."
            )
    except Exception as e:  # noqa: BLE001 - enrichment must never break a run
        log.warning(f"Stock topic attribution failed safely: {e!r}")
    return topics
