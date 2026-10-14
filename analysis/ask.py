"""Answer a question asked on the dashboard: from the briefing first, then
from the news, then from what the model knows, each kept apart.

The dashboard's Ask view sends a question as an issue the owner submits;
scripts/dashboard_actions.py hands it here. A comment the owner adds to that
issue later comes here too, as a follow-up, with the exchange so far. An
answer draws on three sources and says which one each statement came from:

  * the briefing: an extract of the committed data, with what is asked about
    (the holdings and sectors the question names, or the one the page was
    open on) in full and the day's summary around it;
  * the news: headlines from a Google News search run for the question. The
    model writes the query, since it knows "Oracle Fin.Serv." as Oracle
    Financial Services and CPPLUS as the CP PLUS brand. The answer cites the
    headlines by number and lists them, with links, under the answer;
  * the model's general knowledge, as background only: what a company does,
    how a scheme works. It never supplies a figure or a recent event.

Gemini can search the web itself ("grounding with Google Search"). Its terms,
however, let a grounded answer be shown only to the person who asked, next to
Google's search suggestions, and restrict keeping or republishing it. An
answer here is a comment on a public issue, kept and shown on a public page,
so the search is run here instead, on the feed the briefing already reads.

It is a reading like every other LLM output here: marked as one, and checked
by whoever reads it against the items it cites.
"""

import datetime
import html
import json
import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The dashboard caps a question at 500 characters; a follow-up typed on
# GitHub is not capped, so this is wider.
MAX_QUESTION = 1000
MAX_HOLDINGS = 5
MAX_CONTEXT_CHARS = 60_000
# The exchange so far, newest kept first, on a follow-up.
MAX_HISTORY_CHARS = 12_000

NEWS_URL = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
NEWS_DAYS = 180
MAX_NEWS = 10
MAX_QUERY = 150

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
companies. You have three sources, and the reader must always be able to tell
which one a statement came from:

1. DATA: an extract of today's briefing, built by an automated pipeline from
   news, filings and market data. Use it first.
2. NEWS: headlines from a Google News search run for this question, numbered,
   each with its date and source. They are headlines only: say what a
   headline says, not what its article might go on to say.
3. Your general knowledge, for background the other two lack: what a company
   does, how a scheme, a contract or an industry works. Never give a figure, a
   result, an order book, a price or a recent event from memory; it may be
   out of date or wrong.

Answer in up to three parts, each opening with its heading on a line of its
own, and leave out a part you have nothing for:
**From the briefing**
**From the news**
**Background (general knowledge, not from a source here)**

- Cite what you rely on: from the DATA the headline, its date, or the figure
  and its field; from the NEWS the item's number in brackets, as [2].
- If none of the three answers the question, say so and say what is missing.
  Then give the nearest thing the sources do have, cited: revenue guidance
  where no order book is published, the last results where no forecast is.
- Describe the evidence; do not tell the investor to buy or sell.
- Thesis grades (Intact / Weakening / Broken) and their reasons come from the
  pipeline's rules. "challenged"/"supported" items and anything marked
  reader "llm" are LLM readings of headlines, less certain than a filing.
- When there is a CONVERSATION, the QUESTION follows on from it: read "it",
  "they" and "that" from it, and do not repeat what was already said.
