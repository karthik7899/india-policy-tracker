"""Stock-level MTF snapshots from the NSE-disclosure-backed public API.

The API is an independent aggregation of NSE's daily Margin Trading
Disclosure files. Values are INR crore and typically lag the market by one
trading day. Keep its attribution and as-of date with every published value.
"""

from typing import Any, Dict, Optional

from logger import log

API_URL = "https://margintradingfacility.com/api/stocks?limit=1000"
SOURCE_NAME = "Margin Trading Facility (NSE disclosure aggregation)"
SOURCE_URL = "https://margintradingfacility.com/methodology"
ATTRIBUTION = (
    "MTF data via Margin Trading Facility; compiled from NSE daily disclosures"
)


def _number(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return None


def _rows(payload: Any):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("stocks", "data", "results", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _first(row: Dict[str, Any], keys):
    for key in keys:
        if row.get(key) is not None:
            return row[key]
    return None


def parse_mtf_payload(payload: Any) -> Dict[str, Dict[str, Any]]:
    """Return SYMBOL -> validated MTF book fields; malformed rows are skipped."""
    if not isinstance(payload, (dict, list)):
        return {}
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    as_of = (
        meta.get("as_of")
        or meta.get("date")
        or payload.get("as_of")
        or payload.get("date")
        if isinstance(payload, dict)
        else None
    )
    out = {}
    for row in _rows(payload):
        if not isinstance(row, dict):
            continue
        ticker = str(
            _first(row, ("ticker", "symbol", "stock_symbol", "scrip")) or ""
        ).strip().upper()
        if not ticker:
            continue
        book = _number(
            _first(
                row,
                (
                    "outstanding_cr",
                    "mtf_outstanding_cr",
                    "book_cr",
                    "mtf_book_cr",
                    "outstanding",
                    "mtf_book",
                ),
            )
        )
        if book is None or book < 0:
            continue
        change_1m = _number(
            _first(
                row,
                ("change_1m_pct", "change_30d_pct", "1m_change_pct", "change_1m"),
            )
        )
        change_1w = _number(
            _first(
                row,
                ("change_1w_pct", "change_7d_pct", "1w_change_pct", "change_1w"),
            )
        )
        rank = _number(_first(row, ("rank", "mtf_rank")))
        out[ticker] = {
            "mtf_outstanding_cr": round(book, 2),
            "mtf_change_1m_pct": round(change_1m, 2) if change_1m is not None else None,
            "mtf_change_1w_pct": round(change_1w, 2) if change_1w is not None else None,
            "mtf_rank": int(rank) if rank is not None else None,
            "mtf_as_of": as_of or row.get("date") or row.get("as_of"),
            "mtf_source": SOURCE_NAME,
            "mtf_source_url": SOURCE_URL,
            "mtf_attribution": ATTRIBUTION,
            "mtf_status": "available",
        }
    return out


async def fetch_mtf_async(session, watchlist):
    """Fetch once per run; fail closed so unavailable is never shown as zero."""
    try:
        async with session.get(API_URL, timeout=20) as response:
            if response.status != 200:
                log.info(f"MTF feed unavailable (HTTP {response.status}).")
                return {}
            payload = await response.json(content_type=None)
        rows = parse_mtf_payload(payload)
        tickers = {
            str(stock.get("ticker", "")).upper()
            for stocks in (watchlist or {}).values()
            for stock in stocks or []
            if isinstance(stock, dict) and stock.get("ticker")
        }
        matched = {ticker: rows[ticker] for ticker in tickers if ticker in rows}
        log.info(
            f"MTF: {len(matched)} watchlist holding(s) matched "
            f"from {len(rows)} disclosed NSE scrip(s)."
        )
        return matched
    except Exception as exc:  # noqa: BLE001 - optional enrichment
        log.info(f"MTF feed unavailable ({type(exc).__name__}: {str(exc)[:100]}).")
        return {}


def apply_mtf(watchlist, rows):
    """Attach only matched disclosed rows; leave unmatched stocks unknown."""
    applied = 0
    for stocks in (watchlist or {}).values():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            row = (rows or {}).get(str(stock.get("ticker", "")).upper())
            if not row:
                continue
            screener = stock.setdefault("screener", {})
            if not isinstance(screener, dict):
                continue
            screener.update(row)
            applied += 1
    return applied
