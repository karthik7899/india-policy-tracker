"""Tests for the new-entrant radar, the margin-compression severity ladder,
and the extract_row_values fix that had silently blanked sales/shareholding
metrics (which in turn muted the competitive-threat engine entirely)."""

import os
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.competitive_intel import (  # noqa: E402
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
    soup = BeautifulSoup(_SCREENER_SECTION, "html.parser")
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
