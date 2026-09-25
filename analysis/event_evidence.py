"""How well-evidenced is each market event?

Three things a classified event did not carry, each found by measuring the
live corpus:

  WHEN it happened. Every event was stamped with the day it was classified,
  and every run re-reads the whole accumulated news history, so every event
  was re-stamped "today" on every run. On 2026-09-25 all 120 stored events
  read 2026-09-25 while their articles' median age was 56 days: 96 were
  older than the read-through's 10-day window and 62 older than the 45-day
  retention that was supposed to have removed them. article_date() reads the
  date the feed published.

  HOW MANY outlets reported it. One story reaches the corpus as several
  headlines ("Syrma SGS Forms PCB Joint Venture With Kaga Electronics",
  "Syrma SGS, Kaga Electronics Form ₹250 Million EMS Joint Venture", ...),
  and each was a separate event. cluster_stories() groups them, so a story
  carries its number of independent reports instead of being repeated.

  WHETHER THE COMPANY SAID SO. A listed company must disclose material
  orders, acquisitions and joint ventures to the exchange, and the pipeline
  already reads NSE's disclosure feed. confirm_with_filings() looks for the
  holding's own filing of the same kind within days of the story: the
  strongest evidence available short of reading the filing itself.

evidence_level() summarises the three as confirmed / multi-source / single
report. Nothing here removes an event; it records how much to believe it.
"""

import datetime
import re
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional

# A filing counts as the same event if it falls in this window around the
# story: companies usually file the same day or just before the press picks
# it up, and occasionally a few days after.
FILING_WINDOW_BEFORE = 7
FILING_WINDOW_AFTER = 3

# Two headlines are one story only within this many days of each other.
STORY_WINDOW_DAYS = 7

# Filing vocabulary per event type. Matched against the filing's own subject
# text — NSE's "Bagging/Receiving of orders/contracts", a company's "Receipt
# of order worth Rs. 263.25 Crore" — so the words are the exchange's.
_FILING_TERMS: Dict[str, tuple] = {
    "order_win": (
        "bagging",
        "receiving of order",
        "receipt of order",
        "order",
        "contract",
        "letter of award",
        "letter of intent",
        "loa",
        "purchase order",
        "work order",
    ),
    "acquisition": (
        "acquisition",
        "acquire",
        "amalgamation",
        "merger",
        "scheme of arrangement",
        "divest",
        "disinvest",
        "sale of",
        "stake",
        "takeover",
        "open offer",
    ),
    "tie_up": (
        "joint venture",
        "jv",
        "memorandum of understanding",
        "mou",
        "agreement",
        "partnership",
        "collaboration",
        "alliance",
        "tie-up",
        "tie up",
    ),
    "capacity_add": (
        "commercial operation",
        "commercial production",
        "commissioning",
        "commissioned",
        "commencement of operation",
        "capacity",
        "plant",
        "facility",
        "inauguration",
        "capex",
    ),
    "supply_disruption": (
        "disruption",
        "shutdown",
        "force majeure",
        "fire",
        "strike",
        "suspension of operation",
        "lockout",
    ),
}

_STOPWORDS = {
    "with",
    "from",
    "into",
    "that",
    "this",
    "after",
    "over",
    "shares",
    "share",
    "stock",
    "stocks",
    "india",
    "indian",
    "limited",
    "ltd",
    "company",
    "announces",
    "signs",
    "forms",
    "wins",
    "bags",
    "secures",
    "crore",
    "worth",
    "order",
    "orders",
    "deal",
    "news",
}


def article_date(raw: Any) -> Optional[str]:
    """The ISO date a feed item was published, or None if unreadable.

    Feeds use three shapes in the live corpus: RFC 822 ("Thu, 24 Sep 2026
    01:09:49 GMT"), day-month-year ("24 Sep 2026") and ISO.
    """
    text = str(raw or "").strip()
    if not text:
        return None
    for parse in (
        lambda s: datetime.date.fromisoformat(s[:10]),
        lambda s: parsedate_to_datetime(s).date(),
        lambda s: datetime.datetime.strptime(s[:11].strip(), "%d %b %Y").date(),
        lambda s: datetime.datetime.strptime(s[:12].strip(), "%d %B %Y").date(),
    ):
        try:
            return parse(text).isoformat()
        except Exception:
            continue
    return None


