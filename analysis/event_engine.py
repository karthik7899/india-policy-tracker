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

from analysis.competitive_intel import (
    SECTOR_BATTLEGROUNDS,
    collect_headlines,
    collect_sources,
)
from analysis.event_evidence import article_date, evidence_level
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

# Shapes the literal phrases above cannot express, because headlines put
# words between the verb and its object. "Suzlon bags 306 MW wind turbine
# orders" and "Coforge Wins $230M AI Transformation Contract" matched nothing:
# "bags order" and "wins contract" are in the vocabulary, but only as
# adjacent words. Found by scoring the rules against eval/event_labels.json
# (see scripts/eval_events.py), where they were the largest single class of
# miss. Tuned on the 'dev' split only.
#
# The gap is bounded — at most six words — so a verb in one statement cannot
# reach an "order" several phrases later.
_GAP = r"(?:\W+[\w$₹.%'-]+){0,6}?\W+"
EVENT_PATTERNS: Dict[str, tuple] = {
    "tie_up": (
        re.compile(
            r"\b(?:forms?|formed|forming|to form)\s+(?:an?\s+)?(?:jv|joint venture)\b"
        ),
        re.compile(r"\bjv with\b"),
        re.compile(r"\b(?:signs?|signed|inks?|inked)\s+(?:an?\s+)?mous?\b"),
        # "LTTS and Anthropic Partner to Transform Engineering": a plural
        # subject takes the bare verb, which "partners with" never matches.
        re.compile(r"\band\s+[\w.&' -]{1,40}?\s+partner\s+(?:to|for|on|in)\b"),
    ),
    "acquisition": (
        re.compile(r"\bstake acquisition\b"),
        # A divestment is the same transaction seen from the seller.
        re.compile(r"\b(?:divests?|divested|divestment|stake sale|sells stake)\b"),
    ),
    "order_win": (
        re.compile(
            r"\b(?:wins?|won|bags?|bagged|secures?|secured|lands?|landed|"
            r"receives?|received)" + _GAP + r"(?:orders?|contracts?|bid)\b"
        ),
        # Not "order win from X": there X is the customer. "Defence stock
        # jumps... Order win from BEL" is another company's win.
        re.compile(r"\border win\b(?!\s+from\b)"),
    ),
    "capacity_add": (
        re.compile(
            r"\b(?:inaugurat\w*|opens|opened)"
            + _GAP
            + r"(?:facility|plant|factory|unit)\b"
        ),
    ),
}


def match_event_type(clause_lower: str):
    """``(event_type, phrase)`` for the first type whose vocabulary or
    pattern appears in the clause, else ``(None, None)``.

    The phrase is the matched text itself, so it can be found in the clause
    again later (event_clause relies on that).
    """
    for etype, vocabulary in EVENT_VOCABULARY.items():
        hit = next((v for v in vocabulary if v in clause_lower), None)
        if hit:
            return etype, hit
        for pattern in EVENT_PATTERNS.get(etype, ()):
            m = pattern.search(clause_lower)
            if m:
                return etype, m.group(0)
    return None, None


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


def graph_entities(clause: str, graph: Dict[str, Any]) -> List[str]:
    """Graph entities named in this clause — Google, Apple, Broadcom, Marvell.

    ``actors`` records only watchlist tickers, which is right for direct
    attribution and useless for second-order reasoning: a headline about
    Google tying up with Marvell names nothing we hold, so both names were
    discarded and there was no way to walk the entity graph from the event.
    Recording them is what makes a read-through derivable at all.

    input_cost sources are excluded — they are commodity keywords ("copper",
    "memory chip"), not companies, and read_through matches them separately
    with vocabulary suited to a material rather than to a corporate name.

    Matched with the same word-boundary and person-guard rules as every other
    attribution here, so "Mr Apple" or "Broadcom Institute" cannot enrol an
    entity that is not really the subject.
    """
    names = sorted(
        {
            str(edge.get("src"))
            for edge in (graph or {}).get("edges", [])
            if edge.get("type") != "input_cost" and edge.get("src")
        }
        | {
            str(edge.get("dst"))
            for edge in (graph or {}).get("edges", [])
            if edge.get("type") in ("competitor", "supplier_customer")
            and edge.get("dst")
        }
    )
    return [name for name in names if title_matches_company(clause, "", name)]


