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


def test_an_anchors_weaker_business_reads_through_and_its_partnership_end_does_not():
    """Less demand from an anchor is the sector's to read; an anchor leaving
    one partner can send the work either way."""
    weaker = _event(
        "Google cuts full-year revenue guidance",
        event_type="business_weakness",
        external=["Google"],
        direction="risk",
    )
    assert [f["mechanism"] for f in _run([weaker])] == ["anchor_shift"]
    ended = _event(
        "Google ends partnership with Marvell",
        event_type="partnership_end",
        external=["Google", "Marvell"],
        direction="risk",
    )
    assert _run([ended]) == []


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


def test_a_material_is_matched_as_a_material_not_as_a_company():
    """Found on the live feed the day after shipping.

    Materials were matched with the company matcher, whose single-token guard
    rejects a following capitalised word so that "ITC Hotels" is not read as
    ITC. Correct for company names, wrong for materials: "DRAM Inventory Falls"
    is still about DRAM. The headline below — a real one — produced nothing,
    while the same story phrased "RAM shortage" matched only because the next
    word happened to be lower case.
    """
    from analysis.read_through import material_in

    headline = "HBM4 Shortage: DRAM Inventory Falls Below 10 Days"
    assert material_in(headline, "DRAM")
    # HBM4 is HBM: an optional trailing generation number is part of the name.
    assert material_in(headline, "HBM")
    assert material_in("higher price on RAM shortage", "RAM")


def test_the_material_matcher_keeps_its_word_boundaries():
    """The generation-number allowance is digits only, so it cannot become the
    substring matching it replaced."""
    from analysis.read_through import material_in

    assert not material_in("Government programme faces a shortage", "RAM")
    assert not material_in("Gurugram dispute settled", "RAM")
    assert not material_in("Steelcase reports a shortage", "steel")
    assert not material_in("Ramp-up delayed by shortage", "RAM")
    assert not material_in("", "RAM")
    assert not material_in("RAM shortage", "")


def test_the_real_dram_headline_reaches_every_exposed_sector():
    graph = {
        "edges": [
            {
                "src": "DRAM",
                "dst": "manufacturing_electronics",
                "type": "input_cost",
                "evidence": "curated",
            },
            {
                "src": "HBM",
                "dst": "data_center_support",
                "type": "input_cost",
                "evidence": "curated",
            },
        ]
    }
    watchlist = {
        "manufacturing_electronics": [{"ticker": "DIXON", "name": "Dixon"}],
        "data_center_support": [{"ticker": "STLTECH", "name": "Sterlite"}],
    }
    flags = compute_read_throughs(
        [],
        graph,
        watchlist,
        today=TODAY,
        headlines=["HBM4 Shortage: DRAM Inventory Falls Below 10 Days"],
    )
    assert sorted(f["sector"] for f in flags) == [
        "data_center_support",
        "manufacturing_electronics",
    ]
    assert all(f["direction"] == "risk" for f in flags)


# ---------------------------------------------------------------------------
# Transmission and strength
# ---------------------------------------------------------------------------


def test_email_row_says_how_it_travels_and_when_its_news_is_not_binding():
    from emails.sections import build_read_through_html

    soft = dict(
        _ROW,
        mechanism="rival_move",
        transmission="competitive_threat",
        strength="soft",
        strength_note="not yet binding: an MoU, a lowest bid or an intention",
    )
    html = build_read_through_html([soft])
    assert "competitive threat · rival move" in html
    assert "not yet binding: an MoU, a lowest bid or an intention" in html

    hard = dict(soft, strength="hard", strength_note="")
    assert "not yet binding" not in build_read_through_html([hard])
    # A row from before rows carried a transmission still names its rule.
    assert "displacement" in build_read_through_html([_ROW])


