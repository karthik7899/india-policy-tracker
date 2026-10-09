"""Answering a question from the briefing (analysis/ask.py).

The model is never called here: a fake transport records the prompt, so the
tests are about what the answer is drawn from and how failures read.
"""

import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from analysis import ask  # noqa: E402
from analysis.llm_reader import ReaderUnavailable  # noqa: E402

WATCHLIST = {
    "aerospace_defence": [
        {"ticker": "HAL", "name": "Hindustan Aeronautics", "catalyst": "Fighter jets."},
        {"ticker": "BEL", "name": "Bharat Electronics"},
    ],
    "manufacturing_electronics": [
        {"ticker": "SYRMA", "name": "Syrma SGS Tech.", "catalyst": "EMS growth."},
        {"ticker": "DIXON", "name": "Dixon Technologies"},
    ],
    "data_center_support": [{"ticker": "ANANTRAJ", "name": "Anant Raj Ltd"}],
    "textiles_apparel": [{"ticker": "ARVIND", "name": "Arvind Ltd"}],
    "macro_indicators": [{"ticker": "NIFTY", "name": "Nifty 50"}],
}


def test_a_question_names_its_holdings_and_sectors():
    assert ask.subjects("why is syrma broken?", WATCHLIST) == (["SYRMA"], [])
    assert ask.subjects("what changed for Dixon Technologies", WATCHLIST)[0] == [
        "DIXON"
    ]
    # The page it was asked from comes first.
    assert ask.subjects("and its margins?", WATCHLIST, focus="hal")[0] == ["HAL"]
    assert ask.subjects("which defence holdings have tailwinds", WATCHLIST)[1] == [
        "aerospace_defence"
    ]
    assert ask.subjects("how are semiconductor stocks doing", WATCHLIST)[1] == [
        "semiconductors_equipment"
    ]


def test_ordinary_words_do_not_name_a_holding_or_sector():
    # "data" is not the Data Center sector; a CEO called Arvind is not Arvind Ltd.
    assert ask.subjects("what data do you have?", WATCHLIST) == ([], [])
    assert ask.subjects("IBM CEO Arvind Krishna says", WATCHLIST)[0] == []
    # Macro indicators are not holdings to answer about.
    assert ask.subjects("how is NIFTY", WATCHLIST)[0] == []


def _sources(tmp_path):
    (tmp_path / "news").mkdir()
    (tmp_path / "news" / "SYRMA.json").write_text(
        json.dumps(
            {
                "items": [
                    {"headline": "Syrma opens Jodhpur plant", "date": "2026-10-01"},
                    {"headline": "dup", "status": "merged"},
                ]
            }
        )
    )
    return {
        "briefing": {
            "thesis_health": {
                "SYRMA": {"status": "Broken", "reasons": ["Margins fell 3 quarters"]},
                "HAL": {"status": "Intact", "reasons": []},
            },
            "early_warnings": [
                {"ticker": "SYRMA", "signal": "OPM down", "severity": "High"}
            ],
            "track_record": {"as_of": "2026-10-08", "summary": {"beat": 23}},
        },
        "watchlist": WATCHLIST,
        "digest": {"as_of": "2026-10-08", "companies": []},
        "edges": [{"src": "Elemaster", "dst": "SYRMA", "type": "partner"}],
        "root": str(tmp_path),
    }


def test_the_extract_carries_the_holding_in_full(tmp_path):
    ctx = ask.build_context("Why is SYRMA broken?", _sources(tmp_path))
    (h,) = ctx["holdings_asked_about"]
    assert h["thesis_health"]["status"] == "Broken"
    assert h["warnings"][0]["signal"] == "OPM down"
    assert h["links"][0]["src"] == "Elemaster"
    # Set-aside coverage stays out.
    assert [c["headline"] for c in h["coverage"]] == ["Syrma opens Jodhpur plant"]
    assert ctx["briefing_date"] == "2026-10-08"
    assert "all_holdings" not in ctx


def test_a_general_question_gets_every_holding_in_brief(tmp_path):
    ctx = ask.build_context("How is the portfolio doing?", _sources(tmp_path))
    assert {h["ticker"] for h in ctx["all_holdings"]} == {
        "HAL",
        "BEL",
        "SYRMA",
        "DIXON",
        "ANANTRAJ",
        "ARVIND",
    }
    assert ctx["today"]["broken"] == ["SYRMA"]


