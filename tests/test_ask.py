"""Answering a question from the briefing and the news (analysis/ask.py),
and following it up (scripts/dashboard_actions.py).

The model is never called here: a fake transport records the prompts, so the
tests are about what the answer is drawn from and how failures read. Neither
is the news search: a fake fetch stands in, and a real one fails the test.
"""

import datetime
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from analysis import ask  # noqa: E402
from analysis.reader_runtime import ReaderUnavailable  # noqa: E402


def _refuse(url):
    raise AssertionError(f"a test reached the network: {url}")


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(ask, "_get", _refuse)


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


def test_a_question_can_name_a_holding_as_headlines_do():
    """By the shorter name in headline_names.json, not only the registered
    one: nobody asks about "Kalpataru Projects International"."""
    watchlist = {
        "big_cap_industries": [
            {"ticker": "KPIL", "name": "Kalpataru Projects International"}
        ]
    }
    assert ask.subjects("what orders has Kalpataru Projects won?", watchlist)[0] == [
        "KPIL"
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
    """The model: writes ``plan`` when asked for a search, ``reply`` else."""

    model = "fake-model"

    def __init__(self, reply="SYRMA is **Broken**.", plan="NONE", raise_=None):
        self.reply, self.plan, self.raise_ = reply, plan, raise_
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        if self.raise_:
            raise self.raise_
        return self.plan if prompt.startswith("Plan a Google News") else self.reply


def _item(title, source, day, link):
    return (
        f"<item><title>{title} - {source}</title><link>{link}</link>"
        f"<pubDate>{day} 06:00:00 GMT</pubDate>"
        f'<source url="https://x.in">{source}</source></item>'
    )


def _rss(*items):
    return (
        '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
        + "".join(items)
        + "</channel></rss>"
    )


A = "https://news.google.com/rss/articles/"
RSS = _rss(
    _item(
        "Aditya Infotech Q1: revenue up 30%",
        "Business Standard",
        "Tue, 11 Aug 2026",
        A + "a1",
    ),
    _item(
        "CP Plus maker eyes exports &amp; more",
        "The Economic Times",
        "Fri, 02 Oct 2026",
        A + "a2",
    ),
    # Found for "Aditya Infotech" "order book" on 12 Oct: the words are in the
    # article, the company is not in the headline.
    _item(
        "VA Tech Wabag Q1 profit rises 37%; order book at Rs 19,400 crore",
        "The Financial Express",
        "Wed, 12 Aug 2026",
        A + "a3",
    ),
    _item("An old story", "Mint", "Mon, 01 Jan 2024", A + "a4"),
    _item(
        "CP Plus maker eyes exports &amp; more",
        "The Economic Times",
        "Fri, 02 Oct 2026",
        A + "a5",
    ),
)
PLAN = 'QUERY: "Aditya Infotech" order book\nNAMES: Aditya Infotech; CP Plus'

TODAY = datetime.date(2026, 10, 12)


def _feed(urls=None, status=200, body=RSS):
    def fetch(url):
        if urls is not None:
            urls.append(url)
        return status, body

    return fetch


def test_an_answer_is_drawn_from_the_extract_and_says_what_read_it():
    fake = _Fake()
    text, footer, news = ask.answer("Why is SYRMA broken?", transport=fake)
    assert text == "SYRMA is **Broken**."
    # The model judged that no news answers a question about a grade.
    assert news is None
    prompt = fake.prompts[-1]
    assert "1. DATA: an extract of today's briefing" in prompt
    assert "Never give a figure" in prompt
    assert "**Background (general knowledge, not from a source here)**" in prompt
    assert "NEWS: no search was run for this question" in prompt
    assert "QUESTION: Why is SYRMA broken?" in prompt
    assert '"ticker": "SYRMA"' in prompt
    assert "fake-model" in footer and "SYRMA" in footer and "LLM reading" in footer
    assert "Google News" not in footer
    assert "Background is the model's general knowledge" in footer


def test_the_model_plans_the_search_and_the_answer_cites_what_it_found():
    """12 Oct: "How does CP PLUS order book look like ?" was answered "no
    mention of the order book": the extract was all the model could use."""
    urls = []
    fake = _Fake(reply="**From the news**\n- Exports [1]", plan=PLAN)
    text, footer, news = ask.answer(
        "How does CP PLUS order book look like ?",
        focus="CPPLUS",
        transport=fake,
        fetch=_feed(urls),
        today=TODAY,
    )
    plan, prompt = fake.prompts
    # The search is planned knowing which holding is meant.
    assert '"ticker": "CPPLUS"' in plan and "Aditya Infotech" in plan
    assert "QUESTION: How does CP PLUS order book look like ?" in plan
    # The question's own search, then the company's names alone.
    assert "%22Aditya%20Infotech%22%20order%20book%20when%3A180d" in urls[0]
    assert "%22Aditya%20Infotech%22%20OR%20%22CP%20Plus%22%20when" in urls[1]
    assert news["queries"] == [
        '"Aditya Infotech" order book',
        '"Aditya Infotech" OR "CP Plus"',
    ]
    assert (
        'NEWS (Google News searches: "Aditya Infotech" order book; '
        '"Aditya Infotech" OR "CP Plus"):'
    ) in prompt
    assert (
        "[1] 2026-10-02 · The Economic Times · CP Plus maker eyes exports & more"
        in prompt
    )
    assert "[2] 2026-08-11 · Business Standard" in prompt
    # The other company's order book is not passed off as CP PLUS's.
    assert "Wabag" not in prompt and news["left_out"] == 1
    assert "drawing on CPPLUS, and of 2 headline(s) from Google News" in footer


def test_the_plan_is_read_from_whatever_the_model_wraps_it_in():
    assert ask._read_plan(PLAN) == {
        "query": '"Aditya Infotech" order book',
        "names": ["Aditya Infotech", "CP Plus"],
    }
    assert ask._read_plan('```\nQUERY: "Syrma SGS" margins\nNAMES:\n```') == {
        "query": '"Syrma SGS" margins',
        "names": [],
    }
    # A bare query, the shape the first version asked for.
    assert ask._read_plan('"Dixon Technologies" this week') == {
        "query": '"Dixon Technologies" this week',
        "names": [],
    }
    # Names alone still search for the company's news.
    plan = ask._read_plan(
        'QUERY: NONE\nNAMES: "Dixon Technologies"; Dixon Technologies; ab'
    )
    assert plan == {"query": None, "names": ["Dixon Technologies"]}
    assert ask.searches(plan) == ['"Dixon Technologies"']
    assert ask._read_plan("NONE") is None
    assert ask._read_plan("none.") is None
    assert ask._read_plan("QUERY: ???\nNAMES: none") is None
    assert ask._read_plan("") is None
    assert len(ask._read_plan("word " * 100)["query"]) == ask.MAX_QUERY
    assert ask.searches(None) == []
    # The same search is not run twice.
    assert ask.searches({"query": '"Dixon"', "names": ["Dixon"]}) == ['"Dixon"']


def test_dixon_this_week_is_searched_not_taken_for_the_dashboard():
    """12 Oct: "What changed for Dixon this week?" ran no search: the first
    instructions kept the search off questions about the dashboard's
    "changes", and the model read this one as such."""
    assert "changes" not in ask._SEARCH_INSTRUCTIONS
    assert "how this dashboard works" in ask._SEARCH_INSTRUCTIONS


def test_a_headline_counts_only_if_it_names_the_company():
    dixon = [{"ticker": "DIXON", "name": "Dixon Technologies"}]
    names = ["Dixon Technologies"]
    # The briefing's own matcher reads "Dixon Tech" as Dixon Technologies.
    assert ask.names_company("Dixon Tech shares jump 5% on Q2 hopes", names, dixon)
    assert ask.names_company("dixon technologies wins order", names, [])
    assert not ask.names_company("Amber eyes 20% of Oppo India volumes", names, dixon)
    assert not ask.names_company("Dixon Technologiesx", names, [])


def test_news_is_newest_first_without_old_or_repeated_headlines():
    news = ask.fetch_news(["x"], fetch=_feed(), today=TODAY)
    assert [(i["headline"], i["source"], i["date"]) for i in news["items"]] == [
        ("CP Plus maker eyes exports & more", "The Economic Times", "2026-10-02"),
        (
            "VA Tech Wabag Q1 profit rises 37%; order book at Rs 19,400 crore",
            "The Financial Express",
            "2026-08-12",
        ),
        ("Aditya Infotech Q1: revenue up 30%", "Business Standard", "2026-08-11"),
    ]
    assert news["items"][0]["link"] == A + "a2"
    # Nothing named, nothing left out: a question about an industry.
    assert news["left_out"] == 0 and "error" not in news


def test_the_questions_own_search_comes_first_when_there_is_too_much(monkeypatch):
    monkeypatch.setattr(ask, "MAX_NEWS", 2)
    feeds = {
        "first": _rss(
            _item("Dixon order win", "Mint", "Mon, 10 Aug 2026", A + "f1"),
            _item("Dixon plant", "Mint", "Tue, 11 Aug 2026", A + "f2"),
        ),
        "second": _rss(_item("Dixon newest", "Mint", "Fri, 09 Oct 2026", A + "s1")),
    }

    def fetch(url):
        return 200, feeds["first" if "first" in url else "second"]

    news = ask.fetch_news(["first", "second"], ["Dixon"], [], fetch, TODAY)
    assert [i["headline"] for i in news["items"]] == ["Dixon plant", "Dixon order win"]


def test_a_failed_search_is_said_and_the_answer_goes_on():
    fake = _Fake(plan="QUERY: Syrma SGS margins")
    text, footer, news = ask.answer(
        "Why is SYRMA broken?",
        transport=fake,
        fetch=_feed(status=503, body=""),
        today=TODAY,
    )
    assert text == "SYRMA is **Broken**."
    assert news == {
        "queries": ["Syrma SGS margins"],
        "items": [],
        "left_out": 0,
        "error": "HTTP 503",
    }
    assert "NEWS: none found (searched: Syrma SGS margins)" in fake.prompts[-1]
    assert "The news search failed (HTTP 503)." in footer

    def down(url):
        raise ConnectionError("no route")

    assert ask.fetch_news(["x"], fetch=down)["error"] == "ConnectionError"
    # One search failing is not the search failing.
    flaky = iter([(503, ""), (200, RSS)])
    news = ask.fetch_news(["a", "b"], fetch=lambda url: next(flaky), today=TODAY)
    assert "error" not in news and len(news["items"]) == 3
    empty = ask.fetch_news(["x"], fetch=_feed(body="<rss><channel></channel></rss>"))
    assert empty == {"queries": ["x"], "items": [], "left_out": 0}
    _, footer, _ = ask.answer(
        "How does CP PLUS order book look like ?",
        transport=_Fake(plan=PLAN),
        fetch=_feed(body="<rss><channel></channel></rss>"),
    )
    assert (
        "found no headline naming Aditya Infotech or CP Plus from the last 180 days"
        in footer
    )


def test_a_follow_up_keeps_the_holding_and_reads_the_exchange():
    fake = _Fake(plan="QUERY: Syrma SGS operating margin\nNAMES: Syrma SGS")
    history = [
        ("question", "Why is SYRMA broken?"),
        ("answer", "Margins fell three quarters running."),
    ]
    text, footer, news = ask.answer(
        "and what do they say about it?",
        transport=fake,
        history=history,
        fetch=_feed(),
        today=TODAY,
    )
    plan, prompt = fake.prompts
    # "they" is SYRMA, named only in the first question.
    assert '"ticker": "SYRMA"' in plan and '"ticker": "SYRMA"' in prompt
    assert "CONVERSATION:\nQ: Why is SYRMA broken?\nA: Margins fell" in plan
    assert (
        "CONVERSATION:\nQ: Why is SYRMA broken?\n"
        "A: Margins fell three quarters running.\n\n"
        "QUESTION: and what do they say about it?"
    ) in prompt
    assert "SYRMA" in footer


def test_a_long_exchange_keeps_its_latest_turns(monkeypatch):
    monkeypatch.setattr(ask, "MAX_HISTORY_CHARS", 40)
    kept = ask._history(
        [
            ("question", "first " * 10),
            ("answer", "an old answer"),
            ("question", "  latest   question "),
            ("note", "not a turn"),
        ]
    )
    assert kept == [("answer", "an old answer"), ("question", "latest question")]


def test_a_failed_model_is_the_answer_not_an_exception():
    text, footer, news = ask.answer(
        "anything", transport=_Fake(raise_=ReaderUnavailable("busy"))
    )
    assert text.startswith("Could not answer this time: busy")
    assert footer == "" and news is None
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
        ask,
        "answer",
        lambda q, focus=None, **kw: (f"answer to {q} about {focus}", "foot.", None),
    )
    da.answer_question(5, {"question": "Why?", "focus": "syrma"})
    comment = next(
        kw["json"]["body"] for m, p, kw in calls if p == "/issues/5/comments"
    )
    assert comment.startswith("answer to Why? about SYRMA")
    # How to go on is said where the answer is read.
    assert comment.endswith(
        "\n\n---\n<sub>foot. Comment on this issue to ask a follow-up.</sub>"
    )
    assert "tracker:answered" not in comment
    assert ("PATCH", "/issues/5") in [(m, p) for m, p, _ in calls]
    assert any(p == "/issues/5/labels" for _, p, _ in calls)
    # A focus that is not a ticker is dropped, not passed on.
    calls.clear()
    da.answer_question(6, {"question": "Why?", "focus": "<script>"})
    comment = next(
        kw["json"]["body"] for m, p, kw in calls if p == "/issues/6/comments"
    )
    assert "about None" in comment


