"""Generic market-event engine: classify WHAT happened, route to WHO it touches.

Design rule zero: no entity name appears in this module. Companies, anchors
and commodities exist only as data — the watchlist, the Screener peer radar
and entity_graph.json. Routing is two-tier so the engine works with an empty
graph: Tier 1 maps an event's domain to sectors through vocabulary alone
("X commits $30B for custom chips" routes to electronics holdings whoever X
is); Tier 2 upgrades a signal to holding level when a typed edge exists.

Fully deterministic by decision (no LLM): the RSS queries are themselves
classifiers, and a material event generates many differently-phrased
headlines of which the engine only needs to catch one. Misses found in
production logs become vocabulary entries with regression tests — the same
loop that hardened the headline→company matcher.
"""

import datetime
import re
from typing import Any, Dict, List

from analysis.competitive_intel import SECTOR_BATTLEGROUNDS, collect_headlines
from analysis.parsing import title_matches_company
from config import SECTOR_METADATA
from logger import log

# What happened — each type is (vocabulary, direction-for-domain-sectors).
EVENT_VOCABULARY: Dict[str, tuple] = {
    "tie_up": (
        "joint venture",
        "strategic partnership",
        "partnership with",
        "partners with",
        "ties up with",
        "tie-up with",
        "joins hands",
        "alliance with",
        "mou with",
        "memorandum of understanding",
        "collaboration with",
        "technology transfer",
    ),
    "acquisition": (
        "acquires",
        "acquisition of",
        "buys stake",
        "stake purchase",
        "to acquire",
        "takeover of",
        "merger with",
    ),
    "order_win": (
        "wins order",
        "bags order",
        "secures order",
        "wins contract",
        "bags contract",
        "order worth",
        "letter of intent",
        "purchase order",
    ),
    "capacity_add": (
        "new plant",
        "new facility",
        "new factory",
        "groundbreaking",
        "capacity expansion",
        "expands capacity",
        "commercial production",
        "begins production",
        "starts production",
        "commissions",
        "sets up plant",
        "sets up unit",
        "multiyear commitment",
        "billion deal",
        "billion commitment",
    ),
    "supply_disruption": (
        "shortage",
        "supply crunch",
        "supply chain disruption",
        "export restriction",
        "export curb",
        "export ban",
        "halts production",
        "production halt",
        "plant shutdown",
        "force majeure",
        "embargo",
        "supply constraints",
    ),
    "input_cost_shock": (
        "prices surge",
        "prices soar",
        "prices spike",
        "prices jump",
        "price surge",
        "cost surge",
        "raw material cost",
        "freight rates",
        "input costs rise",
        "costlier imports",
    ),
}

# How settled the event is. The engine used to record every match as though
# it had happened: "Schneider Electric Announces Intention To Acquire Cognite"
# and "Dixon Tech Up ... on Reports of Govt Approval Likely to Vivo Joint
# Venture" were both filed as completed events, and 16% of a live run's events
# were intentions or rumours read as fact. Order matters — the weakest reading
# that fits wins, so a reported intention is reported, not announced.
CERTAINTY_MARKERS = (
    (
        "reported",
        (
            "reportedly",
            "reports of",
            "report says",
            "sources say",
            "rumour",
            "rumor",
            "speculation",
            "likely to",
            "could ",
            "may ",
            "in talks",
            "exploring",
            "mulls",
            "weighing",
            "considering",
        ),
    ),
    (
        "announced",
        (
            "intention to",
            "intends to",
            "plans to",
            "planning to",
            "proposed",
            "proposes",
            "set to",
            "to acquire",
            "to buy",
            "agreed to",
            "in principle",
            "signs mou",
            "mou with",
            "memorandum of understanding",
        ),
    ),
)

CERTAINTY_COMPLETED = "completed"

# Clause boundaries. Semicolons and dashes separate independent statements in
# headline style; a comma followed by a market-reaction verb usually does too.
_CLAUSE_RE = re.compile(r"\s*[;—–]\s*|\s+-\s+|\s*\|\s*")

# A negated move is not a move — "denies plans to enter" must classify as
# nothing rather than as an entry. Scoped to a clause, so a denial in one
# statement no longer cancels a genuine event in another.
NEGATION_MARKERS = (
    "denies",
    "rules out",
    "no plans",
    "refutes",
    "dismisses report",
    "calls off",
    "cancels",
    "scraps",
    "shelves",
)

