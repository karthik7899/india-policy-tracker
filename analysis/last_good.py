"""Last known good: a value a source failed to deliver today, kept for up to
a week and marked as kept.

A Screener.in fetch that timed out or was rate-limited used to cost the
holding every fundamental. Each run blanks the holding's screener dict before
fetching (providers/screener.py), so a failed fetch left it empty. The run's
data completeness dropped, and scoring read the company as having no ROCE,
no margins and no growth. A failed price fetch did the opposite: the old
price stayed, unmarked, for as long as the fetch kept failing.

Now both follow one rule. A value the run did not refresh is kept if it was
fetched at most TTL_DAYS ago, and recorded in the holding's ``_stale_fields``
with that date, so scoring keeps using it and the dashboard can say it is
kept rather than fresh. Older than that it is dropped: a week-old ROCE is
still the company's ROCE, a month-old price is not its price.

Only what a live source writes is kept: Screener's parsed fields, turnover
and the 52-week range from the price download, and NSE delivery. The rest of
the screener dict (the Graham value, the peer P/E, revenue growth) is
computed later in the run from those, every run.

Rows Screener prints only when they apply (a promoter pledge, R&D spend) are
not kept when the fetch itself succeeded. Their absence then means the row
is gone (the pledge was released), not that the fetch failed.

Bookkeeping lives on the holding:

    _fetched       {"price": ts, "screener": ts, "run": ts}  last live fetch,
                   and the run that last assembled the holding (UTC, ISO)
    _stale_fields  {"roce": "2026-10-12", "price": "2026-10-11"}  kept values,
                   each with the day it was fetched; absent when none are kept
"""

import datetime
from typing import Any, Dict, Iterable, Optional

TTL_DAYS = 7

SCREENER_FIELDS = (
    "annual_eps_trend",
    "annual_sales_trend",
    "capex",
    "cash_flow_trend",
    "current_price",
    "debt_to_equity",
    "debt_trend",
    "dii_change",
    "dii_pct",
    "dividend_yield",
    "eps_trend",
    "fii_change",
    "fii_pct",
    "market_cap",
    "operating_margin_trend",
    "opm_expansion",
    "pe_ratio",
    "pledged_change",
    "pledged_pct",
    "pledged_trend",
    "promoter_change",
    "promoter_pct",
    "q_eps",
    "q_net_profit",
    "q_opm",
    "q_sales",
    "qoq_sales_growth",
    "quarterly_ebitda_margin",
    "quarterly_revenue_growth",
    "rd_expenditure",
    "rd_pct",
    "roce",
    "roce_trend",
    "roe",
    "sales_trend",
    "ttm_eps",
)
# Turnover (analysis/liquidity.assess) and the 52-week range, both from the
# price download (analysis/growth.py), and NSE delivery (providers/nse_delivery).
LIQUIDITY_FIELDS = (
    "advt_cr",
    "liquidity_band",
    "sessions",
    "days_to_exit_1cr",
    "days_to_exit_5cr",
    "week52_low",
    "week52_high",
    "pct_above_low",
)
DELIVERY_FIELDS = ("deliv_pct", "delivery_band", "series", "turnover_cr_last")
KEPT_FIELDS = SCREENER_FIELDS + LIQUIDITY_FIELDS + DELIVERY_FIELDS
OPTIONAL_ROWS = (
    "pledged_pct",
    "pledged_change",
    "pledged_trend",
    "rd_expenditure",
    "rd_pct",
)
# Derived from the price, and meaningless once the price is dropped.
_PRICE_DERIVED = ("growth_pct",)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _stamp(when: datetime.datetime) -> str:
    return when.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")


def mark(stock: Dict[str, Any], source: str, when=None) -> None:
    """Record that ``source`` ("price" or "screener") delivered just now."""
    stock.setdefault("_fetched", {})[source] = _stamp(when or _now())


def _holdings(watchlist) -> Iterable[Dict[str, Any]]:
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for stock in stocks:
            if isinstance(stock, dict) and stock.get("ticker"):
                yield stock


