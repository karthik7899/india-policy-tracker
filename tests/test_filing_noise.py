"""Exchange-filing housekeeping is kept away from the event rules and the LLM
reader (analysis/headline_text.is_filing_noise), and Indian contract-award
phrasing reaches the rules (analysis/event_engine)."""

import pytest

from analysis.competitive_intel import collect_headlines, collect_sources
from analysis.event_engine import classify_certainty, match_event_type
from analysis.headline_text import classify, is_filing_noise


@pytest.mark.parametrize(
    "filing",
    [
        "XYZ Ltd has informed the Exchange about Certificate under Reg. 74(5) of "
        "SEBI (DP) Regulations, 2018",
        "Certificate under Regulation 74 (5) of SEBI (Depositories and "
        "Participants) Regulations",
        "Loss of Share Certificates / Issue of Duplicate Share Certificates",
        "Copy of Newspaper Clippings",
        "Indian Oil Corporation Limited has informed the Exchange regarding the "
        "Trading Window closure pursuant to SEBI (PIT) Regulations",
        "Statement of Investor Grievances for the quarter ended September 2026",
        "Indian Oil Corporation Limited has informed the Exchange about General "
        "Updates",
    ],
)
def test_housekeeping_filings_are_noise(filing):
    assert is_filing_noise(filing)


@pytest.mark.parametrize(
    "filing",
    [
        # Adverse is never housekeeping, whatever else it says.
        "Penalty levied by the Exchange for non-compliance with Regulation 17",
        # A large holder crossing a threshold: the LLM read two as acquisitions.
        "The Exchange has received the disclosure under Regulation 29(2) of SEBI "
        "(Substantial Acquisition of Shares & Takeovers) Regulations",
        # A change at the top is news a shareholder acts on.
        "Appointment of Chief Executive Officer",
        "Receipt of Letter of Award from NHAI worth Rs 450 crore",
        # A price move is commentary for the digest, but not for this test:
        # on news it would take a freight-rate shock for a stock tip.
        "VLCC Freight Rates Surge More Than 800% Amid Hormuz Tensions",
    ],
)
def test_what_matters_is_not_noise(filing):
    assert not is_filing_noise(filing)


def test_the_digest_drops_the_new_housekeeping_too():
    # The Reg 74(5) pattern ended in a bracket, after which its closing \b
    # can never match: it never matched anything until this.
    assert classify("Certificate under Reg. 74(5)") == "routine"
    assert classify("Statement of investor complaints") == "routine"


def test_housekeeping_filings_never_reach_the_rules_or_the_llm():
    data = {
        "corporate_filings": [
            {"company": "IOC", "filing": "Closure of Trading Window", "link": "a"},
            {
                "company": "KEC",
                "filing": "KEC International receives LoA for Rs 1,200 crore orders",
                "link": "b",
            },
        ]
    }
    headlines = collect_headlines(data, {})
    assert headlines == ["KEC International receives LoA for Rs 1,200 crore orders"]
    assert list(collect_sources(data, {})) == [headlines[0].lower()]
    # The feed itself is untouched: the calendar reads board meetings from it.
    assert len(data["corporate_filings"]) == 2


@pytest.mark.parametrize(
    "headline,certainty",
    [
        ("Receipt of Letter of Award from NHAI worth Rs 450 crore", "completed"),
        ("KEC International receives LoA for Rs 1,200 crore T&D orders", "completed"),
        ("RVNL emerges L1 bidder for Rs 500 crore railway project", "announced"),
        ("RVNL emerges as lowest bidder for a Central Railway contract", "announced"),
    ],
)
def test_contract_awards_as_india_files_them_are_order_wins(headline, certainty):
    assert match_event_type(headline.lower())[0] == "order_win"
    # The lowest bid is not yet the award.
    assert classify_certainty(headline) == certainty


def test_an_order_book_is_a_state_not_an_event():
    """On 14 Oct every "order book" headline in the cache was commentary
    ("hits all-time high on strong order book"), and the LLM agreed."""
    for headline in (
        "Diamond Power Infrastructure Hits All-Time High on Strong Order Book",
        "L&T shares may rise 25% as CLSA flags record order inflows",
    ):
        assert match_event_type(headline.lower()) == (None, None)
