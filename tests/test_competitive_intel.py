"""Tests for the new-entrant radar, the margin-compression severity ladder,
and the extract_row_values fix that had silently blanked sales/shareholding
metrics (which in turn muted the competitive-threat engine entirely)."""

import os
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.competitive_intel import (  # noqa: E402
    battleground_sectors,
    detect_new_entrants,
    new_entrant_signals,
)
from analysis.early_warning import generate_early_warnings  # noqa: E402
from analysis.parsing import extract_row_values  # noqa: E402

_WATCHLIST = {
    "manufacturing_electronics": [
        {"ticker": "DIXON", "name": "Dixon Technologies"},
        {"ticker": "KAYNES", "name": "Kaynes Technology"},
    ],
    "surveillance_security": [
        {"ticker": "CPPLUS", "name": "Aditya Infotech (CP PLUS)"},
    ],
}


# ---------------------------------------------------------------------------
# extract_row_values: Screener's expandable rows wrap the label in a <button>
# ---------------------------------------------------------------------------

_SCREENER_SECTION = """
<section id="quarters">
  <table>
    <tr><th></th><th>Mar 2026</th><th>Jun 2026</th></tr>
    <tr>
      <td class="text"><button class="button-plain">Sales&nbsp;<span>+</span></button></td>
      <td>1,000</td><td>1,200</td>
    </tr>
    <tr><td class="text">OPM %</td><td>15%</td><td>13%</td></tr>
    <tr>
      <td class="text"><button class="button-plain">Net Profit&nbsp;<span>+</span></button></td>
      <td>80</td><td>95</td>
    </tr>
  </table>
</section>
"""


def test_extract_row_values_handles_button_wrapped_labels():
    """Regression: BeautifulSoup's string= matcher returns None for tags with
    child elements, so every button-wrapped Screener row (Sales, Net Profit,
    Borrowings, Promoters...) silently extracted nothing in production."""
    soup = BeautifulSoup(_SCREENER_SECTION, "lxml")
    assert extract_row_values(soup, "quarters", "Sales") == [1000.0, 1200.0]
    assert extract_row_values(soup, "quarters", "Net Profit") == [80.0, 95.0]
    assert extract_row_values(soup, "quarters", "OPM") == [15.0, 13.0]  # still works
    assert extract_row_values(soup, "quarters", "Borrowings") == []
    assert extract_row_values(soup, "missing-section", "Sales") == []


# ---------------------------------------------------------------------------
# margin-compression severity ladder
# ---------------------------------------------------------------------------


def _margin_warnings(opm_expansion, q_margins=None):
    wl = {
        "sec": [
            {
                "ticker": "X",
                "name": "X Ltd",
                "screener": {
                    "opm_expansion": opm_expansion,
                    "quarterly_ebitda_margin": q_margins or [],
                },
            }
        ]
    }
    return [
        w
        for w in generate_early_warnings({}, wl)
        if w["category"] == "Margin Compression"
    ]


def test_margin_severity_ladders_with_drop_size():
    assert _margin_warnings(-2.5)[0]["severity"] == "Medium"
    assert _margin_warnings(-7.0)[0]["severity"] == "High"
    assert _margin_warnings(-61.0)[0]["severity"] == "Critical"  # the QUICKHEAL case
    assert _margin_warnings(-1.0) == []  # below threshold


def test_persistent_compression_escalates_and_shows_trend():
    warnings = _margin_warnings(-2.0, q_margins=[18.0, 16.0, 15.0, 13.0])
    assert warnings[0]["severity"] == "High"  # Medium escalated
    assert "3 straight quarters" in warnings[0]["signal"]
    assert "16.0% → 15.0% → 13.0%" in warnings[0]["signal"]


def test_one_off_dip_does_not_escalate():
    warnings = _margin_warnings(-2.0, q_margins=[15.0, 13.0, 16.0, 13.0])
    assert warnings[0]["severity"] == "Medium"
    assert "QoQ" in warnings[0]["signal"]


# ---------------------------------------------------------------------------
# new-entrant radar — anchored on the real Amber → Dixon case
# ---------------------------------------------------------------------------


