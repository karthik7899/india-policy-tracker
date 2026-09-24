"""Tie-up counterparties, the partner-proposal review queue, and what an
accepted partner edge makes possible.

Three layers, tested in the order data flows through them:

  1. analysis/counterparty.py reads the other party out of a tie-up headline.
     Every positive case below is a real headline from the live corpus, and
     every negative case is a shape that would put a false name in front of a
     reviewer.
  2. analysis/entity_graph.py queues each completed tie-up as a proposal and
     moves the ones a person accepts into the graph.
  3. analysis/read_through.py reads a partner's disruption across to the
     holding — the payoff that makes the first two worth having.
"""

import datetime
import json
import os

import pytest

from analysis.counterparty import extract_counterparties
from analysis.entity_graph import (
    PROPOSAL_STATUSES,
    PROPOSALS_PATH,
    apply_accepted_proposals,
    load_entity_graph,
    load_proposals,
    record_partner_proposals,
)
from analysis.read_through import compute_read_throughs

TODAY = datetime.date.today().isoformat()

SYRMA = ("SYRMA", "Syrma SGS Tech.")
DIXON = ("DIXON", "Dixon Technologies")
KAYNES = ("KAYNES", "Kaynes Technology")
BHEL = ("BHEL", "Bharat Heavy Electricals")
TCS = ("TCS", "Tata Consultancy Services")
COFORGE = ("COFORGE", "Coforge Ltd")
RELIANCE = ("RELIANCE", "Reliance Industries")
MPHASIS = ("MPHASIS", "Mphasis Ltd")
SUZLON = ("SUZLON", "Suzlon Energy")


# ---------------------------------------------------------------------------
# 1. counterparty extraction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "clause, holding, expected",
    [
        # "X ... with Y" — the object of "with"
        (
            "Syrma SGS Tech Forms Joint Venture With Kaga Electronics India To Produce PCBs",
            SYRMA,
            ["Kaga Electronics"],
        ),
        (
            "Kaynes Technology Partners with BOSGAME for India Launch",
            KAYNES,
            ["BOSGAME"],
        ),
        (
            "TCS expands strategic partnership with ABB to build ai-driven network",
            TCS,
            ["ABB"],
        ),
        (
            "Coforge launches AI-Powered zero trust security product in partnership with Zscaler",
            COFORGE,
            ["Zscaler"],
        ),
        # "X and Y ..." / "X, Y ..." — a list of subjects
        (
            "Aareal Bank and TCS forge strategic partnership to accelerate digital transformation",
            TCS,
            ["Aareal Bank"],
        ),
        (
            "Syrma SGS, Kaga Electronics Form ₹250 Million EMS Joint Venture",
            SYRMA,
            ["Kaga Electronics"],
        ),
        # a topic label before the colon is not a party
        (
            "Vande Bharat Sleeper trains: BHEL, Titagarh to form joint venture for 35-year maintenance",
            BHEL,
            ["Titagarh"],
        ),
        # the holding is the object; the subject is the counterparty
        (
            "SAS Partners with TCS, AI-driven Cyber Resilience Takes Flight",
            TCS,
            ["SAS"],
        ),
        (
            "Sabre : launches strategic collaboration with trusted engineering partner Coforge",
            COFORGE,
            ["Sabre"],
        ),
        # "X-Y joint venture", parentheticals and all
        (
            "Government clears Dixon (India)-Vivo (China) joint venture for manufacturing smartphones",
            DIXON,
            ["Vivo"],
        ),
        (
            "Syrma SGS-Elemaster joint venture opens electronics manufacturing facility in Bengaluru",
            SYRMA,
            ["Elemaster"],
        ),
    ],
)
def test_counterparty_is_read_from_live_headlines(clause, holding, expected):
    assert extract_counterparties(clause, [holding]) == expected


def test_a_possessive_country_is_a_qualifier_not_the_party():
    """ "with China's Bosgame" is a partnership with Bosgame."""
    assert extract_counterparties(
        "Kaynes Technology signs MoU with China’s Bosgame to launch computing products",
        [KAYNES],
    ) == ["Bosgame"]


def test_an_advisor_is_not_a_party():
    """SAM advised on the deal; Vivo is the one Dixon is partnering."""
    assert extract_counterparties(
        "SAM Advises Vivo Mobile India On Strategic Joint Venture With Dixon Technologies",
        [DIXON],
    ) == ["Vivo Mobile"]


def test_a_person_is_not_proposed_as_a_partner():
    assert (
        extract_counterparties(
            "US President Trump Announces $300 Billion Partnership with Reliance to Build Refinery",
            [RELIANCE],
        )
        == []
    )


def test_a_charity_is_not_a_commercial_partner():
    assert (
        extract_counterparties(
            "Mphasis Partners With SGBS Unnati Foundation For Bengaluru Initiative",
            [MPHASIS],
        )
        == []
    )


