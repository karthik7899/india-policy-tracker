"""The per-company digest behind the dashboard's Companies view."""

from analysis.company_digest import build_company_digest

WATCHLIST = {
    "clean_energy": [
        {
            "ticker": "SUZLON",
            "name": "Suzlon Energy",
            "catalyst": "Debt-free wind leader.",
        },
        {"ticker": "QUIET", "name": "Quiet Co"},
    ],
    "macro_indicators": [{"ticker": "MAKEINDIA", "name": "ETF"}],
}


def _item(headline, date, **kw):
    return {
        "headline": headline,
        "date": date,
        "status": "counted",
        "source_url": "https://n.test/" + headline[:5],
        "source_label": "Test",
        **kw,
    }


COVERAGE = {
    "SUZLON": [
        _item(
            "Suzlon bags 400 MW wind EPC order from Tata Power",
            "2026-10-01",
            event_type="order_win",
        ),
        _item(
            "Suzlon Energy Limited has informed the Exchange about Trading Window closure",
            "2026-10-02",
        ),
        _item(
            "Suzlon bags 400 MW wind EPC order from Tata Power", "2026-10-01"
        ),  # repeat
        _item(
            "Suzlon fined by exchanges for LODR non-compliance",
            "2026-09-25",
            source_kind="Filing",
        ),
        _item("Suzlon old news", "2026-07-01"),
        # Another outlet's copy of the order story, cut short.
        _item("Suzlon bags 400 MW wind EPC order", "2026-09-30"),
        _item("Merged copy", "2026-10-01", status="merged"),
    ],
}
BRIEF = {
    "thesis_health": {"SUZLON": {"status": "Intact"}},
    "thesis_check": {
        "holdings": {
            "SUZLON": {
                "challenged": [{"headline": "Suzlon takes loan", "claim": "Debt-free"}]
            }
        }
    },
    "policy_balance": {"clean_energy": {"net": 1.5}},
    "policy_impacts": [
        {
            "headline": "Gujarat government notifies wind repowering policy",
            "date": "2026-09-30",
            "status": "in_force",
            "state": "Gujarat",
            "effects": [{"sector": "clean_energy", "direction": "tailwind"}],
            "link": "https://n.test/g",
        },
        {
            "headline": "Centre cuts ALMM relief for Suzlon Energy rivals",
            "date": "2026-09-20",
            "status": "approved",
            "effects": [
                {"sector": "semiconductors_equipment", "direction": "headwind"}
            ],
        },
        {
            "headline": "Steel duty raised",
            "date": "2026-10-01",
            "status": "approved",
            "effects": [
                {"sector": "industrial_manufacturing", "direction": "headwind"}
            ],
        },
        {
            "headline": "Old solar scheme",
            "date": "2026-06-01",
            "status": "in_force",
            "effects": [{"sector": "clean_energy", "direction": "tailwind"}],
        },
    ],
}


def _digest():
    return build_company_digest(WATCHLIST, COVERAGE, BRIEF, today="2026-10-03")


def _co(ticker):
    return next(c for c in _digest()["companies"] if c["ticker"] == ticker)


def test_activity_is_the_companys_own_news_without_routine_repeats_or_old_items():
    s = _co("SUZLON")
    assert [(a["date"], a["kind"]) for a in s["activity"]] == [
        ("2026-10-01", "order"),
        ("2026-09-25", "adverse"),
    ]
    assert s["activity"][0]["link"].startswith("https://n.test/")
    assert s["last_activity"] == "2026-10-01"


def test_policies_are_those_touching_its_sector_with_the_named_ones_first():
    s = _co("SUZLON")
    heads = [p["headline"] for p in s["policies"]]
    # Names Suzlon (though filed under another sector), then its sector's.
    assert heads == [
        "Centre cuts ALMM relief for Suzlon Energy rivals",
        "Gujarat government notifies wind repowering policy",
    ]
    assert s["policies"][0]["names_company"] is True
    assert s["policies"][0]["direction"] is None  # no effect on its own sector
    assert s["policies"][1] == {
        "date": "2026-09-30",
        "headline": "Gujarat government notifies wind repowering policy",
        "direction": "tailwind",
        "status": "in_force",
        "measure": "",
        "names_company": False,
        "state": "Gujarat",
        "link": "https://n.test/g",
    }
    assert s["policy_net"] == 1.5