def test_unknown_names_and_unheld_destinations_raise_nothing(caplog):
    """Names the graph has never seen, edges to a sector and a holding we do
    not have, and edges missing an end. compute_read_throughs turns any
    exception into an empty list, so a KeyError here would not fail loudly:
    it would silently drop the one flag below that is real."""
    graph = {
        "edges": [
            {"src": "MegaCorp", "dst": "no_such_sector", "type": "anchor_demand"},
            {"src": "coal", "dst": "NOTHELD", "type": "input_cost"},
            {
                "src": "Rivalco",
                "dst": "NOTHELD",
                "type": "competitor",
                "scope": ["packaging"],
            },
            {"src": "Partnerco", "dst": "NOTHELD", "type": "partner"},
            {"src": "Ghost", "type": "partner"},
            {"type": "anchor_demand"},
            {
                "src": "copper",
                "dst": "clean_energy",
                "type": "input_cost",
                "evidence": "curated",
            },
        ]
    }
    events = [
        _event(
            "MegaCorp opens new plant",
            event_type="capacity_add",
            external=["MegaCorp"],
            domains=["manufacturing_electronics"],
        ),
        _event("Rivalco ties up for chip packaging", external=["Rivalco"]),
        _event(
            "Partnerco hit by shortage",
            event_type="supply_disruption",
            direction="risk",
            external=["Partnerco", "Unknown Corp"],
        ),
        # The bare minimum a stored event might carry.
        {
            "headline": "Unknown Corp wins order",
            "date": TODAY,
            "event_type": "order_win",
        },
    ]
    with caplog.at_level("WARNING"):
        flags = compute_read_throughs(
            events,
            graph,
            WATCHLIST,
            today=TODAY,
            headlines=["Coal shortage deepens as copper prices surge"],
        )
    assert "failed safely" not in caplog.text
    assert [(f["sector"], f["tickers"]) for f in flags] == [
        ("clean_energy", ["SUZLON"])
    ]


# ---------------------------------------------------------------------------
# The committed graph: entities we do not hold, reaching holdings we do
#
# Read through entity_graph.json and watchlist.json as a daily run reads them,
# so a broken alias, a mistyped destination or an edge that lost its scope
# fails here rather than in a briefing.
# ---------------------------------------------------------------------------


def _committed(*headlines):
    from analysis.entity_graph import load_entity_graph
    from analysis.event_engine import classify_headlines
    from config import load_watchlist

    graph, watchlist = load_entity_graph(), load_watchlist()
    events = classify_headlines(
        {"corporate_agreements": [{"title": h} for h in headlines]}, watchlist, graph
    )
    flags = compute_read_throughs(
        events, graph, watchlist, today=TODAY, headlines=list(headlines)
    )
    return events, flags, watchlist


def _held(watchlist, sector):
    return sorted(s["ticker"] for s in watchlist.get(sector) or [])


def test_a_foundry_named_in_full_reaches_the_holdings_it_anchors():
    """No holding is named, and the foundry is written out in full, which the
    company matcher used to read as some other company. The alias makes it
    TSMC, and TSMC's anchor edges carry the disruption to both sectors it
    drives."""
    events, flags, watchlist = _committed(
        "Taiwan Semiconductor Manufacturing halts production after earthquake"
    )
    assert [e["external"] for e in events] == [["TSMC"]]
    assert {f["sector"] for f in flags} == {
        "manufacturing_electronics",
        "semiconductors_equipment",
    }
    for f in flags:
        assert f["mechanism"] == "anchor_shift"
        assert (f["transmission"], f["direction"], f["strength"]) == (
            "demand_pull",
            "risk",
            "hard",
        )
        assert f["tickers"] == _held(watchlist, f["sector"])
        assert f["chain"][0] == "TSMC hit by supply disruption"


@pytest.mark.parametrize(
    "headline,says",
    [
        (
            "Hon Hai Precision to set up new smartphone assembly plant in Tamil Nadu",
            "Foxconn is adding capacity",
        ),
        (
            "Bharat FIH wins order to assemble smartphones in India",
            "Foxconn won an order",
        ),
    ],
)
def test_an_ems_anchor_by_any_of_its_names_is_demand_for_our_ems_holdings(
    headline, says
):
    events, flags, watchlist = _committed(headline)
    assert [e["external"] for e in events] == [["Foxconn"]]
    (flag,) = flags
    assert flag["mechanism"] == "anchor_pull"
    assert (flag["transmission"], flag["direction"]) == ("demand_pull", "opportunity")
    assert flag["tickers"] == _held(watchlist, "manufacturing_electronics")
    assert flag["chain"][0] == says


