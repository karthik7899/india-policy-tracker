"""Company names (analysis/company_names.py): the registered name, the names
cut down from it, and the shorter forms headlines use."""

import json
import os

import pytest

from analysis import company_names as names
from analysis.company_names import (
    clean_registered_name,
    found_only_by_ticker,
    looks_shortened,
    name_rows,
    repair_holding_names,
    repaired_name,
    tidy_name,
)
from analysis.parsing import title_matches_company

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_a_registered_name_is_written_as_headlines_write_it():
    assert clean_registered_name("NTPC Green Energy Limited") == "NTPC Green Energy"
    assert clean_registered_name("The Indian Hotels Company Limited") == (
        "Indian Hotels Company"
    )
    # A bracket would read as an alias, and "(India)" matches every headline
    # about India.
    assert clean_registered_name("Data Patterns (India) Limited") == "Data Patterns"
    assert clean_registered_name("Narayana Hrudayalaya Ltd.") == "Narayana Hrudayalaya"
    assert clean_registered_name("State Bank of India") == "State Bank of India"


@pytest.mark.parametrize(
    "stored, registered, repaired",
    [
        # Screener's peer-table labels, cut at about fifteen characters.
        ("NTPC Green Ene.", "NTPC Green Energy Limited", "NTPC Green Energy"),
        (
            "Oracle Fin.Serv.",
            "Oracle Financial Services Software Limited",
            "Oracle Financial Services Software",
        ),
        ("Hind. Unilever", "Hindustan Unilever Limited", "Hindustan Unilever"),
        # Abbreviated rather than truncated: "Devl.", "Natl.".
        (
            "IRB Infra.Devl.",
            "IRB Infrastructure Developers Limited",
            "IRB Infrastructure Developers",
        ),
        ("Punjab Natl.Bank", "Punjab National Bank", "Punjab National Bank"),
        # Cut without a dot, and initials.
        (
            "Inventurus Knowl",
            "Inventurus Knowledge Solutions Limited",
            "Inventurus Knowledge Solutions",
        ),
        (
            "B P C L",
            "Bharat Petroleum Corporation Limited",
            "Bharat Petroleum Corporation",
        ),
        # The legal suffix, which no headline needs.
        ("Anant Raj Ltd", "Anant Raj Limited", "Anant Raj"),
        ("Faze Three Limited", "Faze Three Limited", "Faze Three"),
        ("Tata Power Co.", "Tata Power Company Limited", "Tata Power Company"),
        # Words kept whole keep the stored spelling: NSE writes "Acme",
        # "Mtar" and "MphasiS", and SIGMA ADVANCED SYSTEMS in capitals.
        ("ACME Solar Hold.", "Acme Solar Holdings Limited", "ACME Solar Holdings"),
        ("MTAR Technologie", "Mtar Technologies Limited", "MTAR Technologies"),
        ("Mphasis Ltd", "MphasiS Limited", "Mphasis"),
        (
            "Sigma Advanced System",
            "SIGMA ADVANCED SYSTEMS LIMITED",
            "Sigma Advanced Systems",
        ),
        # An alias on the stored name stays.
        (
            "Kalpataru Proj. (KPIL)",
            "Kalpataru Projects International Limited",
            "Kalpataru Projects International (KPIL)",
        ),
    ],
)
def test_a_name_cut_down_from_the_registered_one_is_repaired(
    stored, registered, repaired
):
    assert repaired_name(stored, registered) == repaired


@pytest.mark.parametrize(
    "stored, registered",
    [
        # A complete shorter name is how someone chose to write it.
        ("Kaynes Technology", "Kaynes Technology India Limited"),
        ("TVS Supply", "TVS Supply Chain Solutions Limited"),
        ("Indian Hotels Company", "The Indian Hotels Company Limited"),
        ("Aditya Infotech (CP PLUS)", "Aditya Infotech Limited"),
        # A brand that is not the registered name at all.
        ("Nykaa", "FSN E-Commerce Ventures Limited"),
        ("Leela Palaces Hotels", "Leela Palaces Hotels & Resorts Limited"),
        ("CG Power & Industrial", "CG Power and Industrial Solutions Limited"),
        ("Hindustan Aeronautics", None),
    ],
)
def test_a_name_that_is_not_cut_down_is_left_alone(stored, registered):
    assert repaired_name(stored, registered) is None
    assert tidy_name(stored, registered) == stored


def test_without_a_registered_name_only_the_legal_suffix_goes():
    assert tidy_name("Arvind Ltd") == "Arvind"
    assert tidy_name("Relaxo Footwears Limited") == "Relaxo Footwears"
    assert tidy_name("Varun Beverages (PepsiCo)") == "Varun Beverages (PepsiCo)"
    assert tidy_name("ASM Technologies") == "ASM Technologies"


def test_holdings_are_repaired_and_the_changes_reported():
    watchlist = {
        "clean_energy": [
            {"ticker": "NTPCGREEN", "name": "NTPC Green Ene."},
            {"ticker": "SUZLON", "name": "Suzlon Energy"},
        ],
        "macro_indicators": [{"ticker": "NIFTY", "name": "Nifty Ltd"}],
    }
    changed = repair_holding_names(
        watchlist,
        {"NTPCGREEN": "NTPC Green Energy Limited", "SUZLON": "Suzlon Energy Limited"},
    )
    assert changed == [("NTPCGREEN", "NTPC Green Ene.", "NTPC Green Energy")]
    assert watchlist["clean_energy"][0]["name"] == "NTPC Green Energy"
    assert watchlist["macro_indicators"][0]["name"] == "Nifty Ltd"


