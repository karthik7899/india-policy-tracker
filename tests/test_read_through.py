"""Second-order read-throughs.

The two worked examples this feature was built from are the first two tests,
because they are the specification. Everything after them is a guard: this is
the one part of the pipeline that asserts a causal chain nobody wrote down,
and a confident wrong answer here costs more trust than a miss costs
information.
"""

import datetime

import pytest

from analysis.read_through import compute_read_throughs

TODAY = datetime.date.today().isoformat()

# A graph with exactly the relationships the examples need, so a test failure
# points at the engine rather than at whatever entity_graph.json happens to
# hold today.
GRAPH = {
    "edges": [
        {
            "src": "Broadcom",
            "dst": "Google",
            "type": "supplier_customer",
            "note": "Custom TPU silicon",
            "evidence": "curated",
        },
        {
            "src": "Marvell",
            "dst": "Broadcom",
            "type": "competitor",
            "note": "Custom silicon",
            "evidence": "curated",
        },
        {
            "src": "Broadcom",
            "dst": "semiconductors_equipment",
            "type": "anchor_demand",
            "evidence": "curated",
        },
        {
            "src": "Google",
            "dst": "manufacturing_electronics",
            "type": "anchor_demand",
            "evidence": "curated",
        },
        {
            "src": "RAM",
            "dst": "manufacturing_electronics",
            "type": "input_cost",
            "evidence": "curated",
        },
        {
            "src": "copper",
            "dst": "clean_energy",
            "type": "input_cost",
            "evidence": "curated",
        },
    ]
}

WATCHLIST = {
    "semiconductors_equipment": [{"ticker": "MTARTECH", "name": "MTAR Technologies"}],
    "manufacturing_electronics": [
        {"ticker": "DIXON", "name": "Dixon Technologies"},
        {"ticker": "SYRMA", "name": "Syrma SGS"},
    ],
    "clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}],
}


def _event(headline, **kw):
    base = {
        "headline": headline,
        "event_type": "tie_up",
        "phrase": "partnership",
        "certainty": "announced",
        "domains": [],
        "actors": [],
        "external": [],
        "direction": "opportunity",
        "date": TODAY,
    }
    base.update(kw)
    return base


def _run(events=None, headlines=None):
    return compute_read_throughs(
        events or [], GRAPH, WATCHLIST, today=TODAY, headlines=headlines or []
    )


# ---------------------------------------------------------------------------
# The two worked examples
# ---------------------------------------------------------------------------


def test_an_anchor_picking_a_rival_reads_across_to_the_incumbents_sector():
    """Google taps Marvell; Broadcom is the incumbent; we hold the sector that
    tracks Broadcom. The headline names nothing we own."""
    events = [
        _event(
            "Google taps Marvell for custom AI silicon in multi-year partnership",
            external=["Google", "Marvell"],
        )
    ]
    flags = _run(events)

    assert len(flags) == 1, flags
    flag = flags[0]
    assert flag["mechanism"] == "displacement"
    assert flag["direction"] == "risk"
    assert flag["sector"] == "semiconductors_equipment"
    assert flag["tickers"] == ["MTARTECH"]
    assert flag["confidence"] == "curated"

    # The chain is the deliverable. A conclusion without it is unfalsifiable.
    assert flag["chain"] == [
        "Google tied up with Marvell",
        "Marvell competes with Broadcom (Custom silicon)",
        "Broadcom supplies Google (Custom TPU silicon)",
        "our semiconductors equipment holdings track Broadcom",
    ]


def test_an_input_shortage_reads_through_to_whoever_buys_the_part():
    """ "iPhone priced higher on RAM shortage" is a statement about every
    device assembler's bill of materials, and it matches no event vocabulary —
    so it is read from the headline corpus, not from the typed events."""
    flags = _run(
        headlines=[
            "iPhone 18 Pro launches with 2nm A20 chip, higher price on RAM shortage"
        ]
    )

    assert len(flags) == 1, flags
    flag = flags[0]
    assert flag["mechanism"] == "input_squeeze"
    assert flag["direction"] == "risk"
    assert flag["sector"] == "manufacturing_electronics"
    assert flag["tickers"] == ["DIXON", "SYRMA"]
    assert flag["chain"][0] == "headline reports RAM scarcer or dearer"