def test_the_answers_log_says_which_models_failed_before_one_answered(
    monkeypatch, capsys
):
    """The comment names the model that answered; Ask runs in a workflow of
    its own, so its log is where the models that failed first are told."""
    import dashboard_actions as da
    from analysis import reader_runtime

    monkeypatch.setattr(da, "_api", lambda method, path, **kw: None)

    def busy(prompt):
        raise ReaderUnavailable("busy", model_specific=True)

    def answered(q, focus=None, **kw):
        chain = reader_runtime.chained_transport(
            [("a", busy), ("b", lambda p: "fine")], reader="ask"
        )
        return chain(q), "foot.", None

    monkeypatch.setattr(ask, "answer", answered)
    da.answer_question(7, {"question": "Why?"})
    out = capsys.readouterr().out
    assert "AI readers: ask 1 call(s) in " in out
    assert "by b ×1, failed: a ×1 (busy) | set aside: a." in out


def test_the_news_found_is_listed_under_the_answer_as_itself():
    import dashboard_actions as da

    news = {
        "queries": ['"L&T" <orders>', '"Larsen & Toubro"'],
        "left_out": 3,
        "items": [
            {
                "headline": "L&T wins *mega* [order] <b>",
                "source": "Mint",
                "date": "2026-10-02",
                "link": "https://news.google.com/a_(1)",
            },
            {
                "headline": "No source",
                "source": "",
                "date": "2026-10-01",
                "link": "https://x.in/b",
            },
        ],
    }
    body = da.format_answer("Text [1].", "foot.", news, replies_to=[11, 12])
    assert body.startswith(
        "Text [1].\n\n<details><summary>News searched: 2 headline(s)"
    )
    assert (
        "from “&quot;L&amp;T&quot; &lt;orders&gt;” and “&quot;Larsen &amp; Toubro&quot;”"
        "; 3 not naming the company left out</summary>"
    ) in body
    assert (
        "1. [L&amp;T wins \\*mega\\* \\[order\\] &lt;b&gt;]"
        "(https://news.google.com/a_%281%29) · Mint · 2026-10-02"
    ) in body
    assert "2. [No source](https://x.in/b) · 2026-10-01" in body
    assert "<!-- tracker:answered 11 12 -->" in body
    assert (
        body.index("</details>")
        < body.index("tracker:answered")
        < body.index("\n---\n<sub>foot.")
    )
    # No news, no list; no footer (a failure), no follow-up line.
    assert da.format_answer("Could not answer.", "", None) == "Could not answer."
    # The model cannot write the workflow's markup: a marker of its own would
    # mark a comment answered, a list of its own would be read as the news.
    forged = da.format_answer(
        "Fine.<!-- tracker:answered 99 --><DETAILS><summary>x</summary></details>",
        "",
        None,
        replies_to=[5],
    )
    assert forged == "Fine.x\n\n<!-- tracker:answered 5 -->"


