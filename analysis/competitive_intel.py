"""News-driven new-entrant detection.

The pipeline already fetches the evidence of competitive incursions — the
day Amber Enterprises moved on mobile manufacturing, "Amber eyes 20% of
Oppo India volumes" was sitting in the collected agreements feed — but
nothing connected it to the incumbents it threatens (Dixon, Kaynes). This
module closes that gap: it scans every collected headline for an
ENTRY MOVE (eyes / enters / forays / sets up / new facility / wins order
...) landing on a sector's BATTLEGROUND vocabulary (mobile manufacturing,
CCTV, solar modules, ...), extracts the challenger, and — when the
challenger is not already one of that sector's own holdings — raises a
threat naming the incumbents.
"""

import re
from typing import Any, Dict, List

from analysis.parsing import title_matches_company
from config import SECTOR_METADATA
from logger import log

# Phrases that signal a company is moving into a market.
_ENTRY_MOVES = (
    "enters",
    "entry into",
    "forays into",
    "foray into",
    "to manufacture",
    "to make",
    "eyes",
    "targets",
    "wins order",
    "bags order",
    "wins contract",
    "sets up",
    "setting up",
    "groundbreaking",
    "new facility",
    "new plant",
    "expands into",
    "expansion into",
    "begins production",
    "starts production",
    "ramps up",
)

# What each sector's turf looks like in a headline. A headline must touch a
# sector's battleground for an entry move to be read as an incursion there.
# Sectors without an entry (pure services, index trackers) simply never fire.
SECTOR_BATTLEGROUNDS: Dict[str, tuple] = {
    "manufacturing_electronics": (
        "mobile manufacturing",
        "smartphone",
        "handset",
        "oppo",
        "vivo",
        "xiaomi",
        "laptop",
        "notebook",
        "ems",
        "electronics manufacturing",
        "pcb",
        "pcba",
        "led tv",
        "television",
        "contract manufacturing",
    ),
    "surveillance_security": (
        "cctv",
        "surveillance camera",
        "ip camera",
        "dvr",
        "anti-drone",
        "drone system",
    ),
    "clean_energy": (
        "solar module",
        "solar cell",
        "wind turbine",
        "electrolyser",
        "electrolyzer",
        "green hydrogen",
        "battery storage",
    ),
    "semiconductors_equipment": (
        "osat",
        "semiconductor fab",
        "chip packaging",
        "wafer",
        "silicon carbide",
    ),
    "data_center_support": (
        "data center",
        "data centre",
        "optical fibre",
        "optical fiber",
    ),
    "aerospace_defence": (
        "missile",
        "radar system",
        "defence electronics",
        "uav",
    ),
    "textiles_apparel": (
        "garment manufacturing",
        "apparel manufacturing",
        "textile mill",
        "home textiles",
    ),
    "sports_athleisure": ("footwear manufacturing", "athleisure"),
}

# A capitalized company-ish name directly followed by an entry verb
# ("Amber eyes ...", "Syrma SGS wins order ...").
_CHALLENGER_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+){0,2})\s+"
    r"(?:eyes|enters|targets|forays|sets|wins|bags|begins|starts|expands|ramps|plans)\b"
)

# Actors that are never a corporate challenger.
_NON_COMPANIES = {
    "india",
    "centre",
    "center",
    "government",
    "cabinet",
    "ministry",
    "minister",
    "sebi",
    "rbi",
    "nse",
    "bse",
    "pm",
    "cm",
    "state",
    "union",
    "budget",
    "china",
    "us",
    "usa",
}


def collect_headlines(data: Dict[str, Any], watchlist: Dict[str, Any]) -> List[str]:
    """Every collected headline, whichever feed carried it."""
    seen = set()
    headlines: List[str] = []

    def _add(text):
        text = str(text or "").strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            headlines.append(text)

    for sector in watchlist or {}:
        for item in data.get(sector, []) or []:
            if isinstance(item, dict):
                _add(item.get("title"))
    for item in data.get("corporate_agreements", []) or []:
        if isinstance(item, dict):
            _add(item.get("title"))
    for item in data.get("product_launches", []) or []:
        if isinstance(item, dict):
            _add(item.get("product"))
    for item in data.get("corporate_filings", []) or []:
        if isinstance(item, dict):
            _add(item.get("filing"))
    for item in data.get("global_market_news", []) or []:
        if isinstance(item, dict):
            _add(item.get("title"))
    return headlines


def _extract_challenger(headline: str, data: Dict[str, Any]) -> str:
    """Name the company making the move — a known listed peer from the
    Screener radar when possible (most reliable), else the capitalized name
    driving the entry verb."""
    for rows in (data.get("peer_competitors") or {}).values():
        for peer in rows or []:
            if not isinstance(peer, dict):
                continue
            if title_matches_company(
                headline, peer.get("ticker", ""), peer.get("name", "")
            ):
                return str(peer.get("name") or peer.get("ticker"))

    match = _CHALLENGER_RE.search(headline)
    if match:
        candidate = match.group(1).strip()
        tokens = candidate.lower().split()
        if all(tok not in _NON_COMPANIES for tok in tokens):
            return candidate
    return ""


def detect_new_entrants(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Returns one entry per (sector, challenger) incursion detected:
    {sector, sector_label, challenger, headline, incumbents}."""
    results: List[Dict[str, Any]] = []
    seen_pairs = set()

    try:
        headlines = collect_headlines(data, watchlist)
        for headline in headlines:
            lower = headline.lower()
            if not any(move in lower for move in _ENTRY_MOVES):
                continue

            for sector, battleground in SECTOR_BATTLEGROUNDS.items():
                holdings = (watchlist or {}).get(sector) or []
                if not holdings:
                    continue
                if not any(term in lower for term in battleground):
                    continue

                # The incumbent expanding on its own turf is not a threat.
                incumbent_move = any(
                    title_matches_company(
                        headline, s.get("ticker", ""), s.get("name", "")
                    )
                    for s in holdings
                    if isinstance(s, dict)
                )
                if incumbent_move:
                    continue

                challenger = _extract_challenger(headline, data)
                if not challenger:
                    continue

                pair = (sector, challenger.lower())
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                results.append(
                    {
                        "sector": sector,
                        "sector_label": SECTOR_METADATA.get(sector, {}).get(
                            "label", sector
                        ),
                        "challenger": challenger,
                        "headline": headline[:180],
                        "incumbents": [
                            s.get("ticker")
                            for s in holdings
                            if isinstance(s, dict) and s.get("ticker")
                        ],
                    }
                )
        if results:
            log.info(
                f"New-entrant radar: {len(results)} incursion(s) detected: "
                + "; ".join(f"{r['challenger']} → {r['sector']}" for r in results)
            )
    except Exception as e:
        log.warning(f"New-entrant radar failed safely: {e!r}")
    return results


def new_entrant_signals(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Early-warning alerts for each incumbent threatened by an incursion."""
    alerts: List[Dict[str, Any]] = []
    names_by_ticker = {}
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if isinstance(stock, dict) and stock.get("ticker"):
                names_by_ticker[stock["ticker"]] = stock.get("name")

    for entry in data.get("new_entrants", []) or []:
        for ticker in entry.get("incumbents", []) or []:
            alerts.append(
                {
                    "ticker": ticker,
                    "name": names_by_ticker.get(ticker, ticker),
                    "sector": entry.get("sector_label", entry.get("sector")),
                    "severity": "High",
                    "direction": "risk",
                    "category": "New Entrant",
                    "signal": (
                        f"{entry.get('challenger')} is moving onto this turf: "
                        f"“{entry.get('headline', '')}”"
                    ),
                }
            )
    return alerts
