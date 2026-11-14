"""Source-grounded, cached company research briefs.

This optional synthesis layer uses evidence already collected by the pipeline.
It never changes deterministic scores, warnings, thesis health or rankings.
Every returned source reference is copied from the input digest.
"""

import datetime
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

from analysis.reader_runtime import ReaderUnavailable, default_transport
from logger import log
from utils import atomic_write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "research_cache.json")
PROMPT_VERSION = "1"
DEFAULT_MAX_NEW = 4
MAX_EVIDENCE = 6
MAX_TEXT = 700

_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "ticker": {"type": "STRING"},
            "business_impact": {"type": "STRING"},
            "market_readthrough": {"type": "STRING"},
            "opportunity": {"type": "STRING"},
            "risks": {"type": "STRING"},
            "thesis_view": {"type": "STRING"},
            "evidence_refs": {"type": "ARRAY", "items": {"type": "INTEGER"}},
        },
        "required": [
            "ticker",
            "business_impact",
            "market_readthrough",
            "opportunity",
            "risks",
            "thesis_view",
            "evidence_refs",
        ],
    },
}


def _load_cache(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as handle:
            value = json.load(handle)
        if not isinstance(value, dict) or not isinstance(value.get("entries"), dict):
            return None
        return value
    except FileNotFoundError:
        return {"format": 1, "entries": {}}
    except (OSError, ValueError, TypeError):
        return None


def _fingerprint(company: Dict[str, Any], stock: Dict[str, Any]) -> str:
    source = {
        "version": PROMPT_VERSION,
        "company": company,
        "financials": {
            key: stock.get(key)
            for key in (
                "price",
                "revenue_growth",
                "growth_pct",
                "pe_ratio",
                "market_cap",
                "score",
                "screener",
            )
            if stock.get(key) is not None
        },
    }
    raw = json.dumps(source, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _evidence(company: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    groups = (
        ("company_activity", company.get("activity") or []),
        ("policy", company.get("policies") or []),
        ("brokerage_call", company.get("calls") or []),
        ("thesis_challenge", company.get("challenges") or []),
    )
    for kind, items in groups:
        for item in items:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("headline") or ""
            if not text:
                continue
            row = {
                "type": kind,
                "date": str(item.get("date") or ""),
                "text": str(text)[:MAX_TEXT],
            }
            for field in ("link", "source", "direction", "stance"):
                if item.get(field):
                    row[field] = item[field]
            rows.append(row)
    return rows[:MAX_EVIDENCE]


def _four_week_return(company: Dict[str, Any]) -> Optional[float]:
    prices = company.get("prices")
    if not isinstance(prices, list) or len(prices) < 2:
        return None

    def close(row):
        try:
            value = row[1] if isinstance(row, (list, tuple)) else None
            number = float(value)
            return number if number > 0 else None
        except (TypeError, ValueError, IndexError):
            return None

    end = close(prices[-1])
    base = close(prices[max(0, len(prices) - 1 - 4)])
    if end is None or base is None:
        return None
    return round((end / base - 1) * 100, 2)


def _company_input(company: Dict[str, Any], stock: Dict[str, Any]) -> Dict[str, Any]:
    screener = stock.get("screener") if isinstance(stock.get("screener"), dict) else {}
    metrics = {}
    keys = (
        "price",
        "revenue_growth",
        "growth_pct",
        "pe_ratio",
        "market_cap",
        "roce",
        "roe",
        "debt_to_equity",
        "operating_margin",
        "fii_change",
        "dii_change",
        "promoter_change",
        "mtf_pct",
        "mtf",
    )
    for key in keys:
        value = stock.get(key, screener.get(key))
        if value is not None and value != "":
            metrics[key] = value
    return {
        "ticker": company.get("ticker"),
        "name": company.get("name"),
        "sector": company.get("sector"),
        "thesis": company.get("thesis") or "",
        "thesis_status": company.get("thesis_status") or "not available",
        "metrics": metrics,
        "market_reaction_4w_pct": _four_week_return(company),
        "activity": _evidence(company),
        "policy_net": company.get("policy_net"),
        "activity_count": company.get("activity_count", 0),
    }


def _prompt(companies: List[Dict[str, Any]]) -> str:
    instructions = (
        "You are an equity research assistant reviewing Indian listed companies. "
        "Use only supplied company metrics and evidence. Do not browse, infer "
        "missing figures, invent events, or give buy/sell/target-price advice. "
        "Separate business impact from short-term share-price reaction; use the supplied four-week price return only for market reaction. If "
        "evidence is insufficient, say so plainly. Treat policy as a tailwind "
        "only when its supplied direction supports that sector/company. Thesis "
        "view must compare evidence with the supplied thesis and status. Keep "
        "each field to 1-3 concise sentences. evidence_refs must contain only "
        "zero-based indices of supplied activity entries that support the brief. "
        "Return one object per ticker and no extra prose.\nINPUT:\n"
    )
    return instructions + json.dumps(companies, ensure_ascii=False, default=str)


def _clean(raw: Any, inputs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if isinstance(raw, dict):
        raw = raw.get("companies", [])
    if not isinstance(raw, list):
        raise ValueError("research response is not an array")
    out = {}
    fields = (
        "business_impact",
        "market_readthrough",
        "opportunity",
        "risks",
        "thesis_view",
    )
    for item in raw:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").upper()
        source = inputs.get(ticker)
        if not source:
            continue
        evidence = source["activity"]
        refs = []
        for index in item.get("evidence_refs") or []:
            if (
                isinstance(index, int)
                and 0 <= index < len(evidence)
                and index not in refs
            ):
                refs.append(index)
        row = {
            "ticker": ticker,
            "name": source["name"],
            "evidence": [evidence[i] for i in refs],
        }
        for field in fields:
            value = str(item.get(field) or "").strip()
            row[field] = value[:700] if value else "Insufficient evidence in this run."
        row["generated_by"] = "Gemini"
        row["evidence_count"] = len(refs)
        out[ticker] = row
    return out


def build_company_research(
    watchlist: Dict[str, Any],
    digest: Dict[str, Any],
    today: str = "",
    cache_path: str = CACHE_PATH,
    max_new: Optional[int] = None,
    transport=None,
) -> Dict[str, Any]:
    """Return cached and newly generated briefs, never failing the core pipeline."""
    today = today or datetime.date.today().isoformat()
    try:
        cache = _load_cache(cache_path)
        if cache is None:
            return {
                "as_of": today,
                "companies": {},
                "status": {
                    "cached": 0,
                    "read": 0,
                    "pending": 0,
                    "skipped": "research cache unreadable",
                },
            }
        stocks = {
            str(stock.get("ticker") or "").upper(): stock
            for sector, rows in (watchlist or {}).items()
            if sector != "macro_indicators" and isinstance(rows, list)
            for stock in rows
            if isinstance(stock, dict) and stock.get("ticker")
        }
        inputs = {}
        for company in (digest or {}).get("companies") or []:
            ticker = str(company.get("ticker") or "").upper()
            stock = stocks.get(ticker)
            if not ticker or not stock:
                continue
            payload = _company_input(company, stock)
            fingerprint = _fingerprint(company, stock)
            inputs[ticker] = (payload, fingerprint)

        entries = cache["entries"]
        result = {}
        todo = []
        for ticker, (payload, fingerprint) in inputs.items():
            entry = entries.get(ticker) or {}
            if entry.get("fingerprint") == fingerprint and isinstance(
                entry.get("brief"), dict
            ):
                result[ticker] = entry["brief"]
            else:
                todo.append((ticker, payload, fingerprint))
        todo.sort(
            key=lambda row: (
                (
                    str(row[1].get("activity", [{}])[0].get("date", ""))
                    if row[1].get("activity")
                    else ""
                ),
                row[0],
            ),
            reverse=True,
        )

        limit = max_new
        if limit is None:
            try:
                limit = int(
                    os.environ.get("GEMINI_RESEARCH_MAX_COMPANIES", DEFAULT_MAX_NEW)
                )
            except (TypeError, ValueError):
                limit = DEFAULT_MAX_NEW
        limit = max(0, min(limit, 12))
        selected = todo[:limit]
        status = {
            "cached": len(result),
            "read": 0,
            "pending": len(todo),
            "skipped": "",
        }
        if not selected:
            return {"as_of": today, "companies": result, "status": status}

        if transport is None:
            transport, detail = default_transport(_SCHEMA, reader="research")
            if transport is None:
                status["skipped"] = detail
                return {"as_of": today, "companies": result, "status": status}

        request_inputs = {ticker: payload for ticker, payload, _ in selected}
        raw = transport(_prompt([payload for _, payload, _ in selected]))
        cleaned = _clean(json.loads(raw), request_inputs)
        for ticker, _, fingerprint in selected:
            brief = cleaned.get(ticker)
            if not brief:
                continue
            result[ticker] = brief
            entries[ticker] = {
                "fingerprint": fingerprint,
                "updated": today,
                "brief": brief,
            }
            status["read"] += 1
        status["pending"] = max(0, len(todo) - status["read"])
        try:
            atomic_write_json(cache, cache_path)
        except OSError as error:
            log.warning(f"Company research cache could not be saved: {error!r}")
        return {"as_of": today, "companies": result, "status": status}
    except (ReaderUnavailable, ValueError, TypeError, KeyError) as error:
        log.warning(f"Company research skipped safely: {error!r}")
        return {
            "as_of": today,
            "companies": {},
            "status": {
                "cached": 0,
                "read": 0,
                "pending": 0,
                "skipped": str(error),
            },
        }
    except Exception as error:  # enrichment must never fail the daily pipeline
        log.warning(f"Company research failed safely: {error!r}")
        return {
            "as_of": today,
            "companies": {},
            "status": {
                "cached": 0,
                "read": 0,
                "pending": 0,
                "skipped": "unexpected research error",
            },
        }