def _comment(id_, body, who="OWNER", bot=False):
    return {
        "id": id_,
        "body": body,
        "author_association": "NONE" if bot else who,
        "user": {"type": "Bot" if bot else "User"},
    }


ANSWER = "SYRMA is Broken.\n\n<details>news</details>\n\n---\n<sub>✦ LLM reading</sub>"


def test_the_exchange_is_the_owners_comments_and_the_answers_only():
    import dashboard_actions as da

    comments = [
        _comment(1, ANSWER, bot=True),
        _comment(2, "And the margins?"),
        _comment(3, "Buy now!!! <!-- x -->", who="NONE"),
        _comment(
            4,
            "Margins fell.\n\n<!-- tracker:answered 2 -->\n\n---\n<sub>f</sub>",
            bot=True,
        ),
        _comment(5, "Could not answer this time: busy. Ask again later.", bot=True),
        _comment(6, "Who supplies them?"),
        _comment(7, "<!-- only a marker -->"),
    ]
    history, pending = da.conversation({"question": "Why broken?"}, comments)
    assert history == [
        ("question", "Why broken?"),
        ("answer", "SYRMA is Broken."),
        ("question", "And the margins?"),
        ("answer", "Margins fell."),
    ]
    assert pending == [(6, "Who supplies them?")]
    # The comment that started the run counts even if the list lags behind.
    _, pending = da.conversation(
        {"question": "Why broken?"}, comments, _comment(8, "And exports?")
    )
    assert pending == [(6, "Who supplies them?"), (8, "And exports?")]