def _counterparties(event_type, clause, actors, holdings):
    """The other side of a tie-up, or None when the question does not apply.

    Only a tie-up has a counterparty in the sense that matters here — a party
    whose later news reads across to ours. None for every other event type,
    kept distinct from [] ("a tie-up, and nobody else could be named") so the
    two are never confused downstream.
    """
    if event_type != "tie_up":
        return None
    from analysis.counterparty import extract_counterparties

    named = set(actors or [])
    return extract_counterparties(
        clause, [(ticker, name) for ticker, name in holdings if ticker in named]
    )


def _evidence_note(event: Dict[str, Any]) -> str:
    """How the alert text states its evidence, in words a reader can check."""
    level = evidence_level(event)
    if level == "confirmed":
        c = event["confirmation"]
        return f"confirmed by {c.get('ticker')}'s {c.get('source')} filing of {c.get('date')}"
    if level == "multi-source":
        return f"reported by {event.get('reports')} outlets"
    return "single report, not yet confirmed"


def classify_headlines(
    data: Dict[str, Any], watchlist: Dict[str, Any], graph: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Classify every collected headline into typed market events.

    Returns [{headline, event_type, phrase, certainty, domains, actors,
    external, direction, date}] — ``domains`` are watchlist sectors whose
    battleground vocabulary the headline touches (Tier 1); ``actors`` are
    watchlist tickers named in the same clause as the event (direct
    attribution); ``external`` are entity-graph names in that clause, which is
    what second-order read-throughs are derived from; ``certainty`` is how
    settled the event is (reported / announced / completed).
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
        sources = collect_sources(data, watchlist)
        for headline in collect_headlines(data, watchlist):
            lower = headline.lower()

            # Classify within a clause, not across the whole headline. A
            # headline routinely carries two of them — "ITC Hotels to acquire
            # GHK for Rs 155 crore; shares decline 5%" — and matching the
            # event, its actors and any negation against the full string lets
            # one clause cancel or claim what belongs to the other.
            event_type = phrase = certainty = counterparties = None
            actors: List[str] = []
            external: List[str] = []
            for clause in split_clauses(headline):
                clause_lower = clause.lower()
                if any(neg in clause_lower for neg in NEGATION_MARKERS):
                    continue  # this clause is a denial; others may still count

                hit_type, hit_phrase = match_event_type(clause_lower)
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
                external = graph_entities(clause, graph)
                counterparties = _counterparties(event_type, clause, actors, holdings)
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
            # An event naming a graph entity is kept even when it touches no
            # sector vocabulary and none of our tickers. That is exactly the
            # shape of the events worth reading through — "Google taps Marvell
            # for custom silicon" mentions nothing we hold, and the whole point
            # is to derive what it means for what we do hold. Before this, such
            # a headline was classified and then dropped on this line.
            if not domains and not actors and not external:
                continue  # classified, but touches nothing we track

            # The citation, looked up on the full headline before it is
            # truncated for storage. An event that names a headline but cannot
            # be traced back to the article is an assertion the reader has to
            # take on faith, which is the one thing this pipeline tries never
            # to ask of them. Absent when the feed carried no link — omitted
            # rather than written as "", so "no link" and "" stay distinct.
            citation = sources.get(headline.lower()) or {}

            events.append(
                {
                    "headline": headline[:180],
                    "event_type": event_type,
                    "phrase": phrase,
                    "certainty": certainty,
                    "domains": domains,
                    "actors": actors,
                    "external": external,
                    **(
                        {"counterparties": counterparties}
                        if counterparties is not None
                        else {}
                    ),
                    "direction": _EVENT_DIRECTION.get(event_type, "opportunity"),
                    # The article's own date, not the run's. Every run
                    # re-reads the accumulated news history, so the run date
                    # re-stamped months-old stories as today's on every run.
                    "date": article_date(citation.get("date")) or today,
                    "first_seen": today,
                    **(
                        {"link": citation["link"], "source": citation.get("source", "")}
                        if citation.get("link")
                        else {}
                    ),
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


def event_clause(event: Dict[str, Any]) -> str:
    """The clause the event was classified from — the whole headline if the
    stored phrase is no longer found in any one clause."""
    headline = event.get("headline") or ""
    return next(
        (
            c
            for c in split_clauses(headline)
            if event.get("phrase") and event["phrase"] in c.lower()
        ),
        headline,
    )


# Events older than this leave the corpus. Without it the list only ever
# grows, and entries classified by an older version of the engine outlive
# every fix made since.
EVENT_RETENTION_DAYS = 45


def refresh_merged_events(
    events: List[Dict[str, Any]],
    watchlist: Dict[str, Any],
    today: str = "",
    graph: Dict[str, Any] = None,
    sources: Dict[str, Dict[str, str]] = None,
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

        dropped_stale = dropped_orphan = reattributed = redated = 0
        for event in events:
            if not isinstance(event, dict):
                continue
            # Stored events carry the run date they were last re-classified
            # on; the article's own date replaces it wherever the feed still
            # has the article. Done before the retention check, so a story
            # that was only ever "today" by accident now ages out properly.
            published = article_date(
                ((sources or {}).get(str(event.get("headline", "")).lower()) or {}).get(
                    "date"
                )
            )
            if published and published != event.get("date"):
                event.setdefault("first_seen", event.get("date"))
                event["date"] = published
                redated += 1
            if str(event.get("date", "")) < cutoff:
                dropped_stale += 1
                continue

            clause = event_clause(event)
            if event.get("reader") == "llm":
                # The LLM's parties, not the matcher's reading of the whole
                # headline — re-deriving would attribute every holding the
                # headline mentions. Only pruned to what is still held.
                held = {str(t).upper() for t, _ in holdings}
                event["actors"] = [a for a in event.get("actors") or [] if a in held]
                if event["actors"]:
                    refreshed.append(event)
                else:
                    dropped_orphan += 1
                continue
            actors = [
                ticker
                for ticker, name in holdings
                if title_matches_company(clause, ticker, name)
            ]
            # Re-derived for the same reason actors are: an event carried over
            # from before the graph knew about Marvell would otherwise keep an
            # empty external list for its whole 45-day retention, and the fix
            # that taught the graph about Marvell would never reach it.
            external = (
                graph_entities(clause, graph)
                if graph
                else (event.get("external") or [])
            )

            if actors != (event.get("actors") or []):
                reattributed += 1
            if not actors and not (event.get("domains") or []) and not external:
                dropped_orphan += 1
                continue

            event["actors"] = actors
            event["external"] = external
            if not event.get("certainty"):
                event["certainty"] = classify_certainty(clause)
            # Re-derived like actors, so the 45 days of tie-ups already in the
            # corpus gain their counterparty on the first run after this
            # shipped rather than only the ones classified from then on.
            counterparties = _counterparties(
                event.get("event_type"), clause, actors, holdings
            )
            if counterparties is None:
                event.pop("counterparties", None)
            else:
                event["counterparties"] = counterparties
            refreshed.append(event)

        if dropped_stale or dropped_orphan or reattributed or redated:
            log.info(
                f"Event corpus refresh: {reattributed} re-attributed, "
                f"{redated} re-dated to the article's date, "
                f"{dropped_orphan} no longer touch the watchlist, "
                f"{dropped_stale} past {EVENT_RETENTION_DAYS}d retention."
            )
    except Exception as e:  # noqa: BLE001 - housekeeping must not break a run
        log.warning(f"Event corpus refresh failed safely: {e!r}")
        return events
    return refreshed


def _financials_by_ticker(watchlist: Dict[str, Any]) -> Dict[str, Any]:
    from models.core import CompanyFinancials

    fins: Dict[str, Any] = {}
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        for stock in stocks or []:
            if not isinstance(stock, dict) or not stock.get("ticker"):
                continue
            sc = stock.get("screener")
            if isinstance(sc, dict):
                try:
                    fins[str(stock["ticker"]).upper()] = CompanyFinancials(**sc)
                except Exception:
                    continue
    return fins


def annotate_event_materiality(
    events: List[Dict[str, Any]], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """How big each event is, against the holding it happened to.

    analysis/materiality.py made this argument for scoring and for alerts and
    was never applied here, so "bags orders worth ₹94 crore" and "₹15,000
    crore acquisition" reached the event list as indistinguishable rows. Two
    fields, both ABSENT rather than null when nothing could be measured, so
    "not sized" never reads as "sized at zero":

      amount_cr     the figure, in crore, once the materiality guards have
                    agreed it belongs to one company — not a sector budget, a
                    share-price move or a joint venture's capital
      materiality   {TICKER: {pct_of_revenue, band}} per actor with revenue

    Measured on the event's own clause, not the whole headline. "X wins Rs
    500 crore order; stock rallies 5%" is two statements, and the price-move
    guard in the second would otherwise veto the order in the first — the
    same clause discipline the classifier already applies.

    Recomputed on every run, like attribution, because revenue moves and the
    guards get fixed. Never raises.
    """
    from analysis import materiality

    sized = 0
    try:
        fins = _financials_by_ticker(watchlist)
        for event in events or []:
            if not isinstance(event, dict):
                continue
            event.pop("amount_cr", None)
            event.pop("materiality", None)

            clause = event_clause(event)
            etype = event.get("event_type") or ""
            if not materiality.is_sized_event(etype, clause):
                continue
            amount = materiality.extract_amount_cr(clause)
            if amount is None:
                continue
            event["amount_cr"] = round(amount, 2)

            by_holding = {}
            for ticker in event.get("actors") or []:
                verdict = materiality.assess(
                    clause, etype, fins.get(str(ticker).upper())
                )
                if verdict.get("pct_of_revenue") is None:
                    continue
                by_holding[str(ticker).upper()] = {
                    "pct_of_revenue": verdict["pct_of_revenue"],
                    "band": verdict["band"],
                }
            if by_holding:
                event["materiality"] = by_holding
                sized += 1

        amounts = sum(
            1 for e in events or [] if isinstance(e, dict) and "amount_cr" in e
        )
        log.info(
            f"Event materiality: {amounts} event(s) carry an attributable amount; "
            f"{sized} sized against a holding's revenue."
        )
    except Exception as e:  # noqa: BLE001 - an enrichment must never break a run
        log.warning(f"Event materiality failed safely: {e!r}")
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
            # A rumoured disruption is not a disruption. Counting one toward
            # a sector's stress score would let speculation trip a threshold
            # built to measure things that actually happened.
            if event.get("certainty") == "reported":
                continue
            if event.get("reader") == "llm":
                continue  # unverified; see analysis/llm_reader.reconcile
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
        sector_of: Dict[str, str] = {}
        by_sector: Dict[str, list] = {}
        for sector, stocks in (watchlist or {}).items():
            for s in stocks or []:
                if isinstance(s, dict) and s.get("ticker"):
                    names[s["ticker"]] = s.get("name")
                    sector_of.setdefault(s["ticker"], sector)
                    by_sector.setdefault(sector, []).append(s["ticker"])

        emitted_per_sector: Dict[str, int] = {}

        def sector_label(sector):
            return SECTOR_METADATA.get(sector, {}).get("label", sector)

        for event in events:
            if not isinstance(event, dict):
                continue

            # External-only events are read-through material, not warning
            # material. They exist in the corpus because a headline naming a
            # graph entity and nothing else is now kept, which is what makes a
            # second-order chain derivable — but the anchor matching below
            # would turn a Google/Marvell tie-up into Ecosystem Signals on
            # every held sector, and that is exactly the hypothesis-into-
            # evidence leak read_through.py exists to avoid. Before those
            # events were kept they could not reach here at all; skipping them
            # restores that boundary rather than inventing a new one.
            if not (event.get("actors") or event.get("domains")):
                continue
            # Found only by the LLM reader: shown, never graded as evidence.
            if event.get("reader") == "llm":
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
                        # Its own sector, not "—": the email groups "sectors
                        # moving" by this field and printed "— (6)".
                        "sector": sector_label(sector_of.get(ticker, "")) or "—",
                        "severity": "Low",
                        "direction": event.get("direction", "opportunity"),
                        "category": "Corporate Move",
                        "signal": (
                            f"{etype.replace('_', ' ').title()}{qualifier}: "
                            f"“{headline}” ({_evidence_note(event)})"
                        ),
                        # The clause, kept apart from the prose, so the
                        # order-materiality pass sizes this alert by the same
                        # rule as every other headline-backed one. Without it a
                        # Corporate Move stayed Low whatever the deal was
                        # worth: that pass skips alerts with no source.
                        #
                        # Sized, and so escalated, only when the story is
                        # corroborated: the holding filed it with the
                        # exchange, or more than one outlet reported it. A
                        # single report can still be wrong about the amount
                        # or the company, and escalation is the one place a
                        # wrong number reaches the top of the email. Never
                        # for a reported (rumoured) deal.
                        **(
                            {
                                "source_headlines": [
                                    {"title": event_clause(event), "kind": etype}
                                ]
                            }
                            if certainty != "reported"
                            and evidence_level(event) != "single report"
                            else {}
                        ),
                        "evidence": evidence_level(event),
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
