"""The thesis check: grounding, pair selection, caching, and where it shows."""

import json

import pytest

from analysis import thesis_check
from analysis.llm_reader import ReaderUnavailable
from analysis.thesis_check import (
    annotate_health,
    ground,
    has_thesis,
    pair_key,
    read_pairs,
    run_thesis_check,
    summarise,
    thesis_pairs,
)

THESIS = (
    "Turnaround story, completely debt-free, dominating wind turbine supply "
    "with a record order book."
)
LOAN = "Suzlon Energy raises ₹2,500 crore term loan, ending its debt-free status"
ORDER = "Suzlon bags 400 MW wind EPC order from Tata Power Renewable"
PRICE = "Suzlon Share Price Slumps Over 12% In One Month"
PLACEHOLDER = (
    "Auto-discovered via media radar. Catalyst: Policy tailwinds in the "
    "big_cap_industries segment."
)

WATCHLIST = {
    "clean_energy": [
        {"ticker": "SUZLON", "name": "Suzlon Energy", "catalyst": THESIS},
    ],
    "big_cap_industries": [
        {"ticker": "KPIL", "name": "Kalpataru Projects", "catalyst": PLACEHOLDER},
    ],
    "macro_indicators": [{"ticker": "MAFANG", "name": "ETF", "catalyst": "x"}],
}


def _item(headline, date="24 Sep 2026", status="counted"):
    return {
        "headline": headline,
        "date": date,
        "status": status,
        "source_url": f"https://news.test/{abs(hash(headline))}",
        "source_label": "Test",
    }


COVERAGE = {
    "SUZLON": [
        _item(ORDER, "20 Sep 2026"),
        _item(LOAN, "25 Sep 2026"),
        _item(PRICE, "23 Sep 2026"),
        _item("Suzlon Energy Limited has informed the Exchange about Trading Window"),
        _item("Suzlon old duplicate", status="merged"),
    ],
    "KPIL": [_item("Kalpataru bags ₹2,000 crore orders")],
}


def fake(answers, calls=None):
    """A transport answering by headline text, from the numbered prompt lines."""

    def call(prompt):
        if calls is not None:
            calls.append(prompt)
        out = []
        for line in prompt.splitlines():
            head, _, text = line.strip().partition(": ")
            if head.isdigit() and text in answers:
                out.append({"id": int(head), **answers[text]})
        return json.dumps(out)

    return call


ANSWERS = {
    LOAN: {
        "stance": "contradicts",
        "claim": "completely debt-free",
        "because": "raises ₹2,500 crore term loan",
    },
    ORDER: {
        "stance": "supports",
        "claim": "record order book",
        "because": "bags 400 MW wind EPC order",
    },
    PRICE: {"stance": "unrelated", "claim": "", "because": ""},
}


@pytest.fixture
def cache(tmp_path):
    return str(tmp_path / "thesis_cache.json")


# ---------------------------------------------------------------------------
# grounding
# ---------------------------------------------------------------------------


def test_a_stance_quoting_both_sides_is_kept():
    r = ground(LOAN, THESIS, ANSWERS[LOAN])
    assert r == {
        "stance": "contradicts",
        "claim": "completely debt-free",
        "because": "raises ₹2,500 crore term loan",
    }


def test_a_claim_the_thesis_never_makes_is_downgraded():
    r = ground(
        LOAN,
        THESIS,
        {"stance": "contradicts", "claim": "low leverage", "because": "term loan"},
    )
    assert r["stance"] == "unrelated"
    assert r["downgraded"] == "contradicts"


def test_words_the_headline_never_says_are_downgraded():
    r = ground(
        ORDER,
        THESIS,
        {
            "stance": "supports",
            "claim": "record order book",
            "because": "order book grows",
        },
    )
    assert r["stance"] == "unrelated"
    assert r["downgraded"] == "supports"


def test_typographic_quotes_do_not_fail_a_faithful_quote():
    headline = "Army cancels ideaForge’s ‘Yeti’ drone contract"
    r = ground(
        headline,
        "Pioneer in tactical drones, primary supplier for Indian Army and police",
        {
            "stance": "contradicts",
            "claim": "primary supplier for Indian Army",
            "because": "Army cancels ideaForge's 'Yeti' drone contract",
        },
    )
    assert r["stance"] == "contradicts"


def test_an_unknown_stance_is_the_weakest_reading():
    r = ground(LOAN, THESIS, {"stance": "bearish", "claim": "", "because": ""})
    assert r["stance"] == "unrelated"


# ---------------------------------------------------------------------------
# which headlines are checked
# ---------------------------------------------------------------------------