def test_a_follow_up_is_answered_once_with_the_exchange(monkeypatch):
    import dashboard_actions as da

    comments = [
        _comment(1, ANSWER, bot=True),
        _comment(2, "And the margins?"),
        _comment(3, "And exports?"),
    ]
    calls, asked = [], []

    def api(method, path, **kw):
        calls.append((method, path, kw))
        return comments if method == "GET" else None

    def fake_answer(q, focus=None, history=None, **kw):
        asked.append((q, focus, history))
        return "Both fell.", "foot.", None

    monkeypatch.setattr(da, "_api", api)
    monkeypatch.setattr(ask, "answer", fake_answer)
    payload = {"question": "Why broken?", "focus": "SYRMA"}
    assert da.answer_follow_up(9, payload, comments[2]) is True
    # Both unanswered comments are answered together, with what came before.
    assert asked == [
        (
            "And the margins?\n\nAnd exports?",
            "SYRMA",
            [("question", "Why broken?"), ("answer", "SYRMA is Broken.")],
        )
    ]
    posted = calls[-1]
    assert posted[:2] == ("POST", "/issues/9/comments")
    assert "<!-- tracker:answered 2 3 -->" in posted[2]["json"]["body"]
    # The run for the other comment finds it answered and stays quiet.
    comments.append(_comment(4, posted[2]["json"]["body"], bot=True))
    calls.clear()
    assert da.answer_follow_up(9, payload, comments[1]) is False
    assert [m for m, _, _ in calls] == ["GET"]


