"""Tests for headline→company attribution (analysis.parsing.title_matches_company).

Regression suite for the mis-attribution class of bug: bare substring
matching credited "IBM CEO Arvind Krishna Confirms Quantum Computer For
Andhra Pradesh" to Arvind Ltd (textiles), and would let ticker LT match
any headline containing "Ltd" or HAL match "Himachal"."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from analysis.parsing import title_matches_company  # noqa: E402

# ---------------------------------------------------------------------------
# the production bug and its person-name class
# ---------------------------------------------------------------------------


def test_ibm_ceo_arvind_krishna_is_not_arvind_ltd():
    title = "IBM CEO Arvind Krishna Confirms Quantum Computer For Andhra Pradesh"
    assert title_matches_company(title, "ARVIND", "Arvind Ltd") is False


def test_person_given_name_plus_surname_rejected_without_title_too():
    assert (
        title_matches_company(
            "Arvind Krishna outlines IBM strategy", "ARVIND", "Arvind Ltd"
        )
        is False
    )


def test_person_title_prefix_rejected():
    assert (
        title_matches_company("Mr Arvind said demand is strong", "ARVIND", "Arvind Ltd")
        is False
    )
    assert (
        title_matches_company(
            "Shri Arvind inaugurated the plant", "ARVIND", "Arvind Ltd"
        )
        is False
    )


def test_legit_arvind_company_headlines_still_match():
    assert title_matches_company(
        "Arvind shares zoom 13% to hit 52-week high", "ARVIND", "Arvind Ltd"
    )
    assert title_matches_company(
        "Arvind Ltd announces new denim capacity", "ARVIND", "Arvind Ltd"
    )
    # Title-Case headline: capitalized verb after the name must not read as a surname
    assert title_matches_company(
        "Arvind Posts Strong Q1 Results", "ARVIND", "Arvind Ltd"
    )


def test_different_company_sharing_first_token_rejected():
    # Arvind Fashions is a separate listed company from Arvind Ltd.
    assert (
        title_matches_company("Arvind Fashions Q1 results out", "ARVIND", "Arvind Ltd")
        is False
    )


# ---------------------------------------------------------------------------
# substring-era latent bugs: short tickers inside longer words
# ---------------------------------------------------------------------------


def test_lt_does_not_match_ltd():
    assert (
        title_matches_company(
            "Unrelated Company Ltd wins export order", "LT", "Larsen & Toubro (L&T)"
        )
        is False
    )


def test_lt_matches_via_alias_and_full_name():
    assert title_matches_company(
        "L&T wins metro construction order", "LT", "Larsen & Toubro (L&T)"
    )
    assert title_matches_company(
        "Larsen & Toubro bags defence contract", "LT", "Larsen & Toubro (L&T)"
    )


def test_hal_does_not_match_himachal():
    assert (
        title_matches_company(
            "Himachal Pradesh announces industrial policy",
            "HAL",
            "Hindustan Aeronautics",
        )
        is False
    )


def test_hal_matches_all_caps_ticker_mention():
    # ALL-CAPS occurrence reads as a ticker, never a person's given name.
    assert title_matches_company(
        "HAL Delivers First Tejas Mk1A To IAF", "HAL", "Hindustan Aeronautics"
    )
    assert title_matches_company(
        "Hindustan Aeronautics wins engine deal", "HAL", "Hindustan Aeronautics"
    )


def test_rir_does_not_match_inside_words():
    assert (
        title_matches_company(
            "Stirring growth in power electronics sector",
            "RIR",
            "RIR Power Electronics",
        )
        is False
    )


# ---------------------------------------------------------------------------
# general behavior
# ---------------------------------------------------------------------------


def test_own_name_continuation_is_not_a_surname():
    assert title_matches_company(
        "Dixon Technologies Shares Surge On PLI News", "DIXON", "Dixon Technologies"
    )


def test_headline_verbs_after_mixed_case_name_accepted():
    assert title_matches_company(
        "Suzlon Wins 300MW Wind Order", "SUZLON", "Suzlon Energy"
    )


def test_match_at_end_of_title():
    assert title_matches_company(
        "Policy tailwind boosts Suzlon", "SUZLON", "Suzlon Energy"
    )


def test_possessive_and_alias_handling():
    assert title_matches_company(
        "Suzlon's order book hits record", "SUZLON", "Suzlon Energy"
    )
    assert title_matches_company(
        "CP PLUS expands CCTV manufacturing", "CPPLUS", "Aditya Infotech (CP PLUS)"
    )


def test_empty_and_garbage_inputs():
    assert title_matches_company("", "ARVIND", "Arvind Ltd") is False
    assert title_matches_company(None, "ARVIND", "Arvind Ltd") is False
    assert title_matches_company("Some headline", "", "") is False
