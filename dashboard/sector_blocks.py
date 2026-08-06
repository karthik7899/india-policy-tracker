"""Per-sector blocks: one assembly, rendered by both the email and the page.

The email and the dashboard had been building their sector views separately
from the same corpus, which is how they drift: a cap tightened in one place,
an ordering rule changed in the other, and the two surfaces quietly stop
agreeing about which sectors matter. Assembling once here and shipping the
result in the payload makes that impossible by construction.

Selection is delta-first, matching the email's cap ladder. A sector earns a
block by having something new or escalated in it, or news this cycle. Ranking
is severity-weighted, because four Mediums are not a Critical.

Every list is capped, and the caps are ranked rather than truncated
arbitrarily — an order win that a Critical alert already points at is worth
more than the fifth tie-up of the week.
"""

from typing import Any, Dict, List

from config import SECTOR_METADATA

_SEVERITY_WEIGHT = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

# Per-sector caps. Sector content is the dominant email cost, so these are the
# knobs the size ladder turns before it drops a sector entirely.
MAX_NEWS = 4
MAX_FOCUS = 3
MAX_THREATS = 2

# News ranking. A headline a Critical alert already points at is the one the
# reader most needs; a generic tie-up is the one they least need.
_NEWS_RANK = {
    "linked_to_critical": 0,
    "order_win": 1,
    "policy": 2,
    "tie_up": 3,
    "other": 4,
}


def _sector_names(key: str) -> set:
    """Every form a sector is referred to by.

    Warnings carry the label, the payload keys on the slug, and matching only
    one silently degrades every ranking that depends on it.
    """
    meta = SECTOR_METADATA.get(key) or {}
    names = {
        str(key).lower(),
        str(meta.get("label", "")).lower(),
        str(meta.get("name", "")).lower(),
    }
    names.discard("")
    return names


def _warnings_for(key: str, brief: Dict[str, Any]) -> List[Dict[str, Any]]:
    names = _sector_names(key)
    return [
        w
        for w in brief.get("early_warnings") or []
        if isinstance(w, dict) and str(w.get("sector", "")).lower() in names
    ]


def sector_delta(key: str, brief: Dict[str, Any]) -> int:
    """Severity-weighted count of what changed in this sector this run."""
    return sum(
        _SEVERITY_WEIGHT.get(w.get("severity"), 1)
        for w in _warnings_for(key, brief)
        if (w.get("status") or "ongoing") in ("new", "escalated")
    )


def _news_kind(item: Dict[str, Any], critical_tickers: set) -> str:
    text = f"{item.get('title', '')} {item.get('headline', '')}".lower()
    tags = " ".join(str(t) for t in (item.get("event_tags") or []))
    blob = f"{text} {tags} {item.get('event_type', '')}".lower()
    if any(t.lower() in text for t in critical_tickers):
        return "linked_to_critical"
    if "order" in blob or "contract" in blob:
        return "order_win"
    if any(w in blob for w in ("policy", "pli", "scheme", "cabinet", "government")):
        return "policy"
    if any(w in blob for w in ("tie-up", "tie up", "partnership", "mou", "agreement")):
        return "tie_up"
    return "other"


def _build_news(key: str, brief: Dict[str, Any], critical_tickers: set) -> List[Dict]:
    rows = []
    for item in brief.get(key) or []:
        if not isinstance(item, dict):
            continue
        headline = item.get("title") or item.get("headline") or ""
        if not headline:
            continue
        kind = _news_kind(item, critical_tickers)
        rows.append(
            {
                "date": item.get("date") or "",
                "headline": headline,
                # Kept even when empty so the renderer can say the link is
                # missing rather than silently emitting dead markup.
                "url": item.get("link") or "",
                "source": item.get("source") or "",
                "tags": [kind],
                "confidence": item.get("confidence") or "M",
                "affected_tickers": item.get("actors") or [],
            }
        )
    rows.sort(key=lambda r: (_NEWS_RANK.get(r["tags"][0], 9), r["date"]))
    return rows[:MAX_NEWS]


