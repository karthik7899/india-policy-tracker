"""Tests for the generic market-event engine and the typed entity graph."""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.entity_graph import (  # noqa: E402
    harvest_partner_edges,
    load_entity_graph,
    match_anchor_edges,
    save_entity_graph,
)
from analysis.event_engine import (  # noqa: E402
    classify_headlines,
    compute_supply_stress,
    market_event_signals,
)
from config import SECTOR_METADATA  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TODAY = datetime.date.today().isoformat()

_WATCHLIST = {
    "manufacturing_electronics": [
        {"ticker": "DIXON", "name": "Dixon Technologies"},
        {"ticker": "KAYNES", "name": "Kaynes Technology"},
    ],
    "clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}],
}


def _data(*titles):
    return {"corporate_agreements": [{"title": t} for t in titles]}


# ---------------------------------------------------------------------------
# classification — generic by construction (no entity is special)
# ---------------------------------------------------------------------------


def test_big_tech_deal_classifies_and_routes_by_vocabulary_alone():
    """The Broadcom-class case: neither company is in any watchlist or graph,
    yet the event classifies and lands on the right sector via Tier 1."""
    events = classify_headlines(
        _data("MegaCorp signs multiyear commitment for custom smartphone chips"),
        _WATCHLIST,
    )
    assert len(events) == 1
    assert events[0]["event_type"] == "capacity_add"
    assert "manufacturing_electronics" in events[0]["domains"]
    assert events[0]["actors"] == []  # nobody we track is named — still routed


def test_supply_disruption_classification():
    events = classify_headlines(
        _data("Rare earth export restriction threatens electronics manufacturing"),
        _WATCHLIST,
    )
    assert len(events) == 1
    assert events[0]["event_type"] == "supply_disruption"
    assert events[0]["direction"] == "risk"


def test_holding_actor_is_attributed():
    events = classify_headlines(
        _data("Dixon Technologies wins order for smartphone assembly"), _WATCHLIST
    )
    assert events[0]["actors"] == ["DIXON"]
    assert events[0]["event_type"] == "order_win"


def test_negated_moves_are_dropped():
    events = classify_headlines(
        _data("MegaCorp denies plans for smartphone joint venture"), _WATCHLIST
    )
    assert events == []


def test_untracked_domains_are_dropped():
    events = classify_headlines(
        _data("Two foreign banks announce partnership with fintech"), _WATCHLIST
    )
    assert events == []


def test_classifier_never_raises():
    assert classify_headlines(None, None) == []
    assert classify_headlines({"corporate_agreements": "junk"}, _WATCHLIST) == []


# ---------------------------------------------------------------------------
# supply stress — rolling window + input_cost edges
# ---------------------------------------------------------------------------

_GRAPH = {
    "edges": [
        {"src": "copper", "dst": "clean_energy", "type": "input_cost"},
        {
            "src": "MegaCorp",
            "dst": "manufacturing_electronics",
            "type": "anchor_demand",
        },
    ]
}


def test_stress_counts_recent_risk_events_only():
    old = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    events = [
        {
            "event_type": "supply_disruption",
            "domains": ["manufacturing_electronics"],
            "headline": "chip shortage",
            "date": _TODAY,
        },
        {
            "event_type": "input_cost_shock",
            "domains": [],
            "headline": "copper prices surge on mine outage",
            "date": _TODAY,
        },
        {
            "event_type": "supply_disruption",
            "domains": ["manufacturing_electronics"],
            "headline": "old news",
            "date": old,
        },
        {
            "event_type": "tie_up",
            "domains": ["manufacturing_electronics"],
            "headline": "not a risk",
            "date": _TODAY,
        },
    ]
    stress = compute_supply_stress(events, _GRAPH)
    assert stress == {"manufacturing_electronics": 1, "clean_energy": 1}


# ---------------------------------------------------------------------------
# signals — direct, anchor-edge, tier-1, forward stress
# ---------------------------------------------------------------------------


