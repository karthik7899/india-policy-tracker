"""Does the news contradict why we own it?

Every holding's ``catalyst`` is a one-line thesis — "Turnaround story,
completely debt-free, dominating wind turbine supply with a record order
book". analysis/thesis.py grades it from the risk signals this run computed,
which catches what those signals can see: a critical warning, a consensus
target cut. It cannot see a headline that quietly removes the reason the
stock is owned — the order the thesis counts on cancelled, the scheme it
relies on withdrawn, the debt it says is gone back on the balance sheet —
because nothing connects a headline to the words of the thesis.

This asks the LLM reader to make that connection. For each headline
attributed to a holding (the coverage audit's counted items), it answers
whether the headline contradicts a specific claim in the thesis, supports
one, or neither, and must quote both sides: the words of the thesis and the
words of the headline. Either quote not found verbatim and the answer is
downgraded to "unrelated" — the model cannot argue from outside knowledge or
paraphrase a claim the thesis does not make.

A contradiction is a prompt to review, not a verdict. It is shown as
"thesis challenged" beside the thesis health, with both quotes and the link,
and changes no score, status or warning: a single headline read by a model
is exactly the kind of evidence this pipeline does not act on unreviewed.
Scored against eval/thesis_labels.json.

Holdings whose catalyst is the rotation engine's boilerplate ("Auto-discovered
via media radar. Catalyst: Policy tailwinds in the X segment.") have no
thesis to check and are listed as such — write one to include them.
"""

import datetime
import hashlib
import json
import os
import re
import time
from typing import Any, Dict, List, Tuple

from logger import log

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "thesis_cache.json")

# Bump when the prompt or schema changes meaning; older readings are re-read.
PROMPT_VERSION = "1"

STANCES = ("contradicts", "supports", "unrelated")

# Pairs per request and new pairs per run. The first run has the whole
# window unread (~320 pairs); later runs read only what is new.
BATCH_PAIRS = 30
MAX_NEW_PER_RUN = 300
# Newest attributed headlines checked per holding. A holding in the news
# every day would otherwise take the run's whole budget.
MAX_PER_HOLDING = 15
CACHE_RETENTION_DAYS = 120

_BOILERPLATE = re.compile(r"auto-discovered via media radar", re.IGNORECASE)

_INSTRUCTIONS = """You check business news against an investor's reasons for owning a stock.

Each HOLDING below has a THESIS: why the investor owns it. Under it are
numbered headlines that mention the company. For each numbered headline return:

stance — exactly one of:
  contradicts  the headline reports a development that, if true, undermines a
               specific claim in the THESIS: an order, programme, approval,
               plant or plan the thesis relies on is lost, cancelled, delayed
               or cut; a competitor wins what the thesis expects the company
               to win; a policy or subsidy the thesis counts on is withdrawn,
               cut or reversed; the thing the thesis states (debt-free, market
               leader, asset quality, margins expanding, order book) is
               reported to be no longer true.
  supports     the headline reports concrete progress on a specific claim in
               the THESIS.
  unrelated    anything else, including: share-price moves, analyst ratings,
               targets and tips, stock lists, results that do not touch a
               claim in the thesis, routine filings, and headlines about a
               different company or person with a similar name.
claim   — the words of the THESIS the headline bears on, copied EXACTLY and
          contiguously. "" when unrelated.
because — the words of the HEADLINE that bear on the claim, copied EXACTLY and
          contiguously. "" when unrelated.

A falling share price is not evidence against a thesis, and a rising one is
not evidence for it. Judge only from the thesis and the headline; do not use
outside knowledge."""

_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "INTEGER"},
            "stance": {"type": "STRING", "enum": list(STANCES)},
            "claim": {"type": "STRING"},
            "because": {"type": "STRING"},
        },
        "required": ["id", "stance", "claim", "because"],
    },
}


def has_thesis(catalyst: Any) -> bool:
    """A written thesis, as opposed to the rotation engine's placeholder."""
    text = str(catalyst or "").strip()
    return bool(text) and not _BOILERPLATE.search(text)


