"""Sector-relative valuation (market valuation context).

The Graham/Buffett screens in this project are *absolute* single-stock checks.
This module adds the missing *relative* dimension: how a stock's P/E compares
with the median P/E of its watchlist peer group. It reuses the P/E already
scraped from Screener.in (``stock["screener"]["pe_ratio"]``) — no new data
source — and:

* annotates each stock's screener dict with ``industry_pe`` (the peer-group
  median, which the dashboard already knows how to display) and a human-readable
  ``pe_vs_peers`` label, and
* returns a per-sector rollup (``build_sector_valuation``) used by the dashboard
  and the email digest.

"Industry P/E" here is a watchlist peer-group proxy, not the exchange-wide
industry figure; the peer set is the curated holdings in the same sector.
"""

from statistics import median
from typing import Any, Dict, List, Optional

from config import SECTOR_METADATA

# How far a stock's P/E must sit from the peer median before we label it
# cheap/expensive rather than "in line".
_INLINE_BAND = 0.10  # ±10%


def _to_float(value: Any) -> Optional[float]:
    """Best-effort numeric coercion tolerant of ``None``/strings/``N/A``."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned or cleaned.upper() in {"N/A", "NA", "-", "—"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _relative_label(pe: float, peer_median: float) -> str:
    """Human-readable position of ``pe`` versus the peer median."""
    if peer_median <= 0:
        return "—"
    delta = (pe - peer_median) / peer_median
    if delta <= -_INLINE_BAND:
        return f"{abs(delta) * 100:.0f}% below peers"
    if delta >= _INLINE_BAND:
        return f"{delta * 100:.0f}% above peers"
    return "In line with peers"


def build_sector_valuation(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compute a per-sector P/E rollup and annotate each stock in-place.

    Returns a list (one entry per sector with at least one valid P/E), sorted by
    peer-group median P/E ascending (cheapest sectors first). Every stock that
    has a usable P/E gets ``industry_pe`` and ``pe_vs_peers`` written onto its
    screener dict so the dashboard's existing "vs Ind" display lights up.
    """
    rollup: List[Dict[str, Any]] = []

    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue

        # Collect (stock, pe) pairs that carry a usable P/E.
        priced = []
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            sc = stock.get("screener")
            if not isinstance(sc, dict):
                continue
            pe = _to_float(sc.get("pe_ratio"))
            if pe is not None and pe > 0:
                priced.append((stock, pe))

        if not priced:
            continue

        pes = [pe for _, pe in priced]
        peer_median = round(median(pes), 1)

        cheapest = min(priced, key=lambda p: p[1])
        priciest = max(priced, key=lambda p: p[1])

        # Annotate each stock with its standing versus the peer median.
        for stock, pe in priced:
            sc = stock["screener"]
            sc["industry_pe"] = peer_median
            sc["pe_vs_peers"] = _relative_label(pe, peer_median)

        rollup.append(
            {
                "sector": sector,
                "label": SECTOR_METADATA.get(sector, {}).get("label", sector),
                "icon": SECTOR_METADATA.get(sector, {}).get("icon", "📊"),
                "median_pe": peer_median,
                "stock_count": len(priced),
                "cheapest_ticker": cheapest[0].get("ticker", ""),
                "cheapest_pe": round(cheapest[1], 1),
                "most_expensive_ticker": priciest[0].get("ticker", ""),
                "most_expensive_pe": round(priciest[1], 1),
            }
        )

    rollup.sort(key=lambda r: r["median_pe"])
    return rollup