def snapshot(watchlist, when=None) -> Dict[str, Any]:
    """Every holding's values before the run fetches anything."""
    return {
        "started": _stamp(when or _now()),
        "holdings": {
            str(s["ticker"]).upper(): {
                "price": s.get("price"),
                "screener": dict(s.get("screener") or {}),
                "fetched": dict(s.get("_fetched") or {}),
                "stale": dict(s.get("_stale_fields") or {}),
            }
            for s in _holdings(watchlist)
        },
    }


def _day(stamp: Optional[str]) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat(str(stamp)[:10])
    except ValueError:
        return None


def restore(
    watchlist, prior: Dict[str, Any], when=None, ttl_days: int = TTL_DAYS
) -> Dict[str, Any]:
    """Put back what this run failed to refresh, and mark it as kept.

    Runs after every live source has written (prices, Screener, turnover,
    delivery) and before anything reads them. Returns counts for the log.
    """
    now = when or _now()
    today = now.astimezone(datetime.timezone.utc).date()
    started = prior.get("started") or _stamp(now)
    report = {"kept": 0, "holdings": 0, "dropped": 0, "oldest": None}
    for stock in _holdings(watchlist):
        before = (prior.get("holdings") or {}).get(str(stock["ticker"]).upper())
        fetched = stock.setdefault("_fetched", {})
        stale: Dict[str, str] = {}
        if before:

            def since(field: str, source: str) -> datetime.date:
                # The day the value was fetched: when it was first kept, else
                # its source's last fetch, else the run that last assembled
                # the holding, else (records from before this existed) the
                # day before.
                for stamp in (
                    before["stale"].get(field),
                    before["fetched"].get(source),
                    before["fetched"].get("run"),
                ):
                    day = _day(stamp)
                    if day:
                        return day
                return today - datetime.timedelta(days=1)

            def keep(field: str, day: datetime.date) -> bool:
                if (today - day).days > ttl_days:
                    report["dropped"] += 1
                    return False
                stale[field] = day.isoformat()
                report["kept"] += 1
                oldest = report["oldest"]
                report["oldest"] = min(oldest, day) if oldest else day
                return True

            price_fresh = str(fetched.get("price") or "") >= started
            if not price_fresh and before["price"] not in (None, ""):
                if keep("price", since("price", "price")):
                    stock["price"] = before["price"]
                else:
                    stock.pop("price", None)
                    for key in _PRICE_DERIVED:
                        stock.pop(key, None)

            screener = stock.get("screener")
            if not isinstance(screener, dict):
                screener = stock["screener"] = {}
            screener_fresh = str(fetched.get("screener") or "") >= started
            for field in KEPT_FIELDS:
                if field in screener or field not in before["screener"]:
                    continue
                if screener_fresh and field in OPTIONAL_ROWS:
                    continue
                source = (
                    "screener"
                    if field in SCREENER_FIELDS
                    else "price" if field in LIQUIDITY_FIELDS else "run"
                )
                if keep(field, since(field, source)):
                    screener[field] = before["screener"][field]
        if stale:
            stock["_stale_fields"] = stale
            report["holdings"] += 1
        else:
            stock.pop("_stale_fields", None)
        fetched["run"] = _stamp(now)
    if report["oldest"]:
        report["oldest"] = report["oldest"].isoformat()
    return report


def describe(report: Dict[str, Any]) -> str:
    """One log line for what was kept and what was dropped."""
    if not report["kept"] and not report["dropped"]:
        return "Last known good: every holding's values were fetched this run."
    line = (
        f"Last known good: kept {report['kept']} value(s) a source did not "
        f"deliver this run, for {report['holdings']} holding(s)"
    )
    if report["oldest"]:
        line += f", the oldest fetched {report['oldest']}"
    if report["dropped"]:
        line += (
            f"; dropped {report['dropped']} older than {TTL_DAYS} days rather "
            "than show them as current"
        )
    return line + "."
