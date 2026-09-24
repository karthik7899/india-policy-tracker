"""A second reader for market events: an LLM, checked against the rules.

WHY. The rules are precise and blind to anything their vocabulary does not
anticipate. Scored against eval/event_labels.json they catch 83% of labelled
holdout events at 100% precision, and what they miss is the long tail no
phrase list reaches: "Persistent Systems Secures 83.25% Nagarro Ownership",
"BPCL exits Numaligarh Refinery". A language model reads those easily. It
also invents companies, misreads whose number is whose, and answers the same
question differently tomorrow. So it is used as a second reader, never as the
classifier, and every one of those failure modes has a guard here:

  * Read once, remembered. Each headline is sent at most once per prompt
    version; the answer lives in llm_cache.json, committed like the ISIN
    master. Runs are therefore reproducible, cost only new headlines, and a
    reading cannot flip between days — which matters, because warnings are
    graded "new" by comparing against yesterday.
  * Grounded. Every company name and amount returned must appear verbatim in
    the headline, or it is discarded. The model cannot introduce an entity.
  * No arithmetic, no tickers. The model names parties as written; the
    existing matcher decides which holding each one is, and
    analysis/materiality.py still does the sizing.
  * Agreement is the confidence. The model's own confidence is not a
    probability and is not asked for. See reconcile().
  * Optional. With no GEMINI_API_KEY, or on any API failure, the pass is
    skipped, the log says so, and the rules carry the run alone.
"""

import datetime
import hashlib
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from logger import log
from utils import atomic_write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "llm_cache.json")

# Bump when the prompt or schema changes meaning. Cached readings from another
# version are ignored and re-read, so an improved prompt reaches old
# headlines instead of only new ones.
PROMPT_VERSION = "1"

# The model is configuration, not code: GEMINI_MODEL (a repository variable in
# the workflow) overrides this. Gemini 3.8 Flash is the model the key was
# issued for; the API ID below was written without access to Google's model
# list, so if it is wrong the API answers 404 and the log says to set
# GEMINI_MODEL.
DEFAULT_MODEL = "gemini-3.8-flash"
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

# Headlines per request, and new headlines read per run. The first run finds
# the whole corpus unread and works through it over a few days rather than
# spending one run's quota on the backlog.
BATCH_SIZE = 40
MAX_NEW_PER_RUN = 600
TIMEOUT_S = 60
# Server-side failures worth retrying, and how.
_TRANSIENT = {500, 502, 503, 504}
RETRY_ATTEMPTS = 3
RETRY_BASE_S = 15
RETRY_CAP_S = 60


def _backoff(resp, attempt: int) -> float:
    """Seconds before the next attempt: Retry-After if given, else doubling."""
    try:
        after = float((resp.headers or {}).get("Retry-After", ""))
    except (AttributeError, TypeError, ValueError):
        after = None
    wait = after if after is not None else RETRY_BASE_S * 2 ** (attempt - 1)
    return max(0.0, min(wait, RETRY_CAP_S))


# Unused cache entries are dropped after this long so the file stays small.
CACHE_RETENTION_DAYS = 120

EVENT_TYPES = (
    "tie_up",
    "acquisition",
    "order_win",
    "capacity_add",
    "supply_disruption",
    "input_cost_shock",
)
CERTAINTIES = ("completed", "announced", "reported")

_INSTRUCTIONS = """You classify Indian business-news headlines for an equity analyst.
For each headline return one object with:

event_type — exactly one of:
  tie_up             joint venture, partnership, alliance, MoU, collaboration
  acquisition        buying or selling a company, business or stake (divestments count)
  order_win          a company winning an order, contract or bid
  capacity_add       a new plant, facility or capacity opening, commissioning or being built
  supply_disruption  shortages, export bans, plant shutdowns, supply crunches
  input_cost_shock   a sharp rise in the cost of an input or raw material
  none               anything else: results, share-price moves, analyst views,
                     awards, product launches, fund or promoter stake changes,
                     policy announcements, board meetings, legal matters
parties — the companies that are PARTIES to the event, copied EXACTLY as written
  in the headline. Include both sides of a tie-up or acquisition, the company that
  won an order (NOT the customer that placed it), the company adding capacity.
  Never include advisers, law firms, governments, people, or countries.
  Use [] when event_type is none.
certainty — completed (it happened), announced (agreed or intended, e.g. MoU,
  "to acquire", "plans to"), or reported (rumour, "in talks", "likely", "close to").
amount_text — the deal's money figure copied EXACTLY as written (e.g. "Rs 1,081 crore",
  "$230M"), or "" if none or if the figure is not this deal's value.

Answer only from the headline. Do not use outside knowledge to add companies."""