# ---------------------------------------------------------------------------
# Guards. Each of these is a way to be confidently wrong.
# ---------------------------------------------------------------------------


def test_a_tie_up_with_no_path_through_the_graph_produces_nothing():
    """Two entities we know nothing relational about is not a read-through.
    Inventing one would be the whole failure mode of this feature."""
    events = [
        _event(
            "Google and Apple announce mapping partnership",
            external=["Google", "Apple"],
        )
    ]
    assert _run(events) == []


def test_an_event_naming_only_one_entity_produces_no_displacement():
    events = [_event("Google announces custom silicon plans", external=["Google"])]
    assert _run(events) == []


def test_a_chain_landing_on_a_sector_we_hold_nothing_in_is_dropped():
    """Sound reasoning, nothing to do about it. Reporting it is noise dressed
    as insight."""
    flags = compute_read_throughs(
        [],
        GRAPH,
        {"manufacturing_electronics": []},  # no holdings anywhere relevant
        today=TODAY,
        headlines=["RAM shortage worsens"],
    )
    assert flags == []


def test_a_material_must_match_on_a_word_boundary():
    """ "programme" contains "ram". Substring matching here would flag the
    electronics book on any headline about a government programme."""
    flags = _run(headlines=["Government programme faces cost increase and shortage"])
    assert flags == []


def test_easing_vocabulary_produces_an_opportunity_not_a_risk():
    """A glut is as real a read-through as a shortage. Reporting only the bad
    news would make this a pessimism generator."""
    flags = _run(headlines=["Memory glut deepens as RAM prices fall"])
    assert len(flags) == 1
    assert flags[0]["direction"] == "opportunity"


def test_a_turn_reads_as_easing_not_as_both():
    """ "shortage eases" carries both vocabularies; it is one story and the
    direction is the second half."""
    flags = _run(headlines=["RAM shortage eases as new capacity comes online"])
    assert [f["direction"] for f in flags] == ["opportunity"]


def test_a_headline_with_no_price_vocabulary_is_not_a_price_story():
    flags = _run(headlines=["New RAM standard published by JEDEC"])
    assert flags == []


def test_events_outside_the_window_are_ignored():
    old = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
    events = [
        _event(
            "Google taps Marvell for custom AI silicon",
            external=["Google", "Marvell"],
            date=old,
        )
    ]
    assert _run(events) == []


def test_the_same_trigger_and_sector_is_reported_once():
    """One headline reaching a sector by several chains is one problem, not
    several."""
    events = [
        _event(
            "Google taps Marvell for custom AI silicon",
            external=["Google", "Marvell"],
        )
    ] * 3
    assert len(_run(events)) == 1


def test_an_anchor_shift_only_fires_on_risk_direction():
    good = _event(
        "Google expands datacentre capacity",
        event_type="capacity_add",
        external=["Google"],
        direction="opportunity",
    )
    assert _run([good]) == []

    bad = _event(
        "Google hit by datacentre supply disruption",
        event_type="supply_disruption",
        external=["Google"],
        direction="risk",
    )
    flags = _run([bad])
    assert [f["mechanism"] for f in flags] == ["anchor_shift"]
    assert flags[0]["sector"] == "manufacturing_electronics"


def test_confidence_reports_the_weakest_link_not_the_strongest():
    graph = {
        "edges": [
            dict(e, evidence="harvested") if e.get("type") == "competitor" else e
            for e in GRAPH["edges"]
        ]
    }
    flags = compute_read_throughs(
        [
            _event(
                "Google taps Marvell for custom AI silicon",
                external=["Google", "Marvell"],
            )
        ],
        graph,
        WATCHLIST,
        today=TODAY,
    )
    assert len(flags) == 1
    assert flags[0]["confidence"] == "harvested"


@pytest.mark.parametrize(
    "events,graph,watchlist",
    [
        (None, None, None),
        ("not a list", {"edges": []}, {}),
        ([{"headline": None}], {"edges": [None]}, {"sector": None}),
        ([{"date": "not-a-date"}], GRAPH, WATCHLIST),
    ],
)
def test_never_raises_on_junk(events, graph, watchlist):
    """An enhancement layer must not be able to take down a briefing."""
    assert compute_read_throughs(events, graph, watchlist, today=TODAY) == []


