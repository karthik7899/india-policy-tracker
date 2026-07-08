"""ISIN entity master — the permanent fix for the dead/duplicate-ticker
class of bug this watchlist has hit repeatedly: RIRPOWER vs RIR, SPEL vs
SPELS were the same companies tracked under wrong exchange symbols, and
DIXON is (as of this module landing) tracked under two different sectors
at once because ticker/name string-matching missed that they were the
same holding.

Exchange ticker symbols are not a stable identity — they can be entered
wrong, or a company can be found again independently under a slightly
different name. ISIN (International Securities Identification Number) is
the one identifier that doesn't drift: it is assigned once per security by
the depositories and never changes for the life of the listing.

This module treats ISIN as the canonical key and the ticker as just one
more per-venue attribute of an entity, sourced opportunistically from
Screener.in — providers/screener.py stamps ``stock["screener"]["isin"]``
once a company's page has been scraped, so this costs no new network call
and no new failure surface. Coverage builds up run over run as Screener
fetches succeed; a holding with no ISIN yet simply isn't indexed until it
is.
"""

import re
from typing import Any, Dict, List, Optional

# Indian ISINs are always "IN" + a 2-char issuer-type code + 7-char issuer/
# security code + 1 numeric check digit = 12 chars. A regex scan of raw page
# text is resilient to markup/DOM changes that would break a CSS-selector
# approach, at the cost of (very rarely) matching an unrelated 12-char token
# that happens to fit the shape — acceptable for a best-effort index.
_ISIN_RE = re.compile(r"\bIN[A-Z0-9]{9}[0-9]\b")


def extract_isin(text: str) -> Optional[str]:
    """Best-effort ISIN extraction from raw page text."""
    if not text:
        return None
    match = _ISIN_RE.search(text)
    return match.group(0) if match else None


def build_entity_master(watchlist: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Index every holding with a known ISIN, keyed by ISIN.

    Each entry: ``{isin, ticker, name, sector}``. Holdings without a
    resolved ISIN yet are simply absent — this is a best-effort index built
    from whatever Screener has already returned, not a hard requirement.
    """
    master: Dict[str, Dict[str, Any]] = {}
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            isin = (stock.get("screener") or {}).get("isin")
            if not isin:
                continue
            master[isin] = {
                "isin": isin,
                "ticker": stock.get("ticker"),
                "name": stock.get("name"),
                "sector": sector,
            }
    return master


def find_duplicate_holdings(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect the same ISIN tracked under more than one watchlist entry —
    the exact failure mode ISIN keying exists to catch.

    Returns one entry per duplicated ISIN: ``{isin, holdings: [...]}`` where
    each holding is ``{sector, ticker, name}``.
    """
    by_isin: Dict[str, List[Dict[str, Any]]] = {}
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            isin = (stock.get("screener") or {}).get("isin")
            if not isin:
                continue
            by_isin.setdefault(isin, []).append(
                {
                    "sector": sector,
                    "ticker": stock.get("ticker"),
                    "name": stock.get("name"),
                }
            )
    return [
        {"isin": isin, "holdings": holdings}
        for isin, holdings in by_isin.items()
        if len(holdings) > 1
    ]


def resolve_entity_by_isin(
    isin: Optional[str], entity_master: Dict[str, Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Look up an already-tracked holding by ISIN, or ``None``."""
    if not isin:
        return None
    return entity_master.get(isin)
