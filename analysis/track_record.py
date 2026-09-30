"""Did the rotation engine's picks beat the market?

analysis/postmortem.py scores each add/rotate decision against its own
price target, which answers "did the stock rise as far as expected" and
not "was it worth picking". A stock that rose 8% while the Nifty rose 12%
"played out" and still cost money against an index fund. And it priced
decisions off the CURRENT watchlist, so any pick that had since been
rotated out was recorded as "Left Watchlist (unscored)" — 8 of the first
26 scored decisions. The picks most likely to be dropped are the ones that
went badly, so the hit rate was computed on the survivors.

This scores every decision the same way, still held or not: the pick's
return from the decision date to today, against the Nifty 50 over the
same days, and against the pick's sector index where one exists. Prices
come from one batched yfinance download of daily closes (split- and
bonus-adjusted), so both ends of every comparison are the same kind of
number.

What it does not claim:

  * No Sharpe ratio or annualised alpha. The ledger starts in July 2026;
    a few dozen overlapping picks over weeks is a sample, not a strategy
    history, and a volatility-adjusted number on it would be precision the
    data does not have. The summary states n and the window instead.
  * No backtest of today's watchlist over past years. Today's picks were
    chosen partly because they had grown, so their history flatters them.
    Only decisions, from the day they were made, are scored.
  * Decisions younger than MIN_AGE_DAYS are listed but left out of the
    summary: over a few days the difference is noise.

A pick is "held for" the days since its decision even if it was later
rotated out, because the ledger does not record exits. That measures the
pick, not the timing of its exit — which is the question here.
"""

import datetime
from statistics import median
from typing import Any, Callable, Dict, List, Optional, Tuple

from logger import log

NIFTY = "^NSEI"

# Sector indices with a Yahoo symbol. Only sectors whose index matches what
# the sector holds; the rest are compared with the Nifty 50 alone rather
# than with an index that tracks something else (Nifty Pharma is not
# hospitals, Nifty Auto is not EMS).
#
# Each index lists Yahoo symbols to try in order, the first that returns a
# series winning. The first live run got nothing for ^CNXINFRA or ^CNXENERGY,
# silently: 14 picks had no sector comparison, most of them oil and energy
# names where the question "stock or sector?" matters most. An exchange-
# traded fund tracking the index is the fallback where one is listed; its
# label says so, since an ETF carries tracking error and fees.
SECTOR_INDEX = {
    "banking_financials": ("Nifty Bank", ("^NSEBANK", "BANKBEES.NS")),
    "midcap_it": ("Nifty IT", ("^CNXIT", "ITBEES.NS")),
    "fmcg": ("Nifty FMCG", ("^CNXFMCG",)),
    # No listed ETF tracks Nifty Energy that this could name with confidence;
    # if ^CNXENERGY stays empty the rows say so rather than guess.
    "clean_energy": ("Nifty Energy", ("^CNXENERGY",)),
    "big_cap_industries": ("Nifty Infrastructure", ("^CNXINFRA", "INFRABEES.NS")),
    "logistics_heavy_capital": (
        "Nifty Infrastructure",
        ("^CNXINFRA", "INFRABEES.NS"),
    ),
}

# Summary includes only decisions at least this old.
MIN_AGE_DAYS = 30
# The same ticker picked again within this many days is one decision: the
# engine re-logs a rotation on consecutive runs (BIRLACABLE on 25 and 26
# September), and counting both would double its weight.
REPICK_DAYS = 14
# A bar more than this many days before the decision date is not the price
# at the decision.
MAX_STALENESS_DAYS = 7
# History ledger price and download disagree by more than this: flagged (a
# split or bonus between the two), and the adjusted history is used.
PRICE_CHECK_TOLERANCE = 0.25

# {symbol: [(iso_date, close), ...]} ascending by date.
Closes = Dict[str, List[Tuple[str, float]]]
Fetcher = Callable[[List[str], str], Closes]


def yahoo_closes(symbols: List[str], start: str) -> Closes:
    """Daily adjusted closes from ``start`` to today, one batched download."""
    import yfinance as yf

    out: Closes = {}
    if not symbols:
        return out
    frame = yf.download(
        symbols,
        start=start,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        timeout=20,
        progress=False,
    )
    for symbol in symbols:
        try:
            sub = frame[symbol] if len(symbols) > 1 else frame
            series = sub["Close"].dropna()
        except (KeyError, TypeError):
            continue
        if series.empty:
            continue
        out[symbol] = [(idx.date().isoformat(), float(v)) for idx, v in series.items()]
    return out