def test_amber_eyeing_oppo_volumes_threatens_dixon():
    data = {"corporate_agreements": [{"title": "Amber eyes 20% of Oppo India volumes"}]}
    entrants = detect_new_entrants(data, _WATCHLIST)
    assert len(entrants) == 1
    e = entrants[0]
    assert e["sector"] == "manufacturing_electronics"
    assert e["challenger"] == "Amber"
    assert set(e["incumbents"]) == {"DIXON", "KAYNES"}

    signals = new_entrant_signals({"new_entrants": entrants}, _WATCHLIST)
    assert {s["ticker"] for s in signals} == {"DIXON", "KAYNES"}
    assert all(
        s["severity"] == "High" and s["category"] == "New Entrant" for s in signals
    )
    assert "Amber" in signals[0]["signal"]


def test_incumbents_own_expansion_is_not_a_threat():
    data = {
        "corporate_agreements": [
            {"title": "Dixon Technologies eyes bigger share of smartphone assembly"}
        ]
    }
    assert detect_new_entrants(data, _WATCHLIST) == []


def test_government_actors_are_not_challengers():
    data = {
        "corporate_agreements": [{"title": "India eyes smartphone export hub status"}]
    }
    assert detect_new_entrants(data, _WATCHLIST) == []


def test_challenger_named_via_peer_radar_when_available():
    data = {
        "corporate_agreements": [
            {"title": "Syrma SGS wins order for smartphone assembly lines"}
        ],
        "peer_competitors": {
            "surveillance_security": [
                {"ticker": "SYRMA", "name": "Syrma SGS Tech."},
            ]
        },
    }
    entrants = detect_new_entrants(data, _WATCHLIST)
    assert len(entrants) == 1
    assert entrants[0]["challenger"] == "Syrma SGS Tech."
    assert entrants[0]["sector"] == "manufacturing_electronics"


def test_entry_move_without_battleground_is_ignored():
    data = {"corporate_agreements": [{"title": "Amber eyes bigger dividend payout"}]}
    assert detect_new_entrants(data, _WATCHLIST) == []


def test_same_incursion_reported_once():
    data = {
        "corporate_agreements": [
            {"title": "Amber eyes 20% of Oppo India volumes"},
            {"title": "Amber eyes Oppo smartphone contract"},
        ]
    }
    assert len(detect_new_entrants(data, _WATCHLIST)) == 1


def test_radar_never_raises_on_garbage():
    assert detect_new_entrants(None, None) == []
    assert detect_new_entrants({"corporate_agreements": "junk"}, _WATCHLIST) == []
    assert new_entrant_signals({}, _WATCHLIST) == []


def _entrants(*titles, watchlist=None):
    data = {"corporate_agreements": [{"title": t} for t in titles]}
    return detect_new_entrants(data, watchlist or _WATCHLIST)


def test_a_turf_word_inside_another_word_is_not_turf():
    """Regression for 17 Oct: "ems" inside "Systems" made a university's
    library corner an electronics incursion, and broke the theses of all
    five electronics holdings."""
    assert (
        _entrants(
            "Tripura University sets up Indian Knowledge Systems Corner in "
            "Central Library"
        )
        == []
    )
    assert _entrants("Amber sets up defence systems unit") == []
    assert battleground_sectors("Persistent Systems wins $650M+ order") == []
    assert (
        battleground_sectors("APEDA MoU to Strengthen Global Food Trade Opportunities")
        == []
    )


def test_an_entry_move_inside_another_word_is_not_a_move():
    """ "enters" sits inside "centers"."""
    watchlist = {"data_center_support": [{"ticker": "ANANTRAJ", "name": "Anant Raj"}]}
    assert _entrants("Amber plans data centers in Pune", watchlist=watchlist) == []


def test_plurals_and_hyphens_still_count():
    assert battleground_sectors(
        "Hystar and BHEL Partner to Manufacture PEM Electrolysers in India"
    ) == ["clean_energy"]
    assert battleground_sectors(
        "Syrma SGS Tech Forms Joint Venture With Kaga Electronics India To Produce PCBs"
    ) == ["manufacturing_electronics"]
    assert battleground_sectors("ReNew to build a data-centre park in MMR") == [
        "data_center_support"
    ]
    assert len(_entrants("Amber wins orders for laptop PCBs")) == 1


