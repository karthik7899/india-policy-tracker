"""Sector placement: does a company belong in the sector it is filed under?"""

from unittest.mock import patch

import pytest

from analysis.sector_fit import audit_watchlist, fits, keywords, place

# Yahoo profiles as the check sees them: industry, and the keyword groups of
# the business summary. Summaries are paraphrased to what each says.
GODREJ = (
    "Real Estate - Development",
    keywords("develops residential and commercial real estate projects"),
)
ADANI_POWER = (
    "Utilities - Independent Power Producers",
    keywords("generates thermal power; also a 40 MW solar power project"),
)
OFSS = (
    "Software - Application",
    keywords(
        "provides IT solutions and banking software to the financial services industry"
    ),
)
CAPILLARY = (
    "Software - Application",
    keywords("customer loyalty and engagement SaaS platform for retailers and brands"),
)
DIACABS = (
    "Electrical Equipment & Parts",
    keywords("manufactures power cables, conductors and transformers"),
)
UTL_SOLAR = (
    "Solar",
    keywords("manufactures rooftop solar panels, inverters and batteries"),
)
QUICKHEAL = (
    "Software - Infrastructure",
    keywords("provides antivirus, endpoint and cyber security software"),
)
NTPC_GREEN = (
    "Utilities - Renewable",
    keywords("generates power from renewable sources: solar and wind"),
)
ANANT_RAJ = (
    "Real Estate - Development",
    keywords("real estate developer building data centers in NCR"),
)
SUZLON = (
    "Specialty Industrial Machinery",
    keywords("manufactures wind turbine generators"),
)


@pytest.mark.parametrize(
    "profile, sector",
    [
        (GODREJ, "data_center_support"),
        (ADANI_POWER, "clean_energy"),
        (OFSS, "cybersecurity"),
        (CAPILLARY, "cybersecurity"),
        (DIACABS, "semiconductors_equipment"),
        (UTL_SOLAR, "semiconductors_equipment"),
    ],
)
def test_the_six_misplaced_holdings_do_not_fit_where_they_sit(profile, sector):
    assert fits(sector, *profile) is False


@pytest.mark.parametrize(
    "profile, sector",
    [
        (QUICKHEAL, "cybersecurity"),
        (NTPC_GREEN, "clean_energy"),
        (SUZLON, "clean_energy"),
        # Anant Raj is a developer held for its data-centre build-out: the
        # summary carries what the industry label cannot.
        (ANANT_RAJ, "data_center_support"),
    ],
)
def test_holdings_that_belong_still_fit(profile, sector):
    assert fits(sector, *profile) is True


def test_an_unknown_industry_is_never_refused():
    assert fits("clean_energy", None, []) is None
    assert place("clean_energy", "", []) == (
        "clean_energy",
        "industry unknown; sector unverified",
    )


def test_a_candidate_is_moved_to_the_one_sector_it_fits():
    sector, reason = place("semiconductors_equipment", *UTL_SOLAR)
    assert sector == "clean_energy"
    assert "not semiconductors_equipment" in reason


def test_a_candidate_fitting_nothing_is_refused():
    sector, reason = place("data_center_support", *GODREJ)
    assert sector is None
    assert reason == "Real Estate - Development fits none of our sectors"


def test_a_candidate_fitting_several_others_is_refused_rather_than_guessed():
    # Banking software fits Midcap IT only; a cable maker fits several
    # industrial sectors and the check will not pick between them.
    assert place("cybersecurity", *OFSS)[0] == "midcap_it"
    sector, reason = place("semiconductors_equipment", *DIACABS)
    assert sector is None and "fits" in reason


def test_placement_only_considers_sectors_on_the_watchlist():
    sector, _ = place(
        "semiconductors_equipment", *UTL_SOLAR, among={"semiconductors_equipment"}
    )
    assert sector is None


def test_the_audit_reports_misfits_and_moves_nothing():
    watchlist = {
        "data_center_support": [
            {
                "ticker": "ANANTRAJ",
                "yahoo_industry": ANANT_RAJ[0],
                "business_keywords": ANANT_RAJ[1],
            },
            {
                "ticker": "GODREJPROP",
                "name": "Godrej Properties",
                "yahoo_industry": GODREJ[0],
                "business_keywords": GODREJ[1],
            },
            {"ticker": "NEWCO"},
        ],
        "macro_indicators": [{"ticker": "MAKEINDIA"}],
    }
    before = repr(watchlist)
    audit = audit_watchlist(watchlist)
    assert audit["checked"] == 2
    assert [m["ticker"] for m in audit["misfits"]] == ["GODREJPROP"]
    assert audit["misfits"][0]["suggested"] == []
    assert audit["unverified"] == ["NEWCO"]
    assert repr(watchlist) == before


