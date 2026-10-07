"""One card per holding: what it did lately, and which policies cut its way.

The briefing is organised by where data came from — an agreements feed, a
launches feed, a filings feed, sector blocks, a policy list — so one
company's week is scattered over half a dozen sections, and a policy is
listed by headline, never under the companies it helps. Finding "what has
Suzlon done lately, and is policy behind it?" meant reading all of them.

This regroups what is already computed, by company:

  activity   the holding's own attributed headlines (the coverage audit's
             counted items), routine disclosure dropped, filing envelopes
             tidied, newest first, with what kind of news each is
  policies   policy measures read as touching the holding's sector, with
             the direction for THAT sector, the measure's status and whose
             measure it is (central or a state) — and first, any policy
             headline that names the company itself
  thesis     its thesis-health grade and any thesis-check challenge

Nothing new is fetched or judged here. The digest is written as a sidecar
(dashboard/sidecars.py) and loaded only when the Companies view opens.
"""

import datetime
import re
from typing import Any, Dict, Iterable, List, Tuple

from analysis.event_evidence import article_date

WINDOW_DAYS = 30
MAX_ACTIVITY = 6
MAX_POLICIES = 4
_TEXT_LIMIT = 180

_KIND = {
    "order_win": "order",
    "acquisition": "acquisition",
    "tie_up": "tie-up",
    "capacity_add": "capacity",
    "supply_disruption": "supply disruption",
    "input_cost_shock": "input cost",
}


def _kind(item: Dict[str, Any]) -> str:
    event = item.get("event_type") or ""
    if event in _KIND:
        return _KIND[event]
    source = str(item.get("source_kind") or "").lower()
    if source == "filing":
        return "filing"
    if source == "launch":
        return "launch"
    if source == "state policy":
        return "state policy"
    return "news"


def _activity(items, cutoff: str) -> List[Dict[str, Any]]:
    from analysis.headline_text import classify, tidy

    rows, seen = [], set()
    for item in items or []:
        if not isinstance(item, dict) or item.get("status") != "counted":
            continue
        text = item.get("headline") or ""
        date = article_date(item.get("date")) or ""
        if not text or not date or date < cutoff:
            continue
        kind = classify(text)
        if kind == "routine":
            continue
        shown = tidy(text)
        # Two outlets' copies of one story often differ only in the tail
        # ("... cold chain" / "... cold chain and logistics ecosystem"):
        # one headline that starts with another is the same story.
        key = " ".join(re.findall(r"[a-z0-9]+", shown.lower()))
        if any(key.startswith(k) or k.startswith(key) for k in seen):
            continue
        seen.add(key)
        rows.append(
            {
                "date": date,
                "kind": "adverse" if kind == "adverse" else _kind(item),
                "text": shown[:_TEXT_LIMIT],
                **({"link": item["source_url"]} if item.get("source_url") else {}),
                **(
                    {"source": item["source_label"]} if item.get("source_label") else {}
                ),
            }
        )
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def _policies(
    ticker: str, name: str, sector: str, impacts, cutoff: str
) -> List[Dict[str, Any]]:
    from analysis.parsing import title_matches_company

    rows = []
    for imp in impacts or []:
        if not isinstance(imp, dict) or str(imp.get("date", "")) < cutoff:
            continue
        headline = imp.get("headline") or ""
        names = bool(name) and title_matches_company(headline, ticker, name)
        effect = next(
            (e for e in imp.get("effects") or [] if e.get("sector") == sector), None
        )
        if not names and effect is None:
            continue
        rows.append(
            {
                "date": imp.get("date") or "",
                "headline": headline[:_TEXT_LIMIT],
                "direction": (effect or {}).get("direction"),
                "status": imp.get("status") or "",
                "measure": imp.get("measure") or "",
                "names_company": names,
                **({"state": imp["state"]} if imp.get("state") else {}),
                **({"link": imp["link"]} if imp.get("link") else {}),
                **({"outlets": imp["outlets"]} if imp.get("outlets") else {}),
            }
        )
    # The company named outright first, then newest (two stable sorts).
    rows.sort(key=lambda r: r["date"], reverse=True)
    rows.sort(key=lambda r: not r["names_company"])
    return rows


