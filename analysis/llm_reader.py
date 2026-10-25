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
from typing import Any, Dict, List, Optional, Tuple

from analysis.reader_runtime import ReaderUnavailable, Transport, default_transport
from logger import log
from utils import atomic_write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(ROOT, "llm_cache.json")

# Bump when the prompt or schema changes meaning. Cached readings from another
# version are ignored and re-read, so an improved prompt reaches old
# headlines instead of only new ones.
# 4: divestment, product_launch and management_change, the types the rules
#    gained on 24 Oct. Version 3 filed a sale as an acquisition ("BPCL exits
#    Numaligarh Refinery" read as BPCL buying) and every launch as none.
PROMPT_VERSION = "4"

# Headlines per request, and new headlines read per run. The first run finds
# the whole corpus unread and works through it over a few days rather than
# spending one run's quota on the backlog.
BATCH_SIZE = 40
MAX_NEW_PER_RUN = 600
# Between batches: gentle on per-minute limits; a daily batch has time to
# spare. Replayed answers (scripts/reader_eval.py) need none.
BATCH_PAUSE_S = 1.0

# Unused cache entries are dropped after this long so the file stays small.
CACHE_RETENTION_DAYS = 120

# The rules' types the reader is asked for. Not partnership_end or
# business_weakness: those stay the rules' alone, and reconcile() does not
# count the reader's "none" for one as a disagreement.
EVENT_TYPES = (
    "tie_up",
    "acquisition",
    "divestment",
    "order_win",
    "capacity_add",
    "product_launch",
    "management_change",
    "supply_disruption",
    "input_cost_shock",
)
CERTAINTIES = ("completed", "announced", "reported")

POLICY_MEASURES = (
    "duty_or_tariff",
    "incentive_scheme",
    "subsidy_or_funding",
    "procurement",
    "regulation",
    "ban_or_restriction",
    "tax",
    "trade_agreement",
    "approval",
    "other",
)
POLICY_STATUSES = ("proposed", "approved", "in_force")
DIRECTIONS = ("tailwind", "headwind", "mixed")


def _sectors():
    from config import SECTOR_METADATA

    return {k: v for k, v in SECTOR_METADATA.items() if k != "macro_indicators"}


_POLICY_SECTORS = tuple(_sectors())