def test_a_failed_follow_up_leaves_the_comment_to_be_answered_later(monkeypatch):
    import dashboard_actions as da

    calls = []
    monkeypatch.setattr(
        da,
        "_api",
        lambda method, path, **kw: calls.append(kw)
        or ([] if method == "GET" else None),
    )
    monkeypatch.setattr(
        ask, "answer", lambda q, **kw: ("Could not answer this time: busy.", "", None)
    )
    da.answer_follow_up(9, {"question": "Why?"}, _comment(2, "And margins?"))
    assert calls[-1]["json"]["body"] == "Could not answer this time: busy."


def test_only_the_owners_comment_on_a_question_is_a_follow_up(monkeypatch, tmp_path):
    import dashboard_actions as da

    answered = []
    monkeypatch.setattr(
        da, "answer_follow_up", lambda n, p, c: answered.append((n, c["id"])) or True
    )
    body = (
        "<!-- tracker:question v1 -->\n```json\n"
        + json.dumps({"v": 1, "question": "Why?"})
        + "\n```"
    )
    issue = {"number": 4, "body": body, "labels": [{"name": da.QUESTION_LABEL}]}

    def run(issue, comment):
        path = tmp_path / "event.json"
        path.write_text(json.dumps({"issue": issue, "comment": comment}))
        return da.main(str(path))

    assert run(issue, _comment(10, "More?")) == 0
    assert answered == [(4, 10)]
    answered.clear()
    run(issue, _comment(11, "More?", who="CONTRIBUTOR"))
    run(issue, _comment(12, "An answer", bot=True))
    run({**issue, "labels": []}, _comment(13, "More?"))
    run({**issue, "pull_request": {"url": "u"}}, _comment(14, "More?"))
    run({**issue, "body": "a plain issue"}, _comment(15, "More?"))
    assert answered == []


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


def test_a_read_through_reaches_the_extract_with_how_it_travels(tmp_path):
    """The answer can say a lead is a lowest bid or a rumour only if the
    extract tells it so."""
    src = _sources(tmp_path)
    src["briefing"]["read_throughs"] = [
        {
            "trigger": "Elemaster signs MoU for a new plant in India",
            "date": "2026-10-08",
            "direction": "mixed",
            "mechanism": "partner_exposure",
            "transmission": "demand_pull",
            "strength": "soft",
            "weight": 0.5,
            "tickers": ["SYRMA"],
            "chain": ["Elemaster: new capacity", "Elemaster is a partner of SYRMA"],
        }
    ]
    (h,) = ask.build_context("Why is SYRMA broken?", src)["holdings_asked_about"]
    (row,) = h["read_throughs"]
    assert (row["transmission"], row["strength"]) == ("demand_pull", "soft")
    # A ranking number, not something to quote.
    assert "weight" not in row
