"""Typed entity graph: the relationship substrate for second-order signals.

Follows the pattern proven by isin_master.json — a committed JSON data file,
offline-first, grown opportunistically, integrity-enforced by CI. Edges are
data, never code: {src, dst, type, note?, evidence, added}.

Edge types:
  anchor_demand     global demand anchor → exposed sector or holding
  supplier_customer directional commercial relationship
  partner           tie-up/JV (undirected — keyword harvesting can't infer
                    direction reliably, and routing doesn't need it)
  competitor        rivals (regenerated live from Screener peers, so rarely
                    persisted here); one curated with a ``scope`` ends at a
                    holding, for a rival in one of its lines
  input_cost        commodity/input keyword → cost-exposed sector or holding;
                    a ``not_scope`` names kinds of the input the exposure
                    does not cover ("AI chip" for boards of mature-node parts)

Aliases are data too: {canonical name: [other names]}. An edge names an
entity once, and headlines name it many ways. The matcher accepts a one-word
name only when the next word does not start another name, so that "ITC
Hotels" is never ITC, and that same rule read "Samsung Electronics", "Micron
Technology" and "Corning Incorporated" as companies other than Samsung,
Micron and Corning. Every edge involving them missed the commonest way they
are written. An alias also carries a parent ("Alphabet"), a subsidiary ("Hon
Hai", "Bharat FIH") or a product only its maker sells ("iPhone"). Matching
an alias yields the canonical name, so edges, chains and proposals meet one
spelling.

An alias must mean what the edges mean. "Google Cloud" is not one: its
headlines are IT-services deals (TCS, Accenture, Wipro), while Google's
edges are demand for data centres and devices.

The graph never blocks anything: an empty or missing file degrades every
consumer to Tier-1 vocabulary routing.
"""

import datetime
import os
import re
from typing import Any, Dict, Iterable, List, Tuple

from analysis.parsing import title_matches_company
from logger import log
from utils import atomic_write_json

GRAPH_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "entity_graph.json"
)

# Partner edges the pipeline has noticed but a person has not yet accepted.
# A separate file on purpose — see record_partner_proposals.
PROPOSALS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "entity_graph_proposals.json",
)

EDGE_TYPES = {
    "anchor_demand",
    "supplier_customer",
    "partner",
    "competitor",
    "input_cost",
}

# Tie-up vocabulary reused for edge harvesting (import here would be
# circular: event_engine imports competitive_intel which is unrelated, but
# entity_graph must stay import-light since event_engine imports it lazily).
_TIE_UP_MARKERS = (
    "joint venture",
    "partnership",
    "ties up",
    "tie-up",
    "mou",
    "collaboration",
    "alliance",
    "agreement with",
)


def _valid_edge(edge: Any) -> bool:
    return (
        isinstance(edge, dict)
        and bool(edge.get("src"))
        and bool(edge.get("dst"))
        and edge.get("type") in EDGE_TYPES
    )


def _valid_aliases(raw: Any) -> Dict[str, List[str]]:
    """{canonical: [alias, ...]}, keeping only non-empty strings."""
    if not isinstance(raw, dict):
        return {}
    aliases = {}
    for name, others in raw.items():
        if not isinstance(name, str) or not name.strip():
            continue
        kept = [
            str(o).strip()
            for o in (others if isinstance(others, list) else [])
            if isinstance(o, str) and o.strip()
        ]
        if kept:
            aliases[name.strip()] = kept
    return aliases


def load_entity_graph(path: str = GRAPH_PATH) -> Dict[str, Any]:
    """Committed graph; {"edges": [], "aliases": {}} on any problem —
    consumers degrade to Tier-1 routing, never break."""
    import json

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        edges = [e for e in (data.get("edges") or []) if _valid_edge(e)]
        return {"edges": edges, "aliases": _valid_aliases(data.get("aliases"))}
    except FileNotFoundError:
        return {"edges": [], "aliases": {}}
    except Exception as e:
        log.warning(f"Could not load entity_graph.json: {e}")
        return {"edges": [], "aliases": {}}