def test_an_institution_is_not_a_challenger():
    assert _entrants("IIT Madras sets up PCB design lab") == []


def test_the_challengers_own_name_is_not_the_turf():
    """ "Ai+ Smartphone" is a phone brand; its cricket sponsorship is not a
    move onto smartphones."""
    assert (
        _entrants(
            "Ai+ Smartphone enters New Zealand Cricket partnership for India’s tour"
        )
        == []
    )


def test_a_foreign_company_abroad_is_not_on_our_turf():
    watchlist = {"data_center_support": [{"ticker": "ANANTRAJ", "name": "Anant Raj"}]}
    for headline in (
        "Philippines' Globe Telecom targets US$1 billion AI and data centre "
        "investment by 2027",
        "US-based Lumen targets data centre push",
        # The place before more than one descriptor (review on #221).
        "Taiwanese electronics giant Foxconn targets US$1 billion data centre "
        "investment",
    ):
        assert _entrants(headline, watchlist=watchlist) == [], headline
    # Coming to India is exactly what the radar is for.
    for headline in (
        "Taiwan's Foxconn eyes Indian EMS market",
        "Taiwan's Foxconn sets up smartphone plant in Tamil Nadu",
    ):
        entrants = _entrants(headline)
        assert [e["challenger"] for e in entrants] == ["Foxconn"], headline
    # A function word ends the qualifier: China is not Amber's.
    entrants = _entrants("US tariffs hit China as Amber eyes laptop PCB orders")
    assert [e["challenger"] for e in entrants] == ["Amber"]
    # A city places a move in India as well as a state does.
    entrants = _entrants("Taiwan's Foxconn sets up smartphone plant in Sriperumbudur")
    assert [e["challenger"] for e in entrants] == ["Foxconn"]


def test_an_old_article_is_not_a_new_entrant():
    """Regression for 19 Oct: "Amber eyes 20% of Oppo India volumes", dated
    22 June, raised a fresh High alert on five holdings every run."""
    from analysis.competitive_intel import RADAR_MAX_AGE_DAYS
    from analysis.event_engine import EVENT_RETENTION_DAYS

    assert RADAR_MAX_AGE_DAYS == EVENT_RETENTION_DAYS

    def run(date):
        item = {"title": "Amber eyes 20% of Oppo India volumes"}
        if date:
            item["date"] = date
        return detect_new_entrants(
            {"corporate_agreements": [item]}, _WATCHLIST, today="2026-10-19"
        )

    assert run("Mon, 22 Jun 2026 05:50:06 GMT") == []
    assert len(run("Mon, 05 Oct 2026 05:50:06 GMT")) == 1
    # Nothing to judge an undated item's age by: it is kept.
    assert len(run(None)) == 1


# ---------------------------------------------------------------------------
# competitive-threat fallback: challenger visible even without incumbent data
# ---------------------------------------------------------------------------


def test_fast_peer_pointed_to_even_when_incumbent_growth_unknown():
    """Regression for the Syrma silence: every holding lacked
    qoq_sales_growth, so the threat engine skipped all of them and a +58%
    challenger went entirely unmentioned."""
    wl = {
        "surveillance_security": [
            {"ticker": "CPPLUS", "name": "Aditya Infotech (CP PLUS)", "screener": {}}
        ]
    }
    data = {
        "peer_competitors": {
            "surveillance_security": [
                {"ticker": "SYRMA", "name": "Syrma SGS Tech.", "sales_var_pct": 58.49}
            ]
        }
    }
    threats = [
        w
        for w in generate_early_warnings(data, wl)
        if w["category"] == "Competitive Threat"
    ]
    assert len(threats) == 1
    assert threats[0]["ticker"] == "CPPLUS"
    assert threats[0]["severity"] == "Low"
    assert "Syrma" in threats[0]["signal"]
