"""Sector revenue-growth rankings: which sectors are compounding fastest.

Built on ``screener.sales_trend`` — up to 8 quarters of absolute quarterly
revenue per holding (populated by the Screener fetch; the row-extraction
repair made this field real in production). Two measures per stock, both
robust to Indian quarterly seasonality in different ways:

  * YoY   — latest quarter vs the same quarter a year earlier (S[-1]/S[-5]),
            seasonally clean by construction.
  * CAGR  — annualized growth over the full available span, smoothing
            single-quarter noise.

Sector figures are the MEDIAN of member stocks (one hyper-grower must not
relabel a whole sector), ranked fastest first. Complements curve staging:
stages classify the shape of adoption, this ranks the raw speed.
"""

from statistics import median
from typing import Any, Dict, List, Optional

from config import SECTOR_METADATA
from logger import log
from utils import to_float

# Below this many quarters the numbers are too thin to annualize honestly.
_MIN_QUARTERS = 5
# Base-effect guard: growth computed off a near-zero base is noise, and
# anything past this cap is displayed as capped rather than pretending
# three significant digits of precision.
_GROWTH_CAP_PCT = 200.0


def compute_stock_growth(sales_trend: Any) -> Optional[Dict[str, float]]:
    """{yoy_pct, cagr_pct, quarters} from a quarterly revenue series, or
    None when the series is too short or the base is unusable."""
    series = [v for v in (to_float(x) for x in (sales_trend or [])) if v is not None]
    if len(series) < _MIN_QUARTERS:
        return None
    start, prior_year, latest = series[0], series[-5], series[-1]
    if start <= 0 or prior_year <= 0 or latest <= 0:
        return None

    yoy = (latest / prior_year - 1.0) * 100.0
    intervals = len(series) - 1
    cagr = ((latest / start) ** (4.0 / intervals) - 1.0) * 100.0

    clamp = lambda v: max(-_GROWTH_CAP_PCT, min(_GROWTH_CAP_PCT, v))  # noqa: E731
    return {
        "yoy_pct": round(clamp(yoy), 1),
        "cagr_pct": round(clamp(cagr), 1),
        "quarters": len(series),
    }


def build_sector_growth(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Per-sector revenue-growth rollup, fastest median YoY first.

    Each qualifying stock is annotated in place (``screener.revenue_yoy_pct``
    / ``revenue_cagr_pct``) so the dashboard's stock views can show the same
    numbers the ranking used.
    """
    rollup: List[Dict[str, Any]] = []
    try:
        for sector, stocks in (watchlist or {}).items():
            if sector == "macro_indicators":
                continue
            measured = []
            for stock in stocks or []:
                if not isinstance(stock, dict):
                    continue
                sc = stock.get("screener")
                if not isinstance(sc, dict):
                    continue
                growth = compute_stock_growth(sc.get("sales_trend"))
                if not growth:
                    continue
                sc["revenue_yoy_pct"] = growth["yoy_pct"]
                sc["revenue_cagr_pct"] = growth["cagr_pct"]
                measured.append((stock, growth))
            if not measured:
                continue

            yoys = [g["yoy_pct"] for _, g in measured]
            cagrs = [g["cagr_pct"] for _, g in measured]
            fastest = max(measured, key=lambda m: m[1]["yoy_pct"])
            rollup.append(
                {
                    "sector": sector,
                    "label": SECTOR_METADATA.get(sector, {}).get("label", sector),
                    "median_yoy_pct": round(median(yoys), 1),
                    "median_cagr_pct": round(median(cagrs), 1),
                    "stock_count": len(measured),
                    "fastest_ticker": fastest[0].get("ticker", ""),
                    "fastest_yoy_pct": fastest[1]["yoy_pct"],
                }
            )
        rollup.sort(key=lambda r: r["median_yoy_pct"], reverse=True)
        if rollup:
            top = rollup[0]
            log.info(
                f"Sector growth: {len(rollup)} sectors ranked; fastest "
                f"{top['sector']} (median YoY {top['median_yoy_pct']:+.1f}%)."
            )
    except Exception as e:
        log.warning(f"Sector growth ranking failed safely: {e!r}")
    return rollup