# Which way an event leans for the sectors whose turf it lands on.
_EVENT_DIRECTION = {
    "tie_up": "opportunity",
    "acquisition": "opportunity",
    "order_win": "opportunity",
    "capacity_add": "opportunity",
    "supply_disruption": "risk",
    "input_cost_shock": "risk",
}

_RISK_TYPES = ("supply_disruption", "input_cost_shock")
_MAX_SIGNALS_PER_SECTOR = 3


def split_clauses(headline: str) -> List[str]:
    """Break a headline into independent statements.

    Falls back to the whole headline when there is nothing to split on, so a
    single-clause headline behaves exactly as before.
    """
    parts = [p.strip() for p in _CLAUSE_RE.split(headline or "") if p and p.strip()]
    return parts or ([headline] if headline else [])


def classify_certainty(text: str) -> str:
    """``reported`` / ``announced`` / ``completed`` for one clause."""
    lower = (text or "").lower()
    for level, markers in CERTAINTY_MARKERS:
        if any(m in lower for m in markers):
            return level
    return CERTAINTY_COMPLETED


def classify_headlines(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Classify every collected headline into typed market events.

    Returns [{headline, event_type, phrase, certainty, domains, actors,
    direction, date}] — ``domains`` are watchlist sectors whose battleground
    vocabulary the headline touches (Tier 1); ``actors`` are watchlist tickers
    named in the same clause as the event (direct attribution); ``certainty``
    is how settled the event is (reported / announced / completed).
    """
    events: List[Dict[str, Any]] = []
    today = datetime.date.today().isoformat()
    try:
        holdings = [
            (s.get("ticker", ""), s.get("name", ""))
            for stocks in (watchlist or {}).values()
            for s in stocks or []
            if isinstance(s, dict)
        ]
        for headline in collect_headlines(data, watchlist):
            lower = headline.lower()

            # Classify within a clause, not across the whole headline. A
            # headline routinely carries two of them — "ITC Hotels to acquire
            # GHK for Rs 155 crore; shares decline 5%" — and matching the
            # event, its actors and any negation against the full string lets
            # one clause cancel or claim what belongs to the other.
            event_type = phrase = certainty = None
            actors: List[str] = []
            for clause in split_clauses(headline):
                clause_lower = clause.lower()
                if any(neg in clause_lower for neg in NEGATION_MARKERS):
                    continue  # this clause is a denial; others may still count

                hit_type = hit_phrase = None
                for etype, vocabulary in EVENT_VOCABULARY.items():
                    hit = next((v for v in vocabulary if v in clause_lower), None)
                    if hit:
                        hit_type, hit_phrase = etype, hit
                        break
                if not hit_type:
                    continue

                # Attribution is relational, so the company has to appear
                # alongside the event, not merely somewhere in the headline.
                event_type, phrase = hit_type, hit_phrase
                certainty = classify_certainty(clause)
                actors = [
                    ticker
                    for ticker, name in holdings
                    if title_matches_company(clause, ticker, name)
                ]
                break
            if not event_type:
                continue

            # Domains stay headline-wide: unlike actors they are topical
            # rather than relational, and Tier 1 routing is deliberately loose.
            domains = [
                sector
                for sector, battleground in SECTOR_BATTLEGROUNDS.items()
                if any(term in lower for term in battleground)
            ]
            if not domains and not actors:
                continue  # classified, but touches nothing we track

            events.append(
                {
                    "headline": headline[:180],
                    "event_type": event_type,
                    "phrase": phrase,
                    "certainty": certainty,
                    "domains": domains,
                    "actors": actors,
                    "direction": _EVENT_DIRECTION.get(event_type, "opportunity"),
                    "date": today,
                }
            )
        if events:
            counts: Dict[str, int] = {}
            for e in events:
                counts[e["event_type"]] = counts.get(e["event_type"], 0) + 1
            log.info(
                f"Event engine: {len(events)} market events classified "
                f"({', '.join(f'{k}={v}' for k, v in sorted(counts.items()))})."
            )
    except Exception as e:
        log.warning(f"Event engine failed safely: {e!r}")
    return events


# Events older than this leave the corpus. Without it the list only ever
# grows, and entries classified by an older version of the engine outlive
# every fix made since.
EVENT_RETENTION_DAYS = 45


def refresh_merged_events(
    events: List[Dict[str, Any]], watchlist: Dict[str, Any], today: str = ""
) -> List[Dict[str, Any]]:
    """Re-derive attribution on the accumulated event list, and drop stale rows.

    Events merge across runs, so a correction to the matcher or the vocabulary
    only ever applies to what is classified *today* — yesterday's mistakes are
    carried forward untouched. That is not hypothetical: after the entity
    boundary fix, three ITC Hotels events stayed attributed to ITC, and since
    per-stock coverage reads these actors directly, they were still showing on
    ITC's card the next day.

    So every merged event is re-attributed with the current rules. An event
    that no longer names anything we track is dropped, which is how those
    three finally disappear. Certainty is filled in for rows that predate the
    field. Cheap enough to do unconditionally — the list is capped at 120.
    """
    if not events:
        return []
    refreshed: List[Dict[str, Any]] = []
    try:
        holdings = [
            (s.get("ticker", ""), s.get("name", ""))
            for stocks in (watchlist or {}).values()
            for s in stocks or []
            if isinstance(s, dict)
        ]
        today = today or datetime.date.today().isoformat()
        cutoff = (
            datetime.date.fromisoformat(today)
            - datetime.timedelta(days=EVENT_RETENTION_DAYS)
        ).isoformat()

        dropped_stale = dropped_orphan = reattributed = 0
        for event in events:
            if not isinstance(event, dict):
                continue
            if str(event.get("date", "")) < cutoff:
                dropped_stale += 1
                continue

            headline = event.get("headline") or ""
            clause = next(
                (
                    c
                    for c in split_clauses(headline)
                    if event.get("phrase") and event["phrase"] in c.lower()
                ),
                headline,
            )
            actors = [
                ticker
                for ticker, name in holdings
                if title_matches_company(clause, ticker, name)
            ]
            if actors != (event.get("actors") or []):
                reattributed += 1
            if not actors and not (event.get("domains") or []):
                dropped_orphan += 1
                continue

            event["actors"] = actors
            if not event.get("certainty"):
                event["certainty"] = classify_certainty(clause)
            refreshed.append(event)

        if dropped_stale or dropped_orphan or reattributed:
            log.info(
                f"Event corpus refresh: {reattributed} re-attributed, "
                f"{dropped_orphan} no longer touch the watchlist, "
                f"{dropped_stale} past {EVENT_RETENTION_DAYS}d retention."
            )
    except Exception as e:  # noqa: BLE001 - housekeeping must not break a run
        log.warning(f"Event corpus refresh failed safely: {e!r}")
        return events
    return refreshed


def compute_supply_stress(
    events: List[Dict[str, Any]], graph: Dict[str, Any], window_days: int = 14
) -> Dict[str, int]:
    """Rolling count of supply-side events per sector — the forward-looking
    counterpart of the (lagging) reported-OPM margin ladder. Domains come
    from Tier-1 vocabulary plus the graph's input_cost edges (a headline
    naming a tracked input routes to the sectors exposed to it)."""
    stress: Dict[str, int] = {}
    try:
        cutoff = (
            datetime.date.today() - datetime.timedelta(days=window_days)
        ).isoformat()
        input_edges = [
            e for e in (graph or {}).get("edges", []) if e.get("type") == "input_cost"
        ]
        for event in events or []:
            if not isinstance(event, dict):
                continue
            if event.get("event_type") not in _RISK_TYPES:
                continue
            # A rumoured disruption is not a disruption. Counting one toward
            # a sector's stress score would let speculation trip a threshold
            # built to measure things that actually happened.
            if event.get("certainty") == "reported":
                continue
            if str(event.get("date", "")) < cutoff:
                continue
            sectors = set(event.get("domains") or [])
            lower = str(event.get("headline", "")).lower()
            for edge in input_edges:
                if str(edge.get("src", "")).lower() in lower:
                    sectors.add(edge.get("dst"))
            for sector in sectors:
                if sector in SECTOR_METADATA:
                    stress[sector] = stress.get(sector, 0) + 1
        if stress:
            worst = max(stress.items(), key=lambda kv: kv[1])
            log.info(
                f"Supply-chain stress ({window_days}d window): "
                f"{len(stress)} sector(s) touched; highest {worst[0]}={worst[1]}."
            )
    except Exception as e:
        log.warning(f"Supply-stress computation failed safely: {e!r}")
    return stress


# Stress level (events in window) at which a forward margin warning fires.
_STRESS_WARN_AT = 2


def market_event_signals(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Early-warning signals from classified events, two-tier routed.

    - Direct (actor is a holding): "Corporate Move" info signal on it.
    - Tier 2 (graph anchor edge): "Ecosystem Signal" naming the path.
    - Tier 1 (domain only): supply-side risks hit every holding in the
      exposed sector; positive ecosystem events surface at Low severity.
    - Sustained supply stress (rolling window) escalates to a forward
      "Supply Stress" warning — the leading pair of Margin Compression.
    """
    from analysis.entity_graph import load_entity_graph, match_anchor_edges

    alerts: List[Dict[str, Any]] = []
    try:
        events = data.get("market_events") or []
        graph = load_entity_graph()
        names = {}
        by_sector: Dict[str, list] = {}
        for sector, stocks in (watchlist or {}).items():
            for s in stocks or []:
                if isinstance(s, dict) and s.get("ticker"):
                    names[s["ticker"]] = s.get("name")
                    by_sector.setdefault(sector, []).append(s["ticker"])

        emitted_per_sector: Dict[str, int] = {}

        def sector_label(sector):
            return SECTOR_METADATA.get(sector, {}).get("label", sector)

        for event in events:
            if not isinstance(event, dict):
                continue
            headline = event.get("headline", "")
            etype = event.get("event_type", "event")

            # Direct attribution: a holding named in the headline. The
            # certainty qualifier travels with the signal, so a rumour is
            # never read as a done deal.
            certainty = event.get("certainty") or ""
            qualifier = (
                f" ({certainty})" if certainty and certainty != "completed" else ""
            )
            for ticker in event.get("actors") or []:
                alerts.append(
                    {
                        "ticker": ticker,
                        "name": names.get(ticker, ticker),
                        "sector": "—",
                        "severity": "Low",
                        "direction": event.get("direction", "opportunity"),
                        "category": "Corporate Move",
                        "signal": (
                            f"{etype.replace('_', ' ').title()}{qualifier}: "
                            f"“{headline}”"
                        ),
                    }
                )

            # Tier 2: anchor edges (typed relationships from the graph).
            for edge in match_anchor_edges(headline, graph):
                dst = edge.get("dst")
                dst_tickers = [dst] if dst in names else by_sector.get(dst, [])
                for ticker in dst_tickers[:_MAX_SIGNALS_PER_SECTOR]:
                    alerts.append(
                        {
                            "ticker": ticker,
                            "name": names.get(ticker, ticker),
                            "sector": sector_label(dst) if dst not in names else "—",
                            "severity": "Low",
                            "direction": event.get("direction", "opportunity"),
                            "category": "Ecosystem Signal",
                            "signal": (
                                f"{edge.get('src')} → {edge.get('type')} edge: "
                                f"“{headline}”"
                            ),
                        }
                    )

            # Tier 1: supply-side risks propagate to every exposed sector.
            if etype in _RISK_TYPES:
                for sector in event.get("domains") or []:
                    if emitted_per_sector.get(sector, 0) >= _MAX_SIGNALS_PER_SECTOR:
                        continue
                    emitted_per_sector[sector] = emitted_per_sector.get(sector, 0) + 1
                    for ticker in by_sector.get(sector, []):
                        alerts.append(
                            {
                                "ticker": ticker,
                                "name": names.get(ticker, ticker),
                                "sector": sector_label(sector),
                                "severity": "Medium",
                                "direction": "risk",
                                "category": "Supply Chain",
                                "signal": f"Sector input exposure: “{headline}”",
                            }
                        )

        # Forward margin watch on sustained stress.
        for sector, count in (data.get("supply_stress") or {}).items():
            if count >= _STRESS_WARN_AT:
                for ticker in by_sector.get(sector, []):
                    alerts.append(
                        {
                            "ticker": ticker,
                            "name": names.get(ticker, ticker),
                            "sector": sector_label(sector),
                            "severity": "Medium",
                            "direction": "risk",
                            "category": "Supply Stress (Forward)",
                            "signal": (
                                f"{count} supply-side events touched this sector "
                                f"in 14 days — margin pressure may be building "
                                f"before it shows in reported OPM."
                            ),
                        }
                    )
    except Exception as e:
        log.warning(f"Market-event signals failed safely: {e!r}")
    return alerts
