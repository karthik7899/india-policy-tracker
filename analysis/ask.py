"""Answer a question asked on the dashboard, from the briefing's own data.

The dashboard's Ask view sends a question as an issue the owner submits;
scripts/dashboard_actions.py hands it here. The answer comes from the LLM
reading an extract of the committed briefing, never the open web: what is
asked about (the holdings and sectors the question names, or the one the
page was open on) in full, and the day's summary around it. The model is
told to answer from that extract only, to cite what it used, and to say
what the extract does not contain rather than fill the gap.

It is a reading like every other LLM output here: marked as one, and checked
by whoever reads it against the items it cites.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_QUESTION = 500
MAX_HOLDINGS = 5
MAX_CONTEXT_CHARS = 60_000

# Words in sector names too ordinary to mean the sector when a question uses
# them: "what data is there" is not about data centres.
_GENERIC_SECTOR_WORDS = {
    "and",
    "big",
    "cap",
    "capital",
    "center",
    "centre",
    "data",
    "equipment",
    "heavy",
    "industries",
    "industrial",
    "support",
    "security",
    "energy",
}

_INSTRUCTIONS = """You answer questions about an investor's watchlist of Indian listed
companies. Answer ONLY from the DATA below: an extract of today's briefing,
built by an automated pipeline from news, filings and market data.

- Cite what you rely on: the headline, its date, or the figure and its field.
- If the DATA does not answer the question, say so and say what is missing.
  Do not fill the gap from general knowledge.
- Describe the evidence; do not tell the investor to buy or sell.
- Thesis grades (Intact / Weakening / Broken) and their reasons come from the
  pipeline's rules. "challenged"/"supported" items and anything marked
  reader "llm" are LLM readings of headlines, less certain than a filing.
