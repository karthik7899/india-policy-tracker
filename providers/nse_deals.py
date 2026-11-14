"""Official NSE daily bulk/block deal disclosures.

Unlike headline-derived news, these rows are exchange-published transactions.
The parser requires a tracked symbol and the exchange's client/action/quantity
fields; incomplete rows are not promoted to institutional activity.
"""

import csv
import io
from typing import Any, Dict

from logger import log

BASE = "https://nsearchives.nseindia.com/content/equities"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
}
FILES = {"bulk": "bulk.csv", "block": "block.csv"}


def _clean_key(value):
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _pick(row, *names):
    normalized = {_clean_key(k): v for k, v in row.items()}
    for name in names:
        value = normalized.get(_clean_key(name))
        if value not in (None, ""):
            return str(value).strip()
    return None


def parse_deal_csv(text: str, deal_type: str, tracked: Dict[str, str]):
    """Parse official deal rows into normalized records keyed by NSE symbol."""
    if not text or not tracked:
        return []
    out = []
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
        for raw in reader:
            row = {str(k or "").strip(): v for k, v in raw.items()}
            ticker = (_pick(row, "Symbol", "Scrip", "Trading Symbol") or "").upper()
            if ticker not in tracked:
                continue
            participant = _pick(row, "Client Name", "Client", "Name of Client")
            action = (_pick(row, "Buy/Sell", "Buy Sell", "Transaction Type") or "").upper()
            quantity_raw = _pick(row, "Quantity", "Traded Quantity", "Qty")
            price_raw = _pick(
                row, "Wtd. Avg. Price", "Weighted Average Price", "Price"
            )
            try:
                quantity = float(str(quantity_raw).replace(",", "")) if quantity_raw else None
                price = float(str(price_raw).replace(",", "")) if price_raw else None
            except (TypeError, ValueError):
                continue
            if not participant or action not in ("BUY", "SELL") or not quantity or quantity <= 0:
                continue
            if price is not None and price <= 0:
                price = None
            out.append(
                {
                    "ticker": ticker,
                    "company": tracked[ticker],
                    "headline": (
                        f"{participant} {action.lower()} {quantity:,.0f} shares "
                        f"in {tracked[ticker]} ({deal_type.lower()})"
                    ),
                    "participant": participant,
                    "buyer": participant if action == "BUY" else None,
                    "seller": participant if action == "SELL" else None,
                    "action": "Buy" if action == "BUY" else "Sell",
                    "quantity": int(quantity),
                    "price": round(price, 2) if price is not None else None,
                    "value_cr": (
                        round(quantity * price / 1e7, 3) if price is not None else None
                    ),
                    "deal_type": deal_type,
                    "source": "NSE",
                    "source_url": f"{BASE}/{FILES[deal_type.lower()]}",
                    "confidence": "exchange_disclosed",
                    "date": _pick(row, "Date", "Trade Date"),
                }
            )
    except Exception as exc:  # noqa: BLE001 - one malformed report is non-fatal
        log.info(f"NSE {deal_type} report parse skipped ({type(exc).__name__}).")
    return out


async def fetch_nse_deals_async(session, watchlist):
    """Fetch current NSE bulk and block deal files; empty files are valid."""
    tracked = {
        str(stock.get("ticker", "")).upper(): str(stock.get("name") or stock["ticker"])
        for stocks in (watchlist or {}).values()
        for stock in stocks or []
        if isinstance(stock, dict) and stock.get("ticker")
    }
    results = []
    for deal_type, filename in FILES.items():
        url = f"{BASE}/{filename}"
        try:
            async with session.get(url, headers=HEADERS, timeout=20) as response:
                if response.status != 200:
                    log.info(f"NSE {deal_type} deal file unavailable (HTTP {response.status}).")
                    continue
                body = await response.text()
            rows = parse_deal_csv(body, deal_type.title(), tracked)
            results.extend(rows)
            log.info(f"NSE {deal_type} deals: {len(rows)} tracked transaction(s).")
        except Exception as exc:  # noqa: BLE001 - optional source
            log.info(f"NSE {deal_type} deal fetch unavailable ({type(exc).__name__}).")
    return results
