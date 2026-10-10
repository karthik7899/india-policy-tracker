"""What is coming up for each holding, and what its latest results said.

Two things the briefing could not say before:

  * WHEN. Results dates, dividend ex-dates, splits, AGMs. They come from
    NSE's event calendar and corporate actions (providers/nse_calendar.py),
    from the board-meeting intimations already read off NSE's announcements
    feed (a company files one a week or more before the meeting), and from
    the previous run's calendar, so a day NSE refuses us does not empty it.
    Market-wide dates (an RBI policy, the Budget) are read from
    macro_events.json, which a person fills in; none are invented here.

  * WHAT A RESULT SAID. Screener's quarterly table gains a column when a
    company reports. The run keeps the last quarterly sales series it saw for
    each holding (in the briefing, so a day Screener fails does not reset
    it), and when today's series is yesterday's moved along by one, the
    holding has reported. The scorecard compares the new quarter with a year
    earlier first -- several holdings are seasonal (HAL's March quarter is
    two and a half times its others), so a quarter-on-quarter change alone
    misleads -- then with the quarter before and the last eight.

What it does not claim: there is no consensus estimate behind any of this, so
no result is called a beat or a miss. The quarter a result belongs to is
inferred from when it appeared (the last quarter to end before that day),
and the scorecard says so.
"""

import datetime
import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from logger import log
from utils import to_float

MACRO_PATH = "macro_events.json"

AHEAD_DAYS = 45
BACK_DAYS = 14
# How long a scorecard stays on the page after the results appeared.
SCORECARD_DAYS = 45

# Preferred source first when two report the same event.
_SOURCE_RANK = {
    "NSE event calendar": 0,
    "NSE corporate actions": 1,
    "NSE filing": 2,
}

_DATE = (
    r"(\d{1,2}[-/ ][A-Za-z]{3,9}[-/ ,]+\d{4}"
    r"|\d{1,2}[-/]\d{1,2}[-/]\d{4}"
    r"|[A-Za-z]{3,9} \d{1,2},? \d{4})"
)
# "... about Board Meeting to be held on 31-Oct-2026 to consider ..."; also
# "Board Meeting scheduled on", "Outcome of Board Meeting held on".
_MEETING = re.compile(
    r"board\s+meeting\b[^.]{0,80}?\b(?:on|dated)\s+" + _DATE, re.IGNORECASE
)
_DATE_FORMATS = (
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
)


def _parse(text: str) -> Optional[str]:
    text = re.sub(r"\s+", " ", (text or "").strip().rstrip(".,"))
    text = re.sub(r"(\d{4}),", r"\1", text)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def meetings_from_filings(
    filings: Iterable[Dict[str, Any]], held: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Board meetings announced in the exchange filings the run already keeps.

    The intimation is the earliest public notice of a results date, and it is
    already on hand: providers/nse_announcements.py reads it every day.
    """
    from providers.nse_calendar import classify

    out = []
    for f in filings or []:
        if not isinstance(f, dict):
            continue
        ticker = str(f.get("ticker") or "").upper()
        text = str(f.get("text") or "")
        if ticker not in held:
            continue
        m = _MEETING.search(text)
        date = _parse(m.group(1)) if m else None
        if not date:
            continue
        outcome = bool(re.search(r"\boutcome\b", text, re.IGNORECASE))
        out.append(
            {
                "ticker": ticker,
                "date": date,
                "kind": "outcome" if outcome else classify(text),
                "title": "Board meeting held" if outcome else "Board meeting",
                "detail": re.sub(r"\s+", " ", text)[:200],
                "source": "NSE filing",
                **({"link": f["link"]} if f.get("link") else {}),
            }
        )
    return out


def load_macro(path: str = MACRO_PATH) -> List[Dict[str, Any]]:
    """Market-wide dates a person entered; [] without the file."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            body = json.load(fh)
    except (OSError, ValueError) as e:
        log.warning(f"Calendar: {path} could not be read: {e!r}")
        return []
    events = body.get("events") if isinstance(body, dict) else None
    out = []
    for e in events if isinstance(events, list) else []:
        if not isinstance(e, dict) or not e.get("title"):
            continue
        date = _parse(str(e.get("date") or "")) or (
            str(e.get("date"))
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(e.get("date") or ""))
            else None
        )
        if date:
            out.append(
                {
                    "date": date,
                    "kind": "macro",
                    "title": str(e["title"]),
                    "detail": str(e.get("detail") or ""),
                    "sectors": [str(s) for s in e.get("sectors") or []],
                    **({"link": str(e["link"])} if e.get("link") else {}),
                    "source": "macro_events.json",
                }
            )
    return out