def _close_on_or_before(series, date: str) -> Optional[Tuple[str, float]]:
    """The last close on or before ``date``, if it is recent enough."""
    best = None
    for d, v in series or []:
        if d <= date:
            best = (d, v)
        else:
            break
    if best is None:
        return None
    gap = (
        datetime.date.fromisoformat(date) - datetime.date.fromisoformat(best[0])
    ).days
    return best if gap <= MAX_STALENESS_DAYS else None


def _return(series, date: str) -> Optional[Tuple[float, float, float]]:
    """``(start_close, end_close, pct)`` from ``date`` to the latest close."""
    start = _close_on_or_before(series, date)
    if not start or not series:
        return None
    end = series[-1][1]
    if not start[1]:
        return None
    return start[1], end, round((end - start[1]) / start[1] * 100, 2)


def unique_decisions(ledger: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ledger decisions with re-logs of the same pick collapsed to the first."""
    rows = sorted(
        (
            e
            for e in ledger or []
            if isinstance(e, dict) and e.get("ticker") and e.get("date")
        ),
        key=lambda e: (str(e["date"]), str(e["ticker"])),
    )
    last: Dict[str, str] = {}
    kept = []
    for e in rows:
        ticker = str(e["ticker"]).upper()
        prev = last.get(ticker)
        if prev is not None:
            gap = (
                datetime.date.fromisoformat(str(e["date"]))
                - datetime.date.fromisoformat(prev)
            ).days
            if gap <= REPICK_DAYS:
                continue
        last[ticker] = str(e["date"])
        kept.append(e)
    return kept


def _held_now(watchlist: Dict[str, Any]) -> set:
    return {
        str(s.get("ticker")).upper()
        for stocks in (watchlist or {}).values()
        if isinstance(stocks, list)
        for s in stocks
        if isinstance(s, dict) and s.get("ticker")
    }


def build_track_record(
    ledger: List[Dict[str, Any]],
    watchlist: Dict[str, Any],
    fetch: Optional[Fetcher] = None,
    today: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """Every decision against the Nifty 50 and its sector index. Never raises."""
    today = today or datetime.date.today()
    try:
        return _build(ledger, watchlist, fetch or yahoo_closes, today)
    except Exception as e:  # noqa: BLE001 - an enrichment must never break a run
        log.warning(f"Track record failed safely: {e!r}")
        return {
            "as_of": today.isoformat(),
            "decisions": [],
            "summary": {},
            "error": repr(e),
        }


def _build(ledger, watchlist, fetch: Fetcher, today: datetime.date) -> Dict[str, Any]:
    decisions = unique_decisions(ledger)
    if not decisions:
        return {"as_of": today.isoformat(), "decisions": [], "summary": {}}
    start = (
        datetime.date.fromisoformat(min(str(e["date"]) for e in decisions))
        - datetime.timedelta(days=MAX_STALENESS_DAYS + 3)
    ).isoformat()

    tickers = sorted({str(e["ticker"]).upper() for e in decisions})
    wanted = {
        SECTOR_INDEX[e["sector"]] for e in decisions if e.get("sector") in SECTOR_INDEX
    }
    indices = sorted({NIFTY} | {sym for _, cands in wanted for sym in cands})
    closes = fetch([f"{t}.NS" for t in tickers] + indices, start)
    # BSE listing for anything NSE did not serve (ASMTEC is BSE-only).
    missing = [t for t in tickers if f"{t}.NS" not in closes]
    if missing:
        closes.update(fetch([f"{t}.BO" for t in missing], start))

    # Which symbol served each index — the first candidate with a series.
    served: Dict[str, Tuple[str, str]] = {}
    failed: List[str] = []
    for label, cands in sorted(wanted):
        hit = next((c for c in cands if closes.get(c)), None)
        if hit:
            served[label] = (
                hit,
                label if hit.startswith("^") else f"{label} (via {hit[:-3]} ETF)",
            )
        else:
            failed.append(f"{label} ({', '.join(cands)})")
    if failed:
        log.warning("Track record: no index data for " + "; ".join(failed) + ".")

    held = _held_now(watchlist)
    rows = []
    for e in decisions:
        ticker = str(e["ticker"]).upper()
        date = str(e["date"])
        series = closes.get(f"{ticker}.NS") or closes.get(f"{ticker}.BO")
        row: Dict[str, Any] = {
            "date": date,
            "ticker": ticker,
            "name": e.get("name") or ticker,
            "sector": e.get("sector") or "",
            "action": e.get("action") or "",
            "days": (today - datetime.date.fromisoformat(date)).days,
            "still_held": ticker in held,
        }
        pick = _return(series, date)
        nifty = _return(closes.get(NIFTY), date)
        if pick is None or nifty is None:
            row["unmeasured"] = (
                "no price history for the pick"
                if pick is None
                else "no Nifty 50 history for the window"
            )
            rows.append(row)
            continue
        row["return_pct"] = pick[2]
        row["nifty_pct"] = nifty[2]
        row["vs_nifty_pct"] = round(pick[2] - nifty[2], 2)
        logged = e.get("price_at_decision")
        if isinstance(logged, (int, float)) and logged > 0:
            if abs(pick[0] / logged - 1) > PRICE_CHECK_TOLERANCE:
                row["price_check"] = (
                    f"ledger price {logged:g} vs adjusted close {pick[0]:.2f} — "
                    "a split or bonus in between; the adjusted series is used"
                )
        mapped = SECTOR_INDEX.get(row["sector"])
        if mapped:
            label, cands = mapped
            symbol, shown = served.get(label, (None, label))
            sector = _return(closes.get(symbol), date) if symbol else None
            if sector is not None:
                row["index"] = shown
                row["index_pct"] = sector[2]
                row["vs_index_pct"] = round(pick[2] - sector[2], 2)
            else:
                # Said, not left blank: a missing comparison read as "no
                # index for this sector" hid the failure last time.
                row["index_unmeasured"] = (
                    f"{label}: no data from {', '.join(cands)}"
                    if not symbol
                    else f"{label}: no close near {date}"
                )
        rows.append(row)

    rows.sort(key=lambda r: (r["date"], r["ticker"]), reverse=True)
    summary = summarise(rows)
    log.info(
        f"Track record: {len(rows)} decision(s) ({len(ledger or []) - len(rows)} "
        f"re-logs collapsed); {summary.get('n', 0)} at least {MIN_AGE_DAYS} days old"
        + (
            f" — {summary['beat_nifty']}/{summary['n']} beat the Nifty 50, "
            f"median {summary['median_vs_nifty_pct']:+.1f} pts"
            if summary.get("n")
            else ""
        )
        + f"; {sum(1 for r in rows if r.get('unmeasured'))} unmeasured."
    )
    return {
        "as_of": today.isoformat(),
        "benchmark": "Nifty 50",
        "index_failed": failed,
        "min_age_days": MIN_AGE_DAYS,
        "decisions": rows,
        "summary": summary,
    }


def summarise(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregates over decisions old enough to judge. Equal-weighted."""
    judged = [r for r in rows if "vs_nifty_pct" in r and r["days"] >= MIN_AGE_DAYS]
    young = sum(1 for r in rows if "vs_nifty_pct" in r and r["days"] < MIN_AGE_DAYS)
    if not judged:
        return {"n": 0, "too_recent": young}
    vs = [r["vs_nifty_pct"] for r in judged]
    with_index = [r for r in judged if "vs_index_pct" in r]
    exited = [r for r in judged if not r["still_held"]]
    out = {
        "n": len(judged),
        # A stock picked twice counts twice (two decisions); this says so.
        "stocks": len({r["ticker"] for r in judged}),
        "index_unmeasured": sum(1 for r in judged if r.get("index_unmeasured")),
        "too_recent": young,
        "since": min(r["date"] for r in judged),
        "beat_nifty": sum(1 for v in vs if v > 0),
        "mean_return_pct": round(sum(r["return_pct"] for r in judged) / len(judged), 2),
        "mean_nifty_pct": round(sum(r["nifty_pct"] for r in judged) / len(judged), 2),
        "mean_vs_nifty_pct": round(sum(vs) / len(vs), 2),
        "median_vs_nifty_pct": round(median(vs), 2),
        "exited": len(exited),
        "exited_mean_vs_nifty_pct": (
            round(sum(r["vs_nifty_pct"] for r in exited) / len(exited), 2)
            if exited
            else None
        ),
    }
    if with_index:
        out["with_index"] = len(with_index)
        out["beat_index"] = sum(1 for r in with_index if r["vs_index_pct"] > 0)
        out["mean_vs_index_pct"] = round(
            sum(r["vs_index_pct"] for r in with_index) / len(with_index), 2
        )
    return out
