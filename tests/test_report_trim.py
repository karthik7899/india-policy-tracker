"""Trimming the report: what is dropped, what is shortened, what survives.

Every rule here was found by reading one day's rendered email end to end.
The tests pin the real lines that motivated each one.
"""

import pytest

from analysis.headline_text import classify, display, tidy

# ---------------------------------------------------------------------------
# the filing envelope
# ---------------------------------------------------------------------------


def test_the_envelope_is_removed_and_the_news_kept():
    raw = (
        "Lemon Tree Hotels Limited has informed the Exchange regarding a press "
        'release dated September 24, 2026, titled "LEMON TREE HOTELS EXPANDS '
        'MUMBAI FOOTPRINT; ACQUIRES LAND TO DEVELOP LEMON TREE PREMIER".'
    )
    assert tidy(raw) == (
        "Lemon Tree Hotels Expands Mumbai Footprint; Acquires Land To Develop "
        "Lemon Tree Premier"
    )


def test_an_nse_press_release_subject_loses_its_prefix():
    raw = (
        "Tata Consultancy Services Limited has informed the Exchange regarding "
        "'Press Release - DGCX partners with TCS to advance derivatives market "
        "infrastructure'."
    )
    assert (
        tidy(raw)
        == "DGCX partners with TCS to advance derivatives market infrastructure"
    )


def test_ordinary_headlines_are_untouched():
    headline = "BEL bags additional orders worth Rs 1,081 crore"
    assert tidy(headline) == headline


# ---------------------------------------------------------------------------
# what counts as news
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Lemon Tree Hotels Limited has informed the Exchange about Resignation of Director/KMP/SMP",
        "Optiemus Infracom Limited has informed the Exchange about Copy of Newspaper Publication",
        "Pearl Global Industries Limited has informed the Exchange about Link of Audio Recording",
        "Allotment of 18,890 equity shares pursuant to the OFSS Stock Plan, 2014",
        "Interaction with Institutional Investors / Analysts",
        "State Bank Of India has informed the Exchange about Schedule of meet",
        "IKS Health Appoints Arun Nair as Vice President – Human Resources",
        "State Bank Of India Stock Leads These 3 India Catalyst Picks",
        "Sterlite Technologies Share Price",
        "Paras Defence, ideaForge, other defence stocks slide up to 5%",
        "Hindustan Petroleum Corporation Limited has informed the Exchange about General Updates",
    ],
)
def test_routine_disclosure_and_commentary_is_routine(text):
    assert classify(text) == "routine"


@pytest.mark.parametrize(
    "text",
    [
        "Optiemus Infracom Limited has informed the Exchange regarding 'Board comments on fine levied by the Exchange'.",
        "BHEL fined ₹11 lakh by exchanges for LODR non-compliance",
    ],
)
def test_a_regulators_action_is_adverse_not_a_tailwind(text):
    assert classify(text) == "adverse"


@pytest.mark.parametrize(
    "text",
    [
        "Completion of acquisition of land parcel in Bandra (East), Mumbai by Fleur Hotels Limited",
        "Receipt of order worth of Rs. 263.25 Crore",
        "Bata India Central Government Approval New MD CEO",
        "Resignation of Managing Director and CEO with effect from today",
    ],
)
def test_business_news_and_top_job_changes_are_kept(text):
    assert classify(text) == "substantive"


def test_the_gist_is_shown_when_the_reader_has_one():
    raw = (
        "Lemon Tree Hotels Limited has informed the Exchange regarding a press release"
    )
    assert (
        display(raw, {"gist": "acquires land in Bandra (East)"})
        == "Acquires land in Bandra (East)"
    )
    assert display(raw, None) == tidy(raw)


# ---------------------------------------------------------------------------
# the LLM's gist is a quotation, never a rewrite
# ---------------------------------------------------------------------------


def test_a_gist_that_is_not_a_passage_of_the_headline_is_dropped():
    from analysis.llm_reader import ground

    headline = 'Lemon Tree Hotels Limited ... titled "LEMON TREE HOTELS ACQUIRES LAND IN BANDRA (EAST)"'
    base = {
        "event_type": "none",
        "parties": [],
        "certainty": "completed",
        "amount_text": "",
    }
    kept = ground(
        headline,
        {**base, "gist": "LEMON TREE HOTELS ACQUIRES LAND IN BANDRA", "material": True},
    )
    assert kept["gist"] == "LEMON TREE HOTELS ACQUIRES LAND IN BANDRA"
    assert kept["material"] is True
    reworded = ground(
        headline, {**base, "gist": "Lemon Tree buys Mumbai land", "material": True}
    )
    assert reworded["gist"] == ""


def test_an_unstated_materiality_is_unknown_not_false():
    from analysis.llm_reader import ground

    reading = ground("Some headline about a company", {"event_type": "none"})
    assert reading["material"] is None


# ---------------------------------------------------------------------------
# the alerts and the score
# ---------------------------------------------------------------------------


def _stock():
    return {"ticker": "LEMONTREE", "name": "Lemon Tree Hotels", "screener": {}}