def _held(watchlist: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for s in stocks:
            if isinstance(s, dict) and s.get("ticker"):
                t = str(s["ticker"]).upper()
                out[t] = {"name": s.get("name") or t, "sector": sector, "stock": s}
    return out


def build_calendar(
    watchlist: Dict[str, Any],
    fetched: Optional[Dict[str, Any]] = None,
    filings: Optional[Iterable[Dict[str, Any]]] = None,
    prior: Optional[Dict[str, Any]] = None,
    macro: Optional[List[Dict[str, Any]]] = None,
    today: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """Every dated event for a holding, from BACK_DAYS ago to AHEAD_DAYS on."""
    today = today or datetime.date.today()
    held = _held(watchlist)
    first = (today - datetime.timedelta(days=BACK_DAYS)).isoformat()
    last = (today + datetime.timedelta(days=AHEAD_DAYS)).isoformat()
    fetched = fetched or {}
    from_nse = [e for e in fetched.get("events") or [] if isinstance(e, dict)]
    from_filings = meetings_from_filings(filings, held)
    # The last run's events still ahead: an event does not stop being
    # scheduled because today's request was refused.
    carried = [
        {**e, "carried": True}
        for e in ((prior or {}).get("upcoming") or [])
        if isinstance(e, dict) and str(e.get("date") or "") >= today.isoformat()
    ]

    # One board meeting per holding per day, however many sources report it;
    # a corporate action on the same day is a separate event. The best
    # source is kept, but "board" gives way to a purpose another source read.
    chosen: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for e in from_nse + from_filings + carried:
        t = str(e.get("ticker") or "").upper()
        if t not in held or not (first <= str(e.get("date") or "") <= last):
            continue
        kind = e.get("kind") or "board"
        group = (
            f"action:{kind}"
            if e.get("source") == "NSE corporate actions"
            else "meeting"
        )
        key = (t, e["date"], group)
        rank = _SOURCE_RANK.get(e.get("source"), 3) + (10 if e.get("carried") else 0)
        entry = {
            **{k: v for k, v in e.items() if k != "carried"},
            "ticker": t,
            "kind": kind,
            "name": held[t]["name"],
            "sector": held[t]["sector"],
            "_rank": rank,
            "_carried": bool(e.get("carried")),
        }
        old = chosen.get(key)
        if old is None:
            chosen[key] = entry
            continue
        best, other = (entry, old) if rank < old["_rank"] else (old, entry)
        if best["kind"] == "board" and other["kind"] != "board":
            best = {**best, "kind": other["kind"]}
        chosen[key] = best
    events = sorted(
        (
            {k: v for k, v in e.items() if k not in ("_rank", "_carried")}
            | ({"carried": True} if e["_carried"] else {})
            for e in chosen.values()
        ),
        key=lambda e: (e["date"], e["ticker"], e.get("kind") or ""),
    )
    macro = load_macro() if macro is None else macro
    macro = [m for m in macro if first <= m["date"] <= last]
    now = today.isoformat()
    upcoming = [e for e in events if e["date"] >= now]
    next_results = {}
    for e in upcoming:
        if e.get("kind") == "results":
            next_results.setdefault(e["ticker"], e["date"])
    return {
        "as_of": now,
        "ahead_days": AHEAD_DAYS,
        "back_days": BACK_DAYS,
        "upcoming": upcoming,
        "recent": [e for e in events if e["date"] < now][::-1],
        "macro": sorted(macro, key=lambda m: m["date"]),
        "next_results": next_results,
        "sources": {
            "nse": dict(fetched.get("published") or {}),
            "nse_errors": list(fetched.get("errors") or []),
            "filings": len(from_filings),
            "carried": sum(1 for e in events if e.get("carried")),
        },
    }


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------


def _series(value: Any) -> List[float]:
    if not isinstance(value, list):
        return []
    out = []
    for v in value:
        f = to_float(v)
        if f is None:
            return []
        out.append(f)
    return out


def _same(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.5, 0.01 * max(abs(a), abs(b)))


def new_quarter(old: List[float], new: List[float]) -> bool:
    """True when ``new`` is ``old`` moved along by one quarter.

    Screener keeps a fixed window of quarters, so a new result drops the
    oldest and appends the latest: the overlap must line up, allowing one
    restated quarter, and the series must have changed.
    """
    if len(old) < 4 or len(new) < 4:
        return False

    def misses(pairs):
        return sum(1 for a, b in pairs if not _same(a, b))

    # Lined up as they stand, all but the latest quarter agree: the latest
    # was restated, or nothing changed. For a company whose sales barely move
    # the shifted reading can agree too; that is read as no new quarter,
    # since a missed scorecard costs less than an invented one.
    if len(old) == len(new) and misses(zip(old[:-1], new[:-1])) <= 1:
        return False
    k = min(len(old), len(new)) - 1
    return misses(zip(old[-k:], new[-k - 1 : -1])) <= 1


def _quarter_end(day: datetime.date) -> datetime.date:
    """The last quarter to end before ``day``."""
    for month in (12, 9, 6, 3):
        end = datetime.date(day.year, month, 31 if month in (12, 3) else 30)
        if end < day:
            return end
    return datetime.date(day.year - 1, 12, 31)


def _change(now: float, then: Optional[float]) -> Optional[float]:
    if then is None or then <= 0:
        return None
    return round((now / then - 1) * 100, 1)


def scorecard(
    ticker: str, held: Dict[str, Any], detected: datetime.date
) -> Optional[Dict[str, Any]]:
    """The quarter just reported, against a year earlier and the quarter
    before. None without a sales series to read."""
    sc = held["stock"].get("screener") or {}
    sales = _series(sc.get("sales_trend"))
    if len(sales) < 2:
        return None
    eps = _series(sc.get("eps_trend"))
    opm = _series(sc.get("quarterly_ebitda_margin"))
    quarter = _quarter_end(detected)
    card: Dict[str, Any] = {
        "ticker": ticker,
        "name": held["name"],
        "sector": held["sector"],
        "detected": detected.isoformat(),
        "quarter": quarter.strftime("%b %Y"),
        "quarters": len(sales),
        "sales_cr": sales[-1],
        "sales_qoq_pct": _change(sales[-1], sales[-2]),
        "sales_rank": 1 + sum(1 for s in sales[:-1] if s > sales[-1]),
    }
    if len(sales) >= 5:
        card["sales_yoy_pct"] = _change(sales[-1], sales[-5])
    if eps:
        card["eps"] = eps[-1]
        if len(eps) >= 5:
            card["eps_yoy_pct"] = _change(eps[-1], eps[-5])
            if eps[-5] <= 0:
                card["eps_year_ago"] = eps[-5]
    if opm:
        card["opm_pct"] = opm[-1]
        if len(opm) >= 2:
            card["opm_change_pp"] = round(opm[-1] - opm[-2], 1)
    profit = to_float(sc.get("q_net_profit"))
    if profit is not None:
        card["net_profit_cr"] = profit
    card["summary"] = _summary(card)
    return card


def _signed(v: float, unit: str = "%") -> str:
    return f"{'+' if v > 0 else ''}{v:.1f}{unit}"


def _summary(c: Dict[str, Any]) -> str:
    """One sentence, year-on-year first."""
    parts = [f"Sales ₹{c['sales_cr']:,.0f} Cr"]
    if c.get("sales_yoy_pct") is not None:
        parts[-1] += f", {_signed(c['sales_yoy_pct'])} on a year ago"
    if c.get("sales_qoq_pct") is not None:
        parts[-1] += f" ({_signed(c['sales_qoq_pct'])} on the quarter before)"
    if c["sales_rank"] == 1 and c["quarters"] >= 4:
        parts[-1] += f", the highest of {c['quarters']} quarters"
    elif c["sales_rank"] == c["quarters"] and c["quarters"] >= 4:
        parts[-1] += f", the lowest of {c['quarters']} quarters"
    if c.get("eps") is not None:
        if c.get("eps_yoy_pct") is not None:
            parts.append(
                f"EPS {c['eps']:.2f}, {_signed(c['eps_yoy_pct'])} on a year ago"
            )
        elif c.get("eps_year_ago") is not None:
            parts.append(
                f"EPS {c['eps']:.2f} against {c['eps_year_ago']:.2f} a year ago"
            )
        else:
            parts.append(f"EPS {c['eps']:.2f}")
    if c.get("opm_pct") is not None:
        parts.append(
            f"operating margin {c['opm_pct']:.0f}%"
            + (
                f", {_signed(c['opm_change_pp'], ' pts')} on the quarter before"
                if c.get("opm_change_pp")
                else ""
            )
        )
    return "; ".join(parts) + "."


def update_results(
    watchlist: Dict[str, Any],
    prior: Optional[Dict[str, Any]] = None,
    today: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """Scorecards for holdings that reported since the last run, plus those
    still recent enough to show, and the series to compare with next time.

    ``seen`` keeps each holding's last non-empty sales and EPS series.
    Screener empties a holding's figures on a failed fetch, and comparing
    against that would miss the next result entirely.
    """
    today = today or datetime.date.today()
    held = _held(watchlist)
    prior = prior or {}
    seen = {
        t: v
        for t, v in (prior.get("seen") or {}).items()
        if t in held and isinstance(v, dict)
    }
    first_run = "seen" not in prior
    reported = []
    for t, h in sorted(held.items()):
        sc = h["stock"].get("screener") or {}
        sales = _series(sc.get("sales_trend"))
        if len(sales) < 4:
            continue
        eps = _series(sc.get("eps_trend"))
        old = seen.get(t) or {}
        if new_quarter(_series(old.get("sales")), sales):
            card = scorecard(t, h, today)
            # EPS is read from the same table and moves with sales. Where it
            # has not, it would be set against the wrong quarter, so it is
            # left out rather than shown misaligned.
            old_eps = _series(old.get("eps"))
            if card and old_eps and eps and not new_quarter(old_eps, eps):
                for k in ("eps", "eps_yoy_pct", "eps_year_ago"):
                    card.pop(k, None)
                card["summary"] = _summary(card)
            if card:
                reported.append(card)
        seen[t] = {"sales": sales, "eps": eps}
    cutoff = (today - datetime.timedelta(days=SCORECARD_DAYS)).isoformat()
    fresh = {c["ticker"] for c in reported}
    kept = [
        c
        for c in prior.get("scorecards") or []
        if isinstance(c, dict)
        and c.get("ticker") in held
        and c.get("ticker") not in fresh
        and str(c.get("detected") or "") >= cutoff
    ]
    scorecards = sorted(
        reported + kept, key=lambda c: (c["detected"], c["ticker"]), reverse=True
    )
    log.info(
        f"Results: {len(reported)} holding(s) reported since the last run"
        + (f" ({', '.join(c['ticker'] for c in reported)})" if reported else "")
        + f"; {len(scorecards)} scorecard(s) within {SCORECARD_DAYS} days"
        + ("; first run, series recorded for next time" if first_run else "")
        + "."
    )
    return {
        "as_of": today.isoformat(),
        "reported_today": [c["ticker"] for c in reported],
        "scorecards": scorecards,
        "seen": seen,
    }