def test_signals_two_tier_routing(monkeypatch):
    import analysis.event_engine as ee
    import analysis.entity_graph as eg

    monkeypatch.setattr(eg, "load_entity_graph", lambda path=None: _GRAPH)

    data = {
        "market_events": [
            {
                "headline": "MegaCorp signs multiyear commitment for smartphone chips",
                "event_type": "capacity_add",
                "domains": ["manufacturing_electronics"],
                "actors": [],
                "direction": "opportunity",
                "date": _TODAY,
            },
            {
                "headline": "Rare earth export ban hits electronics manufacturing",
                "event_type": "supply_disruption",
                "domains": ["manufacturing_electronics"],
                "actors": [],
                "direction": "risk",
                "date": _TODAY,
            },
        ],
        "supply_stress": {"manufacturing_electronics": 3},
    }
    signals = ee.market_event_signals(data, _WATCHLIST)
    categories = {s["category"] for s in signals}
    assert "Ecosystem Signal" in categories  # Tier 2 via MegaCorp anchor edge
    assert "Supply Chain" in categories  # Tier 1 risk propagation
    assert "Supply Stress (Forward)" in categories  # sustained-stress escalation
    eco = next(s for s in signals if s["category"] == "Ecosystem Signal")
    assert "MegaCorp" in eco["signal"] and "anchor_demand" in eco["signal"]
    assert eco["ticker"] in {"DIXON", "KAYNES"}
    forward = [s for s in signals if s["category"] == "Supply Stress (Forward)"]
    assert {s["ticker"] for s in forward} == {"DIXON", "KAYNES"}


def test_direct_actor_gets_corporate_move_signal(monkeypatch):
    import analysis.event_engine as ee
    import analysis.entity_graph as eg

    monkeypatch.setattr(eg, "load_entity_graph", lambda path=None: {"edges": []})
    data = {
        "market_events": [
            {
                "headline": "Suzlon Energy wins order for 300MW wind turbines",
                "event_type": "order_win",
                "domains": ["clean_energy"],
                "actors": ["SUZLON"],
                "direction": "opportunity",
                "date": _TODAY,
            }
        ]
    }
    signals = ee.market_event_signals(data, _WATCHLIST)
    moves = [s for s in signals if s["category"] == "Corporate Move"]
    assert len(moves) == 1 and moves[0]["ticker"] == "SUZLON"


def test_signals_never_raise():
    assert market_event_signals({}, _WATCHLIST) == []
    assert market_event_signals(None, None) == []


# ---------------------------------------------------------------------------
# entity graph — load/save, anchor matching, self-growth, committed integrity
# ---------------------------------------------------------------------------


def test_graph_roundtrip_and_validation(tmp_path):
    path = str(tmp_path / "graph.json")
    graph = {
        "edges": [
            {"src": "A", "dst": "B", "type": "partner"},
            {"src": "bad", "dst": "", "type": "partner"},  # invalid: no dst
            {"src": "C", "dst": "D", "type": "not_a_type"},  # invalid type
        ]
    }
    assert save_entity_graph(graph, path)
    loaded = load_entity_graph(path)
    assert len(loaded["edges"]) == 1
    assert load_entity_graph(str(tmp_path / "missing.json")) == {"edges": []}


def test_match_anchor_edges_uses_word_boundary_matching():
    hits = match_anchor_edges("MegaCorp signs multiyear chip commitment", _GRAPH)
    assert len(hits) == 1 and hits[0]["dst"] == "manufacturing_electronics"
    # input_cost edges never match as anchors, and substrings don't count.
    assert match_anchor_edges("copper prices surge", _GRAPH) == []
    assert match_anchor_edges("MegaCorporation expands", _GRAPH) == []


def test_harvest_partner_edges_from_agreements(tmp_path):
    path = str(tmp_path / "graph.json")
    graph = {"edges": []}
    agreements = [
        {"title": "Dixon Technologies signs joint venture with Kaynes Technology"},
        {"title": "Dixon Technologies reports quarterly results"},  # no tie-up vocab
    ]
    added = harvest_partner_edges(agreements, _WATCHLIST, graph, path)
    assert added == 1
    edge = graph["edges"][0]
    assert {edge["src"], edge["dst"]} == {"DIXON", "KAYNES"}
    assert edge["type"] == "partner"
    assert "joint venture" in edge["evidence"].lower()
    # Idempotent: same headline again adds nothing.
    assert harvest_partner_edges(agreements, _WATCHLIST, graph, path) == 0


def test_committed_graph_is_well_formed():
    graph = load_entity_graph(os.path.join(_REPO_ROOT, "entity_graph.json"))
    assert len(graph["edges"]) >= 30
    for edge in graph["edges"]:
        dst = edge["dst"]
        # Every destination must be a real sector key or a plausible ticker.
        assert dst in SECTOR_METADATA or dst == dst.upper(), edge


def test_committed_graph_json_parses_raw():
    with open(os.path.join(_REPO_ROOT, "entity_graph.json"), encoding="utf-8") as f:
        raw = json.load(f)
    assert isinstance(raw.get("edges"), list)