def test_a_placeholder_is_not_a_thesis():
    assert has_thesis(THESIS)
    assert not has_thesis(PLACEHOLDER)
    assert not has_thesis("")


def test_pairs_are_counted_substantive_headlines_newest_first():
    pairs, no_thesis = thesis_pairs(WATCHLIST, COVERAGE)
    assert [p["headline"] for p in pairs] == [LOAN, PRICE, ORDER]
    assert no_thesis == ["KPIL"]
    assert pairs[0]["date"] == "2026-09-25"
    assert pairs[0]["link"].startswith("https://news.test/")
    assert all(p["ticker"] == "SUZLON" and p["thesis"] == THESIS for p in pairs)


def test_each_holding_is_capped(monkeypatch):
    monkeypatch.setattr(thesis_check, "MAX_PER_HOLDING", 2)
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    assert [p["headline"] for p in pairs] == [LOAN, PRICE]


# ---------------------------------------------------------------------------
# reading and caching
# ---------------------------------------------------------------------------


def test_one_prompt_states_the_thesis_once_per_holding(cache):
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    calls = []
    readings, status = read_pairs(
        pairs, fake(ANSWERS, calls), cache, today="2026-09-26"
    )
    assert status["read"] == 3 and len(calls) == 1
    assert calls[0].count(f"THESIS: {THESIS}") == 1
    key = pair_key("SUZLON", THESIS, LOAN)
    assert readings[key]["stance"] == "contradicts"


def test_a_pair_is_read_once_then_served_from_the_cache(cache):
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    read_pairs(pairs, fake(ANSWERS), cache, today="2026-09-26")
    calls = []
    readings, status = read_pairs(
        pairs, fake(ANSWERS, calls), cache, today="2026-09-27"
    )
    assert calls == [] and status["cached"] == 3 and len(readings) == 3


def test_rewriting_the_thesis_rereads_its_news(cache):
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    read_pairs(pairs, fake(ANSWERS), cache, today="2026-09-26")
    rewritten = [{**p, "thesis": "Wind turbine leader."} for p in pairs]
    calls = []
    read_pairs(rewritten, fake({}, calls), cache, today="2026-09-26")
    assert len(calls) == 1


def test_an_api_failure_keeps_what_was_read_and_says_why(cache):
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)

    def down(prompt):
        raise ReaderUnavailable("quota reached (429)")

    readings, status = read_pairs(pairs, down, cache, today="2026-09-26")
    assert readings == {}
    assert "429" in status["skipped"] and status["pending"] == 3