def save_entity_graph(graph: Dict[str, Any], path: str = GRAPH_PATH) -> bool:
    """Write the edges, and the aliases with them.

    A graph built without an "aliases" key keeps the ones already in the
    file: this is called by self-growth steps that only add edges, and a save
    that dropped the aliases would quietly undo every name they map.
    """
    try:
        edges = sorted(
            (e for e in graph.get("edges", []) if _valid_edge(e)),
            key=lambda e: (e["type"], str(e["src"]).lower(), str(e["dst"]).lower()),
        )
        if "aliases" in graph:
            aliases = _valid_aliases(graph.get("aliases"))
        else:
            aliases = load_entity_graph(path).get("aliases", {})
        atomic_write_json(
            {
                "edges": edges,
                "aliases": {k: aliases[k] for k in sorted(aliases, key=str.lower)},
            },
            path,
        )
        return True
    except Exception as e:
        log.warning(f"Could not save entity_graph.json: {e}")
        return False


def canonical_name(name: str, graph: Dict[str, Any]) -> str:
    """The graph's own spelling of ``name``: the canonical name an alias
    belongs to, matched without regard to case; ``name`` itself otherwise."""
    wanted = str(name or "").strip().lower()
    for canonical, others in ((graph or {}).get("aliases") or {}).items():
        if wanted == canonical.lower() or wanted in (o.lower() for o in others):
            return canonical
    return name


def names_mentioned(
    text: str, names: Iterable[str], graph: Dict[str, Any]
) -> List[str]:
    """Which of ``names`` (canonical) ``text`` mentions, by the name itself or
    any of its aliases, with the same word-boundary and person-guard rules as
    every other attribution."""
    aliases = (graph or {}).get("aliases") or {}
    lowered = {k.lower(): v for k, v in aliases.items()}
    return [
        name
        for name in names
        if any(
            title_matches_company(text, "", form)
            for form in [name] + list(lowered.get(str(name).lower(), ()))
        )
    ]


def _edge_key(edge: Dict[str, Any]):
    a, b = str(edge.get("src", "")).lower(), str(edge.get("dst", "")).lower()
    if edge.get("type") == "partner":  # undirected
        a, b = sorted((a, b))
    return (edge.get("type"), a, b)