def test_competitor_rows_get_registered_names():
    peers = {
        "aerospace_defence": [
            {"ticker": "GRSE", "name": "Garden Reach Sh."},
            {"ticker": "BDL", "name": "Bharat Dynamics"},
        ],
        "fmcg": [{"ticker": "NHPC", "name": "NHPC Ltd"}],
    }
    registered = {
        "GRSE": "Garden Reach Shipbuilders & Engineers Limited",
        "BDL": "Bharat Dynamics Limited",
    }
    assert name_rows(peers, registered) == 2
    assert peers["aerospace_defence"][0]["name"] == (
        "Garden Reach Shipbuilders & Engineers"
    )
    assert peers["aerospace_defence"][1]["name"] == "Bharat Dynamics"
    assert peers["fmcg"][0]["name"] == "NHPC"


def test_a_repaired_name_matches_the_headlines_the_cut_one_missed(monkeypatch):
    # The name alone, without the shorter forms headline_names.json lists.
    monkeypatch.setattr(names, "HEADLINE_NAMES_PATH", os.devnull)
    headline = "NTPC Green Energy commissions 50 MW solar capacity in Rajasthan"
    assert not title_matches_company(headline, "NTPCGREEN", "NTPC Green Ene.")
    assert title_matches_company(headline, "NTPCGREEN", "NTPC Green Energy")
    assert not title_matches_company(
        "Anant Raj plans data centre bet", "ANANTRAJ", "Anant Raj Ltd"
    )
    assert title_matches_company(
        "Anant Raj plans data centre bet", "ANANTRAJ", "Anant Raj"
    )


@pytest.mark.parametrize(
    "name, shortened",
    [
        ("ACME Solar Hold.", True),
        ("Oracle Fin.Serv.", True),
        ("B P C L", True),
        ("Coforge Ltd", True),
        ("S.P. Apparels", False),
        ("Dr. Reddy's Laboratories", False),
        ("Hindustan Aeronautics", False),
        ("Aditya Infotech (CP PLUS)", False),
        ("L&T Technology Services", False),
    ],
)
def test_a_cut_down_name_is_recognised_without_nse(name, shortened):
    assert looks_shortened(name) is shortened


@pytest.fixture
def forms(tmp_path, monkeypatch):
    path = tmp_path / "headline_names.json"
    path.write_text(
        json.dumps(
            {
                "names": {
                    "KPIL": ["Kalpataru Projects"],
                    "INDHOTEL": ["IHCL", "Indian Hotels"],
                    "HINDPETRO": ["HPCL"],
                }
            }
        )
    )
    monkeypatch.setattr(names, "HEADLINE_NAMES_PATH", str(path))
    return path


def test_a_shorter_form_matches_beside_the_registered_name(forms):
    headline = "Kalpataru Projects bags orders worth Rs 2,000 crore"
    assert title_matches_company(headline, "KPIL", "Kalpataru Projects International")
    # Only for the ticker it is listed under.
    assert not title_matches_company(
        headline, "OTHER", "Kalpataru Projects International"
    )


def test_a_shorter_form_must_be_capitalised_as_written(forms):
    name = "Indian Hotels Company"
    assert title_matches_company(
        "Indian Hotels targets over 15% top-line growth", "INDHOTEL", name
    )
    assert title_matches_company("IHCL signs two new hotels in Goa", "INDHOTEL", name)
    # The same words about hotels in India.
    assert not title_matches_company(
        "Indian hotels see record festive demand", "INDHOTEL", name
    )
    # A one-word form keeps the matcher's guard: HPCL-Mittal Energy aside,
    # "HPCL Mittal" is another company.
    assert not title_matches_company(
        "HPCL Mittal Energy plans expansion",
        "HINDPETRO",
        "Hindustan Petroleum Corporation",
    )


def test_a_holding_found_only_by_its_ticker_is_reported(forms):
    watchlist = {"clean_energy": [{"ticker": "NTPCGREEN", "name": "NTPC Green Ene."}]}
    coverage = {
        "NTPCGREEN": [
            {"headline": f"NTPCGREEN share price today {i}", "status": "counted"}
            for i in range(3)
        ]
    }
    assert found_only_by_ticker(watchlist, coverage) == [
        ("NTPCGREEN", "NTPC Green Ene.", 3)
    ]
    # Once a headline names it, it is not.
    coverage["NTPCGREEN"].append(
        {"headline": "NTPC Green Energy commissions 50 MW", "status": "counted"}
    )
    watchlist["clean_energy"][0]["name"] = "NTPC Green Energy"
    assert found_only_by_ticker(watchlist, coverage) == []
    # Too few items to say.
    assert (
        found_only_by_ticker(watchlist, {"NTPCGREEN": coverage["NTPCGREEN"][:2]}) == []
    )


def test_no_holding_carries_a_cut_down_name():
    """The committed watchlist: every name NSE can check is not a cut-down
    form of its registered name, and every other name does not look cut."""
    from providers.isin_master import load_registered_names

    registered = load_registered_names(os.path.join(ROOT, "registered_names.json"))
    with open(os.path.join(ROOT, "watchlist.json"), encoding="utf-8") as handle:
        watchlist = json.load(handle)
    cut = []
    for sector, stocks in watchlist.items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for stock in stocks:
            name, ticker = stock.get("name") or "", str(stock.get("ticker")).upper()
            if ticker in registered:
                if tidy_name(name, registered[ticker]) != name:
                    cut.append((ticker, name))
            elif looks_shortened(name):
                cut.append((ticker, name))
    assert cut == [], f"cut-down names in watchlist.json: {cut}"