_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "INTEGER"},
            "event_type": {"type": "STRING", "enum": list(EVENT_TYPES) + ["none"]},
            "parties": {"type": "ARRAY", "items": {"type": "STRING"}},
            "certainty": {"type": "STRING", "enum": list(CERTAINTIES)},
            "amount_text": {"type": "STRING"},
        },
        "required": ["id", "event_type", "parties", "certainty", "amount_text"],
    },
}


class ReaderUnavailable(Exception):
    """The API cannot be used this run. The message says why, for the log."""


# A transport takes the prompt text and returns the model's JSON text. Tests
# pass a fake; production uses gemini_transport().
Transport = Callable[[str], str]


def gemini_transport(api_key: str, model: str) -> Transport:
    import requests

    url = API_URL.format(model=model)

    def call(prompt: str) -> str:
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": _SCHEMA,
            },
        }
        # 5xx is Google's side and usually brief: the first live run met
        # "503 This model is currently experiencing high demand" on its first
        # batch and, with no retry, skipped the whole day. A few spaced
        # attempts, honouring Retry-After, then give up until the next run.
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                resp = requests.post(
                    url,
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=TIMEOUT_S,
                )
            except requests.RequestException as e:
                resp, error = None, f"request failed: {e!r}"
            else:
                error = None
                if resp.status_code not in _TRANSIENT:
                    break
                error = f"Gemini unavailable ({resp.status_code})"
            if attempt < RETRY_ATTEMPTS:
                time.sleep(_backoff(resp, attempt))
        else:
            raise ReaderUnavailable(
                f"{error} after {RETRY_ATTEMPTS} attempts; resuming next run"
            )
        if resp.status_code == 404:
            raise ReaderUnavailable(
                f"model {model!r} not found (404) — set GEMINI_MODEL to a current model"
            )
        if resp.status_code in (401, 403):
            raise ReaderUnavailable(f"key refused ({resp.status_code})")
        if resp.status_code == 429:
            raise ReaderUnavailable(
                "quota or rate limit reached (429); resuming next run"
            )
        if resp.status_code != 200:
            raise ReaderUnavailable(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError) as e:
            # A blocked or empty candidate. Not worth failing the batch over.
            raise ReaderUnavailable(f"unexpected response shape: {e!r}")

    return call


def default_transport() -> Tuple[Optional[Transport], str]:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None, "GEMINI_API_KEY not set"
    model = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
    return gemini_transport(key, model), model


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------


def cache_key(headline: str) -> str:
    norm = re.sub(r"\s+", " ", (headline or "").strip().lower())
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def load_cache(path: str = CACHE_PATH) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as f:
            body = json.load(f)
        return body.get("entries") or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        log.warning(f"LLM cache unreadable, not overwriting it: {e!r}")
        return None


def save_cache(entries: Dict[str, Any], path: str = CACHE_PATH) -> None:
    atomic_write_json(
        {"prompt_version": PROMPT_VERSION, "entries": dict(sorted(entries.items()))},
        path,
    )


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------