- Plain text, at most 250 words. Short paragraphs or "- " bullets."""


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 4 and word.endswith("s") else word


def _load(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def load_sources(root: str = ROOT) -> Dict[str, Any]:
    """The committed data an answer is drawn from."""
    history = _load(os.path.join(root, "history.json")) or {}
    digest = _load(os.path.join(root, "data", "company_digest.json")) or {}
    graph = _load(os.path.join(root, "entity_graph.json")) or {}
    return {
        "briefing": history.get("briefing") or {},
        "watchlist": _load(os.path.join(root, "watchlist.json")) or {},
        "digest": digest.get("value") if isinstance(digest, dict) else None,
        "edges": graph.get("edges") or [],
        "root": root,
    }


def _holdings(watchlist: Dict[str, Any]) -> List[Tuple[str, str, Dict[str, Any]]]:
    return [
        (sector, str(s.get("ticker", "")).upper(), s)
        for sector, stocks in (watchlist or {}).items()
        if sector != "macro_indicators" and isinstance(stocks, list)
        for s in stocks
        if isinstance(s, dict) and s.get("ticker")
    ]


def subjects(
    question: str, watchlist: Dict[str, Any], focus: Optional[str] = None
) -> Tuple[List[str], List[str]]:
    """The holdings and sectors a question is about: ``(tickers, sectors)``.

    A ticker counts written in any case ("syrma"); a company by its name,
    with the same guards that keep "IBM CEO Arvind Krishna" off Arvind Ltd;
    a sector by its label or key. The page the question was asked from
    comes first.
    """
    from analysis.parsing import title_matches_company
    from config import SECTOR_METADATA

    words = set(re.findall(r"[a-z0-9&]+", question.lower()))
    tickers: List[str] = []
    if focus:
        tickers.append(str(focus).upper())
    for _, ticker, stock in _holdings(watchlist):
        if ticker in tickers:
            continue
        # A ticker is often typed in lower case ("why is syrma broken"), which
        # the matcher reads as an ordinary word. Written back in capitals it
        # still faces the matcher's guards, so "CEO Arvind Krishna" stays a
        # person and not Arvind Ltd.
        typed = ticker.lower() in words and title_matches_company(
            re.sub(rf"\b{re.escape(ticker)}\b", ticker, question, flags=re.I),
            ticker,
            "",
        )
        if typed or title_matches_company(question, "", stock.get("name") or ""):
            tickers.append(ticker)
    # Compared without a plural "s": "semiconductor" asks about the
    # Semiconductors & Equipment sector.
    stems = {_stem(w) for w in words}
    generic = {_stem(w) for w in _GENERIC_SECTOR_WORDS}
    sectors = []
    for key, meta in SECTOR_METADATA.items():
        if key == "macro_indicators":
            continue
        label = str((meta or {}).get("label") or "")
        names = {
            _stem(w) for w in re.findall(r"[a-z0-9]+", f"{label} {key}".lower())
        } - generic
        if names & stems:
            sectors.append(key)
    held = {t for _, t, _ in _holdings(watchlist)}
    return [t for t in tickers if t in held][:MAX_HOLDINGS], sectors


def _figures(stock: Dict[str, Any], sc: Dict[str, Any]) -> Dict[str, Any]:
    """The company's reported numbers, under names that say what they are.

    The first live question ("How does this quarter results look like",
    asked of Apollo Hospitals) was answered "the data does not contain the
    quarterly results" while the pipeline held eight quarters of them: only
    P/E, ROCE, ROE and market cap were passed on. Keys are renamed rather than
    passed through because "quarterly_revenue_growth" holds sales, not growth.
    """

    def pick(pairs):
        return {
            name: sc.get(key)
            for name, key in pairs
            if sc.get(key) not in (None, "", [])
        }

    out = {
        "latest_quarter": pick(
            (
                ("sales_cr", "q_sales"),
                ("sales_change_vs_previous_quarter_pct", "qoq_sales_growth"),
                ("sales_change_vs_year_ago_quarter_pct", "revenue_yoy_pct"),
                ("operating_margin_pct", "q_opm"),
                ("operating_margin_change_pp", "opm_expansion"),
                ("net_profit_cr", "q_net_profit"),
                ("eps", "q_eps"),
            )
        ),
        "quarterly_oldest_first": pick(
            (
                ("sales_cr", "sales_trend"),
                ("eps", "eps_trend"),
                ("operating_margin_pct", "quarterly_ebitda_margin"),
            )
        ),
        "annual_oldest_first_last_is_trailing_12_months": pick(
            (
                ("sales_cr", "annual_sales_trend"),
                ("eps", "annual_eps_trend"),
                ("operating_margin_pct", "operating_margin_trend"),
                ("debt_cr", "debt_trend"),
                ("operating_cash_flow_cr", "cash_flow_trend"),
                ("roce_pct", "roce_trend"),
            )
        ),
        "growth": {
            **pick(
                (
                    ("sales_trailing_12_months_pct", "revenue_ttm_growth_pct"),
                    ("sales_multi_year_cagr_pct", "revenue_cagr_pct"),
                    ("eps_trailing_12_months", "ttm_eps"),
                )
            ),
            **{
                name: stock.get(key)
                for name, key in (
                    ("revenue_growth_yahoo", "revenue_growth"),
                    ("earnings_growth_yahoo", "earnings_growth"),
                )
                if stock.get(key)
            },
        },
        "shareholding_pct": pick(
            (
                ("promoter", "promoter_pct"),
                ("promoter_change_pp", "promoter_change"),
                ("fii", "fii_pct"),
                ("fii_change_pp", "fii_change"),
                ("dii", "dii_pct"),
                ("dii_change_pp", "dii_change"),
            )
        ),
        "valuation": pick(
            (
                ("pe_ratio", "pe_ratio"),
                ("industry_pe", "industry_pe"),
                ("pe_vs_peers", "pe_vs_peers"),
                ("roce_pct", "roce"),
                ("roe_pct", "roe"),
                ("market_cap_cr", "market_cap"),
                ("graham_intrinsic_value", "graham_intrinsic_value"),
                ("moat", "moat_status"),
                ("alerts", "valuation_alerts"),
                ("week52_low", "week52_low"),
                ("week52_high", "week52_high"),
            )
        ),
    }
    return {k: v for k, v in out.items() if v}


def _holding_extract(ticker: str, src: Dict[str, Any]) -> Dict[str, Any]:
    b = src["briefing"]
    sector, stock = next(
        ((sec, s) for sec, t, s in _holdings(src["watchlist"]) if t == ticker),
        (None, {}),
    )
    sc = stock.get("screener") if isinstance(stock.get("screener"), dict) else {}
    card = next(
        (
            c
            for c in (src.get("digest") or {}).get("companies") or []
            if str(c.get("ticker", "")).upper() == ticker
        ),
        {},
    )
    check = ((b.get("thesis_check") or {}).get("holdings") or {}).get(ticker) or {}
    prices = card.get("prices") or []
    coverage = _load(os.path.join(src["root"], "news", f"{ticker}.json")) or {}
    return {
        "ticker": ticker,
        "name": stock.get("name"),
        "sector": sector,
        "thesis": stock.get("catalyst"),
        "price": stock.get("price"),
        "target": stock.get("target"),
        "upside": stock.get("growth_pct"),
        "rating": stock.get("rating"),
        "reported": _figures(stock, sc),
        "thesis_health": (b.get("thesis_health") or {}).get(ticker),
        "thesis_check": {
            "challenged": (check.get("challenged") or [])[:5],
            "supported": (check.get("supported") or [])[:5],
        },
        "price_26_weeks": (
            {"first": prices[0], "last": prices[-1]} if len(prices) >= 2 else None
        ),
        "recent_activity": (card.get("activity") or [])[:8],
        "policies": (card.get("policies") or [])[:6],
        "warnings": [
            {
                k: w.get(k)
                for k in ("severity", "direction", "category", "signal", "status")
            }
            for w in b.get("early_warnings") or []
            if str(w.get("ticker", "")).upper() == ticker
        ][:10],
        "read_throughs": [
            {k: r.get(k) for k in ("trigger", "date", "direction", "chain")}
            for r in b.get("read_throughs") or []
            if ticker in [str(t).upper() for t in r.get("tickers") or []]
        ][:5],
        "links": [
            {k: e.get(k) for k in ("src", "dst", "type", "evidence")}
            for e in src.get("edges") or []
            if ticker in (str(e.get("src", "")).upper(), str(e.get("dst", "")).upper())
        ][:10],
        "coverage": [
            {
                "headline": c.get("headline"),
                "date": c.get("date"),
                "source": c.get("source_label"),
            }
            for c in (coverage.get("items") or [])
            if (c.get("status") or "counted") == "counted"
        ][:10],
    }


def _sector_extract(sector: str, src: Dict[str, Any]) -> Dict[str, Any]:
    b = src["briefing"]
    health = b.get("thesis_health") or {}
    return {
        "sector": sector,
        "holdings": [
            {
                "ticker": t,
                "name": s.get("name"),
                "thesis": (health.get(t) or {}).get("status"),
            }
            for sec, t, s in _holdings(src["watchlist"])
            if sec == sector
        ],
        "policy_balance": (b.get("policy_balance") or {}).get(sector),
        "policies": [
            {k: p.get(k) for k in ("headline", "date", "status", "state", "effects")}
            for p in b.get("policy_impacts") or []
            if any(e.get("sector") == sector for e in p.get("effects") or [])
        ][:8],
    }


def build_context(
    question: str, src: Dict[str, Any], focus: Optional[str] = None
) -> Dict[str, Any]:
    """The extract an answer is drawn from: subjects in full, the day in brief."""
    b = src["briefing"]
    tickers, sectors = subjects(question, src["watchlist"], focus)
    health = b.get("thesis_health") or {}
    counts: Dict[str, int] = {}
    for row in health.values():
        counts[row.get("status") or "?"] = counts.get(row.get("status") or "?", 0) + 1
    changes = b.get("changes") or {}
    context = {
        "how_to_read": (
            "Reported figures are as Screener.in publishes them: rupees crore "
            "(_cr) for sales, profit, debt and cash flow, rupees for EPS, "
            "percent (_pct) and percentage points (_pp) for margins and growth. "
            "Series run oldest to latest: the last quarterly value is the "
            "latest reported quarter, the last annual value the trailing twelve "
            "months. Quarter names are not recorded, so say 'the latest "
            "quarter' rather than naming one unless a headline does."
        ),
        "briefing_date": str(
            (src.get("digest") or {}).get("as_of")
            or (b.get("track_record") or {}).get("as_of")
            or ""
        ),
        "holdings_asked_about": [_holding_extract(t, src) for t in tickers],
        "sectors_asked_about": [_sector_extract(s, src) for s in sectors],
        "today": {
            "thesis_grades": counts,
            "broken": sorted(
                t for t, r in health.items() if r.get("status") == "Broken"
            ),
            "since_last_run": changes.get("items"),
            "track_record": (b.get("track_record") or {}).get("summary"),
            "policy": [
                {
                    k: p.get(k)
                    for k in ("headline", "date", "status", "state", "effects")
                }
                for p in (b.get("policy_impacts") or [])[:10]
            ],
        },
    }
    if not tickers and not sectors:
        context["all_holdings"] = [
            {"ticker": t, "sector": sec, "thesis": (health.get(t) or {}).get("status")}
            for sec, t, _ in _holdings(src["watchlist"])
        ]
    # Trim from the least specific end until it fits.
    text = json.dumps(context, ensure_ascii=False, default=str)
    for key in ("all_holdings", "today"):
        if len(text) <= MAX_CONTEXT_CHARS:
            break
        context.pop(key, None)
        text = json.dumps(context, ensure_ascii=False, default=str)
    while len(text) > MAX_CONTEXT_CHARS and context["holdings_asked_about"]:
        context["holdings_asked_about"].pop()
        text = json.dumps(context, ensure_ascii=False, default=str)
    return context


def prompt(question: str, context: Dict[str, Any]) -> str:
    return (
        f"{_INSTRUCTIONS}\n\nDATA:\n"
        + json.dumps(context, ensure_ascii=False, default=str)
        + f"\n\nQUESTION: {question}\n"
    )


def answer(
    question: str, focus: Optional[str] = None, transport=None, root: str = ROOT
) -> Tuple[str, str]:
    """``(answer text, footer)``. Never raises: a failure is the answer."""
    from analysis.llm_reader import ReaderUnavailable, default_transport

    question = " ".join(str(question or "").split())[:MAX_QUESTION]
    if not question:
        return "The question was empty.", ""
    src = load_sources(root)
    context = build_context(question, src, focus)
    if transport is None:
        transport, chain = default_transport(text=True)
        if transport is None:
            return f"Could not answer: {chain}.", ""
    try:
        text = transport(prompt(question, context)).strip()
    except ReaderUnavailable as e:
        return f"Could not answer this time: {e}. Ask again later.", ""
    asked = [h["ticker"] for h in context["holdings_asked_about"]]
    footer = (
        f"✦ LLM reading ({getattr(transport, 'model', None) or 'Gemini'}) of the briefing"
        + (f" dated {context['briefing_date']}" if context["briefing_date"] else "")
        + (f", drawing on {', '.join(asked)}" if asked else "")
        + ". Check the items it cites before relying on it."
    )
    return text or "The model returned an empty answer.", footer