def test_without_a_key_the_check_is_skipped(cache, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    readings, status = read_pairs(pairs, cache_path=cache)
    assert readings == {} and "GEMINI_API_KEY" in status["skipped"]


def test_the_committed_cache_is_well_formed():
    with open(thesis_check.CACHE_PATH, encoding="utf-8") as f:
        body = json.load(f)
    # The header names the version that last wrote the file; entries from an
    # older version are re-read, not trusted.
    assert isinstance(body["prompt_version"], str)
    for entry in body["entries"].values():
        assert entry["reading"]["stance"] in thesis_check.STANCES


# ---------------------------------------------------------------------------
# results
# ---------------------------------------------------------------------------


def _result(cache):
    pairs, no_thesis = thesis_pairs(WATCHLIST, COVERAGE)
    readings, _ = read_pairs(pairs[:2], fake(ANSWERS), cache, today="2026-09-26")
    return summarise(pairs, readings, no_thesis)


def test_summary_lists_challenges_and_support_with_both_quotes(cache):
    result = _result(cache)
    row = result["holdings"]["SUZLON"]
    assert row["read"] == 2 and row["unread"] == 1  # ORDER was not read
    assert [c["headline"] for c in row["challenged"]] == [LOAN]
    assert row["challenged"][0]["claim"] == "completely debt-free"
    assert row["challenged"][0]["reader"] == "llm"
    assert row["supported"] == []
    assert result["challenged"] == 1
    assert result["no_thesis"] == ["KPIL"]


def test_a_challenge_is_counted_beside_the_status_never_changing_it(cache):
    health = {"SUZLON": {"ticker": "SUZLON", "status": "Intact", "reasons": []}}
    assert annotate_health(health, _result(cache)) == 1
    assert health["SUZLON"]["status"] == "Intact"
    assert health["SUZLON"]["challenges"] == 1


def test_the_whole_pass_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("bad coverage")

    monkeypatch.setattr(thesis_check, "thesis_pairs", boom)
    assert run_thesis_check(WATCHLIST, COVERAGE) == {
        "holdings": {},
        "no_thesis": [],
        "challenged": 0,
    }


# ---------------------------------------------------------------------------
# the email
# ---------------------------------------------------------------------------


def test_the_email_quotes_both_sides_and_escapes_once(cache):
    from emails.mailer import _build_thesis_check_html, _escape_deep

    result = _result(cache)
    challenge = result["holdings"]["SUZLON"]["challenged"][0]
    challenge["headline"] = "Suzlon takes loan & ends debt-free run"
    html = _build_thesis_check_html(_escape_deep(result), {"research": 5})
    assert "Thesis Check" in html
    assert "&ldquo;completely debt-free&rdquo;" in html
    assert "loan &amp; ends" in html and "&amp;amp;" not in html
    assert "1 holding(s) have no written thesis" in html


def test_the_email_says_so_when_nothing_is_challenged(cache):
    from emails.mailer import _build_thesis_check_html

    result = _result(cache)
    result["holdings"]["SUZLON"]["challenged"] = []
    html = _build_thesis_check_html(result, {"research": 5})
    assert "No headline this cycle contradicts a written thesis" in html
    assert _build_thesis_check_html({"holdings": {}}, {"research": 5}) == ""


# ---------------------------------------------------------------------------
# the scorer and its labels
# ---------------------------------------------------------------------------


def test_the_scorer_separates_catches_from_false_alarms():
    from scripts.eval_events import score_thesis

    labels = [
        {
            "ticker": "SUZLON",
            "thesis": THESIS,
            "headline": LOAN,
            "stance": "contradicts",
            "split": "dev",
            "synthetic": True,
        },
        {
            "ticker": "SUZLON",
            "thesis": THESIS,
            "headline": PRICE,
            "stance": "unrelated",
            "split": "dev",
        },
        {
            "ticker": "SUZLON",
            "thesis": THESIS,
            "headline": ORDER,
            "stance": "supports",
            "split": "dev",
        },
    ]
    readings = {
        pair_key("SUZLON", THESIS, LOAN): {"stance": "contradicts"},
        pair_key("SUZLON", THESIS, PRICE): {"stance": "contradicts"},  # the false alarm
        pair_key("SUZLON", THESIS, ORDER): {
            "stance": "unrelated",
            "downgraded": "supports",
        },
    }
    r = score_thesis(labels, readings)["dev"]
    assert r["challenge_recall"] == 1.0
    assert r["challenge_precision"] == 0.5
    assert r["false_alarms"] == 1
    assert r["support_recall"] == 0.0
    assert r["downgraded"] == 1


def test_the_committed_thesis_labels_are_well_formed():
    with open("eval/thesis_labels.json", encoding="utf-8") as f:
        body = json.load(f)
    rows = body["labels"]
    keys = [(r["ticker"], r["headline"]) for r in rows]
    assert len(keys) == len(set(keys))
    for r in rows:
        assert r["stance"] in thesis_check.STANCES
        assert set(r["also_acceptable"]) <= set(thesis_check.STANCES)
        assert r["split"] in ("dev", "holdout")
        assert has_thesis(r["thesis"])
    # Enough of each kind to mean something.
    assert sum(r["stance"] == "contradicts" for r in rows) >= 15
    assert sum(not r.get("synthetic") for r in rows) >= 60


def test_a_claim_that_is_the_whole_thesis_is_no_claim():
    # First live run: ideaForge's quarterly loss was "contradicting" its
    # entire thesis, quoted back verbatim.
    thesis = (
        "Pioneer in tactical and mapping drone systems, primary supplier for "
        "Indian Army and police borders."
    )
    headline = "Supply chain disruptions push ideaForge into losses in Q1FY27"
    r = ground(
        headline,
        thesis,
        {
            "stance": "contradicts",
            "claim": thesis,
            "because": "push ideaForge into losses",
        },
    )
    assert r["stance"] == "unrelated" and r["downgraded"] == "contradicts"
    r = ground(
        headline,
        thesis,
        {
            "stance": "contradicts",
            "claim": "primary supplier for Indian Army",
            "because": "push ideaForge into losses",
        },
    )
    assert r["stance"] == "contradicts"  # a specific claim still stands


def test_the_prompt_limits_results_to_theses_that_name_them():
    from analysis.thesis_check import _prompt

    text = _prompt([(0, {"ticker": "X", "name": "X", "thesis": "t", "headline": "h"})])
    assert "ONLY when the thesis" in text
    assert thesis_check.PROMPT_VERSION != "1"
