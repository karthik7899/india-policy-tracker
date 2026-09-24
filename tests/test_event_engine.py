"""Tests for the generic market-event engine and the typed entity graph."""

import datetime
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.entity_graph import (  # noqa: E402
    harvest_partner_edges,
    load_entity_graph,
    match_anchor_edges,
    save_entity_graph,
)
from analysis.competitive_intel import (  # noqa: E402
    collect_headlines,
    collect_sources,
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
    """What a destination may be depends on what the edge means.

    anchor_demand and input_cost both terminate at something we hold — a
    sector, or a holding by ticker — because their whole job is to route
    outside news onto the book. competitor and supplier_customer do not: they
    relate two outside entities to each other, and their destination is a
    company name. Requiring a sector there was right while those two edge
    types were declared and unused, and became wrong the moment they carried
    anything.
    """
    graph = load_entity_graph(os.path.join(_REPO_ROOT, "entity_graph.json"))
    assert len(graph["edges"]) >= 30

    terminal = {"anchor_demand", "input_cost", "partner"}
    relational = {"competitor", "supplier_customer"}

    for edge in graph["edges"]:
        dst = edge["dst"]
        if edge["type"] in terminal:
            # A real sector key or a plausible ticker.
            assert dst in SECTOR_METADATA or dst == dst.upper(), edge
        else:
            assert edge["type"] in relational, edge
            # An entity name: non-empty, and not a sector key masquerading as
            # one, which would mean a relational edge had been mis-typed.
            assert dst and dst not in SECTOR_METADATA, edge


def test_relational_edges_reach_a_sector_in_two_hops():
    """A competitor or supplier edge that leads nowhere we hold is inert.

    Every one of them exists to complete a read-through chain, and a chain
    ends at an anchor_demand edge. One that cannot reach a sector is either a
    typo in an entity name or a relationship nobody can act on; both are worth
    catching here rather than discovering as a silently missing flag.
    """
    graph = load_entity_graph(os.path.join(_REPO_ROOT, "entity_graph.json"))
    anchored = {
        str(e["src"]).lower() for e in graph["edges"] if e["type"] == "anchor_demand"
    }
    for edge in graph["edges"]:
        if edge["type"] not in ("competitor", "supplier_customer"):
            continue
        ends = {str(edge["src"]).lower(), str(edge["dst"]).lower()}
        assert ends & anchored, f"neither end anchors to a sector: {edge}"


def test_committed_graph_json_parses_raw():
    with open(os.path.join(_REPO_ROOT, "entity_graph.json"), encoding="utf-8") as f:
        raw = json.load(f)
    assert isinstance(raw.get("edges"), list)


# ---------------------------------------------------------------------------
# clause scoping and certainty
# ---------------------------------------------------------------------------

from analysis.event_engine import (  # noqa: E402
    classify_certainty,
    split_clauses,
)


def test_split_clauses_on_headline_punctuation():
    assert split_clauses(
        "ITC Hotels to acquire GHK Hospitality for Rs 155 crore; shares decline 5%"
    ) == [
        "ITC Hotels to acquire GHK Hospitality for Rs 155 crore",
        "shares decline 5%",
    ]
    # Nothing to split on -> unchanged, so single-clause headlines behave
    # exactly as they did before.
    assert split_clauses("Suzlon wins a 300MW order") == ["Suzlon wins a 300MW order"]
    assert split_clauses("") == []


def test_certainty_reads_intent_and_rumour_as_such():
    """The three real headlines that were being recorded as completed."""
    assert (
        classify_certainty("Schneider Electric Announces Intention To Acquire Cognite")
        == "announced"
    )
    assert (
        classify_certainty(
            "Dixon Tech Up Almost 1% Intraday on Reports of Govt Approval "
            "Likely to Vivo Joint Venture"
        )
        == "reported"
    )
    assert classify_certainty("Siemens to acquire RTL design automation") == "announced"
    assert classify_certainty("Suzlon signed a 300MW contract") == "completed"


def test_weakest_reading_wins():
    """A reported intention is a rumour, not an announcement."""
    assert classify_certainty("Reportedly plans to acquire a rival") == "reported"


def test_negation_in_one_clause_does_not_kill_another():
    """Regression: negation was matched against the whole headline.

    "A calls off talks; B wins order" dropped B's genuine order win because
    the denial lived in a different clause.
    """
    wl = {"sec": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    data = {
        "sec": [
            {"title": "Rival calls off merger talks; Suzlon wins order worth 300cr"}
        ]
    }
    events = classify_headlines(data, wl)
    assert len(events) == 1
    assert events[0]["event_type"] == "order_win"
    assert events[0]["actors"] == ["SUZLON"]


def test_actor_must_share_a_clause_with_the_event():
    """Attribution is relational: a company in the reaction clause did not
    do the thing described in the first one."""
    wl = {"sec": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    data = {
        "sec": [{"title": "Rival bags order worth 500cr; Suzlon shares decline 5%"}]
    }
    events = classify_headlines(data, wl)
    assert events == [] or events[0]["actors"] == []


def test_events_carry_certainty():
    wl = {"sec": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    data = {"sec": [{"title": "Suzlon reportedly in talks for a joint venture"}]}
    events = classify_headlines(data, wl)
    assert events[0]["certainty"] == "reported"


def test_rumoured_disruption_is_excluded_from_supply_stress():
    """Speculation must not trip a threshold built for real events."""
    import datetime

    today = datetime.date.today().isoformat()
    # A real sector key: compute_supply_stress only counts sectors it tracks.
    rumour = {
        "event_type": "supply_disruption",
        "certainty": "reported",
        "domains": ["clean_energy"],
        "date": today,
    }
    real = dict(rumour, certainty="completed")
    assert compute_supply_stress([rumour, rumour], {}) == {}
    assert compute_supply_stress([real, real], {}).get("clean_energy") == 2


# ---------------------------------------------------------------------------
# corpus refresh: corrections must reach events carried over from prior runs
# ---------------------------------------------------------------------------

from analysis.event_engine import (  # noqa: E402
    EVENT_RETENTION_DAYS,
    refresh_merged_events,
)


def test_reattribution_drops_a_correction_that_the_matcher_now_rejects():
    """Regression: three ITC Hotels events stayed attributed to ITC.

    Events merge across runs, so the entity-boundary fix only applied to
    what was classified that day. Per-stock coverage reads these actors
    directly, so the stale rows were still on ITC's card the next morning.
    """
    import datetime

    today = datetime.date.today().isoformat()
    merged = [
        {
            "headline": "ITC Hotels to acquire GHK Hospitality for Rs 155 crore",
            "event_type": "acquisition",
            "phrase": "to acquire",
            "domains": [],
            "actors": ["ITC"],  # attributed by the old matcher
            "date": today,
        }
    ]
    wl = {"fmcg": [{"ticker": "ITC", "name": "ITC Ltd"}]}
    # No actors left and no domains -> it touches nothing we track.
    assert refresh_merged_events(merged, wl) == []


def test_reattribution_keeps_and_updates_a_genuine_event():
    import datetime

    today = datetime.date.today().isoformat()
    merged = [
        {
            "headline": "Suzlon wins order worth 300cr",
            "event_type": "order_win",
            "phrase": "order worth",
            "domains": [],
            "actors": [],
            "date": today,
        }
    ]
    wl = {"clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    out = refresh_merged_events(merged, wl)
    assert out[0]["actors"] == ["SUZLON"]
    assert out[0]["certainty"] == "completed"


def test_certainty_backfilled_for_rows_predating_the_field():
    import datetime

    today = datetime.date.today().isoformat()
    merged = [
        {
            "headline": "Suzlon reportedly in talks for a joint venture",
            "event_type": "tie_up",
            "phrase": "joint venture",
            "domains": [],
            "actors": ["SUZLON"],
            "date": today,
        }
    ]
    wl = {"clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    assert refresh_merged_events(merged, wl)[0]["certainty"] == "reported"


def test_events_past_retention_are_dropped():
    import datetime

    old = (
        datetime.date.today() - datetime.timedelta(days=EVENT_RETENTION_DAYS + 1)
    ).isoformat()
    merged = [
        {
            "headline": "Suzlon wins order worth 300cr",
            "event_type": "order_win",
            "phrase": "order worth",
            "domains": ["clean_energy"],
            "actors": ["SUZLON"],
            "date": old,
        }
    ]
    wl = {"clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    assert refresh_merged_events(merged, wl) == []


def test_refresh_never_raises_and_returns_input_on_failure():
    assert refresh_merged_events([], {}) == []
    assert refresh_merged_events(None, {}) == []
    # Junk rows are skipped, not fatal.
    assert refresh_merged_events([None, "junk"], {"s": []}) == []


# ---------------------------------------------------------------------------
# Regressions found in production on 14 Sep
# ---------------------------------------------------------------------------


def test_a_truncated_headline_matches_no_anchor_edge():
    """Found via the read-through feature, but this was never about it.

    match_anchor_edges passes an empty ticker, and the matcher's empty
    candidate compared equal to the empty token a trailing "..." leaves behind.
    51 of 74 anchor edges matched a headline naming none of them, which had
    been firing spurious Ecosystem Signal warnings on every truncated headline
    since long before read-throughs existed.
    """
    graph = load_entity_graph(os.path.join(_REPO_ROOT, "entity_graph.json"))
    truncated = "Morgan Stanley bullish on Reliance Industries, sees 28%... "
    assert match_anchor_edges(truncated, graph) == []

    # And a headline that really does name an anchor still matches.
    real = "Apple expands India manufacturing with new supplier agreements"
    assert any(e["src"] == "Apple" for e in match_anchor_edges(real, graph))


def test_external_only_events_do_not_reach_the_warning_engine(monkeypatch):
    """Read-through material must not become graded evidence.

    A headline naming only graph entities is kept in the corpus so a chain can
    be derived from it. The warning engine's anchor matching would otherwise
    turn it into Ecosystem Signals on every held sector — the exact
    hypothesis-into-evidence leak the separation exists to prevent.
    """
    import analysis.entity_graph as eg
    import analysis.event_engine as ee

    monkeypatch.setattr(eg, "load_entity_graph", lambda path=None: _GRAPH)
    data = {
        "market_events": [
            {
                "headline": "MegaCorp ties up with a rival for smartphone chips",
                "event_type": "tie_up",
                "domains": [],
                "actors": [],
                "external": ["MegaCorp"],
                "direction": "opportunity",
                "date": _TODAY,
            }
        ]
    }
    assert ee.market_event_signals(data, _WATCHLIST) == []

    # The same event, once it genuinely touches a sector, still produces one.
    data["market_events"][0]["domains"] = ["manufacturing_electronics"]
    assert ee.market_event_signals(data, _WATCHLIST) != []


class TestAClassifiedEventCitesItsArticle:
    """An event that names a headline but cannot be traced to it is an
    assertion the reader has to take on faith.

    collect_headlines returned bare strings, so the `link` on every source
    record was dropped at that exact point — every classified event, every
    read-through and every headline-derived warning lost its URL there.
    """

    _WL = {
        "aerospace_defence": [{"ticker": "BHEL", "name": "Bharat Heavy Electricals"}]
    }

    def test_the_link_reaches_the_event(self):
        data = {
            "corporate_agreements": [
                {
                    "title": "BHEL partners with Titagarh on rail maintenance",
                    "link": "https://example.test/bhel",
                    "source": "Mint",
                }
            ]
        }
        (event,) = classify_headlines(data, self._WL)
        assert event["link"] == "https://example.test/bhel"
        assert event["source"] == "Mint"

    def test_a_feed_with_no_link_omits_the_key_rather_than_writing_empty(self):
        """ "No link" and "" are different facts, and a consumer checking for a
        citation must be able to tell them apart."""
        data = {
            "corporate_agreements": [
                {"title": "BHEL partners with Titagarh on rail maintenance"}
            ]
        }
        (event,) = classify_headlines(data, self._WL)
        assert "link" not in event

    def test_the_index_is_keyed_to_what_collect_headlines_returns(self):
        """Not a fuzzy re-match on normalised text: same pass, same key, so a
        caller holding a headline can always look its citation back up."""
        data = {
            "corporate_agreements": [
                {"title": "  BHEL Partners With Titagarh  ", "link": "https://x.test/1"}
            ]
        }
        headlines = collect_headlines(data, self._WL)
        sources = collect_sources(data, self._WL)
        assert headlines == ["BHEL Partners With Titagarh"]
        assert sources[headlines[0].lower()]["link"] == "https://x.test/1"

    def test_first_writer_wins_matching_the_dedupe_above_it(self):
        data = {
            "corporate_agreements": [
                {"title": "Same story", "link": "https://first.test"},
                {"title": "same story", "link": "https://second.test"},
            ]
        }
        assert (
            collect_sources(data, self._WL)["same story"]["link"]
            == "https://first.test"
        )


# ---------------------------------------------------------------------------
# counterparties and size on the event itself
# ---------------------------------------------------------------------------

from analysis.event_engine import annotate_event_materiality  # noqa: E402

_EMS = {
    "manufacturing_electronics": [
        {
            "ticker": "SYRMA",
            "name": "Syrma SGS Tech.",
            # Rs 4,000 crore TTM
            "screener": {"sales_trend": [1000.0, 1000.0, 1000.0, 1000.0]},
        },
        {"ticker": "DIXON", "name": "Dixon Technologies"},
    ],
    "aerospace_defence": [
        {
            "ticker": "BEL",
            "name": "Bharat Electronics",
            "screener": {"sales_trend": [7000.0, 7000.0, 7000.0, 7000.0]},
        }
    ],
}


class TestCounterparties:
    def test_a_tie_up_records_the_other_party(self):
        (event,) = classify_headlines(
            _data("Syrma SGS Forms PCB Joint Venture With Kaga Electronics"), _EMS
        )
        assert event["actors"] == ["SYRMA"]
        assert event["counterparties"] == ["Kaga Electronics"]

    def test_the_field_is_absent_on_events_it_does_not_apply_to(self):
        """None for an order win, not [] — [] means "a tie-up, and nobody else
        could be named", which is a different statement."""
        (event,) = classify_headlines(
            _data("Bharat Electronics wins order worth ₹1,081 crore"), _EMS
        )
        assert "counterparties" not in event

    def test_carried_over_tie_ups_gain_their_counterparty_on_refresh(self):
        """The 45 days already in the corpus predate the field."""
        old = {
            "headline": "Syrma SGS and Elemaster inaugurate joint venture facility",
            "event_type": "tie_up",
            "phrase": "joint venture",
            "domains": [],
            "actors": ["SYRMA"],
            "external": [],
            "date": _TODAY,
        }
        (event,) = refresh_merged_events([old], _EMS)
        assert event["counterparties"] == ["Elemaster"]


class TestEventMateriality:
    def test_an_order_is_sized_against_the_holding_that_won_it(self):
        events = classify_headlines(
            _data("Bharat Electronics secures orders worth ₹1,081 crore"), _EMS
        )
        (event,) = annotate_event_materiality(events, _EMS)
        assert event["amount_cr"] == 1081.0
        assert event["materiality"]["BEL"]["band"] == "minor"
        assert event["materiality"]["BEL"]["pct_of_revenue"] == pytest.approx(
            3.86, abs=0.01
        )

    def test_the_price_move_in_one_clause_does_not_veto_the_order_in_another(self):
        """Sized on the event's clause. The whole headline trips the
        price-move guard and would have left a real order unsized."""
        events = classify_headlines(
            _data("Syrma SGS wins order worth ₹800 crore; shares jump 6%"), _EMS
        )
        (event,) = annotate_event_materiality(events, _EMS)
        assert event["materiality"]["SYRMA"]["band"] == "transformative"

    def test_a_joint_ventures_capital_is_not_sized(self):
        """Absent, not zero: unknown is not small."""
        events = classify_headlines(
            _data("Syrma SGS, Kaga Electronics Form ₹250 Million EMS Joint Venture"),
            _EMS,
        )
        (event,) = annotate_event_materiality(events, _EMS)
        assert "amount_cr" not in event and "materiality" not in event

    def test_a_material_corporate_move_is_escalated_by_the_existing_rule(
        self, monkeypatch
    ):
        """The alert carries its clause, so the order-materiality pass sizes it
        like every other headline-backed alert. Without the source it stayed
        Low whatever the order was worth."""
        import analysis.entity_graph as eg
        from analysis.early_warning import annotate_order_materiality

        monkeypatch.setattr(eg, "load_entity_graph", lambda path=None: {"edges": []})
        events = classify_headlines(
            _data("Syrma SGS wins order worth ₹800 crore; shares jump 6%"), _EMS
        )
        alerts = [
            a
            for a in market_event_signals({"market_events": events}, _EMS)
            if a["category"] == "Corporate Move"
        ]
        annotate_order_materiality(alerts, _EMS)
        (alert,) = alerts
        assert alert["severity"] == "Medium"
        assert alert["materiality_band"] == "transformative"

    def test_a_reported_deal_is_never_escalated(self, monkeypatch):
        import analysis.entity_graph as eg

        monkeypatch.setattr(eg, "load_entity_graph", lambda path=None: {"edges": []})
        event = {
            "headline": "Syrma SGS reportedly wins order worth ₹800 crore",
            "event_type": "order_win",
            "phrase": "order worth",
            "certainty": "reported",
            "domains": [],
            "actors": ["SYRMA"],
            "direction": "opportunity",
            "date": _TODAY,
        }
        (alert,) = [
            a
            for a in market_event_signals({"market_events": [event]}, _EMS)
            if a["category"] == "Corporate Move"
        ]
        assert "source_headlines" not in alert