def build_company_digest(
    watchlist: Dict[str, Any],
    coverage: Dict[str, List[Dict[str, Any]]],
    brief: Dict[str, Any],
    today: str = "",
    prices: Dict[str, List[List[Any]]] = None,
    namesakes: Iterable[Tuple[str, str]] = None,
) -> Dict[str, Any]:
    """``{as_of, window_days, companies: [...]}``, most recently active first.

    ``namesakes`` are (TICKER, headline) pairs read as another company's news
    on any run (thesis_check.namesake_headlines). Without them only today's
    check is used, and a day the check cannot run puts every namesake back:
    on 7 Oct Daryl Dixon's teaser returned to Dixon's news that way.
    """
    today = today or datetime.date.today().isoformat()
    cutoff = (
        datetime.date.fromisoformat(today) - datetime.timedelta(days=WINDOW_DAYS)
    ).isoformat()
    health = brief.get("thesis_health") or {}
    checks = (brief.get("thesis_check") or {}).get("holdings") or {}
    balance = brief.get("policy_balance") or {}
    impacts = brief.get("policy_impacts") or []
    read_elsewhere: Dict[str, set] = {}
    for t, h in namesakes or ():
        read_elsewhere.setdefault(str(t).upper(), set()).add(h)

    companies = []
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for stock in stocks:
            if not isinstance(stock, dict) or not stock.get("ticker"):
                continue
            ticker = str(stock["ticker"]).upper()
            name = stock.get("name") or ticker
            activity = _activity((coverage or {}).get(ticker), cutoff)
            # Headlines the thesis check read as being about a namesake —
            # a foreign parent, a person — are kept but set apart, never
            # shown as the company's own news.
            elsewhere = {
                h.strip().lower()
                for h in (checks.get(ticker) or {}).get("not_about") or []
            } | read_elsewhere.get(ticker, set())
            namesakes = [
                a
                for a in activity
                if any(
                    a["text"].lower() in h or h in a["text"].lower() for h in elsewhere
                )
            ]
            activity = [a for a in activity if a not in namesakes]
            policies = _policies(ticker, name, sector, impacts, cutoff)
            thesis = health.get(ticker) or health.get(stock["ticker"]) or {}
            check = checks.get(ticker) or {}
            sector_balance = balance.get(sector) or {}
            companies.append(
                {
                    "ticker": ticker,
                    "name": name,
                    "sector": sector,
                    "thesis": stock.get("catalyst") or "",
                    "thesis_status": thesis.get("status"),
                    "challenges": [
                        {"headline": c["headline"][:_TEXT_LIMIT], "claim": c["claim"]}
                        for c in (check.get("challenged") or [])[:2]
                    ],
                    "activity_count": len(activity),
                    "last_activity": activity[0]["date"] if activity else None,
                    "activity": activity[:MAX_ACTIVITY],
                    **({"namesakes": namesakes[:4]} if namesakes else {}),
                    # Weekly closes for the card's price line, so a reader can
                    # see whether the news and the policies moved the stock.
                    **(
                        {"prices": (prices or {})[ticker]}
                        if (prices or {}).get(ticker)
                        else {}
                    ),
                    "policy_count": len(policies),
                    "policies": policies[:MAX_POLICIES],
                    **(
                        {"policy_net": sector_balance["net"]}
                        if "net" in sector_balance
                        else {}
                    ),
                }
            )
    companies.sort(
        key=lambda c: (c["last_activity"] or "", c["activity_count"]), reverse=True
    )
    return {"as_of": today, "window_days": WINDOW_DAYS, "companies": companies}