def _days_between(a: str, b: str) -> Optional[int]:
    try:
        return abs(
            (datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days
        )
    except (TypeError, ValueError):
        return None


def _words(text: str) -> set:
    return {
        w
        for w in re.findall(r"[a-z][a-z0-9]{3,}", (text or "").lower())
        if w not in _STOPWORDS
    }


def _same_story(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Two headlines about one event?

    Same event type, a holding in common, within a week, and something
    specific in common: a named counterparty, the same amount, or most of
    their distinctive words. The last is a Jaccard overlap because headline
    wording varies more than the facts do.
    """
    if a.get("event_type") != b.get("event_type"):
        return False
    if not set(a.get("actors") or []) & set(b.get("actors") or []):
        return False
    gap = _days_between(str(a.get("date", "")), str(b.get("date", "")))
    if gap is None or gap > STORY_WINDOW_DAYS:
        return False
    parties_a = {p.lower() for p in a.get("counterparties") or []}
    parties_b = {p.lower() for p in b.get("counterparties") or []}
    if parties_a & parties_b:
        return True
    if a.get("amount_cr") is not None and a.get("amount_cr") == b.get("amount_cr"):
        return True
    wa, wb = _words(a.get("headline", "")), _words(b.get("headline", ""))
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= 0.35


def cluster_stories(events: List[Dict[str, Any]]) -> int:
    """Give every event a ``story`` id and its story's ``reports`` count.

    ``reports`` counts distinct outlets, not headlines: one site publishing
    two versions of its own story is one report. Events naming no holding
    are left alone — a story is only worth counting for something we hold.
    Returns the number of stories found.
    """
    items = [e for e in events if isinstance(e, dict) and e.get("actors")]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _same_story(items[i], items[j]):
                parent[find(j)] = find(i)

    groups: Dict[int, List[Dict[str, Any]]] = {}
    for i, event in enumerate(items):
        groups.setdefault(find(i), []).append(event)

    for members in groups.values():
        lead = min(
            members, key=lambda e: (str(e.get("date", "")), e.get("headline", ""))
        )
        outlets = {
            str(e.get("source") or e.get("headline", "")).strip().lower()
            for e in members
        }
        for e in members:
            e["story"] = lead.get("headline", "")[:120]
            e["reports"] = len(outlets)
    return len(groups)


def _filing_kind_matches(event_type: str, text: str) -> bool:
    lower = (text or "").lower()
    return any(
        re.search(rf"\b{re.escape(term)}\b", lower)
        for term in _FILING_TERMS.get(event_type, ())
    )


def confirm_with_filings(
    events: List[Dict[str, Any]], filings: List[Dict[str, Any]]
) -> int:
    """Attach ``confirmation`` to events the holding itself disclosed.

    A filing confirms an event when it is the same holding's, of a matching
    kind, and dated from FILING_WINDOW_BEFORE days before the story to
    FILING_WINDOW_AFTER days after. Only exchange filings are used — the
    news-derived "filings" are somebody's account of a filing, which is the
    thing being checked, not evidence for it.

    Events are never marked unconfirmed by absence alone in the data: a
    missing ``confirmation`` means "no matching filing was found", which is
    what evidence_level() reports. Returns the number confirmed.
    """
    by_ticker: Dict[str, List[Dict[str, Any]]] = {}
    for f in filings or []:
        if (
            isinstance(f, dict)
            and f.get("ticker")
            and f.get("source") in ("NSE", "BSE")
        ):
            by_ticker.setdefault(str(f["ticker"]).upper(), []).append(f)

    confirmed = 0
    for event in events or []:
        if not isinstance(event, dict):
            continue
        event.pop("confirmation", None)
        event_date = str(event.get("date") or "")
        best = None
        for ticker in event.get("actors") or []:
            for f in by_ticker.get(str(ticker).upper(), []):
                if not _filing_kind_matches(
                    event.get("event_type", ""), f.get("text", "")
                ):
                    continue
                try:
                    delta = (
                        datetime.date.fromisoformat(str(f.get("date")))
                        - datetime.date.fromisoformat(event_date)
                    ).days
                except ValueError:
                    continue
                if -FILING_WINDOW_BEFORE <= delta <= FILING_WINDOW_AFTER:
                    if best is None or abs(delta) < abs(best[0]):
                        best = (delta, ticker, f)
        if best:
            _, ticker, f = best
            event["confirmation"] = {
                "ticker": ticker,
                "source": f.get("source"),
                "filing": str(f.get("text") or "")[:160],
                "date": f.get("date"),
                **({"link": f["link"]} if f.get("link") else {}),
            }
            confirmed += 1
    return confirmed


def evidence_level(event: Dict[str, Any]) -> str:
    """``confirmed``, ``multi-source`` or ``single report``."""
    if event.get("confirmation"):
        return "confirmed"
    if (event.get("reports") or 1) >= 2:
        return "multi-source"
    return "single report"


# Holding filings kept for confirmation. Longer than FILING_WINDOW_BEFORE so a
# story reported a week late still finds its filing, and short enough that
# history.json does not accumulate every disclosure the book has ever made.
FILING_RETENTION_DAYS = 21


def prune_filings(
    filings: List[Dict[str, Any]], today: str = ""
) -> List[Dict[str, Any]]:
    """Exchange filings within the retention window, undated ones dropped."""
    today = today or datetime.date.today().isoformat()
    cutoff = (
        datetime.date.fromisoformat(today)
        - datetime.timedelta(days=FILING_RETENTION_DAYS)
    ).isoformat()
    return [
        f
        for f in filings or []
        if isinstance(f, dict) and f.get("date") and str(f["date"]) >= cutoff
    ]
