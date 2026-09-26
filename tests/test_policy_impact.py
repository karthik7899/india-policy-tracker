"""Policy direction per sector: grounding, aggregation, and where it shows."""

import json

from analysis.llm_reader import PROMPT_VERSION, _prompt, ground
from analysis.policy_impact import (
    annotate_sector_news,
    policy_impacts,
    sector_policy_balance,
)
from emails.mailer import _build_policy_direction_html, _policy_badge

DUTY = "Govt cuts import duty on solar glass to boost domestic module makers"
FMCG = "FMCG firms to hold prices through festive season despite rising commodity costs"


def _raw(measure, effects, status="in_force"):
    return {
        "event_type": "none",
        "parties": [],
        "certainty": "reported",
        "amount_text": "",
        "policy_measure": measure,
        "policy_status": status,
        "sector_effects": effects,
    }


def _effect(sector, direction, because):
    return {"sector": sector, "direction": direction, "because": because}


# ---------------------------------------------------------------------------
# grounding
# ---------------------------------------------------------------------------


def test_an_effect_quoting_the_headline_is_kept():
    r = ground(
        DUTY,
        _raw(
            "duty_or_tariff",
            [_effect("clean_energy", "tailwind", "domestic module makers")],
        ),
    )
    assert r["policy_measure"] == "duty_or_tariff"
    assert r["policy_status"] == "in_force"
    assert r["sector_effects"] == [
        _effect("clean_energy", "tailwind", "domestic module makers")
    ]


def test_an_effect_reasoned_from_outside_the_headline_is_dropped():
    r = ground(
        DUTY,
        _raw(
            "duty_or_tariff",
            [_effect("clean_energy", "tailwind", "cheaper imported cells")],
        ),
    )
    assert r["sector_effects"] == []


def test_an_unknown_sector_or_direction_is_dropped_and_duplicates_collapse():
    r = ground(
        DUTY,
        _raw(
            "duty_or_tariff",
            [
                _effect("solar_widgets", "tailwind", "solar glass"),
                _effect("clean_energy", "bullish", "solar glass"),
                _effect("clean_energy", "tailwind", "solar glass"),
                _effect("clean_energy", "headwind", "import duty"),
            ],
        ),
    )
    assert [(e["sector"], e["direction"]) for e in r["sector_effects"]] == [
        ("clean_energy", "tailwind")
    ]


def test_macro_is_not_a_sector_a_policy_can_move():
    r = ground(
        DUTY, _raw("duty_or_tariff", [_effect("macro_indicators", "mixed", "duty")])
    )
    assert r["sector_effects"] == []


def test_an_unknown_measure_reads_as_no_policy():
    r = ground(DUTY, _raw("vibes", [_effect("clean_energy", "tailwind", "duty")]))
    assert r["policy_measure"] == "none"
    assert r["sector_effects"] == []


def test_an_unknown_status_is_read_as_a_proposal():
    r = ground(DUTY, _raw("duty_or_tariff", [], status="rumoured"))
    assert r["policy_status"] == "proposed"


def test_the_prompt_lists_our_sectors_and_the_version_changed():
    prompt = _prompt([(0, DUTY)])
    assert "clean_energy:" in prompt
    assert "macro_indicators" not in prompt
    assert "{sectors}" not in prompt
    assert PROMPT_VERSION != "2"


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------


def _reading(measure, effects, status="in_force"):
    return {
        "event_type": "none",
        "policy_measure": measure,
        "policy_status": status,
        "sector_effects": [
            {"sector": s, "direction": d, "because": "x"} for s, d in effects
        ],
    }


READINGS = {
    DUTY: _reading("duty_or_tariff", [("clean_energy", "tailwind")]),
    "Govt proposes curbs on imported drone parts": _reading(
        "ban_or_restriction", [("aerospace_defence", "headwind")], "proposed"
    ),
    FMCG: _reading("none", []),
    "Old scheme for solar pumps": _reading(
        "subsidy_or_funding", [("clean_energy", "headwind")]
    ),
}
SOURCES = {
    DUTY.lower(): {"date": "Wed, 23 Sep 2026 10:00:00 GMT", "link": "https://x/1"},
    "old scheme for solar pumps": {"date": "2026-06-01"},
}


def test_only_policy_headlines_with_an_effect_become_impacts():
    rows = policy_impacts(READINGS, SOURCES, today="2026-09-25")
    heads = [r["headline"] for r in rows]
    assert FMCG not in heads
    assert rows[0]["headline"] == "Govt proposes curbs on imported drone parts"
    assert rows[0]["date"] == "2026-09-25"  # no feed date: today
    duty = next(r for r in rows if r["headline"] == DUTY)
    assert duty["date"] == "2026-09-23"
    assert duty["link"] == "https://x/1"
    assert all(r["reader"] == "llm" for r in rows)


def test_the_balance_weights_proposals_by_half_and_ignores_old_news():
    rows = policy_impacts(READINGS, SOURCES, today="2026-09-25")
    balance = sector_policy_balance(rows, today="2026-09-25")
    assert balance["clean_energy"]["tailwind"] == 1.0
    assert balance["clean_energy"]["headwind"] == 0.0  # June scheme is outside
    assert balance["clean_energy"]["net"] == 1.0
    assert balance["aerospace_defence"]["headwind"] == 0.5
    assert balance["aerospace_defence"]["net"] == -0.5
    assert balance["clean_energy"]["items"][0]["headline"] == DUTY


