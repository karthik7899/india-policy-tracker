"""Trim the accumulated corpus down to what the dashboard actually displays.

The browser downloads its data file whole on every page load, and the file had
grown to ~790 KB — mostly running lists that merge across runs without any
cap. The corpus needs that depth (see history/store.py); the page does not. It
was rendering every stored item, so a tab could carry 140 agreements or 219
warnings, which is unreadable as well as heavy.

Nothing here affects computation. The pipeline's consumers read the full
corpus before this runs; the output is a display copy.
"""

from typing import Any, Dict, List

from logger import log

# Rows kept per accumulating feed. Well past what anyone scrolls, far short of
# a quarter's backlog.
FEED_CAPS = {
    "corporate_agreements": 40,
    "product_launches": 40,
    "corporate_filings": 40,
    "sebi_filings": 30,
    "institutional_activity": 40,
    "emerging_competitors": 30,
    "market_events": 40,
    "global_market_news": 20,
}

# Coverage items per holding. Eight was generous for a card.
TOPICS_PER_STOCK = 5

_SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _warning_key(warning: Dict[str, Any]) -> tuple:
    return (warning.get("ticker"), warning.get("category"))


def annotate_warning_status(
    warnings: List[Dict[str, Any]], prior: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Tag each warning ``new`` / ``escalated`` / ``ongoing`` against last run.

    Nothing compared runs before, so every warning re-fired identically each
    day: yesterday's 142 Mediums were today's 142 Mediums, and none of it was
    news. A warning is worth reading when it appears for the first time or
    gets worse; the rest is a standing condition.
    """
    previous = {}
    for w in prior or []:
        if isinstance(w, dict):
            previous[_warning_key(w)] = w.get("severity")

    for w in warnings or []:
        if not isinstance(w, dict):
            continue
        was = previous.get(_warning_key(w))
        if was is None:
            w["status"] = "new"
        elif _SEVERITY_RANK.get(w.get("severity"), 9) < _SEVERITY_RANK.get(was, 9):
            w["status"] = "escalated"
        else:
            w["status"] = "ongoing"
    return warnings


def summarize_ongoing(warnings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse unchanged warnings into one row per category and severity.

    "46 holdings carry valuation flags" is a portfolio characteristic, not 46
    decisions. The tickers are kept so the condition stays inspectable without
    shipping 46 paragraphs of identical prose.
    """
    grouped: Dict[tuple, Dict[str, Any]] = {}
    for w in warnings or []:
        if not isinstance(w, dict) or w.get("status") != "ongoing":
            continue
        key = (w.get("category"), w.get("severity"))
        row = grouped.setdefault(
            key,
            {
                "category": w.get("category"),
                "severity": w.get("severity"),
                "direction": w.get("direction"),
                "count": 0,
                "tickers": [],
            },
        )
        row["count"] += 1
        if w.get("ticker") and w["ticker"] not in row["tickers"]:
            row["tickers"].append(w["ticker"])

    rows = list(grouped.values())
    rows.sort(key=lambda r: (_SEVERITY_RANK.get(r["severity"], 9), -r["count"]))
    return rows


def build_display_payload(brief_data: Dict[str, Any]) -> Dict[str, Any]:
    """A display copy of the briefing: capped feeds, actionable warnings."""
    payload = dict(brief_data or {})
    try:
        for key, cap in FEED_CAPS.items():
            rows = payload.get(key)
            if isinstance(rows, list) and len(rows) > cap:
                payload[key] = rows[:cap]

        topics = payload.get("stock_topics")
        if isinstance(topics, dict):
            payload["stock_topics"] = {
                ticker: items[:TOPICS_PER_STOCK]
                for ticker, items in topics.items()
                if isinstance(items, list)
            }

        # Coverage counts ride in the payload; the per-item audit does not.
        # Normalised when present so a malformed value cannot reach the
        # browser, but never invented: a run that computed no coverage must
        # not ship a key claiming it looked and found none. The badge treats a
        # missing entry as zero, which is the same display and an honest one.
        if "coverage_count" in payload:
            counts = payload["coverage_count"]
            payload["coverage_count"] = counts if isinstance(counts, dict) else {}

        warnings = payload.get("early_warnings")
        if isinstance(warnings, list):
            payload["warning_summary"] = summarize_ongoing(warnings)
            payload["early_warnings"] = [
                w
                for w in warnings
                if isinstance(w, dict) and w.get("status") in ("new", "escalated")
            ]
            log.info(
                f"Dashboard payload: {len(payload['early_warnings'])} actionable "
                f"warning(s) shown, {len(warnings) - len(payload['early_warnings'])} "
                f"ongoing collapsed into {len(payload['warning_summary'])} group(s)."
            )
    except Exception as e:  # noqa: BLE001 - trimming must never break a run
        log.warning(f"Payload trimming failed safely: {e!r}")
        return dict(brief_data or {})
    return payload