def match_anchor_edges(headline: str, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Edges whose src entity is actually mentioned in the headline, by its
    name or an alias — word-boundary + person-guard matching, same standard
    as everywhere else. input_cost edges are excluded (their src is a
    commodity keyword handled by the stress computation, not a company
    name)."""
    edges = [e for e in (graph or {}).get("edges", []) if e.get("type") != "input_cost"]
    named = {
        n.lower()
        for n in names_mentioned(
            headline, sorted({str(e.get("src", "")) for e in edges}), graph
        )
    }
    return [e for e in edges if str(e.get("src", "")).lower() in named]


def harvest_partner_edges(
    agreements: List[Dict[str, Any]],
    watchlist: Dict[str, Any],
    graph: Dict[str, Any],
    path: str = GRAPH_PATH,
) -> int:
    """Self-growth: an agreements headline naming TWO known holdings with
    tie-up vocabulary proposes an undirected partner edge, evidence attached.
    Never overwrites, never raises; persists only when something was learned.
    """
    added = 0
    try:
        holdings = [
            (s.get("ticker", ""), s.get("name", ""))
            for stocks in (watchlist or {}).values()
            for s in stocks or []
            if isinstance(s, dict) and s.get("ticker")
        ]
        existing = {_edge_key(e) for e in graph.get("edges", [])}
        for item in agreements or []:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", ""))
            lower = title.lower()
            if not any(marker in lower for marker in _TIE_UP_MARKERS):
                continue
            named = [
                ticker
                for ticker, name in holdings
                if title_matches_company(title, ticker, name)
            ]
            if len(named) < 2:
                continue
            for i in range(len(named)):
                for j in range(i + 1, len(named)):
                    edge = {
                        "src": named[i],
                        "dst": named[j],
                        "type": "partner",
                        "evidence": title[:160],
                        "added": datetime.date.today().isoformat(),
                    }
                    if _edge_key(edge) in existing:
                        continue
                    existing.add(_edge_key(edge))
                    graph.setdefault("edges", []).append(edge)
                    added += 1
        if added:
            save_entity_graph(graph, path)
            log.info(
                f"Entity graph: {added} partner edge(s) harvested from agreements."
            )
    except Exception as e:
        log.warning(f"Partner-edge harvesting failed safely: {e!r}")
    return added


# ---------------------------------------------------------------------------
# Partner proposals: tie-ups with someone we do not hold, reviewed by a person
# ---------------------------------------------------------------------------

# How a reviewer marks a proposal. Anything else is reported, not guessed at:
# "accept" read silently as pending would look exactly like a proposal nobody
# had got to yet.
PROPOSAL_STATUSES = ("pending", "accepted", "rejected")

# A pending proposal nobody has seen a headline for in this long has aged out
# of relevance and is dropped, so the review queue stays a queue. Accepted and
# rejected entries are kept for good: they are the record that stops the same
# pair being proposed again.
PROPOSAL_STALE_DAYS = 90

# Headlines kept per proposal. Enough to judge it; the count is the signal.
MAX_PROPOSAL_EVIDENCE = 5

_REVIEW_NOTE = (
    "Partner edges proposed from completed tie-up headlines. Nothing here "
    "reaches the graph until you set status to 'accepted'; 'rejected' stops "
    "the pair being proposed again. You may correct 'counterparty' before "
    "accepting (e.g. 'Vivo Mobile' -> 'Vivo') — it is the name the graph will "
    "match in future headlines. Leave 'proposed_as' alone: it is how the "
    "pipeline recognises the same pair next time."
)


def _proposal_key(holding: str, name: str):
    return (str(holding or "").upper(), str(name or "").strip().lower())


def _same_party(proposals_by_key, key):
    """An existing proposal for the same holding under a longer or shorter name.

    Headlines name one company several ways — "Vivo" and "Vivo Mobile India",
    "Titagarh" and "Titagarh Rail Systems" — and queuing each as its own
    proposal asks the reviewer the same question twice. A whole-word prefix
    in either direction is treated as the same party; the name already in the
    queue is kept, since the reviewer may have corrected it. Whole words, so
    "Tata Power" and "Tata Steel" stay apart.
    """
    holding, name = key
    words = name.split()
    for (other_holding, other_name), proposal in proposals_by_key.items():
        if other_holding != holding:
            continue
        other = other_name.split()
        shorter, longer = sorted((words, other), key=len)
        if shorter and longer[: len(shorter)] == shorter:
            return proposal
    return None


def load_proposals(path: str = PROPOSALS_PATH) -> List[Dict[str, Any]]:
    import json

    try:
        with open(path, "r", encoding="utf-8") as f:
            body = json.load(f)
        return [p for p in (body.get("proposals") or []) if isinstance(p, dict)]
    except FileNotFoundError:
        return []
    except Exception as e:
        # Not an empty queue — an unreadable one. Saying so matters, because
        # the next save would otherwise overwrite a reviewer's decisions.
        log.warning(f"Could not read {os.path.basename(path)}: {e!r}")
        return None


def _save_proposals(proposals: List[Dict[str, Any]], path: str) -> None:
    order = {"pending": 0, "accepted": 1, "rejected": 2}
    proposals.sort(
        key=lambda p: (
            order.get(p.get("status"), 0),
            -len(p.get("evidence") or []),
            str(p.get("holding", "")),
            str(p.get("proposed_as", "")).lower(),
        )
    )
    atomic_write_json({"_how_to_review": _REVIEW_NOTE, "proposals": proposals}, path)


def apply_accepted_proposals(
    graph: Dict[str, Any],
    path: str = PROPOSALS_PATH,
    graph_path: str = GRAPH_PATH,
) -> int:
    """Move every proposal a person marked ``accepted`` into the graph.

    Run BEFORE classification, so an edge accepted overnight is already known
    to graph_entities when today's headlines are read — otherwise the first
    headline about the new partner would be classified without it.

    The edge's ``evidence`` is the headline that proposed it, not "curated".
    A reviewer confirmed the relationship exists; nobody has written down what
    it is worth, and read_through grades a chain by its weakest link on
    exactly that distinction. Promote it by hand if it earns the upgrade.
    """
    added = 0
    try:
        proposals = load_proposals(path)
        if not proposals:
            return 0
        existing = {_edge_key(e) for e in graph.get("edges", [])}
        today = datetime.date.today().isoformat()
        for p in proposals:
            status = p.get("status")
            if status not in PROPOSAL_STATUSES:
                log.warning(
                    f"Partner proposal {p.get('holding')} ↔ "
                    f"{p.get('counterparty')}: status {status!r} is not one of "
                    f"{', '.join(PROPOSAL_STATUSES)} — left unapplied."
                )
                continue
            if status != "accepted":
                continue
            name = canonical_name(
                str(p.get("counterparty") or p.get("proposed_as") or "").strip(), graph
            )
            holding = str(p.get("holding") or "").upper()
            if not name or not holding:
                continue
            evidence = (p.get("evidence") or [{}])[0]
            edge = {
                "src": name,
                "dst": holding,
                "type": "partner",
                "evidence": str(evidence.get("headline") or "")[:160],
                "added": today,
                "note": "Accepted from partner proposals",
            }
            if evidence.get("link"):
                edge["link"] = evidence["link"]
            if _edge_key(edge) in existing:
                continue
            existing.add(_edge_key(edge))
            graph.setdefault("edges", []).append(edge)
            added += 1
        if added:
            save_entity_graph(graph, graph_path)
            log.info(f"Entity graph: {added} reviewed partner edge(s) accepted.")
    except Exception as e:  # noqa: BLE001 - graph growth must never break a run
        log.warning(f"Applying partner proposals failed safely: {e!r}")
    return added


def _namesake_index(namesakes: Iterable[Tuple[str, str]]) -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {}
    for ticker, headline in namesakes or ():
        index.setdefault(str(ticker).upper(), []).append(headline)
    return index


def _is_namesake(index: Dict[str, List[str]], holding: str, headline: str) -> bool:
    """Prefix either way: the thesis cache keeps a headline's first 200
    characters, the corpus keeps it whole."""
    h = re.sub(r"\s+", " ", str(headline or "").strip().lower())
    return bool(h) and any(
        h.startswith(n) or n.startswith(h) for n in index.get(str(holding).upper(), ())
    )


def _drop_namesake_evidence(proposals, index) -> int:
    """Strip namesake headlines from pending proposals; drop any left empty.

    Pending only: an accepted or rejected pair is a reviewer's decision, and
    its evidence is the record of what they decided on.
    """
    dropped = 0
    for p in list(proposals):
        if p.get("status") != "pending" or not p.get("evidence"):
            continue
        kept = [
            e
            for e in p["evidence"]
            if not _is_namesake(index, p.get("holding"), e.get("headline"))
        ]
        if len(kept) == len(p["evidence"]):
            continue
        if kept:
            p["evidence"] = kept
        else:
            proposals.remove(p)
            dropped += 1
    return dropped


def drop_namesake_proposals(
    namesakes: Iterable[Tuple[str, str]], path: str = PROPOSALS_PATH
) -> int:
    """After the thesis check: take back what it read as somebody else's news.

    Partner proposals are recorded before the thesis check runs, so a
    namesake headline first seen today has already been queued once. This
    removes it again before the queue is committed. From the next run on,
    record_partner_proposals knows it from the cache and never queues it.
    Never raises.
    """
    try:
        index = _namesake_index(namesakes)
        if not index:
            return 0
        proposals = load_proposals(path)
        if not proposals:
            return 0
        before = [dict(p, evidence=list(p.get("evidence") or [])) for p in proposals]
        dropped = _drop_namesake_evidence(proposals, index)
        if proposals != before:
            _save_proposals(proposals, path)
            log.info(
                f"Partner proposals: {dropped} dropped as another company's news "
                "(thesis check, LLM reading)."
            )
        return dropped
    except Exception as e:  # noqa: BLE001 - graph growth must never break a run
        log.warning(f"Dropping namesake proposals failed safely: {e!r}")
        return 0


def record_partner_proposals(
    events: List[Dict[str, Any]],
    graph: Dict[str, Any],
    path: str = PROPOSALS_PATH,
    today: str = "",
    namesakes: Iterable[Tuple[str, str]] = (),
) -> Dict[str, int]:
    """Propose a partner edge for every completed tie-up with a named counterparty.

    Proposals, not edges. harvest_partner_edges above writes straight into the
    graph, and can afford to: both of its parties are holdings, resolved by
    the same matcher as everything else. A counterparty is a name read out of
    headline structure, and a wrong one does not produce a wrong number — it
    produces a plausible chain ("Kaga is Syrma's partner, so ...") that reads
    exactly like a right one. The graph is only worth its reasoning if its
    edges are true, so a person looks first.

    Only ``completed`` tie-ups. An MoU is announced, not done, and most never
    become anything a share price notices.

    ``namesakes`` are (TICKER, headline) pairs the thesis check read as being
    about somebody else (thesis_check.namesake_headlines): Siemens AG's deals
    are not Siemens Ltd's partners. They are never queued, and pending
    proposals resting on them are taken back.

    Returns counts for the log line and tests. Never raises.
    """
    counts = {
        "new": 0,
        "seen_again": 0,
        "pending": 0,
        "dropped_stale": 0,
        "dropped_namesake": 0,
    }
    try:
        proposals = load_proposals(path)
        if proposals is None:
            return counts  # unreadable — never overwrite a reviewer's file
        today = today or datetime.date.today().isoformat()
        elsewhere = _namesake_index(namesakes)
        evidence_before = sum(len(p.get("evidence") or []) for p in proposals)
        counts["dropped_namesake"] = _drop_namesake_evidence(proposals, elsewhere)
        trimmed = (
            sum(len(p.get("evidence") or []) for p in proposals) != evidence_before
        )
        by_key = {
            _proposal_key(p.get("holding"), p.get("proposed_as")): p for p in proposals
        }
        known_edges = {_edge_key(e) for e in graph.get("edges", [])}

        for event in events or []:
            if not isinstance(event, dict):
                continue
            if event.get("event_type") != "tie_up":
                continue
            if event.get("certainty") != "completed":
                continue
            headline = str(event.get("headline") or "")
            for holding in event.get("actors") or []:
                if _is_namesake(elsewhere, holding, headline):
                    continue  # somebody else's deal under our name
                for name in event.get("counterparties") or []:
                    # "Hon Hai" is Foxconn: one pair, under the graph's name.
                    name = canonical_name(name, graph)
                    edge = {"src": name, "dst": holding, "type": "partner"}
                    if _edge_key(edge) in known_edges:
                        continue  # already in the graph; nothing to review
                    key = _proposal_key(holding, name)
                    proposal = by_key.get(key) or _same_party(by_key, key)
                    if proposal is None:
                        proposal = {
                            "holding": key[0],
                            "counterparty": name,
                            "proposed_as": name,
                            "status": "pending",
                            "first_seen": event.get("date") or today,
                            "last_seen": event.get("date") or today,
                            "evidence": [],
                        }
                        by_key[key] = proposal
                        proposals.append(proposal)
                        counts["new"] += 1
                    elif proposal.get("status") != "pending":
                        # Decided. A rejection is final, and an accepted pair
                        # the reviewer renamed is already in the graph under
                        # its corrected name.
                        continue
                    elif proposal.get("counterparty") == proposal.get(
                        "proposed_as"
                    ) and len(name) < len(str(proposal.get("proposed_as") or "")):
                        # Same party, shorter name, and nobody has corrected
                        # it yet: take the shorter one. It is the better
                        # graph entity — an edge only fires when its name
                        # appears in a headline, and "Vivo" appears in every
                        # "Vivo Mobile India" headline but not the reverse.
                        proposal["counterparty"] = proposal["proposed_as"] = name
                        by_key[key] = proposal
                    evidence = proposal.setdefault("evidence", [])
                    # A full list cannot tell a new headline from one already
                    # counted, so it stops counting rather than inflating: the
                    # queue shows "5+" and five is already a strong case.
                    if len(evidence) >= MAX_PROPOSAL_EVIDENCE or any(
                        str(e.get("headline", "")).lower() == headline.lower()
                        for e in evidence
                    ):
                        continue
                    if evidence:
                        counts["seen_again"] += 1
                    citation = {k: event[k] for k in ("link", "source") if event.get(k)}
                    evidence.append(
                        {
                            "headline": headline,
                            "date": event.get("date") or "",
                            **citation,
                        }
                    )
                    proposal["last_seen"] = max(
                        str(proposal.get("last_seen") or ""),
                        str(event.get("date") or today),
                    )

        cutoff = (
            datetime.date.fromisoformat(today)
            - datetime.timedelta(days=PROPOSAL_STALE_DAYS)
        ).isoformat()
        kept = []
        for p in proposals:
            if p.get("status") == "pending" and str(p.get("last_seen", "")) < cutoff:
                counts["dropped_stale"] += 1
                continue
            kept.append(p)
        counts["pending"] = sum(1 for p in kept if p.get("status") == "pending")

        if counts["new"] or counts["seen_again"] or counts["dropped_stale"] or trimmed:
            _save_proposals(kept, path)
        log.info(
            f"Partner proposals: {counts['new']} new, {counts['seen_again']} "
            f"re-sighted, {counts['dropped_stale']} aged out, "
            f"{counts['dropped_namesake']} dropped as another company's news; "
            f"{counts['pending']} awaiting review."
        )
    except Exception as e:  # noqa: BLE001 - graph growth must never break a run
        log.warning(f"Recording partner proposals failed safely: {e!r}")
    return counts
