"""What changed since the last run, and capped upside shown as a bound."""

from analysis.changes import build_changes

PRIOR = {
    "thesis_health": {"SUZLON": {"status": "Intact"}, "HAL": {"status": "Weakening"}},
    "thesis_check": {
        "holdings": {
            "HAL": {"challenged": [{"headline": "Old challenge", "claim": "x"}]}
        }
    },
    "market_events": [{"headline": "Suzlon bags 400 MW order", "actors": ["SUZLON"]}],
    "policy_impacts": [{"headline": "Old policy"}],
}
DATA = {
    "thesis_health": {
        "SUZLON": {"status": "Weakening", "reasons": ["Promoter holding declined 2%"]},
        "HAL": {"status": "Intact"},
        "NEW": {"status": "Intact"},
    },
    "thesis_check": {
        "holdings": {
            "HAL": {"challenged": [{"headline": "Old challenge", "claim": "x"}]},
            "SUZLON": {
                "challenged": [
                    {
                        "headline": "Suzlon takes loan",
                        "claim": "debt-free",
                        "link": "https://n.test/l",
                    }
                ]
            },
        }
    },
    "market_events": [
        {"headline": "Suzlon bags 400 MW order", "actors": ["SUZLON"]},
        {
            "headline": "HAL signs MoU with Safran",
            "actors": ["HAL"],
            "event_type": "tie_up",
            "reader": "llm",
            "link": "https://n.test/h",
        },
        {"headline": "Sector news, no holding", "actors": []},
    ],
    "policy_impacts": [
        {"headline": "Old policy"},
        {
            "headline": "Gujarat government notifies EV policy",
            "state": "Gujarat",
            "status": "in_force",
            "effects": [{"sector": "clean_energy", "direction": "tailwind"}],
        },
    ],
    "early_warnings": [
        {
            "ticker": "BEL",
            "signal": "Order cancelled",
            "severity": "High",
            "direction": "risk",
            "status": "new",
        },
        {"ticker": "HAL", "signal": "Standing", "status": "ongoing"},
    ],
}


def _changes():
    return build_changes(
        DATA,
        PRIOR,
        held_before={"HAL", "SUZLON", "OLD"},
        held_now={"HAL", "SUZLON", "NEW"},
    )


def test_only_what_is_new_is_listed():
    c = _changes()
    assert c["counts"] == {
        "watchlist": 2,
        "thesis": 3,
        "events": 1,
        "policy": 1,
        "warnings": 1,
    }
    assert [i["text"] for i in c["items"]["watchlist"]] == [
        "added to the watchlist",
        "dropped from the watchlist",
    ]


def test_grade_changes_say_which_way_and_why():
    thesis = {(i["ticker"], i["text"]): i for i in _changes()["items"]["thesis"]}
    assert thesis[("HAL", "thesis Weakening → Intact")]["direction"] == "better"
    worse = thesis[("SUZLON", "thesis Intact → Weakening")]
    assert (
        worse["direction"] == "worse"
        and worse["detail"] == "Promoter holding declined 2%"
    )
    challenge = thesis[("SUZLON", "thesis challenged: Suzlon takes loan")]
    assert (
        "LLM reading" in challenge["detail"] and challenge["link"] == "https://n.test/l"
    )


def test_new_events_name_the_holding_and_flag_unverified_ones():
    ev = _changes()["items"]["events"][0]
    assert ev["ticker"] == "HAL" and ev["detail"] == "tie up · LLM only, unverified"


def test_new_policy_carries_its_effects_and_whose_it_is():
    p = _changes()["items"]["policy"][0]
    assert p["detail"] == "clean energy tailwind · Gujarat government · in force"


def test_a_first_run_claims_nothing_is_new():
    c = build_changes(DATA, {}, held_before=set(), held_now={"HAL"})
    assert c["first_run"] is True and not any(c["counts"].values())


def test_the_email_section_lists_changes_and_says_when_there_are_none():
    from emails.mailer import _build_changes_html

    html = _build_changes_html(_changes())
    assert "Since the Last Run" in html and "Thesis (3)" in html
    assert "Suzlon takes loan" in html
    empty = build_changes({}, {"x": 1})
    assert "Nothing new since the last run" in _build_changes_html(empty)
    assert _build_changes_html(build_changes(DATA, {})) == ""


def test_the_email_policy_tally_orders_by_net():
    from emails.mailer import _build_policy_balance_html

    html = _build_policy_balance_html(
        {
            "fmcg": {"tailwind": 0, "headwind": 2, "net": -2},
            "clean_energy": {"tailwind": 3, "headwind": 0.5, "net": 2.5},
            "it": {"tailwind": 0, "headwind": 0, "net": 0},
        }
    )
    assert html.index("Clean Energy") < html.index("FMCG")
    assert "+2.5" in html and "it</td>" not in html
    assert _build_policy_balance_html({}) == ""


def test_a_clamped_fundamental_estimate_is_marked_and_shown_as_a_bound():
    from dashboard.builder import _apply_potential_estimate

    # Graham value a fifth of the price: -80%, clamped at the -50% floor.
    stock = {"ticker": "TVSSCS"}
    _apply_potential_estimate(stock, 130.0, 26.0)
    assert stock["growth_pct"] == "-50.0%" and stock["upside_capped"] == "floor"
    # Inside the bounds: no mark, and a stale mark is cleared.
    _apply_potential_estimate(stock, 130.0, 150.0)
    assert "upside_capped" not in stock
    # Analyst coverage replaces the estimate entirely.
    covered = {"analyst_count": 5, "target": "200", "upside_capped": "floor"}
    _apply_potential_estimate(covered, 130.0, 26.0)
    assert "upside_capped" not in covered


def test_the_email_shows_a_capped_upside_as_a_bound():
    from emails.mailer import _render_email, _CAPS_NORMAL

    stock = {
        "ticker": "TVSSCS",
        "name": "TVS Supply",
        "price": "130.00",
        "growth_pct": "-50.0%",
        "upside_capped": "floor",
        "estimate_method": "Fundamental Estimate",
    }
    news = [{"title": "TVS Supply wins contract", "link": "https://n.test/t", "source": "T", "date": "2026-10-01"}]
    html = _render_email({"logistics_heavy_capital": news}, {"logistics_heavy_capital": [stock]}, _CAPS_NORMAL)
    assert "&le; -50.0% (capped)" in html