def test_a_routine_filing_raises_no_catalyst_and_a_fine_raises_a_risk():
    from analysis.early_warning import _build_policy_map, _evaluate_stock

    data = {
        "corporate_filings": [
            {
                "company": "Lemon Tree Hotels",
                "filing": "Resignation of Director/KMP/SMP",
            },
            {
                "company": "Lemon Tree Hotels",
                "filing": "Board comments on fine levied by the Exchange",
            },
        ]
    }
    alerts = _evaluate_stock(_stock(), "Hospitality", _build_policy_map(data))
    categories = {a["category"] for a in alerts}
    assert "Policy Catalyst" not in categories
    (risk,) = [a for a in alerts if a["category"] == "Regulatory Action"]
    assert risk["direction"] == "risk" and "fine levied" in risk["signal"]


def test_a_catalyst_quotes_three_items_and_counts_the_rest():
    from analysis.early_warning import _build_policy_map, _evaluate_stock

    data = {
        "corporate_filings": [
            {
                "company": "Lemon Tree Hotels",
                "filing": f"Signs management agreement for hotel number {i}",
            }
            for i in range(5)
        ]
    }
    (alert,) = [
        a
        for a in _evaluate_stock(_stock(), "Hospitality", _build_policy_map(data))
        if a["category"] == "Policy Catalyst"
    ]
    assert alert["signal"].endswith("; +2 more")


def test_routine_items_earn_no_momentum():
    """An ESOP allotment and an analyst-meet schedule were scoring as policy
    events: 55 holdings sat at the momentum cap, 34 after this."""
    from dashboard.builder import build_dashboard_views

    watchlist = {
        "banking_financials": [
            {
                "ticker": "SBIN",
                "name": "State Bank Of India",
                "price": 100,
                "screener": {"q_sales": 1, "sales_trend": [1, 1, 1, 1]},
            }
        ]
    }
    data = {
        "corporate_filings": [
            {
                "company": "State Bank Of India",
                "filing": "Interaction with Institutional Investors / Analysts",
            },
            {
                "company": "State Bank Of India",
                "filing": "State Bank Of India Stock Leads These 3 India Catalyst Picks",
            },
        ]
    }
    build_dashboard_views(data, watchlist)
    reasons = watchlist["banking_financials"][0]["score"]["reasons"]
    assert not any(
        "Institutional Investors" in r or "Catalyst Picks" in r for r in reasons
    )


# ---------------------------------------------------------------------------
# the email
# ---------------------------------------------------------------------------


def test_feed_rows_drop_routine_immaterial_and_repeated_items(monkeypatch):
    import analysis.llm_reader as lr
    from emails.mailer import _feed_rows

    readings = {
        "Fortis Hospital Mulund unveils New-Age ER": {"material": False, "gist": ""}
    }
    monkeypatch.setattr(
        lr, "cached_reading", lambda text, path=None: readings.get(text)
    )
    items = [
        {"title": "Syrma SGS Elemaster opens electronics facility in Bengaluru"},
        {"title": "Syrma SGS Elemaster opens electronics facility in Bengaluru."},
        {"title": "Allotment of 8,725 Shares"},
        {"title": "Fortis Hospital Mulund unveils New-Age ER"},
    ]
    rows = _feed_rows(items, "title", {})
    assert [r["_shown"] for r in rows] == [
        "Syrma SGS Elemaster opens electronics facility in Bengaluru"
    ]


def test_institutional_deals_are_kept_only_for_holdings():
    from emails.mailer import _feed_rows

    watchlist = {"midcap_it": [{"ticker": "TCS", "name": "Tata Consultancy Services"}]}
    items = [
        {"headline": "Mastercard to exit Pine Labs in $93 million block deal"},
        {"headline": "Block deal: 0.4% of TCS changes hands"},
    ]
    rows = _feed_rows(items, "headline", watchlist, holdings_only=True)
    assert [r["headline"] for r in rows] == ["Block deal: 0.4% of TCS changes hands"]


def test_a_signal_with_no_sector_is_not_a_sector_moving():
    from emails.summary import build_summary

    warnings = [
        {
            "ticker": "BHEL",
            "sector": "—",
            "status": "new",
            "direction": "opportunity",
            "severity": "Low",
        },
        {
            "ticker": "HAL",
            "sector": "Aerospace & Defence",
            "status": "new",
            "direction": "opportunity",
            "severity": "Low",
        },
    ]
    summary = build_summary({"early_warnings": warnings}, {})
    assert [k for k, _ in summary["hot_sectors"]] == ["Aerospace & Defence"]


def test_a_gist_that_drops_the_company_is_refused():
    """From the first live run: 33 of 153 gists on holding headlines lost it."""
    raw = "ideaForge Now Has a Drone Taking Off Every 2 Minutes; Q1 Revenue Reaches ₹68.6 Cr"
    holdings = [("IDEAFORGE", "IdeaForge Technology")]
    assert display(raw, {"gist": "Q1 Revenue Reaches ₹68.6 Cr"}, holdings) == raw
    assert (
        display(
            raw,
            {"gist": "ideaForge Now Has a Drone Taking Off Every 2 Minutes"},
            holdings,
        )
        == "ideaForge Now Has a Drone Taking Off Every 2 Minutes"
    )
