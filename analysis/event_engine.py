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

# A negated move is not a move — "denies plans to enter" must classify as
# nothing rather than as an entry.
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


def classify_headlines(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Classify every collected headline into typed market events.

    Returns [{headline, event_type, phrase, domains, actors, direction,
    date}] — ``domains`` are watchlist sectors whose battleground vocabulary
    the headline touches (Tier 1); ``actors`` are watchlist tickers named in
    the headline (direct attribution).
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
            if any(neg in lower for neg in NEGATION_MARKERS):
                continue

            event_type = phrase = None
            for etype, vocabulary in EVENT_VOCABULARY.items():
                hit = next((v for v in vocabulary if v in lower), None)
                if hit:
                    event_type, phrase = etype, hit
                    break
            if not event_type:
                continue

            domains = [
                sector
                for sector, battleground in SECTOR_BATTLEGROUNDS.items()
                if any(term in lower for term in battleground)
            ]
            actors = [
                ticker
                for ticker, name in holdings
                if title_matches_company(headline, ticker, name)
            ]
            if not domains and not actors:
                continue  # classified, but touches nothing we track

            events.append(
                {
                    "headline": headline[:180],
                    "event_type": event_type,
                    "phrase": phrase,
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

            # Direct attribution: a holding named in the headline.
            for ticker in event.get("actors") or []:
                alerts.append(
                    {
                        "ticker": ticker,
                        "name": names.get(ticker, ticker),
                        "sector": "—",
                        "severity": "Low",
                        "direction": event.get("direction", "opportunity"),
                        "category": "Corporate Move",
                        "signal": f"{etype.replace('_', ' ').title()}: “{headline}”",
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