def pair_key(ticker: str, thesis: str, headline: str) -> str:
    """Cache key for one reading. The thesis is part of it, so rewriting a
    thesis re-reads its news against the new words."""
    norm = "|".join(
        re.sub(r"\s+", " ", str(x or "").strip().lower())
        for x in (ticker, thesis, headline)
    )
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def _norm(text: str) -> str:
    """Lower-case, straight quotes and dashes, single spaces, no end
    punctuation — so a faithful quote is not refused over typography."""
    s = str(text or "").lower()
    s = s.translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'}))
    s = re.sub(r"[–—]", "-", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,;:'\"")


def ground(headline: str, thesis: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """Keep a stance only when both quotes are verbatim.

    A stance whose ``because`` is not in the headline, or whose ``claim`` is
    not in the thesis, is the model reasoning rather than reading, and is
    downgraded to "unrelated" — the weakest answer. ``downgraded`` records
    what it said, so the eval can tell grounding failures from judgement.
    """
    stance = raw.get("stance")
    if stance not in STANCES:
        stance = "unrelated"
    claim = re.sub(r"\s+", " ", str(raw.get("claim") or "")).strip(" .,;:")
    because = re.sub(r"\s+", " ", str(raw.get("because") or "")).strip(" .,;:")
    out: Dict[str, Any] = {"stance": stance, "claim": "", "because": ""}
    if stance == "unrelated":
        return out
    if (
        _norm(claim)
        and _norm(because)
        and _norm(claim) in _norm(thesis)
        and _norm(because) in _norm(headline)
    ):
        out.update(claim=claim, because=because)
        return out
    return {"stance": "unrelated", "claim": "", "because": "", "downgraded": stance}


def thesis_pairs(
    watchlist: Dict[str, Any], coverage: Dict[str, List[Dict[str, Any]]]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """``(pairs, no_thesis)``: the headlines to check, and the holdings skipped.

    A pair is one counted coverage item for a holding with a written thesis,
    minus routine disclosure (analysis/headline_text.classify), newest first
    and at most MAX_PER_HOLDING per holding.
    """
    from analysis.event_evidence import article_date
    from analysis.headline_text import classify

    pairs: List[Dict[str, Any]] = []
    no_thesis: List[str] = []
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        for stock in stocks or []:
            if not isinstance(stock, dict) or not stock.get("ticker"):
                continue
            ticker = str(stock["ticker"]).upper()
            thesis = str(stock.get("catalyst") or "").strip()
            if not has_thesis(thesis):
                no_thesis.append(ticker)
                continue
            items = [
                i
                for i in (coverage or {}).get(ticker) or []
                if isinstance(i, dict)
                and i.get("status") == "counted"
                and i.get("headline")
                and classify(i["headline"]) != "routine"
            ]
            items.sort(key=lambda i: article_date(i.get("date")) or "", reverse=True)
            for item in items[:MAX_PER_HOLDING]:
                pairs.append(
                    {
                        "ticker": ticker,
                        "name": stock.get("name") or ticker,
                        "sector": sector,
                        "thesis": thesis,
                        "headline": item["headline"],
                        "date": article_date(item.get("date")) or "",
                        **(
                            {"link": item["source_url"]}
                            if item.get("source_url")
                            else {}
                        ),
                        **(
                            {"source": item["source_label"]}
                            if item.get("source_label")
                            else {}
                        ),
                    }
                )
    return pairs, sorted(set(no_thesis))


def _prompt(batch: List[Tuple[int, Dict[str, Any]]]) -> str:
    lines, current = [], None
    for i, pair in batch:
        if pair["ticker"] != current:
            current = pair["ticker"]
            lines.append(f"\nHOLDING: {pair['name']} ({pair['ticker']})")
            lines.append(f"THESIS: {pair['thesis']}")
        lines.append(f"  {i}: {pair['headline']}")
    return (
        f"{_INSTRUCTIONS}\n\nReturn a JSON array, one object per numbered "
        f"headline.\n" + "\n".join(lines)
    )


def read_pairs(
    pairs: List[Dict[str, Any]],
    transport=None,
    cache_path: str = CACHE_PATH,
    max_new: int = MAX_NEW_PER_RUN,
    today: str = "",
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Readings keyed by pair_key — cached ones free, new ones fetched.

    Same contract as llm_reader.read_headlines: never raises, skips cleanly
    without a key or on an API failure, and says why in ``status``.
    """
    from analysis.llm_reader import (
        ReaderUnavailable,
        default_transport,
        load_cache,
        save_cache,
    )

    today = today or datetime.date.today().isoformat()
    status = {"cached": 0, "read": 0, "pending": 0, "skipped": ""}
    readings: Dict[str, Dict[str, Any]] = {}
    entries = load_cache(cache_path)
    if entries is None:
        status["skipped"] = "cache unreadable"
        return readings, status

    todo, seen = [], set()
    for pair in pairs or []:
        key = pair_key(pair["ticker"], pair["thesis"], pair["headline"])
        if key in seen:
            continue
        seen.add(key)
        entry = entries.get(key)
        if entry and entry.get("v") == PROMPT_VERSION:
            readings[key] = entry["reading"]
            entry["seen"] = today
            status["cached"] += 1
        else:
            todo.append((key, pair))

    if transport is None:
        transport, detail = default_transport(_SCHEMA)
        if transport is None:
            status["skipped"] = detail
            status["pending"] = len(todo)
            return readings, status

    changed = False
    batch_todo = todo[:max_new]
    status["pending"] = len(todo) - len(batch_todo)
    try:
        for start in range(0, len(batch_todo), BATCH_PAIRS):
            chunk = batch_todo[start : start + BATCH_PAIRS]
            text = transport(_prompt([(i, p) for i, (_, p) in enumerate(chunk)]))
            try:
                answers = json.loads(text)
            except ValueError:
                log.warning("Thesis check: a batch returned unparseable JSON.")
                status["pending"] += len(chunk)
                continue
            by_id = {a.get("id"): a for a in answers if isinstance(a, dict)}
            for i, (key, pair) in enumerate(chunk):
                raw = by_id.get(i)
                if raw is None:
                    status["pending"] += 1
                    continue
                reading = ground(pair["headline"], pair["thesis"], raw)
                readings[key] = reading
                served_by = getattr(transport, "model", None)
                entries[key] = {
                    "v": PROMPT_VERSION,
                    "ticker": pair["ticker"],
                    "headline": pair["headline"][:200],
                    "reading": reading,
                    "seen": today,
                    **({"model": served_by} if served_by else {}),
                }
                status["read"] += 1
                changed = True
            if start + BATCH_PAIRS < len(batch_todo):
                time.sleep(1.0)
    except ReaderUnavailable as e:
        status["skipped"] = str(e)
        status["pending"] = len(todo) - status["read"]
    if getattr(transport, "model", None):
        status["model"] = transport.model

    cutoff = (
        datetime.date.fromisoformat(today)
        - datetime.timedelta(days=CACHE_RETENTION_DAYS)
    ).isoformat()
    stale = [k for k, v in entries.items() if str(v.get("seen", "")) < cutoff]
    for k in stale:
        del entries[k]
    if changed or stale or status["cached"]:
        save_cache(entries, cache_path, PROMPT_VERSION)
    return readings, status


def summarise(
    pairs: List[Dict[str, Any]],
    readings: Dict[str, Dict[str, Any]],
    no_thesis: List[str] = (),
) -> Dict[str, Any]:
    """Per-holding results for the payload, email and dashboard.

    ``{"holdings": {ticker: {...}}, "no_thesis": [...], "challenged": n}``.
    Each holding lists the headlines that challenge or support its thesis,
    with both quotes, and how many of its headlines were read. A holding
    with nothing read is still listed, so "no challenge" and "not checked"
    stay different statements.
    """
    holdings: Dict[str, Dict[str, Any]] = {}
    for pair in pairs or []:
        row = holdings.setdefault(
            pair["ticker"],
            {
                "ticker": pair["ticker"],
                "name": pair["name"],
                "sector": pair["sector"],
                "thesis": pair["thesis"],
                "challenged": [],
                "supported": [],
                "read": 0,
                "unread": 0,
            },
        )
        reading = readings.get(
            pair_key(pair["ticker"], pair["thesis"], pair["headline"])
        )
        if reading is None:
            row["unread"] += 1
            continue
        row["read"] += 1
        if reading["stance"] == "unrelated":
            continue
        item = {
            "headline": pair["headline"],
            "claim": reading["claim"],
            "because": reading["because"],
            "date": pair.get("date") or "",
            **({"link": pair["link"]} if pair.get("link") else {}),
            **({"source": pair["source"]} if pair.get("source") else {}),
            "reader": "llm",
        }
        key = "challenged" if reading["stance"] == "contradicts" else "supported"
        row[key].append(item)
    for row in holdings.values():
        for key in ("challenged", "supported"):
            row[key].sort(key=lambda i: i["date"], reverse=True)
    return {
        "holdings": holdings,
        "no_thesis": list(no_thesis),
        "challenged": sum(1 for r in holdings.values() if r["challenged"]),
    }


def annotate_health(health: Dict[str, Any], result: Dict[str, Any]) -> int:
    """Put the number of challenging headlines on each thesis_health row.

    A count beside the status, never a change to it. Returns how many rows
    were annotated.
    """
    n = 0
    for ticker, row in (result or {}).get("holdings", {}).items():
        target = (health or {}).get(ticker)
        if target is not None and row.get("challenged"):
            target["challenges"] = len(row["challenged"])
            n += 1
    return n


def run_thesis_check(
    watchlist: Dict[str, Any], coverage: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """The whole pass, for main.py. Never raises."""
    try:
        pairs, no_thesis = thesis_pairs(watchlist, coverage)
        readings, status = read_pairs(pairs)
        result = summarise(pairs, readings, no_thesis)
        result["status"] = status
        log.info(
            f"Thesis check: {len(pairs)} headline(s) for "
            f"{len(result['holdings'])} holding(s) with a written thesis — "
            f"{status['read']} read, {status['cached']} cached, "
            f"{status['pending']} pending"
            + (f" ({status['skipped']})" if status["skipped"] else "")
            + f"; {result['challenged']} holding(s) challenged; "
            f"{len(no_thesis)} holding(s) have no written thesis."
        )
        return result
    except Exception as e:  # noqa: BLE001 - an enrichment must never break a run
        log.warning(f"Thesis check failed safely: {e!r}")
        return {"holdings": {}, "no_thesis": [], "challenged": 0}