def test_an_extract_too_big_is_trimmed_from_the_least_specific_end(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(ask, "MAX_CONTEXT_CHARS", 900)
    ctx = ask.build_context("Why is SYRMA broken?", _sources(tmp_path))
    assert "today" not in ctx
    assert len(json.dumps(ctx, default=str)) <= 900 or not ctx["holdings_asked_about"]


class _Fake:
    model = "fake-model"

    def __init__(self, reply="SYRMA is **Broken**.", raise_=None):
        self.reply, self.raise_, self.prompts = reply, raise_, []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if self.raise_:
            raise self.raise_
        return self.reply


def test_an_answer_is_drawn_from_the_extract_and_says_what_read_it(monkeypatch):
    fake = _Fake()
    text, footer = ask.answer("Why is SYRMA broken?", transport=fake)
    assert text == "SYRMA is **Broken**."
    prompt = fake.prompts[0]
    assert "Answer ONLY from the DATA" in prompt
    assert "QUESTION: Why is SYRMA broken?" in prompt
    assert '"ticker": "SYRMA"' in prompt
    assert "fake-model" in footer and "SYRMA" in footer and "LLM reading" in footer


def test_a_failed_model_is_the_answer_not_an_exception():
    text, footer = ask.answer(
        "anything", transport=_Fake(raise_=ReaderUnavailable("busy"))
    )
    assert text.startswith("Could not answer this time: busy")
    assert footer == ""
    assert ask.answer("   ", transport=_Fake())[0] == "The question was empty."


def test_a_question_request_is_read_from_the_issue():
    import dashboard_actions as da

    body = (
        "Asked.\n<!-- tracker:question v1 -->\n```json\n"
        + json.dumps({"v": 1, "question": "Why?", "focus": "SYRMA"})
        + "\n```"
    )
    kind, payload, error = da.parse_request(body)
    assert (kind, payload["question"], error) == ("question", "Why?", "")


def test_a_question_is_answered_on_the_issue_and_closed(monkeypatch):
    import dashboard_actions as da

    calls = []
    monkeypatch.setattr(
        da, "_api", lambda method, path, **kw: calls.append((method, path, kw))
    )
    monkeypatch.setattr(
        ask, "answer", lambda q, focus=None: (f"answer to {q} about {focus}", "foot")
    )
    da.answer_question(5, {"question": "Why?", "focus": "syrma"})
    comment = next(
        kw["json"]["body"] for m, p, kw in calls if p == "/issues/5/comments"
    )
    assert comment.startswith("answer to Why? about SYRMA") and "foot" in comment
    assert ("PATCH", "/issues/5") in [(m, p) for m, p, _ in calls]
    assert any(p == "/issues/5/labels" for _, p, _ in calls)
    # A focus that is not a ticker is dropped, not passed on.
    calls.clear()
    da.answer_question(6, {"question": "Why?", "focus": "<script>"})
    comment = next(
        kw["json"]["body"] for m, p, kw in calls if p == "/issues/6/comments"
    )
    assert "about None" in comment


def test_a_results_question_gets_the_reported_figures(tmp_path):
    """9 Oct: "How does this quarter results look like", asked of Apollo
    Hospitals, was answered "the data does not contain the quarterly results"
    while the pipeline held eight quarters of them."""
    src = _sources(tmp_path)
    watchlist = json.loads(json.dumps(WATCHLIST))
    watchlist["manufacturing_electronics"][0].update(
        earnings_growth="+34.1%",
        screener={
            "q_sales": 7044.0,
            "qoq_sales_growth": 6.63,
            "revenue_yoy_pct": 20.6,
            "q_opm": 16.0,
            "q_net_profit": 610.0,
            "q_eps": 40.39,
            "sales_trend": [5842.0, 6304.0, 6477.0, 6606.0, 7044.0],
            # Holds four quarters of sales despite its name; not passed on as
            # a growth figure.
            "quarterly_revenue_growth": [6304.0, 6477.0, 6606.0, 7044.0],
            "annual_sales_trend": [25228.0, 26430.0],
            "promoter_pct": 28.02,
            "pe_ratio": 54.8,
        },
    )
    src["watchlist"] = watchlist
    ctx = ask.build_context("How does this quarter results look like", src, "SYRMA")
    reported = ctx["holdings_asked_about"][0]["reported"]
    assert reported["latest_quarter"] == {
        "sales_cr": 7044.0,
        "sales_change_vs_previous_quarter_pct": 6.63,
        "sales_change_vs_year_ago_quarter_pct": 20.6,
        "operating_margin_pct": 16.0,
        "net_profit_cr": 610.0,
        "eps": 40.39,
    }
    assert reported["quarterly_oldest_first"]["sales_cr"][-1] == 7044.0
    assert reported["annual_oldest_first_last_is_trailing_12_months"]["sales_cr"] == [
        25228.0,
        26430.0,
    ]
    assert reported["growth"]["earnings_growth_yahoo"] == "+34.1%"
    assert reported["shareholding_pct"] == {"promoter": 28.02}
    assert "quarterly_revenue_growth" not in json.dumps(reported)
    # The model is told the units and the order, and not to invent quarter names.
    assert "oldest to latest" in ctx["how_to_read"]
    assert "Quarter names are not recorded" in ctx["how_to_read"]


def test_a_holding_without_reported_figures_says_nothing_rather_than_zero(tmp_path):
    ctx = ask.build_context("Why is SYRMA broken?", _sources(tmp_path))
    assert ctx["holdings_asked_about"][0]["reported"] == {}
