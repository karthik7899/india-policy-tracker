"""Quantitative candidate discovery: screen the peer radar on fundamentals.

Discovery used to run entirely on press coverage. ``detect_emerging_players``
regex-matches capitalized names out of headlines and then tries to resolve a
ticker, which means a company is only ever considered if a journalist wrote
about it in one of the handful of RSS items pulled per sector, phrased it with
a competitive verb, and the name happened to resolve. On a representative run
that produced three candidates — "Toubro Heavy Engineering", "Redtape Ltd" and
"Industry" — and all three failed ticker resolution, so nothing was evaluated.

Meanwhile the Screener peer tables hand us ~70 real listed competitors per run,
each arriving with a ticker already attached plus market cap, quarterly sales,
quarterly profit and their growth rates. Syrma sat in that radar at +58% sales
growth and a Rs 24,843 Cr market cap and could never be promoted, because
nothing connected the radar to the rotation engine.

This module is that connection, and it screens rather than scores. Every
candidate has to clear three absolute gates — it must be big enough to matter,
hold a real share of its industry's revenue, and be growing — and survivors are
ranked by profit growth, falling back to sales growth where a company does not
report a comparable profit figure. Gates beat a weighted score here because the
result has to be explainable: a candidate is on the list because of numbers a
reader can check, and the numbers that disqualified the rest are recorded too.
"""

from typing import Any, Dict, List, Optional

from analysis.data_quality import REVENUE_GROWTH_BAND, classify, is_trustworthy
from logger import log
from utils import to_float

# Below this the company is too small for a position to be meaningful, and
# small denominators make its growth rates unstable.
MIN_MARKET_CAP_CR = 1_000.0
# A challenger with a negligible slice of industry revenue is not yet
# competing with a holding, however fast it is compounding.
MIN_INDUSTRY_SHARE_PCT = 1.0
# Growth bar. A candidate must be outgrowing the market to justify displacing
# something already held.
MIN_GROWTH_PCT = 15.0
# How many survivors per sector are handed on to the rotation engine. Each one
# costs a live price lookup there, and a long list would churn the watchlist.
MAX_CANDIDATES_PER_SECTOR = 3


def _round_or_none(value: Any) -> Optional[float]:
    num = to_float(value)
    return None if num is None else round(num, 1)


def _best_growth(row: Dict[str, Any]) -> Optional[float]:
    """Profit growth where reported, else revenue growth.

    Profit is the better signal — revenue bought at no margin is not a threat
    — but loss-making and newly-listed companies often have no comparable
    profit figure, and excluding them would hide exactly the disruptive
    entrants this radar exists to catch.
    """
    profit = to_float(row.get("profit_var_pct"))
    if profit is not None and is_trustworthy(
        classify(profit, band=REVENUE_GROWTH_BAND)
    ):
        return round(profit, 1)
    sales = to_float(row.get("sales_var_pct"))
    if sales is not None and is_trustworthy(classify(sales, band=REVENUE_GROWTH_BAND)):
        return round(sales, 1)
    return None


def screen_sector_candidates(
    peer_competitors: Dict[str, List[Dict[str, Any]]],
    max_per_sector: int = MAX_CANDIDATES_PER_SECTOR,
    known_symbols: Optional[set] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Rank non-holding peers per sector against the three gates.

    Each row already carries ``industry_share_pct``, stamped against its own
    industry table when the peers were fetched. Recomputing a denominator here
    would have to pool every industry scanned for a sector, which understates
    the share of a company competing in only one of them.

    ``known_symbols`` is the NSE equity list (see providers/isin_master.py).
    Screener identifies BSE-only companies by numeric scrip code, and those
    can never resolve through the ``.NS`` price path, so screening them out
    here saves a doomed lookup downstream.
    """
    screened: Dict[str, List[Dict[str, Any]]] = {}
    try:
        for sector, rows in (peer_competitors or {}).items():
            passed = []
            for row in rows or []:
                if not isinstance(row, dict) or not row.get("ticker"):
                    continue
                ticker = str(row["ticker"]).upper()
                if ticker.isdigit():
                    continue
                if known_symbols and ticker not in known_symbols:
                    continue
                market_cap = to_float(row.get("market_cap"))
                growth = _best_growth(row)
                share = to_float(row.get("industry_share_pct"))

                failed = []
                if market_cap is None or market_cap < MIN_MARKET_CAP_CR:
                    failed.append("size")
                if share is None or share < MIN_INDUSTRY_SHARE_PCT:
                    failed.append("share")
                if growth is None or growth < MIN_GROWTH_PCT:
                    failed.append("growth")
                if failed:
                    continue

                passed.append(
                    {
                        "ticker": ticker,
                        "name": row.get("name") or ticker,
                        "sector": sector,
                        "market_cap": market_cap,
                        "industry_share_pct": share,
                        "growth_pct": growth,
                        "profit_var_pct": to_float(row.get("profit_var_pct")),
                        "sales_var_pct": to_float(row.get("sales_var_pct")),
                        "pe_ratio": to_float(row.get("pe_ratio")),
                        "roce": to_float(row.get("roce")),
                        "basis": (
                            "profit growth"
                            if _round_or_none(row.get("profit_var_pct")) == growth
                            else "revenue growth"
                        ),
                    }
                )

            passed.sort(key=lambda c: c["growth_pct"], reverse=True)
            if passed:
                screened[sector] = passed[:max_per_sector]

        if screened:
            total = sum(len(v) for v in screened.values())
            top = max(
                (c for rows in screened.values() for c in rows),
                key=lambda c: c["growth_pct"],
            )
            log.info(
                f"Candidate screen: {total} peer(s) cleared size/share/growth "
                f"across {len(screened)} sector(s); strongest "
                f"{top['ticker']} ({top['growth_pct']:+.1f}% {top['basis']})."
            )
        else:
            log.info("Candidate screen: no peers cleared the gates this run.")
    except Exception as e:  # noqa: BLE001 - discovery must never break a run
        log.warning(f"Candidate screen failed safely: {e!r}")
    return screened


def candidates_for_rotation(
    screened: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Reshape survivors into the (name, ticker) pairs the rotation engine takes.

    These arrive with a ticker already resolved by Screener, so they skip the
    name-resolution step that discards most headline-derived candidates.
    """
    return {
        sector: [{"name": c["name"], "ticker": c["ticker"]} for c in rows]
        for sector, rows in (screened or {}).items()
    }
