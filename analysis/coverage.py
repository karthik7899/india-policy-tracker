"""Per-holding news coverage, including what was *not* counted.

``analysis/stock_topics.py`` already attributes headlines to holdings, but it
keeps only survivors: a duplicate phrasing returns early and an out-of-window
item is never distinguished from one that simply did not match. So the card
shows five items with no way to ask why a sixth is missing, or why a headline
you remember reading is absent.

That gap is not cosmetic. The scoring engine drops events for four distinct
reasons — age, deduplication, entity-boundary rejection, negation — and every
one of them has produced a silent bug in this repository. An audit trail is
the difference between "no news" and "news the matcher rejected".

This module therefore records the whole decision, not the outcome:

    counted   contributed to the momentum score
    merged    a duplicate phrasing of something already counted
    excluded  rejected, with the reason attached

The counted set is what ``coverage_count`` reports and what the badge shows.
The rest ships in per-ticker sidecars so the browser only pays for it when a
reader actually opens the drawer.
"""

import datetime
import re
from typing import Any, Dict, List, Optional

from analysis.parsing import title_matches_company
from logger import log

# The momentum window. Matches analysis/scoring.POLICY_MAX_AGE_DAYS: an item
# outside it scores nothing, so counting it here would make the badge disagree
# with the score it is meant to explain.
WINDOW_DAYS = 120

# Same source list stock_topics walks, kept in that order so the two views
# attribute identically.
_GLOBAL_SOURCES = (
    ("Agreement", "corporate_agreements", "title"),
    ("Launch", "product_launches", "product"),
    ("Filing", "corporate_filings", "filing"),
    ("Global", "global_market_news", "title"),
)

_CONFIDENCE_BY_KIND = {
    # Event-engine items carry resolved actors, so attribution is not a guess.
    "Event": "H",
    "Filing": "M",
    "Agreement": "M",
    "Launch": "M",
    "Sector news": "M",
    "Global": "L",
}


def _normalise(text: str) -> str:
    """Comparison key for deduplication: case and punctuation collapsed."""
    return re.sub(r"[^a-z0-9 ]+", "", (text or "").lower()).strip()


def _parse_date(raw: Any) -> Optional[datetime.date]:
    for parse in (
        lambda s: datetime.date.fromisoformat(str(s)[:10]),
        lambda s: datetime.datetime.strptime(str(s)[:16], "%a, %d %b %Y").date(),
    ):
        try:
            return parse(raw)
        except Exception:
            continue
    return None


def _age_days(raw: Any, today: datetime.date) -> Optional[int]:
    parsed = _parse_date(raw)
    return None if parsed is None else (today - parsed).days


def _item(kind: str, text: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "date": raw.get("date") or "",
        "headline": text,
        "source_url": raw.get("link") or "",
        "source_label": raw.get("source") or "",
        "event_tags": [t for t in [raw.get("event_type"), kind] if t],
        "confidence": _CONFIDENCE_BY_KIND.get(kind, "M"),
        "status": "counted",
    }


def build_coverage(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """``{ticker: [item, ...]}`` — every attributed item, counted or not.

    Never raises: coverage is an enrichment, and a briefing without it beats
    no briefing.
    """
    coverage: Dict[str, List[Dict[str, Any]]] = {}
    try:
        today = datetime.date.today()
        holdings = [
            (str(s.get("ticker", "")).upper(), s.get("name") or "")
            for sector, stocks in (watchlist or {}).items()
            if sector != "macro_indicators"
            for s in stocks or []
            if isinstance(s, dict) and s.get("ticker")
        ]
        seen: Dict[str, Dict[str, str]] = {t: {} for t, _ in holdings}

        def add(ticker: str, item: Dict[str, Any]) -> None:
            key = _normalise(item["headline"])
            if not key:
                return
            bucket = coverage.setdefault(ticker, [])

            # Duplicate phrasing: recorded rather than dropped, because "the
            # same launch counted twice" was a real scoring defect and the
            # audit is how it stays visible.
            if key in seen[ticker]:
                item["status"] = "merged"
                item["exclusion_reason"] = (
                    f"merged: duplicate phrasing of “{seen[ticker][key][:60]}”"
                )
                bucket.append(item)
                return

            age = _age_days(item["date"], today)
            if age is not None and age > WINDOW_DAYS:
                item["status"] = "excluded"
                item["exclusion_reason"] = f"aged >{WINDOW_DAYS}d ({age} days old)"
                bucket.append(item)
                return

            seen[ticker][key] = item["headline"]
            bucket.append(item)

        # Sector feeds match only within their own sector, as stock_topics
        # does: the query behind them was sector-scoped, so a match elsewhere
        # is more likely coincidence than mention.
        for sector, stocks in (watchlist or {}).items():
            if sector == "macro_indicators":
                continue
            for stock in stocks or []:
                if not isinstance(stock, dict) or not stock.get("ticker"):
                    continue
                ticker = str(stock["ticker"]).upper()
                name = stock.get("name") or ""
                for raw in data.get(sector) or []:
                    if not isinstance(raw, dict):
                        continue
                    text = raw.get("title") or ""
                    if text and title_matches_company(text, ticker, name):
                        add(ticker, _item("Sector news", text, raw))

        for kind, key, field in _GLOBAL_SOURCES:
            for raw in data.get(key) or []:
                if not isinstance(raw, dict):
                    continue
                text = raw.get(field) or raw.get("title") or ""
                if not text:
                    continue
                for ticker, name in holdings:
                    if title_matches_company(text, ticker, name):
                        add(ticker, _item(kind, text, raw))

        known = {t for t, _ in holdings}
        for raw in data.get("market_events") or []:
            if not isinstance(raw, dict):
                continue
            text = raw.get("headline") or ""
            if not text:
                continue
            for actor in raw.get("actors") or []:
                actor = str(actor).upper()
                if actor in known:
                    add(actor, _item("Event", text, raw))

        counted = sum(counts_for(items) for items in coverage.values())
        excluded = sum(
            1 for items in coverage.values() for i in items if i["status"] != "counted"
        )
        log.info(
            f"Coverage audit: {counted} item(s) counted across "
            f"{len(coverage)} holding(s); {excluded} merged or excluded."
        )
    except Exception as e:  # noqa: BLE001 - enrichment must never break a run
        log.warning(f"Coverage audit failed safely: {e!r}")
    return coverage


def counts_for(items: List[Dict[str, Any]]) -> int:
    """How many of a holding's items actually count toward its score."""
    return sum(1 for i in items or [] if i.get("status") == "counted")


def coverage_counts(coverage: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
    """``{ticker: counted}`` — the number the badge shows.

    Only counted items, so the badge and the momentum score never disagree
    about how much news a holding has.
    """
    return {ticker: counts_for(items) for ticker, items in (coverage or {}).items()}