def test_thesis_status_and_challenges_ride_along():
    s = _co("SUZLON")
    assert s["thesis_status"] == "Intact"
    assert s["challenges"] == [{"headline": "Suzlon takes loan", "claim": "Debt-free"}]


def test_busy_companies_first_and_macro_left_out():
    d = _digest()
    assert [c["ticker"] for c in d["companies"]] == ["SUZLON", "QUIET"]
    quiet = d["companies"][1]
    assert quiet["activity"] == [] and quiet["last_activity"] is None
    assert quiet["policy_count"] == 1  # its sector's policy still applies


def test_the_digest_is_a_sidecar_not_payload_weight():
    from dashboard.sidecars import SPLIT_WHOLE

    assert "company_digest" in SPLIT_WHOLE


def test_a_sebi_certificate_filing_is_routine():
    from analysis.headline_text import classify

    assert (
        classify(
            "Certificate under SEBI (Depositories and Participants) Regulations, 2018"
        )
        == "routine"
    )


def test_namesake_headlines_are_set_apart_from_the_companys_news():
    brief = dict(BRIEF)
    brief["thesis_check"] = {
        "holdings": {
            "SUZLON": {
                "challenged": [],
                "not_about": ["Suzlon fined by exchanges for LODR non-compliance"],
            }
        }
    }
    s = next(
        c
        for c in build_company_digest(WATCHLIST, COVERAGE, brief, today="2026-10-03")[
            "companies"
        ]
        if c["ticker"] == "SUZLON"
    )
    assert [a["kind"] for a in s["activity"]] == ["order"]
    assert [a["text"] for a in s["namesakes"]] == [
        "Suzlon fined by exchanges for LODR non-compliance"
    ]
    assert s["activity_count"] == 1


def test_weekly_closes_feed_the_card_price_line():
    import pandas as pd

    from analysis import growth

    idx = pd.to_datetime([f"2026-0{m}-0{d}" for m in (7, 8) for d in (1, 8)])
    frame = pd.DataFrame({"Close": [100.0, float("nan"), 102.5, 103.0]}, index=idx)
    assert growth._weekly_closes(frame) == [
        ["2026-07-01", 100.0],
        ["2026-08-01", 102.5],
        ["2026-08-08", 103.0],
    ]
    assert growth._weekly_closes(None) == []

    prices = {"SUZLON": [["2026-09-01", 40.0], ["2026-09-08", 42.0]]}
    d = build_company_digest(
        WATCHLIST, COVERAGE, BRIEF, today="2026-10-03", prices=prices
    )
    by = {c["ticker"]: c for c in d["companies"]}
    assert by["SUZLON"]["prices"] == prices["SUZLON"]
    assert "prices" not in by["QUIET"]

    # The run keeps a year of closes for the portfolio; a card shows half.
    year = {"SUZLON": [[f"w{i:02d}", 40.0 + i] for i in range(53)]}
    d = build_company_digest(
        WATCHLIST, COVERAGE, BRIEF, today="2026-10-03", prices=year
    )
    card = next(c for c in d["companies"] if c["ticker"] == "SUZLON")
    assert card["prices"] == year["SUZLON"][-26:]


def test_namesakes_from_earlier_runs_stay_set_apart():
    """7 Oct: the thesis check could not run, today's result had no namesakes,
    and Daryl Dixon's teaser went back into Dixon's news. Readings from earlier
    runs keep a headline set apart until it is read again."""
    s = next(
        c
        for c in build_company_digest(
            WATCHLIST,
            COVERAGE,
            BRIEF,
            today="2026-10-03",
            namesakes={("SUZLON", "suzlon fined by exchanges for lodr")},
        )["companies"]
        if c["ticker"] == "SUZLON"
    )
    assert [a["text"] for a in s["namesakes"]] == [
        "Suzlon fined by exchanges for LODR non-compliance"
    ]