def _build_focus(
    key: str, watchlist: Dict[str, Any], brief: Dict[str, Any]
) -> List[Dict]:
    counts = brief.get("coverage_count") or {}
    by_ticker: Dict[str, int] = {}
    for w in _warnings_for(key, brief):
        t = str(w.get("ticker", "")).upper()
        by_ticker[t] = max(
            by_ticker.get(t, 0), _SEVERITY_WEIGHT.get(w.get("severity"), 1)
        )

    rows = []
    for stock in watchlist.get(key) or []:
        if not isinstance(stock, dict) or not stock.get("ticker"):
            continue
        ticker = str(stock["ticker"]).upper()
        score = (stock.get("score") or {}).get("overall_score")
        sc = stock.get("screener") or {}
        primary = next(
            (
                w.get("category")
                for w in _warnings_for(key, brief)
                if str(w.get("ticker", "")).upper() == ticker
            ),
            None,
        )
        rows.append(
            {
                "ticker": ticker,
                "score": score,
                "severity_weight": by_ticker.get(ticker, 0),
                "primary_signal": primary or "No signal this cycle",
                "coverage_count": counts.get(ticker, 0),
                "pe_vs_peers": sc.get("pe_vs_peers"),
                "deep_link": f"#stock/{ticker}/snapshot",
            }
        )

    rows.sort(
        key=lambda r: (-r["severity_weight"], -(r["coverage_count"] or 0), r["ticker"])
    )
    return rows[:MAX_FOCUS]


def _build_threats(key: str, brief: Dict[str, Any]) -> List[Dict]:
    threats = []
    for entry in brief.get("new_entrants") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("sector", "")).lower() in _sector_names(key):
            threats.append(
                {"name": entry.get("challenger") or "Unnamed", "detail": "new entrant"}
            )

    for peer in (brief.get("peer_competitors") or {}).get(key) or []:
        if not isinstance(peer, dict):
            continue
        growth = peer.get("sales_var_pct")
        threats.append(
            {
                "name": peer.get("name") or peer.get("ticker") or "Unnamed",
                # An unlisted challenger has no growth figure, and saying so
                # is better than printing a zero it never reported.
                "detail": (
                    f"{growth:+.1f}% revenue growth"
                    if isinstance(growth, (int, float))
                    else "unlisted entrant"
                ),
            }
        )
    return threats[:MAX_THREATS]


def build_sector_blocks(
    brief: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Ordered sector blocks, most-changed first. Never raises."""
    blocks: List[Dict[str, Any]] = []
    try:
        valuation = {
            v.get("sector"): v
            for v in (brief.get("sector_valuation") or [])
            if isinstance(v, dict)
        }
        critical = {
            str(w.get("ticker", "")).upper()
            for w in brief.get("early_warnings") or []
            if isinstance(w, dict) and w.get("severity") == "Critical"
        }

        for key in brief:
            if key not in SECTOR_METADATA or key == "macro_indicators":
                continue
            warnings = _warnings_for(key, brief)
            delta = sector_delta(key, brief)
            news = _build_news(key, brief, critical)
            if not delta and not news:
                continue

            meta = SECTOR_METADATA[key]
            val = valuation.get(key) or {}
            new_n = sum(1 for w in warnings if w.get("status") == "new")
            esc_n = sum(1 for w in warnings if w.get("status") == "escalated")

            blocks.append(
                {
                    "id": key,
                    "name": meta.get("label") or key,
                    "stance_line": (
                        f"{new_n} new, {esc_n} escalated"
                        if (new_n or esc_n)
                        else "No change this cycle; carrying news only"
                    ),
                    "median_pe": val.get("median_pe"),
                    "vs_peers_pct": val.get("vs_peers_pct"),
                    "counts": {"new": new_n, "escalated": esc_n},
                    "delta": delta,
                    "news": news,
                    "focus_stocks": _build_focus(key, watchlist, brief),
                    "threats": _build_threats(key, brief),
                    "suppressed": [
                        str(s.get("ticker", "")).upper()
                        for s in watchlist.get(key) or []
                        if isinstance(s, dict)
                        and s.get("estimate_method") == "No Estimate"
                    ],
                }
            )

        # Deterministic: delta, then news volume, then id. Two sectors tying
        # on both must not swap places between runs — a reordered briefing
        # reads as new information.
        blocks.sort(key=lambda b: (-b["delta"], -len(b["news"]), b["id"]))
    except Exception:  # noqa: BLE001 - a display aid must never break a run
        return []
    return blocks