def test_a_list_after_with_yields_every_party():
    assert extract_counterparties("NTPC signs MoU with NHPC, PTC and TCS", [TCS]) == [
        "NTPC",
        "NHPC",
        "PTC",
    ]


def test_a_company_sharing_our_first_word_is_still_a_counterparty():
    """Tata Power is not TCS. A first-word test would have said it was."""
    assert extract_counterparties(
        "TCS partners with Tata Power for grid AI", [TCS]
    ) == ["Tata Power"]


def test_no_holding_means_no_counterparty():
    """A counterparty only means something relative to what we hold."""
    assert (
        extract_counterparties(
            "Apple unveils leasing programme in partnership with Klarna", []
        )
        == []
    )


# ---------------------------------------------------------------------------
# 2. the review queue
# ---------------------------------------------------------------------------


def _tie_up(headline, actors, counterparties, certainty="completed", **kw):
    event = {
        "headline": headline,
        "event_type": "tie_up",
        "certainty": certainty,
        "actors": actors,
        "counterparties": counterparties,
        "date": TODAY,
    }
    event.update(kw)
    return event


def _proposals(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["proposals"]


def test_a_completed_tie_up_is_proposed_not_merged(tmp_path):
    path = tmp_path / "proposals.json"
    graph = {"edges": []}
    counts = record_partner_proposals(
        [
            _tie_up(
                "Syrma SGS Forms PCB Joint Venture With Kaga Electronics",
                ["SYRMA"],
                ["Kaga Electronics"],
                link="https://example.com/a",
                source="Equitypandit",
            )
        ],
        graph,
        path=str(path),
        today=TODAY,
    )
    assert counts["new"] == 1
    # The graph is untouched — a person has to accept it first.
    assert graph == {"edges": []}
    (p,) = _proposals(path)
    assert p["holding"] == "SYRMA" and p["counterparty"] == "Kaga Electronics"
    assert p["status"] == "pending"
    assert p["evidence"][0]["link"] == "https://example.com/a"


def test_an_announced_mou_is_not_proposed(tmp_path):
    """An MoU is intent, not a relationship yet."""
    path = tmp_path / "proposals.json"
    counts = record_partner_proposals(
        [
            _tie_up(
                "CONCOR signs MoU with APEDA",
                ["CONCOR"],
                ["APEDA"],
                certainty="announced",
            )
        ],
        {"edges": []},
        path=str(path),
        today=TODAY,
    )
    assert counts["new"] == 0
    assert not path.exists()


def test_the_same_pair_in_three_headlines_is_one_proposal_seen_three_times(tmp_path):
    path = tmp_path / "proposals.json"
    events = [
        _tie_up(h, ["SYRMA"], [name])
        for h, name in (
            (
                "Syrma SGS Tech Forms Joint Venture With Kaga Electronics India",
                "Kaga Electronics",
            ),
            (
                "Syrma SGS Forms PCB Joint Venture With Kaga Electronics",
                "Kaga Electronics",
            ),
            (
                "Syrma SGS, Kaga Electronics Form ₹250 Million EMS Joint Venture",
                "kaga electronics",
            ),
        )
    ]
    record_partner_proposals(events, {"edges": []}, path=str(path), today=TODAY)
    (p,) = _proposals(path)
    assert len(p["evidence"]) == 3

    # Idempotent across runs: the event corpus carries these for 45 days.
    counts = record_partner_proposals(
        events, {"edges": []}, path=str(path), today=TODAY
    )
    assert counts == {"new": 0, "seen_again": 0, "pending": 1, "dropped_stale": 0}
    assert len(_proposals(path)[0]["evidence"]) == 3


def test_a_rejected_pair_is_never_proposed_again(tmp_path):
    path = tmp_path / "proposals.json"
    event = _tie_up("TCS Partners With DGCE", ["TCS"], ["DGCE"])
    record_partner_proposals([event], {"edges": []}, path=str(path), today=TODAY)
    body = json.loads(path.read_text())
    body["proposals"][0]["status"] = "rejected"
    path.write_text(json.dumps(body))

    counts = record_partner_proposals(
        [_tie_up("DGCE and TCS extend pact", ["TCS"], ["DGCE"])],
        {"edges": []},
        path=str(path),
        today=TODAY,
    )
    assert counts["new"] == 0
    (p,) = _proposals(path)
    assert p["status"] == "rejected" and len(p["evidence"]) == 1


def test_accepting_moves_the_edge_into_the_graph_under_the_corrected_name(tmp_path):
    proposals = tmp_path / "proposals.json"
    graph_path = tmp_path / "graph.json"
    record_partner_proposals(
        [
            _tie_up(
                "SAM Advises Vivo Mobile India On JV With Dixon",
                ["DIXON"],
                ["Vivo Mobile"],
            )
        ],
        {"edges": []},
        path=str(proposals),
        today=TODAY,
    )
    body = json.loads(proposals.read_text())
    body["proposals"][0]["status"] = "accepted"
    body["proposals"][0]["counterparty"] = "Vivo"  # the reviewer's correction
    proposals.write_text(json.dumps(body))

    graph = {"edges": []}
    assert (
        apply_accepted_proposals(graph, path=str(proposals), graph_path=str(graph_path))
        == 1
    )
    (edge,) = graph["edges"]
    assert (edge["src"], edge["dst"], edge["type"]) == ("Vivo", "DIXON", "partner")
    # Evidence is the headline, never "curated": a reviewer confirmed the
    # relationship exists, not what it is worth.
    assert edge["evidence"] != "curated"
    assert load_entity_graph(str(graph_path))["edges"][0]["src"] == "Vivo"

    # Applying again is a no-op, and the renamed pair is not re-proposed.
    assert (
        apply_accepted_proposals(graph, path=str(proposals), graph_path=str(graph_path))
        == 0
    )
    counts = record_partner_proposals(
        [
            _tie_up(
                "SAM Advises Vivo Mobile India On JV With Dixon",
                ["DIXON"],
                ["Vivo Mobile"],
            )
        ],
        graph,
        path=str(proposals),
        today=TODAY,
    )
    assert counts["new"] == 0


def test_a_misspelt_status_is_reported_not_guessed(tmp_path, caplog):
    path = tmp_path / "proposals.json"
    path.write_text(
        json.dumps(
            {
                "proposals": [
                    {
                        "holding": "SYRMA",
                        "counterparty": "Kaga Electronics",
                        "proposed_as": "Kaga Electronics",
                        "status": "accept",
                        "evidence": [{"headline": "h"}],
                    }
                ]
            }
        )
    )
    graph = {"edges": []}
    assert (
        apply_accepted_proposals(
            graph, path=str(path), graph_path=str(tmp_path / "g.json")
        )
        == 0
    )
    assert graph["edges"] == []
    assert "'accept'" in caplog.text


def test_an_unreadable_queue_is_never_overwritten(tmp_path):
    """A reviewer's half-finished edit must survive the next run."""
    path = tmp_path / "proposals.json"
    path.write_text('{"proposals": [ {"status": "accepted", ')
    record_partner_proposals(
        [
            _tie_up(
                "Syrma SGS Forms JV With Kaga Electronics",
                ["SYRMA"],
                ["Kaga Electronics"],
            )
        ],
        {"edges": []},
        path=str(path),
        today=TODAY,
    )
    assert path.read_text() == '{"proposals": [ {"status": "accepted", '


def test_a_stale_pending_proposal_ages_out_but_a_decision_does_not(tmp_path):
    path = tmp_path / "proposals.json"
    old = (datetime.date.today() - datetime.timedelta(days=200)).isoformat()
    path.write_text(
        json.dumps(
            {
                "proposals": [
                    {
                        "holding": "A",
                        "counterparty": "X",
                        "proposed_as": "X",
                        "status": "pending",
                        "last_seen": old,
                        "evidence": [{"headline": "a"}],
                    },
                    {
                        "holding": "B",
                        "counterparty": "Y",
                        "proposed_as": "Y",
                        "status": "rejected",
                        "last_seen": old,
                        "evidence": [{"headline": "b"}],
                    },
                ]
            }
        )
    )
    counts = record_partner_proposals([], {"edges": []}, path=str(path), today=TODAY)
    assert counts["dropped_stale"] == 1
    assert [p["holding"] for p in _proposals(path)] == ["B"]


def test_the_committed_queue_is_well_formed():
    """Reviewed by hand, often from a phone — so CI checks what was typed.

    CI runs on every push to main, which includes an edit made in GitHub's web
    editor. A status typo there is otherwise only a warning in a run log.
    """
    if not os.path.exists(PROPOSALS_PATH):
        pytest.skip("no proposals committed yet")
    proposals = load_proposals(PROPOSALS_PATH)
    assert proposals is not None, "entity_graph_proposals.json does not parse"
    seen = set()
    for p in proposals:
        assert p.get("status") in PROPOSAL_STATUSES, p
        assert p.get("holding") and p.get("counterparty") and p.get("proposed_as"), p
        key = (p["holding"].upper(), p["proposed_as"].lower())
        assert key not in seen, f"duplicate proposal {key}"
        seen.add(key)


# ---------------------------------------------------------------------------
# 3. what an accepted edge is for
# ---------------------------------------------------------------------------

GRAPH = {
    "edges": [
        {
            "src": "Vivo",
            "dst": "DIXON",
            "type": "partner",
            "evidence": "Government clears Dixon-Vivo joint venture",
        }
    ]
}
WATCHLIST = {
    "manufacturing_electronics": [
        {"ticker": "DIXON", "name": "Dixon Technologies"},
        {"ticker": "SYRMA", "name": "Syrma SGS Tech."},
    ]
}


def _risk(headline, external=("Vivo",), actors=(), direction="risk"):
    return {
        "headline": headline,
        "event_type": "supply_disruption",
        "certainty": "completed",
        "direction": direction,
        "domains": [],
        "actors": list(actors),
        "external": list(external),
        "date": TODAY,
    }


def test_a_partners_disruption_reads_across_to_the_holding():
    (flag,) = compute_read_throughs(
        [_risk("China export ban hits Vivo component shipments")],
        GRAPH,
        WATCHLIST,
        today=TODAY,
    )
    assert flag["mechanism"] == "partner_exposure"
    # Scoped to the partner's holding, not widened to the whole sector:
    # nobody has shown Syrma is exposed to Vivo.
    assert flag["tickers"] == ["DIXON"]
    assert flag["direction"] == "risk"
    assert "Vivo is a partner of DIXON" in flag["chain"][1]
    assert flag["confidence"] == "harvested"


def test_no_read_through_when_the_holding_is_named():
    """First-order attribution already has it; a hypothesis would count it twice."""
    assert (
        compute_read_throughs(
            [_risk("Vivo halts production at Dixon JV plant", actors=("DIXON",))],
            GRAPH,
            WATCHLIST,
            today=TODAY,
        )
        == []
    )


def test_a_partners_good_news_is_not_ours_by_default():
    assert (
        compute_read_throughs(
            [_risk("Vivo wins large order", direction="opportunity")],
            GRAPH,
            WATCHLIST,
            today=TODAY,
        )
        == []
    )


def test_one_partner_shared_by_two_holdings_flags_both():
    """Dedupe keys on tickers too, or one of the two rows silently vanished."""
    graph = {
        "edges": GRAPH["edges"]
        + [{"src": "Vivo", "dst": "SYRMA", "type": "partner", "evidence": "h"}]
    }
    flags = compute_read_throughs(
        [_risk("China export ban hits Vivo component shipments")],
        graph,
        WATCHLIST,
        today=TODAY,
    )
    assert sorted(f["tickers"][0] for f in flags) == ["DIXON", "SYRMA"]


def test_a_longer_name_for_the_same_party_joins_its_proposal(tmp_path):
    """ "Titagarh" and "Titagarh Rail Systems" are one question for a reviewer."""
    path = tmp_path / "proposals.json"
    record_partner_proposals(
        [
            _tie_up(
                "BHEL Partners With Titagarh For Vande Bharat", ["BHEL"], ["Titagarh"]
            ),
            _tie_up(
                "Titagarh Rail Systems Board Approves BHEL Joint Venture",
                ["BHEL"],
                ["Titagarh Rail Systems"],
            ),
        ],
        {"edges": []},
        path=str(path),
        today=TODAY,
    )
    (p,) = _proposals(path)
    assert p["counterparty"] == "Titagarh" and len(p["evidence"]) == 2


def test_companies_sharing_only_a_first_word_stay_apart(tmp_path):
    path = tmp_path / "proposals.json"
    record_partner_proposals(
        [
            _tie_up("TCS partners with Tata Power", ["TCS"], ["Tata Power"]),
            _tie_up("TCS partners with Tata Steel", ["TCS"], ["Tata Steel"]),
        ],
        {"edges": []},
        path=str(path),
        today=TODAY,
    )
    assert sorted(p["counterparty"] for p in _proposals(path)) == [
        "Tata Power",
        "Tata Steel",
    ]


def test_the_shorter_name_wins_unless_a_reviewer_chose_one(tmp_path):
    """ "Vivo" fires on every "Vivo Mobile India" headline; not the reverse."""
    path = tmp_path / "proposals.json"
    first = _tie_up(
        "SAM Advises Vivo Mobile India On JV With Dixon", ["DIXON"], ["Vivo Mobile"]
    )
    later = _tie_up("Government clears Dixon-Vivo joint venture", ["DIXON"], ["Vivo"])
    record_partner_proposals([first, later], {"edges": []}, path=str(path), today=TODAY)
    (p,) = _proposals(path)
    assert (p["counterparty"], p["proposed_as"]) == ("Vivo", "Vivo")

    # A reviewer's own choice is never overridden.
    body = json.loads(path.read_text())
    body["proposals"][0]["counterparty"] = "Vivo Communication Technology"
    path.write_text(json.dumps(body))
    record_partner_proposals(
        [_tie_up("Dixon and Vivo finalise JV terms", ["DIXON"], ["Vivo"])],
        {"edges": []},
        path=str(path),
        today=TODAY,
    )
    assert _proposals(path)[0]["counterparty"] == "Vivo Communication Technology"
