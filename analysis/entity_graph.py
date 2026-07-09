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
                    persisted here)
  input_cost        commodity/input keyword → cost-exposed sector

The graph never blocks anything: an empty or missing file degrades every
consumer to Tier-1 vocabulary routing.
"""

import datetime
import os
from typing import Any, Dict, List

from analysis.parsing import title_matches_company
from logger import log
from utils import atomic_write_json

GRAPH_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "entity_graph.json"
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


def load_entity_graph(path: str = GRAPH_PATH) -> Dict[str, Any]:
    """Committed graph; {"edges": []} on any problem — consumers degrade to
    Tier-1 routing, never break."""
    import json

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        edges = [e for e in (data.get("edges") or []) if _valid_edge(e)]
        return {"edges": edges}
    except FileNotFoundError:
        return {"edges": []}
    except Exception as e:
        log.warning(f"Could not load entity_graph.json: {e}")
        return {"edges": []}


def save_entity_graph(graph: Dict[str, Any], path: str = GRAPH_PATH) -> bool:
    try:
        edges = sorted(
            (e for e in graph.get("edges", []) if _valid_edge(e)),
            key=lambda e: (e["type"], str(e["src"]).lower(), str(e["dst"]).lower()),
        )
        atomic_write_json({"edges": edges}, path)
        return True
    except Exception as e:
        log.warning(f"Could not save entity_graph.json: {e}")
        return False


def _edge_key(edge: Dict[str, Any]):
    a, b = str(edge.get("src", "")).lower(), str(edge.get("dst", "")).lower()
    if edge.get("type") == "partner":  # undirected
        a, b = sorted((a, b))
    return (edge.get("type"), a, b)


def match_anchor_edges(headline: str, graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Edges whose src entity is actually mentioned in the headline —
    word-boundary + person-guard matching, same standard as everywhere else.
    input_cost edges are excluded (their src is a commodity keyword handled
    by the stress computation, not a company name)."""
    hits = []
    for edge in (graph or {}).get("edges", []):
        if edge.get("type") in ("input_cost",):
            continue
        if title_matches_company(headline, "", str(edge.get("src", ""))):
            hits.append(edge)
    return hits


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
