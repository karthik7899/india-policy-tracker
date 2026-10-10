"""What changed since the last run.

Most of the briefing is standing state: 357 ongoing warnings collapse into
20 groups, the thesis grades read the same most mornings, and a policy
first seen a week ago sits beside one from this morning. "What do I need
to look at today?" meant comparing against yesterday from memory.

This compares the run with the previous one (history.json's briefing,
loaded before it is overwritten) and lists only what is new:

  watchlist   holdings added or dropped
  thesis      grade changes, and thesis-check challenges not seen before
  events      market events about holdings not seen before
  policy      policy measures read for the first time
  warnings    alerts that are new or escalated
  portfolio   portfolio limits newly breached, or back within
  results     holdings that reported, and results dates newly announced

Nothing is re-judged; every item is something another step already
produced, and each says which step.
"""

from typing import Any, Dict, Iterable, List, Optional

MAX_PER_KIND = 8
_ORDER = {"Broken": 0, "Weakening": 1, "Intact": 2}


def _headlines(rows: Optional[Iterable[Any]], field: str = "headline") -> set:
    return {
        str(r.get(field) or "").strip().lower()
        for r in rows or []
        if isinstance(r, dict) and r.get(field)
    }


def build_changes(
    data: Dict[str, Any],
    prior: Dict[str, Any],
    held_before: Iterable[str] = (),
    held_now: Iterable[str] = (),
) -> Dict[str, Any]:
    """``{first_run, counts: {kind: n}, items: {kind: [...]}}``."""
    prior = prior or {}
    first_run = not prior
    items: Dict[str, List[Dict[str, Any]]] = {
        "watchlist": [],
        "thesis": [],
        "events": [],
        "policy": [],
        "warnings": [],
        "portfolio": [],
        "results": [],
    }

    before, now = set(held_before or ()), set(held_now or ())
    if before:
        for t in sorted(now - before):
            items["watchlist"].append({"ticker": t, "text": "added to the watchlist"})
        for t in sorted(before - now):
            items["watchlist"].append(
                {"ticker": t, "text": "dropped from the watchlist"}
            )

    old_health = prior.get("thesis_health") or {}
    for ticker, row in sorted((data.get("thesis_health") or {}).items()):
        was = (old_health.get(ticker) or {}).get("status")
        status = (row or {}).get("status")
        if was and status and was != status:
            worse = _ORDER.get(status, 9) < _ORDER.get(was, 9)
            items["thesis"].append(
                {
                    "ticker": ticker,
                    "text": f"thesis {was} → {status}",
                    "direction": "worse" if worse else "better",
                    **(
                        {"detail": (row.get("reasons") or [""])[0]}
                        if row.get("reasons")
                        else {}
                    ),
                }
            )
    old_challenges = {
        (t, c.get("headline"))
        for t, r in ((prior.get("thesis_check") or {}).get("holdings") or {}).items()
        for c in (r or {}).get("challenged") or []
    }
    for t, r in sorted(
        ((data.get("thesis_check") or {}).get("holdings") or {}).items()
    ):
        for c in (r or {}).get("challenged") or []:
            if (t, c.get("headline")) not in old_challenges:
                items["thesis"].append(
                    {
                        "ticker": t,
                        "text": f"thesis challenged: {c.get('headline')}",
                        "direction": "worse",
                        "detail": f"against “{c.get('claim')}” (LLM reading)",
                        **({"link": c["link"]} if c.get("link") else {}),
                    }
                )

    seen_events = _headlines(prior.get("market_events"))
    for e in data.get("market_events") or []:
        if not isinstance(e, dict) or not e.get("actors"):
            continue
        if str(e.get("headline") or "").strip().lower() in seen_events:
            continue
        items["events"].append(
            {
                "ticker": e["actors"][0],
                "text": e.get("headline") or "",
                "detail": str(e.get("event_type") or "").replace("_", " ")
                + (" · LLM only, unverified" if e.get("reader") == "llm" else ""),
                **({"link": e["link"]} if e.get("link") else {}),
            }
        )

    seen_policy = _headlines(prior.get("policy_impacts"))
    for p in data.get("policy_impacts") or []:
        if str(p.get("headline") or "").strip().lower() in seen_policy:
            continue
        effects = ", ".join(
            f"{e.get('sector', '').replace('_', ' ')} {e.get('direction')}"
            for e in p.get("effects") or []
        )
        items["policy"].append(
            {
                "text": p.get("headline") or "",
                "detail": " · ".join(
                    x
                    for x in (
                        effects,
                        f"{p['state']} government" if p.get("state") else "central",
                        str(p.get("status") or "").replace("_", " "),
                    )
                    if x
                ),
                **({"link": p["link"]} if p.get("link") else {}),
            }
        )

    for w in data.get("early_warnings") or []:
        if isinstance(w, dict) and w.get("status") in ("new", "escalated"):
            items["warnings"].append(
                {
                    "ticker": w.get("ticker") or "",
                    "text": w.get("signal") or w.get("category") or "",
                    "detail": f"{w.get('severity', '')} {w.get('direction', '')} · {w['status']}".strip(),
                }
            )

    items["portfolio"] = _limit_changes(data.get("portfolio"), prior.get("portfolio"))
    items["results"] = _result_changes(data, prior)

    if first_run:
        # Without a previous run everything is "new", which says nothing.
        items = {k: [] for k in items}
    counts = {k: len(v) for k, v in items.items()}
    return {
        "first_run": first_run,
        "counts": counts,
        "items": {k: v[:MAX_PER_KIND] for k, v in items.items()},
    }