def test_sector_news_is_labelled_for_the_sector_it_is_filed_under():
    data = {
        "clean_energy": [{"title": DUTY}, {"title": FMCG}],
        "fmcg": [{"title": DUTY, "policy": {"stale": True}}],
    }
    n = annotate_sector_news(data, READINGS, ["clean_energy", "fmcg"])
    assert n == 2
    assert data["clean_energy"][0]["policy"] == {
        "measure": "duty_or_tariff",
        "status": "in_force",
        "direction": "tailwind",
    }
    assert "policy" not in data["clean_energy"][1]
    # Policy news that does not touch this sector says so, not "tailwind".
    assert data["fmcg"][0]["policy"]["direction"] is None


# ---------------------------------------------------------------------------
# the email
# ---------------------------------------------------------------------------


def test_the_badge_shows_direction_and_status_only_when_there_is_one():
    badge = _policy_badge({"direction": "headwind", "status": "proposed"})
    assert "badge-negative" in badge and "Policy headwind" in badge
    assert "(proposed)" in badge
    assert _policy_badge({"direction": None, "status": "in_force"}) == ""
    assert _policy_badge(None) == ""


def test_the_policy_section_puts_measures_in_force_before_proposals():
    rows = policy_impacts(READINGS, SOURCES, today="2026-09-25")
    html = _build_policy_direction_html(rows, {"lists": 5})
    assert "Policy Direction" in html and "not verified" in html
    assert html.index("solar glass") < html.index("drone parts")
    assert "▲ Clean Energy" in html
    assert _build_policy_direction_html([], {"lists": 5}) == ""


# ---------------------------------------------------------------------------
# the scorer
# ---------------------------------------------------------------------------


def test_the_policy_scorer_grades_detection_and_effects():
    from scripts.eval_events import score_policy

    labels = [
        {
            "headline": DUTY,
            "is_policy": True,
            "effects": [{"sector": "clean_energy", "direction": "tailwind"}],
            "also_acceptable": [],
            "split": "dev",
        },
        {
            "headline": FMCG,
            "is_policy": False,
            "effects": [],
            "also_acceptable": [],
            "split": "dev",
        },
        {
            "headline": "Unread",
            "is_policy": True,
            "effects": [],
            "also_acceptable": [],
            "split": "dev",
        },
    ]
    readings = {
        DUTY: _reading(
            "duty_or_tariff",
            [("clean_energy", "tailwind"), ("fmcg", "headwind")],
        ),
        FMCG: _reading("regulation", [("fmcg", "headwind")]),
    }
    r = score_policy(labels, readings)["dev"]
    assert r["rows"] == 2  # the unread row is not scored
    assert r["recall"] == 1.0
    assert r["precision"] == 0.5
    assert r["effect_recall"] == 1.0
    assert r["effect_precision"] == round(1 / 3, 3)


def test_the_committed_policy_labels_are_well_formed():
    from analysis.llm_reader import DIRECTIONS, _POLICY_SECTORS

    with open("eval/policy_labels.json", encoding="utf-8") as f:
        body = json.load(f)
    heads = [r["headline"] for r in body["labels"]]
    assert len(heads) == len(set(heads))
    for row in body["labels"]:
        assert row["split"] in ("dev", "holdout")
        for e in row["effects"] + row["also_acceptable"]:
            assert e["sector"] in _POLICY_SECTORS
            assert e["direction"] in DIRECTIONS
        if not row["is_policy"]:
            assert not row["effects"]


def test_the_sector_block_carries_the_policy_label_to_the_email():
    from dashboard.sector_blocks import _build_news
    from emails.mailer import _sector_block_news_html

    policy = {
        "measure": "duty_or_tariff",
        "status": "in_force",
        "direction": "tailwind",
    }
    brief = {"clean_energy": [{"title": DUTY, "policy": policy}, {"title": FMCG}]}
    rows = _build_news("clean_energy", brief, set())
    labelled = [r for r in rows if r["headline"] == DUTY]
    assert labelled[0]["policy"] == policy
    assert "policy" not in next(r for r in rows if r["headline"] == FMCG)
    html = _sector_block_news_html({"news": rows})
    assert html.count("Policy tailwind") == 1


def test_the_policy_section_escapes_once_and_names_the_state():
    # _render_email escapes all of brief_data at the boundary; the section
    # escaped again, so "M&M" printed as "M&amp;M" in the inbox.
    from emails.mailer import _escape_deep

    rows = [
        {
            "headline": "Gujarat government extends EV incentive to M&M plant",
            "measure": "incentive_scheme",
            "status": "approved",
            "effects": [{"sector": "aerospace_defence", "direction": "tailwind"}],
            "state": "Gujarat",
            "link": "https://news.test/a?b=1&c=2",
        }
    ]
    html = _build_policy_direction_html(_escape_deep(rows), {"lists": 5})
    assert "M&amp;M plant" in html and "&amp;amp;" not in html
    assert ">Gujarat</span>" in html
    assert "Aerospace &amp; Defence" in html  # the config label, escaped here