def ground(headline: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only what the headline itself supports.

    A party name or amount that is not a verbatim part of the headline is the
    model writing, not reading, and is dropped. An unknown event type or
    certainty becomes "none" / "reported" — the weakest reading, never the
    strongest.
    """
    lower = (headline or "").lower()
    etype = raw.get("event_type")
    if etype not in EVENT_TYPES:
        etype = "none"
    parties = []
    for p in raw.get("parties") or []:
        p = str(p or "").strip()
        if p and p.lower() in lower and p not in parties:
            parties.append(p)
    amount = str(raw.get("amount_text") or "").strip()
    if amount and amount.lower() not in lower:
        amount = ""
    certainty = raw.get("certainty")
    if certainty not in CERTAINTIES:
        certainty = "reported"
    if etype == "none":
        parties, amount = [], ""
    return {
        "event_type": etype,
        "parties": parties,
        "certainty": certainty,
        "amount_text": amount,
    }


def _prompt(batch: List[Tuple[int, str]]) -> str:
    lines = "\n".join(f"{i}: {h}" for i, h in batch)
    return f"{_INSTRUCTIONS}\n\nReturn a JSON array, one object per id.\n\n{lines}"


def read_headlines(
    headlines: List[str],
    transport: Optional[Transport] = None,
    cache_path: str = CACHE_PATH,
    max_new: int = MAX_NEW_PER_RUN,
    today: str = "",
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Readings for ``headlines`` — cached ones free, new ones fetched.

    Returns ``(readings, status)``: readings keyed by headline, and a status
    dict for the log line and tests. Never raises.
    """
    today = today or datetime.date.today().isoformat()
    status = {"cached": 0, "read": 0, "pending": 0, "skipped": ""}
    readings: Dict[str, Dict[str, Any]] = {}
    entries = load_cache(cache_path)
    if entries is None:
        status["skipped"] = "cache unreadable"
        return readings, status

    unique = list(dict.fromkeys(h for h in headlines or [] if h and h.strip()))
    todo: List[str] = []
    for h in unique:
        entry = entries.get(cache_key(h))
        if entry and entry.get("v") == PROMPT_VERSION:
            readings[h] = entry["reading"]
            entry["seen"] = today
            status["cached"] += 1
        else:
            todo.append(h)

    if transport is None:
        transport, detail = default_transport()
        if transport is None:
            status["skipped"] = detail
            status["pending"] = len(todo)
            return readings, status

    changed = False
    batch_todo = todo[:max_new]
    status["pending"] = len(todo) - len(batch_todo)
    try:
        for start in range(0, len(batch_todo), BATCH_SIZE):
            batch = list(enumerate(batch_todo[start : start + BATCH_SIZE]))
            text = transport(_prompt(batch))
            try:
                answers = json.loads(text)
            except ValueError:
                log.warning(
                    "LLM reader: a batch returned unparseable JSON; skipped it."
                )
                status["pending"] += len(batch)
                continue
            by_id = {a.get("id"): a for a in answers if isinstance(a, dict)}
            for i, h in batch:
                raw = by_id.get(i)
                if raw is None:
                    status["pending"] += 1  # unanswered; tried again next run
                    continue
                reading = ground(h, raw)
                readings[h] = reading
                entries[cache_key(h)] = {
                    "v": PROMPT_VERSION,
                    "headline": h[:200],
                    "reading": reading,
                    "seen": today,
                }
                status["read"] += 1
                changed = True
            # Gentle on per-minute limits; a daily batch has time to spare.
            if start + BATCH_SIZE < len(batch_todo):
                time.sleep(1.0)
    except ReaderUnavailable as e:
        status["skipped"] = str(e)
        status["pending"] = len(todo) - status["read"]

    cutoff = (
        datetime.date.fromisoformat(today)
        - datetime.timedelta(days=CACHE_RETENTION_DAYS)
    ).isoformat()
    stale = [k for k, v in entries.items() if str(v.get("seen", "")) < cutoff]
    for k in stale:
        del entries[k]
    if changed or stale or status["cached"]:
        save_cache(entries, cache_path)
    return readings, status


# ---------------------------------------------------------------------------
# reconciling the two readers
# ---------------------------------------------------------------------------


def _holdings(watchlist: Dict[str, Any]) -> List[Tuple[str, str]]:
    return [
        (str(s.get("ticker")).upper(), s.get("name") or "")
        for sector, stocks in (watchlist or {}).items()
        if sector != "macro_indicators"
        for s in stocks or []
        if isinstance(s, dict) and s.get("ticker")
    ]


def resolve_parties(parties: List[str], holdings) -> Tuple[List[str], List[str]]:
    """``(tickers, others)``: which named parties are holdings, via the matcher."""
    from analysis.counterparty import _is_holding

    tickers, others = [], []
    for party in parties:
        hit = next((t for t, n in holdings if _is_holding(party, [(t, n)])), None)
        if hit:
            if hit not in tickers:
                tickers.append(hit)
        else:
            others.append(party)
    return tickers, others


def reconcile(
    events: List[Dict[str, Any]],
    readings: Dict[str, Dict[str, Any]],
    watchlist: Dict[str, Any],
    data: Optional[Dict[str, Any]] = None,
    graph: Optional[Dict[str, Any]] = None,
    today: str = "",
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Merge the LLM's readings into the rules' events.

    Three outcomes, and the label each one carries is the confidence:

      corroborated  both readers found this event type for this holding —
                    two independent reads agreeing, the same standard the
                    Graham growth estimate applies before trusting optimism
      rules         only the rules found it, or the two disagree: the rules'
                    event stands unchanged and the LLM's view is attached as
                    ``llm_reading`` so the disagreement can be inspected
      llm           only the LLM found it. Added as ``reader: "llm"`` and
                    treated as unverified everywhere downstream: no
                    warnings, no escalation, no read-throughs, no supply
                    stress. It is shown, and its counterparties may enter the
                    human-reviewed partner queue — nothing more.

    Headlines the LLM read as events but that name no holding are not added:
    the rules keep those only for their graph entities, and an unverified
    reading is not enough to route news onto the book.
    """
    from analysis.event_engine import _EVENT_DIRECTION, graph_entities
    from analysis.competitive_intel import SECTOR_BATTLEGROUNDS, collect_sources

    stats = {"corroborated": 0, "disagreed": 0, "llm_only": 0}
    if not readings:
        return events, stats
    holdings = _holdings(watchlist)
    today = today or datetime.date.today().isoformat()
    sources = collect_sources(data or {}, watchlist) if data else {}

    by_key = {h[:180].lower(): (h, r) for h, r in readings.items()}
    covered = set()
    for event in events:
        key = str(event.get("headline", "")).lower()
        pair = by_key.get(key)
        if not pair:
            continue
        covered.add(key)
        _, reading = pair
        llm_actors, _ = resolve_parties(reading["parties"], holdings)
        actors = set(event.get("actors") or [])
        agrees = reading["event_type"] == event.get("event_type") and (
            not actors or bool(actors & set(llm_actors))
        )
        if agrees:
            event["corroborated"] = True
            stats["corroborated"] += 1
        else:
            event["corroborated"] = False
            event["llm_reading"] = {
                "event_type": reading["event_type"],
                "actors": llm_actors,
            }
            stats["disagreed"] += 1

    for key, (headline, reading) in by_key.items():
        if key in covered or reading["event_type"] == "none":
            continue
        actors, others = resolve_parties(reading["parties"], holdings)
        if not actors:
            continue
        etype = reading["event_type"]
        lower = headline.lower()
        citation = sources.get(lower) or {}
        event = {
            "headline": headline[:180],
            "event_type": etype,
            "phrase": None,
            "certainty": reading["certainty"],
            "domains": [
                s
                for s, terms in SECTOR_BATTLEGROUNDS.items()
                if any(t in lower for t in terms)
            ],
            "actors": actors,
            "external": graph_entities(headline, graph) if graph else [],
            "direction": _EVENT_DIRECTION.get(etype, "opportunity"),
            "date": today,
            "reader": "llm",
            "corroborated": False,
        }
        if etype == "tie_up":
            event["counterparties"] = others
        if citation.get("link"):
            event["link"] = citation["link"]
            event["source"] = citation.get("source", "")
        events.append(event)
        stats["llm_only"] += 1
    return events, stats


def is_unverified(event: Dict[str, Any]) -> bool:
    """Found only by the LLM. Downstream consumers that grade evidence skip these."""
    return isinstance(event, dict) and event.get("reader") == "llm"