# What each kind of portfolio limit is about, for a breach that has cleared.
_LIMIT_SUBJECT = {
    "stock": "position size",
    "sector": "sector weight",
    "group": "group weight",
    "liquidity": "days to exit",
    "ownership": "share of the company owned",
    "excluded": "excluded name held",
    "beta": "beta",
    "tracking_error": "tracking error",
}


def _limit_changes(now: Any, before: Any) -> List[Dict[str, Any]]:
    """Breaches that appeared since the last run, then ones that cleared.

    A book the last run did not measure is skipped: everything in it would
    read as new.
    """
    out: List[Dict[str, Any]] = []
    old_books = {
        str(b.get("id")): b
        for b in (before or {}).get("books") or []
        if isinstance(b, dict) and "breaches" in b
    }
    for book in (now or {}).get("books") or []:
        if not isinstance(book, dict) or "breaches" not in book:
            continue
        was = old_books.get(str(book.get("id")))
        if was is None:
            continue
        old = {(b.get("kind"), b.get("subject")): b for b in was["breaches"]}
        new = {(b.get("kind"), b.get("subject")): b for b in book["breaches"]}
        name = book.get("name") or book.get("id")
        for key, b in new.items():
            if key not in old:
                out.append(
                    {
                        "text": b.get("message") or "",
                        "direction": "worse",
                        "detail": f"{name} · new limit breach",
                    }
                )
        for (kind, subject), b in old.items():
            if (kind, subject) not in new:
                out.append(
                    {
                        "text": f"{subject}: {_LIMIT_SUBJECT.get(kind, kind)} back "
                        "within the limit",
                        "direction": "better",
                        "detail": f"{name} · was: {b.get('message') or ''}",
                    }
                )
    return out


def _result_changes(
    data: Dict[str, Any], prior: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Holdings that reported since the last run, then results dates that
    were not on the last run's calendar."""
    out: List[Dict[str, Any]] = []
    results = data.get("results") or {}
    today = set(results.get("reported_today") or [])
    for c in results.get("scorecards") or []:
        if isinstance(c, dict) and c.get("ticker") in today:
            out.append(
                {
                    "ticker": c["ticker"],
                    "text": (
                        f"reported the {c['quarter']} quarter"
                        if c.get("quarter")
                        else "reported a quarter"
                    ),
                    "detail": c.get("summary") or "",
                }
            )
    if "event_calendar" not in prior:
        return out
    known = {
        (e.get("ticker"), e.get("date"))
        for e in (prior.get("event_calendar") or {}).get("upcoming") or []
        if isinstance(e, dict) and e.get("kind") == "results"
    }
    for e in (data.get("event_calendar") or {}).get("upcoming") or []:
        if not isinstance(e, dict) or e.get("kind") != "results":
            continue
        if (e.get("ticker"), e.get("date")) in known:
            continue
        out.append(
            {
                "ticker": e.get("ticker") or "",
                "text": f"results due {e.get('date')}",
                "detail": e.get("source") or "",
                **({"link": e["link"]} if e.get("link") else {}),
            }
        )
    return out
