"""Sector revenue-growth rankings: which sectors are compounding fastest.

Built on ``screener.sales_trend`` — up to 8 quarters of absolute quarterly
revenue per holding — with ``screener.annual_sales_trend`` (the annual P&L
row) used for a genuine multi-year CAGR where it is available.

Indian quarterly revenue is heavily seasonal: defence and capital-goods names
book a large share of the year in the March quarter, beverages peak in summer.
Any measure that compares two individual quarters therefore has to compare
*like with like*, and any measure that spans several quarters has to span a
whole number of years. The three figures here are each constructed to survive
that:

  * YoY        — latest quarter vs the same quarter a year earlier
                 (``S[-1]`` vs ``S[-5]``), seasonally matched by construction.
  * TTM growth — the last four quarters vs the four before them. Every quarter
                 of the year appears exactly once on each side, so seasonality
                 cancels entirely and the figure does not lurch when the
                 8-quarter window rolls forward.
  * CAGR       — annualized growth across the annual P&L series, the only
                 place a multi-year rate can honestly be computed from.

The predecessor of TTM growth was ``(S[-1]/S[0]) ** (4/intervals)``, which
spanned 7 quarters — 1.75 years, so its endpoints were different quarters of
the fiscal year. It reported +94.6% for a company growing under 7%, and flipped
a holding from +30.7% to -6.0% purely because the window rolled and a peak
quarter landed at position 0. Sector figures are the MEDIAN of member stocks
(one hyper-grower must not relabel a whole sector), ranked fastest first.
"""

from statistics import median
from typing import Any, Dict, List, Optional

from analysis.data_quality import (
    REVENUE_GROWTH_BAND,
    classify,
    clean_series,
    is_trustworthy,
)
from config import SECTOR_METADATA
from logger import log

# A year-on-year comparison needs the same quarter one year back.
_MIN_QUARTERS_YOY = 5
# A trailing-twelve-month comparison needs two non-overlapping years.
_MIN_QUARTERS_TTM = 8
# A multi-year CAGR needs at least three annual periods to annualize over.
_MIN_ANNUAL_PERIODS = 4
# Below this many measured holdings a sector median is one company's opinion.
_MIN_STOCKS_FOR_CONFIDENCE = 2


def _growth_pct(current: float, prior: float) -> Optional[float]:
    if prior <= 0 or current <= 0:
        return None
    return round((current / prior - 1.0) * 100.0, 1)


def compute_stock_growth(
    sales_trend: Any, annual_sales_trend: Any = None
) -> Optional[Dict[str, Any]]:
    """Revenue growth for one holding, or ``None`` when nothing is computable.

    Returns ``yoy_pct``, ``ttm_growth_pct`` and ``cagr_pct`` (any of which may
    be ``None``), the observation counts behind them, and a ``quality`` verdict
    for the headline TTM figure so callers can refuse to rank on an artifact.
    """
    series = clean_series(sales_trend)
    if len(series) < _MIN_QUARTERS_YOY:
        return None

    yoy = None
    if len(series) >= _MIN_QUARTERS_YOY:
        yoy = _growth_pct(series[-1], series[-5])

    ttm = None
    if len(series) >= _MIN_QUARTERS_TTM:
        ttm = _growth_pct(sum(series[-4:]), sum(series[-8:-4]))

    annual = clean_series(annual_sales_trend)
    cagr = None
    if len(annual) >= _MIN_ANNUAL_PERIODS and annual[0] > 0 and annual[-1] > 0:
        years = len(annual) - 1
        cagr = round(((annual[-1] / annual[0]) ** (1.0 / years) - 1.0) * 100.0, 1)

    if yoy is None and ttm is None and cagr is None:
        return None

    quality = classify(
        ttm,
        band=REVENUE_GROWTH_BAND,
        observations=len(series),
        min_observations=_MIN_QUARTERS_TTM,
    )
    return {
        "yoy_pct": yoy,
        "ttm_growth_pct": ttm,
        "cagr_pct": cagr,
        "quarters": len(series),
        "annual_periods": len(annual),
        "quality": quality,
    }


def _median_or_none(values: List[float]) -> Optional[float]:
    usable = [v for v in values if v is not None]
    return round(median(usable), 1) if usable else None


def build_sector_growth(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Per-sector revenue-growth rollup, fastest median TTM growth first.

    Only holdings whose growth figure passes the data-quality gate are ranked;
    sectors measured off a single holding are still reported but flagged
    ``low_confidence`` so a one-stock median is never read as a sector view.
    Each qualifying stock is annotated in place so the dashboard's stock views
    can show the same numbers the ranking used.
    """
    rollup: List[Dict[str, Any]] = []
    try:
        for sector, stocks in (watchlist or {}).items():
            if sector == "macro_indicators":
                continue
            measured = []
            qualities = []
            for stock in stocks or []:
                if not isinstance(stock, dict):
                    continue
                sc = stock.get("screener")
                if not isinstance(sc, dict):
                    continue
                growth = compute_stock_growth(
                    sc.get("sales_trend"), sc.get("annual_sales_trend")
                )
                if not growth:
                    continue
                sc["revenue_yoy_pct"] = growth["yoy_pct"]
                sc["revenue_ttm_growth_pct"] = growth["ttm_growth_pct"]
                sc["revenue_cagr_pct"] = growth["cagr_pct"]
                sc["revenue_growth_quality"] = growth["quality"]
                qualities.append(growth["quality"])
                # Only trustworthy figures are allowed to move a ranking.
                if is_trustworthy(growth["quality"]):
                    measured.append((stock, growth))
            if not measured:
                continue

            ranked_on = [g["ttm_growth_pct"] for _, g in measured]
            fastest = max(measured, key=lambda m: m[1]["ttm_growth_pct"])
            rollup.append(
                {
                    "sector": sector,
                    "label": SECTOR_METADATA.get(sector, {}).get("label", sector),
                    "median_ttm_growth_pct": _median_or_none(ranked_on),
                    "median_yoy_pct": _median_or_none(
                        [g["yoy_pct"] for _, g in measured]
                    ),
                    "median_cagr_pct": _median_or_none(
                        [g["cagr_pct"] for _, g in measured]
                    ),
                    "stock_count": len(measured),
                    "fastest_ticker": fastest[0].get("ticker", ""),
                    "fastest_ttm_growth_pct": fastest[1]["ttm_growth_pct"],
                    # Holdings whose growth figure failed the quality gate are
                    # counted, not hidden: a sector ranked off two of its five
                    # members should say so.
                    "excluded_count": len(qualities) - len(measured),
                    "low_confidence": len(measured) < _MIN_STOCKS_FOR_CONFIDENCE,
                }
            )
        rollup.sort(key=lambda r: r["median_ttm_growth_pct"], reverse=True)
        if rollup:
            top = rollup[0]
            thin = sum(1 for r in rollup if r["low_confidence"])
            log.info(
                f"Sector growth: {len(rollup)} sectors ranked; fastest "
                f"{top['sector']} (median TTM {top['median_ttm_growth_pct']:+.1f}%)"
                f"{f'; {thin} on a single holding' if thin else ''}."
            )
    except Exception as e:
        log.warning(f"Sector growth ranking failed safely: {e!r}")
    return rollup
