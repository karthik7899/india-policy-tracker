"""Is a partner's news good, bad or mixed for the holding — or not its news?

analysis/read_through.screen_partner_news decides; these cases pin each of
its rules. Every headline goes through the real classifier first, so a case
fails if the event engine stops reading it the way the rule assumes.

The Corning edge is curated with the venture's line (cover glass for phones)
and the partner's other lines (optical fibre, display glass); the Vivo and
Kaga edges are not, and take their line from the headline that proposed them.
"""

import datetime
import logging

import pytest

from analysis.event_engine import classify_headlines
from analysis.read_through import PartnerScope, compute_read_throughs
from emails.sections import build_read_through_html

TODAY = datetime.date.today().isoformat()

GRAPH = {
    "edges": [
        {
            "src": "Corning",
            "dst": "OPTIEMUS",
            "type": "partner",
            "evidence": "curated",
            "note": "JV making finished cover glass for phones",
            "scope": ["cover glass", "gorilla glass", "smartphone", "phone", "mobile"],
            "not_scope": ["optical", "fibre", "fiber", "display glass"],
        },
        {
            "src": "Vivo",
            "dst": "DIXON",
            "type": "partner",
            "evidence": "Dixon Technologies and Vivo Form Joint Venture for "
            "Smartphone Manufacturing in India",
        },
        {
            "src": "Kaga Electronics",
            "dst": "SYRMA",
            "type": "partner",
            "evidence": "Syrma SGS Tech Forms Joint Venture With Kaga Electronics "
            "India To Produce PCBs",
        },
    ]
}
WATCHLIST = {
    "manufacturing_electronics": [
        {"ticker": "DIXON", "name": "Dixon Technologies"},
        {"ticker": "KAYNES", "name": "Kaynes Technology"},
        {"ticker": "SYRMA", "name": "Syrma SGS Technology"},
    ],
    "surveillance_security": [{"ticker": "OPTIEMUS", "name": "Optiemus Infracom"}],
}


def _verdicts(headline, peers=None):
    """{ticker: direction} of the partner flags one headline raises."""
    logging.disable(logging.INFO)
    try:
        events = classify_headlines(
            {"global_market_news": [{"title": headline}]}, WATCHLIST, GRAPH
        )
        flags = compute_read_throughs(
            events, GRAPH, WATCHLIST, today=TODAY, peers=peers
        )
    finally:
        logging.disable(logging.NOTSET)
    return {
        f["tickers"][0]: f["direction"]
        for f in flags
        if f["mechanism"] == "partner_exposure"
    }


@pytest.mark.parametrize(
    "headline, expected",
    [
        # The partner in trouble, in the venture's own line: bad.
        (
            "Corning sales fall 12% in third quarter on weak smartphone demand",
            {"OPTIEMUS": "risk"},
        ),
        (
            "Corning halts Gorilla Glass production at Kentucky plant",
            {"OPTIEMUS": "risk"},
        ),
        # The partner as a whole: bad, less directly.
        ("Corning cuts full-year revenue guidance", {"OPTIEMUS": "risk"}),
        ("Kaga Electronics posts net loss, plans job cuts", {"SYRMA": "risk"}),
        ("Vivo faces export curbs on smartphone parts", {"DIXON": "risk"}),
        # Another of the partner's lines: not ours.
        ("Corning optical communications sales fall 8%", {}),
        # The partner winning work in the venture's line, in India: good.
        (
            "Corning wins cover glass order from Apple for India-made iPhones",
            {"OPTIEMUS": "opportunity"},
        ),
        # Winning work elsewhere, or in another line: not ours.
        ("Corning wins optical fibre order from Reliance Jio", {}),
        ("Kaga Electronics wins PCB order from Japanese automaker", {}),
        # The partner as the customer, placing the venture's work elsewhere.
        ("Foxconn bags smartphone assembly order from Vivo", {"DIXON": "risk"}),
        # The partner working with a rival of the holding: bad for it. The
        # rival is the other holding named, read first-order for itself.
        (
            "Vivo ties up with Kaynes Technology for India smartphone assembly",
            {"DIXON": "risk"},
        ),
        # Capacity in the venture's line in India: the venture's own plant,
        # or the partner going round it.
        ("Corning opens new cover glass facility in Tamil Nadu", {"OPTIEMUS": "mixed"}),
        ("Vivo sets up own smartphone plant in Greater Noida", {"DIXON": "mixed"}),
        # A sale there too: read as the acquisition it was filed as before
        # divestments had a type, and against us when a rival buys.
        ("Vivo sells its smartphone plant in Greater Noida", {"DIXON": "mixed"}),
        (
            "Vivo sells its stake in smartphone unit to Kaynes Technology in India",
            {"DIXON": "risk"},
        ),
        # Abroad, with no rival named: the partner's news.
        ("Corning partners with Samsung for smartphone cover glass", {}),
        # A partnership in the venture's line in India ending: it may be ours.
        (
            "Corning exits cover glass joint venture in India",
            {"OPTIEMUS": "risk"},
        ),
    ],
)
def test_each_rule(headline, expected):
    assert _verdicts(headline) == expected


def test_a_screener_peer_is_a_rival_too():
    peers = {
        "manufacturing_electronics": [{"ticker": "PGEL", "name": "PG Electroplast"}]
    }
    headline = "Vivo signs MoU with PG Electroplast for phone components"
    assert _verdicts(headline) == {}
    assert _verdicts(headline, peers=peers) == {"DIXON": "risk"}


def test_the_holding_named_is_first_order_not_a_read_through():
    assert _verdicts("Vivo exits joint venture with Dixon") == {}


def test_the_partners_own_name_is_not_its_line():
    """ "vivo" is electronics vocabulary; "Vivo wins large order in India"
    says nothing about phones."""
    assert _verdicts("Vivo wins large order in India") == {}


def test_a_line_read_off_the_proposing_headline():
    scope = PartnerScope(GRAPH["edges"][2], "manufacturing_electronics")
    assert scope.place("Kaga ships more PCBs to carmakers") == "venture"
    assert scope.place("Kaga to build solar modules in Vietnam") == "other"
    assert scope.place("Kaga reports quarterly results") == "whole"


def test_every_flag_says_why():
    logging.disable(logging.INFO)
    try:
        events = classify_headlines(
            {
                "global_market_news": [
                    {"title": "Corning cuts full-year revenue guidance"}
                ]
            },
            WATCHLIST,
            GRAPH,
        )
        (flag,) = compute_read_throughs(events, GRAPH, WATCHLIST, today=TODAY)
    finally:
        logging.disable(logging.NOTSET)
    assert flag["chain"][0] == "Corning: a weaker business"
    assert flag["chain"][1].startswith("Corning is a partner of OPTIEMUS (JV making")
    assert flag["chain"][2].startswith("About Corning as a whole: bad for OPTIEMUS")
    assert flag["confidence"] == "curated"


def test_the_email_marks_a_mixed_verdict():
    row = {
        "trigger": "Corning opens new cover glass facility in Tamil Nadu",
        "direction": "mixed",
        "sector": "surveillance_security",
        "mechanism": "partner_exposure",
        "tickers": ["OPTIEMUS"],
        "chain": ["Corning: new capacity"],
    }
    html = build_read_through_html([row])
    assert "◆" in html and "#fbbf24" in html