def test_risks_sort_before_opportunities():
    flags = _run(
        events=[
            _event(
                "Google taps Marvell for custom AI silicon",
                external=["Google", "Marvell"],
            )
        ],
        headlines=["RAM glut deepens as prices fall"],
    )
    assert [f["direction"] for f in flags] == ["risk", "opportunity"]


# ---------------------------------------------------------------------------
# Email rendering
# ---------------------------------------------------------------------------

_ROW = {
    "trigger": "Google taps Marvell for custom AI silicon",
    "mechanism": "displacement",
    "direction": "risk",
    "sector": "semiconductors_equipment",
    "tickers": ["MTARTECH"],
    "chain": ["Google tied up with Marvell", "Marvell competes with Broadcom"],
    "confidence": "curated",
}


def test_email_section_is_empty_when_there_is_nothing_to_say():
    """No flags must render no card at all, not an empty one headed
    'Read-throughs' implying the analysis found nothing worth reporting."""
    from emails.sections import build_read_through_html

    assert build_read_through_html([]) == ""
    assert build_read_through_html(None) == ""


def test_email_section_carries_the_chain_not_just_the_conclusion():
    from emails.sections import build_read_through_html

    html = build_read_through_html([_ROW])
    assert "Semiconductors Equipment" in html
    assert "MTARTECH" in html
    for step in _ROW["chain"]:
        assert step in html, step


def test_email_section_escapes_headline_text():
    """Trigger text is a scraped headline and reaches an HTML email."""
    from emails.sections import build_read_through_html

    row = dict(_ROW, trigger="<script>alert(1)</script> & co")
    html = build_read_through_html([row])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_email_section_puts_risks_first():
    from emails.sections import build_read_through_html

    good = dict(_ROW, direction="opportunity", sector="clean_energy")
    html = build_read_through_html([good, _ROW])
    assert html.index("Semiconductors Equipment") < html.index("Clean Energy")


# ---------------------------------------------------------------------------
# Regressions found in production on 14 Sep
# ---------------------------------------------------------------------------


def test_a_truncated_headline_does_not_match_every_material():
    """The worst false positive this feature could have.

    A trailing "..." left an empty token in the parsed title, and the matcher's
    empty-candidate path compared "" == "" and said yes. One Morgan Stanley
    note on Reliance produced ten risk flags across ten sectors, naming
    materials the headline never mentioned. RSS truncates constantly, so this
    was not an edge case.
    """
    flags = _run(
        headlines=[
            "Morgan Stanley bullish on Reliance Industries, flags AI capex as "
            "next capital allocation pivot; sees 28%... "
        ]
    )
    assert flags == [], flags


def test_capital_allocation_is_not_a_supply_shortage():
    """ "allocation" alone is ordinary finance writing. Only the phrases that
    actually mean scarcity count."""
    assert (
        _run(headlines=["Board reviews capital allocation policy for RAM unit"]) == []
    )
    assert len(_run(headlines=["RAM buyers put on allocation as supply tightens"])) == 1


def test_newest_read_through_sorts_first_within_a_tier():
    """ISO dates ascend, so the obvious sort put the OLDEST first while the
    comment promised newest. The email shows four rows; a busy run would have
    buried today's flag behind a ten-day-old one."""
    old = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
    flags = compute_read_throughs(
        [
            _event("Google taps Marvell today", external=["Google", "Marvell"]),
            _event(
                "Google taps Marvell earlier", external=["Google", "Marvell"], date=old
            ),
        ],
        GRAPH,
        WATCHLIST,
        today=TODAY,
    )
    assert [f["date"] for f in flags] == [TODAY, old]


def test_an_undated_flag_never_outranks_a_real_date():
    flags = compute_read_throughs(
        [
            _event(
                "Google taps Marvell undated", external=["Google", "Marvell"], date=""
            ),
            _event("Google taps Marvell today", external=["Google", "Marvell"]),
        ],
        GRAPH,
        WATCHLIST,
        today=TODAY,
    )
    assert flags[0]["date"] == TODAY