_INSTRUCTIONS = """You classify Indian business-news headlines for an equity analyst.
For each headline return one object with:

event_type — exactly one of:
  tie_up             joint venture, partnership, alliance, MoU, collaboration
  acquisition        a company buying a company, business or stake
  divestment         a company selling, spinning off or exiting a company,
                     business, plant or stake it owns. Shareholders selling
                     the company's own shares are none: promoter, government
                     or fund sales, block deals, OFS.
  order_win          a company winning an order, contract or bid
  capacity_add       a new plant, facility or capacity opening, commissioning or being built
  product_launch     a company launching, unveiling or introducing a product,
                     model, platform or service of its own, or planning to.
                     Not a government scheme, an IPO or share issue, or a
                     plan, policy or campaign being launched. A launch made
                     in partnership with another named company is a tie_up.
  management_change  a person appointed to, re-appointed to, resigning from,
                     retiring from or replaced in one of these posts: CEO,
                     MD, CFO, COO, CTO, chairman, whole-time or executive
                     director. Other appointments are none: auditors,
                     agencies, advisers, company secretaries, other staff,
                     independent directors and government officials.
  supply_disruption  shortages, export bans, plant shutdowns, supply crunches
  input_cost_shock   a sharp rise in the cost of an input or raw material
  none               anything else: results, share-price moves, analyst views,
                     awards, fund or promoter stake changes, policy
                     announcements, board meeting notices, legal matters
parties — the companies that are PARTIES to the event, copied EXACTLY as written
  in the headline. Include both sides of a tie-up or acquisition, the seller in a
  divestment (and the buyer, if named), the company that won an order (NOT the
  customer that placed it), the company adding capacity, the company launching
  the product, and the company whose executive changed (NOT a former employer).
  Never include advisers, law firms, governments, people, or countries.
  Use [] when event_type is none.
certainty — completed (it happened), announced (agreed or intended, e.g. MoU,
  "to acquire", "plans to"), or reported (rumour, "in talks", "likely", "close to").
amount_text — the deal's money figure copied EXACTLY as written (e.g. "Rs 1,081 crore",
  "$230M"), or "" if none or if the figure is not this deal's value.
material — true if a long-term shareholder of the company would want to know this:
  orders, deals, capacity, results, guidance, regulatory action, a CEO/MD change,
  litigation outcomes. false for routine disclosure (AGM notices, trading windows,
  share allotments, investor-meet schedules, junior appointments), share-price
  commentary, stock tips, CSR, awards and marketing events.
gist — the shortest part of the headline, copied EXACTLY and contiguously, that
  still states the news, at most 14 words. Drop filing wrappers such as
  "X Limited has informed the Exchange regarding a press release dated ..., titled".
  Use "" if the headline is already that short or has no news.

policy_measure — if a GOVERNMENT or REGULATOR acted (India or abroad), which kind:
  duty_or_tariff, incentive_scheme, subsidy_or_funding, procurement, regulation,
  ban_or_restriction, tax, trade_agreement, approval, other.
  "none" for anything else — including a company's own board approval, market
  commentary about a policy, a speech, or praise for an old scheme.
policy_status — proposed (planned, likely, under consideration), approved, or in_force.
sector_effects — for each sector below that the measure DIRECTLY helps or hurts:
  sector (key from the list), direction (tailwind, headwind or mixed), and because:
  the words of the headline naming what is affected, copied EXACTLY.
  Think about who is on each side: a duty CUT on imported components is a
  tailwind for assemblers and a headwind for domestic makers of that component;
  a tariff cut by another country for India's competitors is a headwind.
  [] when policy_measure is none or no listed sector is directly affected.

SECTORS:
{sectors}

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
            "material": {"type": "BOOLEAN"},
            "gist": {"type": "STRING"},
            "policy_measure": {
                "type": "STRING",
                "enum": list(POLICY_MEASURES) + ["none"],
            },
            "policy_status": {"type": "STRING", "enum": list(POLICY_STATUSES)},
            "sector_effects": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "sector": {"type": "STRING", "enum": list(_POLICY_SECTORS)},
                        "direction": {"type": "STRING", "enum": list(DIRECTIONS)},
                        "because": {"type": "STRING"},
                    },
                    "required": ["sector", "direction", "because"],
                },
            },
        },
        "required": [
            "id",
            "event_type",
            "parties",
            "certainty",
            "amount_text",
            "material",
            "gist",
            "policy_measure",
            "policy_status",
            "sector_effects",
        ],
    },
}


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


def save_cache(
    entries: Dict[str, Any], path: str = CACHE_PATH, version: str = PROMPT_VERSION
) -> None:
    atomic_write_json(
        {"prompt_version": version, "entries": dict(sorted(entries.items()))},
        path,
    )


# ---------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------


def _launched_in_partnership(headline: str) -> bool:
    """A launch the rules read as a tie-up: "Coforge launches ... product in
    partnership with Zscaler". The rules read a partnership before a launch
    (EVENT_VOCABULARY order) and reconcile() corroborates only the same type.
    The prompt says so too, but every recording of version 4 read both
    labelled headlines of this shape as launches, so the rules' own reading
    decides between the two. Their reading of the event's clause, as they
    classify it: a partnership in another clause ("Coforge launches
    SecureEdge AI platform; partners with Zscaler") leaves the launch one."""
    from analysis.event_engine import first_event_clause

    found = first_event_clause(headline)
    return bool(found) and found[1] == "tie_up"


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
    if etype == "product_launch" and _launched_in_partnership(headline or ""):
        etype = "tie_up"
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
    # The gist must be a passage of the headline, checked the same way as the
    # parties: a shortened line the source never said would be a misquote in
    # the reader's briefing. Too short to carry news, or no shorter than the
    # original, and it is dropped.
    gist = re.sub(r"\s+", " ", str(raw.get("gist") or "")).strip(" .;:,-")
    if (
        not gist
        or gist.lower() not in re.sub(r"\s+", " ", lower)
        or len(gist.split()) < 3
        or len(gist) >= len((headline or "").strip())
    ):
        gist = ""
    material = raw.get("material")
    return {
        "event_type": etype,
        "parties": parties,
        "certainty": certainty,
        "amount_text": amount,
        # None when the model did not say: unknown is not "immaterial".
        "material": material if isinstance(material, bool) else None,
        "gist": gist,
        **_ground_policy(headline, raw),
    }


def _ground_policy(headline: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """The policy fields, kept only as far as the headline supports them.

    An effect must name one of our sectors and quote the headline for what
    is affected; one whose ``because`` is not a passage of the headline is
    the model reasoning from outside knowledge, and is dropped. Unknown
    measures read as none — the weakest reading.
    """
    measure = raw.get("policy_measure")
    if measure not in POLICY_MEASURES:
        return {"policy_measure": "none", "policy_status": None, "sector_effects": []}
    status = raw.get("policy_status")
    lower = re.sub(r"\s+", " ", (headline or "").lower())
    effects, seen = [], set()
    for e in raw.get("sector_effects") or []:
        if not isinstance(e, dict):
            continue
        sector, direction = e.get("sector"), e.get("direction")
        because = re.sub(r"\s+", " ", str(e.get("because") or "")).strip(" .,;:")
        if sector not in _POLICY_SECTORS or direction not in DIRECTIONS:
            continue
        if not because or because.lower() not in lower:
            continue
        if sector in seen:
            continue
        seen.add(sector)
        effects.append({"sector": sector, "direction": direction, "because": because})
    return {
        "policy_measure": measure,
        "policy_status": status if status in POLICY_STATUSES else "proposed",
        "sector_effects": effects,
    }


def _prompt(batch: List[Tuple[int, str]]) -> str:
    lines = "\n".join(f"{i}: {h}" for i, h in batch)
    sectors = "\n".join(
        f"  {k}: {v.get('label', k)} — {v.get('desc', '')}"
        for k, v in _sectors().items()
    )
    instructions = _INSTRUCTIONS.replace("{sectors}", sectors)
    return f"{instructions}\n\nReturn a JSON array, one object per id.\n\n{lines}"


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
        transport, detail = default_transport(_SCHEMA, reader="events")
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
                served_by = getattr(transport, "model", None)
                entries[cache_key(h)] = {
                    "v": PROMPT_VERSION,
                    "headline": h[:200],
                    "reading": reading,
                    "seen": today,
                    # Which model said this — readings from a fallback model
                    # can then be told apart, and re-read, later.
                    **({"model": served_by} if served_by else {}),
                }
                status["read"] += 1
                changed = True
            if start + BATCH_SIZE < len(batch_todo):
                time.sleep(BATCH_PAUSE_S)
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
    from analysis.event_evidence import article_date, headline_date
    from analysis.competitive_intel import battleground_sectors, collect_sources

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
        if event.get("event_type") not in EVENT_TYPES:
            # A type the reader is never asked for (business_weakness,
            # partnership_end): its "none" is not a disagreement.
            continue
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
            "domains": battleground_sectors(headline),
            "actors": actors,
            "external": graph_entities(headline, graph) if graph else [],
            "direction": _EVENT_DIRECTION.get(etype, "opportunity"),
            # Dated as a rules event is (event_engine.classify_headlines).
            "date": article_date(citation.get("date"))
            or headline_date(headline, today)
            or today,
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


_CACHED: Optional[Dict[str, Any]] = None


def cached_reading(headline: str, path: str = CACHE_PATH) -> Optional[Dict[str, Any]]:
    """The stored reading for a headline, or None — never an API call.

    For display code (the email, the alert labels), which must not spend
    quota or wait on the network, and must render the same with no key.
    """
    global _CACHED
    if _CACHED is None or path != CACHE_PATH:
        entries = load_cache(path) or {}
        if path != CACHE_PATH:
            entry = entries.get(cache_key(headline))
            return (
                entry["reading"] if entry and entry.get("v") == PROMPT_VERSION else None
            )
        _CACHED = entries
    entry = _CACHED.get(cache_key(headline))
    if entry and entry.get("v") == PROMPT_VERSION:
        return entry["reading"]
    return None


def reset_cached_readings() -> None:
    """Forget the in-memory copy; the next cached_reading() reloads the file."""
    global _CACHED
    _CACHED = None