def test_the_same_anchor_news_raises_an_ecosystem_signal_on_the_sector():
    from analysis.event_engine import market_event_signals

    events, _, watchlist = _committed(
        "Hon Hai Precision to set up new smartphone assembly plant in Tamil Nadu"
    )
    signals = [
        a
        for a in market_event_signals({"market_events": events}, watchlist)
        if a["category"] == "Ecosystem Signal"
    ]
    assert signals
    assert {a["ticker"] for a in signals} <= set(
        _held(watchlist, "manufacturing_electronics")
    )
    for a in signals:
        assert a["signal"].startswith("Foxconn → anchor_demand edge")
        assert a["strength"] == "hard"


@pytest.mark.parametrize(
    "headline,direction",
    [
        ("Gemtek hit by optical transceiver component shortage", "risk"),
        (
            "Gemtek wins 800G optical module order from Indian telecom operator",
            "opportunity",
        ),
        # Wi-Fi gear is Gemtek's own business; the venture makes transceivers.
        ("Gemtek wins Wi-Fi router order in India", None),
    ],
)
def test_the_optical_jv_partners_news_reaches_dixon_only_in_the_jvs_line(
    headline, direction
):
    events, flags, _ = _committed(headline)
    assert [e["external"] for e in events] == [["Gemtek"]]
    if direction is None:
        assert flags == []
        return
    (flag,) = flags
    assert flag["mechanism"] == "partner_exposure"
    assert flag["tickers"] == ["DIXON"]
    assert (flag["direction"], flag["transmission"]) == (direction, "demand_pull")


def test_a_rival_gaining_ground_in_chip_packaging_presses_on_each_osat_holding():
    _, flags, watchlist = _committed(
        "Tata Electronics partners with Besi to advance semiconductor packaging in Assam"
    )
    sector_of = {s["ticker"]: k for k, v in watchlist.items() for s in v or []}
    assert sorted(t for f in flags for t in f["tickers"]) == [
        "CGPOWER",
        "KAYNES",
        "SPELS",
    ]
    for f in flags:
        assert f["mechanism"] == "rival_move"
        assert (f["transmission"], f["direction"]) == ("competitive_threat", "risk")
        # One holding's line, not its whole sector, filed under its own sector.
        (ticker,) = f["tickers"]
        assert f["sector"] == sector_of[ticker]


@pytest.mark.parametrize(
    "headline",
    [
        "Nexperia Partners With Tata Electronics for Semiconductor Manufacturing "
        "in India",
        "Fujifilm and Tata Electronics Announce Strategic Partnership to "
        "Accelerate Semiconductor Materials Ecosystem in India",
    ],
)
def test_the_rivals_news_outside_that_line_is_not_ours(headline):
    events, flags, _ = _committed(headline)
    assert [e["external"] for e in events] == [["Tata Electronics"]]
    assert flags == []


def test_a_lowest_bid_counts_for_half_a_letter_of_award_and_ranks_below_it():
    """PR #211's line, carried into read-throughs: "emerges L-1" is a bid
    that may still be lost, a Letter of Award is the work."""
    from analysis.event_engine import STRENGTH_SAYS

    _, flags, _ = _committed(
        "Tata Electronics emerges L-1 bidder for chip packaging contract",
        "Tata Electronics receives Letter of Award for chip packaging contract",
    )
    assert [(f["strength"], f["weight"]) for f in flags] == [("hard", 1.0)] * 3 + [
        ("soft", 0.5)
    ] * 3
    award, bid = flags[0], flags[-1]
    assert "Letter of Award" in award["trigger"] and award["strength_note"] == ""
    assert "L-1" in bid["trigger"]
    assert bid["strength_note"] == STRENGTH_SAYS["soft"]


def test_an_mou_is_soft_however_it_is_signed():
    _, flags, _ = _committed("Tata Electronics signs MoU with Besi for chip packaging")
    assert flags and {(f["strength"], f["weight"]) for f in flags} == {("soft", 0.5)}