def test_the_yahoo_profile_is_recorded_compactly():
    from providers.yahoo import _parse_profile

    data = {}
    _parse_profile(
        data,
        {"industry": "Solar", "longBusinessSummary": "Rooftop solar panels. " * 50},
    )
    assert data == {"yahoo_industry": "Solar", "business_keywords": ["renewable"]}


def _probe(ticker, profile):
    return {
        "ticker": ticker,
        "full_name": ticker.title(),
        "error": None,
        "isin": None,
        "live_price": 100.0,
        "target_price": 130.0,
        "growth_pct_val": 30.0,
        "rating": "Buy",
        "rev_growth_raw": 0.4,
        "revenue_growth": "40.0%",
        "qoq_growth": 25.0,
        "industry": profile[0],
        "keywords": profile[1],
    }


def _curate(probes, watchlist):
    import analysis.rotation as rot

    screened = {
        sector: [{"name": t.title(), "ticker": t, "growth_pct": "50%"}]
        for sector, t in [(s, t) for s, t, _ in probes]
    }
    by_ticker = {t: _probe(t, p) for _, t, p in probes}

    def fake_probe(name, preresolved, isin_master, watchlisted=()):
        return by_ticker[preresolved]

    with patch.object(rot, "_probe_candidate", fake_probe), patch.object(
        rot, "save_watchlist", lambda *a, **k: None
    ):
        return rot.auto_curate_watchlist({}, watchlist, screened_candidates=screened)


def test_rotation_refuses_a_misfit_and_places_a_movable_one():
    watchlist = {
        "data_center_support": [
            {"ticker": "ANANTRAJ", "name": "Anant Raj", "growth_pct": "5%"}
        ],
        "semiconductors_equipment": [
            {"ticker": "SPELS", "name": "SPEL", "growth_pct": "5%"}
        ],
        "clean_energy": [{"ticker": "SUZLON", "name": "Suzlon", "growth_pct": "5%"}],
    }
    radar, decisions = _curate(
        [
            ("data_center_support", "GODREJPROP", GODREJ),
            ("semiconductors_equipment", "UTLSOLAR", UTL_SOLAR),
        ],
        watchlist,
    )
    held = {s: [x["ticker"] for x in v] for s, v in watchlist.items()}
    assert "GODREJPROP" not in sum(held.values(), [])
    assert "UTLSOLAR" in held["clean_energy"]
    assert "UTLSOLAR" not in held["semiconductors_equipment"]
    refused = [r for r in radar["data_center_support"] if r["ticker"] == "GODREJPROP"]
    assert refused[0]["status"] == "Sector Mismatch"
    added = next(x for x in watchlist["clean_energy"] if x["ticker"] == "UTLSOLAR")
    assert added["yahoo_industry"] == "Solar"
    assert [d["sector"] for d in decisions if d["stock"]["ticker"] == "UTLSOLAR"] == [
        "clean_energy"
    ]


def test_the_email_lists_misfits_only_when_there_are_some():
    from emails.mailer import _build_sector_fit_html

    html = _build_sector_fit_html(
        {
            "misfits": [
                {
                    "ticker": "GODREJPROP",
                    "sector": "data_center_support",
                    "industry": "Real Estate - Development",
                    "suggested": [],
                },
                {
                    "ticker": "UTLSOLAR",
                    "sector": "semiconductors_equipment",
                    "industry": "Solar",
                    "suggested": ["clean_energy"],
                },
            ]
        }
    )
    assert "Sector Placement" in html
    assert "fits none of our sectors" in html
    assert "fits Clean Energy" in html
    assert _build_sector_fit_html({"misfits": []}) == ""
    assert _build_sector_fit_html(None) == ""


def test_a_keyword_counts_only_from_industries_where_it_is_credible():
    asm = (
        "Information Technology Services",
        keywords("semiconductor design and engineering services"),
    )
    thermax = (
        "Conglomerates",
        keywords("boilers and energy systems serving semiconductor plants"),
    )
    assert fits("semiconductors_equipment", *asm) is True
    assert fits("semiconductors_equipment", *thermax) is False
    assert fits("industrial_manufacturing", *thermax) is True


def test_a_client_industry_in_a_summary_does_not_place_a_company():
    capillary = (
        "Software - Application",
        keywords("loyalty software for retail and footwear brands"),
    )
    assert fits("sports_athleisure", *capillary) is False