- Plain text, at most 300 words. Short paragraphs or "- " bullets."""

_SEARCH_INSTRUCTIONS = """Plan a Google News search for the QUESTION below, asked about Indian
listed companies. Reply in two lines:
QUERY: one search that would find news answering the question: each company
the way the press names it (its full name or its brand, never a cut-off or
spaced-out abbreviation) and the few words the question is about. At most 10
words; quotes and OR are allowed.
NAMES: the names the press uses for the companies the question is about,
separated by ";", as "Aditya Infotech; CP Plus". Leave it empty for a
question about an industry, a policy or the market as a whole.
Reply NONE alone only for a question about how this dashboard works or what
its labels mean, which no news could help with."""


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
    A lender's top line is revenue and its margin a financing margin
    (providers/screener.py), and the names say so.
    """
    bank = "q_fin_margin" in sc
    sales = "revenue_cr" if bank else "sales_cr"

    def pick(pairs):
        return {
            name: sc.get(key)
            for name, key in pairs
            if sc.get(key) not in (None, "", [])
        }

    out = {
        "latest_quarter": pick(
            (
                (sales, "q_sales"),
                ("sales_change_vs_previous_quarter_pct", "qoq_sales_growth"),
                ("sales_change_vs_year_ago_quarter_pct", "revenue_yoy_pct"),
                ("operating_margin_pct", "q_opm"),
                ("operating_margin_change_pp", "opm_expansion"),
                ("financing_margin_pct", "q_fin_margin"),
                ("net_profit_cr", "q_net_profit"),
                ("eps", "q_eps"),
            )
        ),
        "quarterly_oldest_first": pick(
            (
                (sales, "sales_trend"),
                ("eps", "eps_trend"),
                ("operating_margin_pct", "quarterly_ebitda_margin"),
                ("financing_margin_pct", "fin_margin_trend"),
            )
        ),
        "annual_oldest_first_last_is_trailing_12_months": pick(
            (
                (sales, "annual_sales_trend"),
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
        "calendar": [
            {k: e.get(k) for k in ("date", "kind", "title", "detail", "source")}
            for e in (b.get("event_calendar") or {}).get("upcoming") or []
            if str(e.get("ticker", "")).upper() == ticker
        ][:6],
        "latest_results": next(
            (
                {k: v for k, v in c.items() if k not in ("name", "sector")}
                for c in (b.get("results") or {}).get("scorecards") or []
                if str(c.get("ticker", "")).upper() == ticker
            ),
            None,
        ),
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
            {
                k: p.get(k)
                for k in ("headline", "date", "status", "strength", "state", "effects")
            }
            for p in b.get("policy_impacts") or []
            if any(e.get("sector") == sector for e in p.get("effects") or [])
        ][:8],
    }


def build_context(
    question: str, src: Dict[str, Any], focus: Optional[str] = None, also: str = ""
) -> Dict[str, Any]:
    """The extract an answer is drawn from: subjects in full, the day in brief.

    ``also`` is what was asked earlier in the exchange, so a follow-up ("and
    their margins?") keeps the holdings the first question named.
    """
    b = src["briefing"]
    tickers, sectors = subjects(f"{question} {also}".strip(), src["watchlist"], focus)
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
            "quarter' rather than naming one unless a headline does; "
            "latest_results.quarter is inferred from when the result appeared. "
            "No consensus estimate exists here, so never call a result a beat "
            "or a miss."
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
            "coming_up": [
                {k: e.get(k) for k in ("date", "ticker", "kind", "title")}
                for e in ((b.get("event_calendar") or {}).get("upcoming") or [])[:15]
            ],
            "policy": [
                {
                    k: p.get(k)
                    for k in (
                        "headline",
                        "date",
                        "status",
                        "strength",
                        "state",
                        "effects",
                    )
                }
                for p in (b.get("policy_impacts") or [])[:10]
            ],
            # Governments' MoUs and pacts: soft, no measure taken yet.
            "government_partnerships": [
                {
                    k: p.get(k)
                    for k in ("headline", "date", "government", "sectors", "tickers")
                }
                for p in (b.get("policy_partnerships") or [])[:8]
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


def _conversation(history: List[Tuple[str, str]]) -> str:
    return "\n".join(
        f"{'Q' if role == 'question' else 'A'}: {text}" for role, text in history
    )


def _history(history) -> List[Tuple[str, str]]:
    """The exchange so far, oldest first, cut from the oldest end to fit."""
    turns = [
        (role, " ".join(str(text or "").split()))
        for role, text in history or []
        if role in ("question", "answer") and str(text or "").strip()
    ]
    kept: List[Tuple[str, str]] = []
    size = 0
    for role, text in reversed(turns):
        size += len(text) + 4
        if size > MAX_HISTORY_CHARS:
            break
        kept.append((role, text))
    return kept[::-1]


def _clean_query(text: str) -> Optional[str]:
    """A query as the model wrote it; None for NONE or nothing usable."""
    line = re.sub(r"^(?:search\s+)?query\s*:\s*", "", text.strip(), flags=re.I)
    line = line.strip("`* ")
    if line.strip(".").upper() == "NONE" or not re.search(r"[A-Za-z]", line):
        return None
    return line[:MAX_QUERY]


def _read_plan(reply: str) -> Optional[Dict[str, Any]]:
    """The search in the model's reply: ``{"query", "names"}``, or None.

    The reply is a QUERY line and a NAMES line; a bare query, the shape the
    first version asked for, is read as the query.
    """
    lines = [x.strip().strip("`*").strip() for x in str(reply or "").splitlines()]
    lines = [x for x in lines if x]
    fields = {}
    for line in lines:
        m = re.match(r"(QUERY|NAMES)\s*:\s*(.*)$", line, flags=re.I)
        if m:
            fields[m.group(1).upper()] = m.group(2).strip()
    query = _clean_query(fields.get("QUERY", "" if fields else " ".join(lines[:1])))
    names = []
    for name in fields.get("NAMES", "").split(";"):
        name = " ".join(name.strip(" \"'.").split())
        if len(name) >= 3 and name.upper() != "NONE" and name not in names:
            names.append(name)
    if query is None and not names:
        return None
    return {"query": query, "names": names[:3]}


def search_plan(
    question: str,
    holdings: List[Dict[str, Any]],
    history: List[Tuple[str, str]],
    transport,
) -> Optional[Dict[str, Any]]:
    """The Google News search the model plans for a question.

    ``{"query", "names"}``: its search for the question, and the names the
    press uses for the companies it is about. None when no search is worth
    running: the question is about how the dashboard works, or the model
    could not plan one. A model that cannot plan one is unlikely to answer
    either, and the answer says so.
    """
    from analysis.llm_reader import ReaderUnavailable

    parts = [_SEARCH_INSTRUCTIONS]
    if holdings:
        parts.append(
            "HOLDINGS ASKED ABOUT: " + json.dumps(holdings, ensure_ascii=False)
        )
    if history:
        # The last exchange is enough to read "their" and "it".
        parts.append("CONVERSATION:\n" + _conversation(history[-2:])[:3000])
    parts.append(f"QUESTION: {question}")
    try:
        return _read_plan(transport("\n\n".join(parts) + "\n"))
    except ReaderUnavailable:
        return None


def searches(plan: Optional[Dict[str, Any]]) -> List[str]:
    """The planned search, then the companies' names alone.

    12 Oct: "How does CP PLUS order book look like ?" was searched as
    "Aditya Infotech" "order book" and found nothing on CP PLUS's order book,
    which it does not publish, and nothing else on the company either. Its
    names alone find its recent news, which holds the nearest thing: the
    results and the revenue guidance.
    """
    if not plan:
        return []
    names = " OR ".join(f'"{n}"' for n in plan["names"])
    return list(dict.fromkeys(q for q in (plan["query"], names) if q))


def names_company(
    headline: str, names: List[str], holdings: List[Dict[str, Any]]
) -> bool:
    """Whether a headline names a company the question is about.

    By a name the model gave, as a whole word, or by the matcher the
    briefing attributes headlines with ("Dixon Tech" is Dixon Technologies).
    """
    from analysis.parsing import title_matches_company

    low = headline.lower()
    if any(
        re.search(rf"(?<![a-z0-9]){re.escape(n.lower())}(?![a-z0-9])", low)
        for n in names
    ):
        return True
    return any(
        title_matches_company(headline, h.get("ticker") or "", h.get("name") or "")
        for h in holdings
    )


def _get(url: str) -> Tuple[int, str]:
    import requests

    resp = requests.get(
        url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (india-policy-tracker)"}
    )
    return resp.status_code, resp.text


def _headline(entry: Dict[str, Any]) -> Tuple[str, str]:
    """``(headline, source)``: Google News writes "Headline - Source"."""
    title = html.unescape(re.sub(r"<[^>]+>", "", entry.get("title") or ""))
    title = " ".join(title.split())
    source = " ".join(str((entry.get("source") or {}).get("title") or "").split())
    if source and title.endswith(f" - {source}"):
        title = title[: -len(source) - 3].strip()
    elif not source and " - " in title:
        title, source = (s.strip() for s in title.rsplit(" - ", 1))
    return title, source


def fetch_news(
    queries: List[str],
    names: List[str] = (),
    holdings: List[Dict[str, Any]] = (),
    fetch=None,
    today: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """Headlines Google News finds for the searches, at most MAX_NEWS.

    The first search's headlines come first, then the next's; the kept ones
    are listed newest first. When the question names companies, a headline
    that names none of them is left out and counted: Google matches words
    anywhere in an article, and on 12 Oct eight of the ten headlines found
    for CP PLUS's order book were about other companies. Google News does
    not always honour "when:" (scraper.py met headlines weeks older than
    asked for), so age is checked here as well.

    Never raises: a search that fails is skipped, and ``error`` is set when
    every one did, so the answer goes on without news and says why.
    """
    import feedparser

    today = today or datetime.date.today()
    oldest = today - datetime.timedelta(days=NEWS_DAYS)
    news: Dict[str, Any] = {"queries": list(queries), "items": [], "left_out": 0}
    errors, seen, kept = [], set(), []
    for query in queries:
        url = NEWS_URL.format(query=urllib.parse.quote(f"{query} when:{NEWS_DAYS}d"))
        try:
            status, text = (fetch or _get)(url)
        except Exception as e:  # noqa: BLE001 - the answer goes on without news
            errors.append(type(e).__name__)
            continue
        if status != 200:
            errors.append(f"HTTP {status}")
            continue
        found = []
        for entry in feedparser.parse(text).entries:
            headline, source = _headline(entry)
            parsed = entry.get("published_parsed")
            day = datetime.date(*parsed[:3]) if parsed else None
            link = str(entry.get("link") or "")
            if (
                not headline
                or day is None
                or not oldest <= day <= today
                or not link.startswith(("https://", "http://"))
                or headline.lower() in seen
            ):
                continue
            seen.add(headline.lower())
            if names and not names_company(headline, names, holdings):
                news["left_out"] += 1
                continue
            found.append(
                {
                    "headline": headline,
                    "source": source,
                    "date": day.isoformat(),
                    "link": link,
                }
            )
        kept += sorted(found, key=lambda i: i["date"], reverse=True)
    if errors and len(errors) == len(queries):
        news["error"] = errors[0]
    news["items"] = sorted(kept[:MAX_NEWS], key=lambda i: i["date"], reverse=True)
    return news


def prompt(
    question: str,
    context: Dict[str, Any],
    news: Optional[Dict[str, Any]] = None,
    history: Optional[List[Tuple[str, str]]] = None,
) -> str:
    items = (news or {}).get("items") or []
    searched = "; ".join((news or {}).get("queries") or [])
    if items:
        found = f"NEWS (Google News searches: {searched}):\n" + "\n".join(
            f"[{n}] {i['date']} · {i['source']} · {i['headline']}"
            for n, i in enumerate(items, 1)
        )
    elif news:
        found = f"NEWS: none found (searched: {searched})"
    else:
        found = "NEWS: no search was run for this question"
    parts = [
        _INSTRUCTIONS,
        "DATA:\n" + json.dumps(context, ensure_ascii=False, default=str),
        found,
    ]
    if history:
        parts.append("CONVERSATION:\n" + _conversation(history))
    parts.append(f"QUESTION: {question}")
    return "\n\n".join(parts) + "\n"


def answer(
    question: str,
    focus: Optional[str] = None,
    transport=None,
    root: str = ROOT,
    history=None,
    fetch=None,
    today: Optional[datetime.date] = None,
) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """``(answer text, footer, news)``. Never raises: a failure is the answer.

    ``history`` is the exchange so far on a follow-up: ``(role, text)`` pairs,
    oldest first, role "question" or "answer". ``news`` is the search run
    for the answer (``queries``, ``items``, ``left_out``, and ``error`` if it
    failed), None when none was.
    """
    from analysis.llm_reader import ReaderUnavailable, default_transport

    question = " ".join(str(question or "").split())[:MAX_QUESTION]
    if not question:
        return "The question was empty.", "", None
    history = _history(history)
    src = load_sources(root)
    asked_before = " ".join(text for role, text in history if role == "question")
    context = build_context(question, src, focus, also=asked_before)
    if transport is None:
        transport, chain = default_transport(text=True)
        if transport is None:
            return f"Could not answer: {chain}.", "", None
    holdings = [
        {k: h.get(k) for k in ("ticker", "name", "sector")}
        for h in context["holdings_asked_about"]
    ]
    plan = search_plan(question, holdings, history, transport)
    names = (plan or {}).get("names") or []
    queries = searches(plan)
    news = fetch_news(queries, names, holdings, fetch, today) if queries else None
    try:
        text = transport(prompt(question, context, news, history)).strip()
    except ReaderUnavailable as e:
        return f"Could not answer this time: {e}. Ask again later.", "", None
    asked = [h["ticker"] for h in holdings]
    found = (news or {}).get("items") or []
    footer = (
        f"✦ LLM reading ({getattr(transport, 'model', None) or 'Gemini'}) of the briefing"
        + (f" dated {context['briefing_date']}" if context["briefing_date"] else "")
        + (f", drawing on {', '.join(asked)}" if asked else "")
        + (f", and of {len(found)} headline(s) from Google News" if found else "")
        + "."
    )
    if news and news.get("error"):
        footer += f" The news search failed ({news['error']})."
    elif news and not found:
        footer += (
            " The news search found no headline"
            + (f" naming {' or '.join(names)}" if names else "")
            + f" from the last {NEWS_DAYS} days."
        )
    footer += (
        " Anything under Background is the model's general knowledge, not checked"
        " against a source. Check the items it cites before relying on it."
    )
    return text or "The model returned an empty answer.", footer, news