def test_an_input_edge_to_one_holding_lands_on_it_and_not_its_sector():
    """Coal is Adani Power's fuel, not its sector-mates': the edge ends at the
    holding, and widening it to the sector would assert exposure nobody has
    shown. It follows the holding wherever the watchlist files it — a
    dashboard decision moved Adani Power out of clean energy."""
    _, flags, watchlist = _committed("Coal prices surge as monsoon floods mines")
    sector_of = {s["ticker"]: k for k, v in watchlist.items() for s in v or []}
    (flag,) = flags
    assert flag["tickers"] == ["ADANIPOWER"]
    assert flag["sector"] == sector_of["ADANIPOWER"]
    assert (flag["mechanism"], flag["transmission"]) == ("input_squeeze", "input_shock")
    assert flag["chain"][1].startswith("coal is an input to ADANIPOWER")


@pytest.mark.parametrize(
    "headline",
    [
        # A material named to say who uses something else.
        "Helium, key for semiconductor manufacturing, faces shortage",
        "Semiconductor skills shortage worsens",
        # Part of another word.
        "Blue-chip stocks rally amid shortage of sellers",
        # A scarcity said not to exist.
        "US Tariff Threat Reprices Copper Without a Global Shortage",
        # A kind the edge rules out: the EMS holdings buy mature-node parts.
        "China's AI chip shortage deepens",
    ],
)
def test_the_committed_input_edges_hold_their_guards(headline):
    assert _committed(headline)[1] == []


@pytest.mark.parametrize(
    "headline,sectors,direction",
    [
        (
            "Mature-node chip shortage deepens",
            {"manufacturing_electronics", "surveillance_security"},
            "risk",
        ),
        # A plural is the material.
        (
            "PCBs get costlier as AI servers soak up capacity",
            {"manufacturing_electronics"},
            "risk",
        ),
        # A duty waived makes the input cheaper for every buyer here.
        (
            "Centre waives cotton import duty till December",
            {"textiles_apparel"},
            "opportunity",
        ),
    ],
)
def test_the_committed_input_edges_still_fire(headline, sectors, direction):
    flags = _committed(headline)[1]
    assert {f["sector"] for f in flags} == sectors
    assert {f["direction"] for f in flags} == {direction}
    assert {f["transmission"] for f in flags} == {"input_shock"}


def test_every_read_through_says_how_it_travels_and_how_binding_it_is():
    from analysis.event_engine import STRENGTH_SAYS, STRENGTH_WEIGHT
    from analysis.read_through import TRANSMISSIONS

    _, flags, _ = _committed(
        "Taiwan Semiconductor Manufacturing halts production after earthquake",
        "Hon Hai Precision to set up new smartphone assembly plant in Tamil Nadu",
        "Gemtek hit by optical transceiver component shortage",
        "Tata Electronics emerges L-1 bidder for chip packaging contract",
        "Coal prices surge as monsoon floods mines",
        "Centre waives cotton import duty till December",
        "Copper shortage could be the undoing of the electrification push",
    )
    assert {f["transmission"] for f in flags} == set(TRANSMISSIONS)
    assert {f["strength"] for f in flags} == {"hard", "soft", "reported"}
    for f in flags:
        assert f["transmission"] in TRANSMISSIONS, f
        assert f["strength_note"] == STRENGTH_SAYS.get(f["strength"], "")
        link = 1.0 if f["confidence"] == "curated" else 0.5
        assert f["weight"] == round(STRENGTH_WEIGHT[f["strength"]] * link, 3)


@pytest.mark.parametrize(
    "headline,direction",
    [
        ("Govt imposes anti-dumping duty on copper rods from China", "risk"),
        ("Anti-dumping duty imposed on copper rods", "risk"),
        ("Centre waives copper import duty till March", "opportunity"),
        # A mention is not a change.
        ("Copper importers challenge anti-dumping duty", None),
        # An export duty moves the price here the other way, if at all.
        ("Govt cuts export duty on copper", None),
        # A change said not to happen.
        ("Centre will not impose import duty on copper", None),
        ("Govt rules out hike in copper import duty", None),
    ],
)
def test_a_duty_change_moves_an_input_and_a_mention_does_not(headline, direction):
    flags = _run(headlines=[headline])
    assert [f["direction"] for f in flags] == ([direction] if direction else [])


def test_a_hedged_duty_change_counts_as_a_rumour():
    (flag,) = _run(headlines=["Govt may impose anti-dumping duty on copper"])
    assert (flag["direction"], flag["strength"]) == ("risk", "reported")
