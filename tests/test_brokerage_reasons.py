"""Brokerage reasons (analysis/brokerage_reasons.py): what is quoted, when a
publisher is asked for an article, and where the reasons are shown."""

import json

import pytest

from analysis import brokerage_reasons as reasons
from analysis.reader_runtime import ReaderUnavailable
from analysis.thesis_check import pair_key, read_pairs, summarise, thesis_pairs

THESIS = "EMS leader riding mobile exports and a display fab, with a record order book"
UPGRADE = "Dixon Technologies shares rise as Motilal Oswal raises target price"
DOWNGRADE = "Dixon Technologies falls after Jefferies downgrades the stock to hold"
# Good news that is no brokerage's call.
ORDER = "Dixon Technologies bags Rs 1,200 crore order from Vivo"
UPGRADE_SUMMARY = (
    "Motilal Oswal raised its target price, citing mobile exports and the "
    "display fab coming on stream."
)
DOWNGRADE_SUMMARY = "Shares of Dixon Technologies fell 4% on Tuesday."
ARTICLE_URL = "https://www.moneycontrol.com/news/dixon-jefferies.html"
ARTICLE = (
    "Jefferies downgraded Dixon Technologies to hold, saying mobile export "
    "margins are under pressure from new entrants and the display fab will "
    "take longer to pay back."
)

WATCHLIST = {
    "manufacturing_electronics": [
        {"ticker": "DIXON", "name": "Dixon Technologies", "catalyst": THESIS}
    ]
}


def _item(headline, date, **extra):
    return {
        "headline": headline,
        "date": date,
        "status": "counted",
        "source_url": f"https://news.google.test/{abs(hash(headline))}",
        "source_label": "Test",
        **extra,
    }


COVERAGE = {
    "DIXON": [
        _item(UPGRADE, "2026-10-27", summary=UPGRADE_SUMMARY),
        _item(
            DOWNGRADE,
            "2026-10-26",
            summary=DOWNGRADE_SUMMARY,
            article_url=ARTICLE_URL,
        ),
        _item(ORDER, "2026-10-25", summary="The order is for smartphones."),
    ]
}

STANCES = {
    UPGRADE: {
        "stance": "supports",
        "claim": "EMS leader",
        "because": "Motilal Oswal raises target price",
    },
    DOWNGRADE: {
        "stance": "contradicts",
        "claim": "EMS leader",
        "because": "Jefferies downgrades the stock to hold",
    },
    ORDER: {
        "stance": "supports",
        "claim": "record order book",
        "because": "bags Rs 1,200 crore order from Vivo",
    },
}


def fake_thesis(answers):
    def call(prompt):
        out = []
        for line in prompt.splitlines():
            head, _, text = line.strip().partition(": ")
            if head.isdigit() and text in answers:
                out.append({"id": int(head), **answers[text]})
        return json.dumps(out)

    return call


def _downgrade(text):
    if "Jefferies downgraded" not in text:
        # The summary names no reason.
        return {
            "call": "downgrades the stock to hold",
            "brokerage": "Jefferies",
            "reasons": [],
            "claim": "",
        }
    return {
        "call": "downgrades the stock to hold",
        "brokerage": "Jefferies",
        "reasons": [
            "mobile export margins are under pressure from new entrants",
            "the display fab will take longer to pay back",
        ],
        "claim": "riding mobile exports and a display fab",
    }


REASONS = {
    UPGRADE: {
        "call": "raises target price",
        "brokerage": "Motilal Oswal",
        "reasons": ["citing mobile exports and the display fab coming on stream"],
        "claim": "riding mobile exports and a display fab",
    },
    DOWNGRADE: _downgrade,
}


def fake_reasons(answers, seen=None, refuse=None):
    """A reasons reader answering by headline, with an answer or a function of
    the text read; ``seen`` records (headline, text) asked; ``refuse(text)``
    makes a call raise as an unreachable model would."""

    def call(prompt):
        out, current = [], None
        for line in prompt.splitlines():
            line = line.strip()
            head, _, rest = line.partition(": ")
            if head.isdigit() and rest.startswith("HOLDING"):
                current = {"id": int(head)}
            elif line.startswith("HEADLINE: "):
                current["headline"] = line[len("HEADLINE: ") :]
            elif line.startswith("TEXT: "):
                text = line[len("TEXT: ") :]
                if refuse and refuse(text):
                    raise ReaderUnavailable("busy")
                if seen is not None:
                    seen.append((current["headline"], text))
                answer = answers.get(current["headline"])
                if callable(answer):
                    answer = answer(text)
                if answer is not None:
                    out.append({"id": current["id"], **answer})
        return json.dumps(out)

    call.model = "reasons-model"
    return call


def fake_fetch(pages, asked):
    """fetch_article answering from ``pages``: {url: (outcome, detail,
    paragraphs)}; anything else is a 404. Records the URLs asked for."""

    def fetch(url):
        asked.append(url)
        return pages.get(url, ("refused", "HTTP 404", []))

    return fetch


@pytest.fixture
def cache(tmp_path):
    return str(tmp_path / "thesis_cache.json")


def _read(cache, *, today="2026-10-28", reader=None, fetch=None, **kw):
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    return read_pairs(
        pairs,
        fake_thesis(STANCES),
        cache,
        today=today,
        reasons_transport=reader,
        fetch_article=fetch,
        **kw,
    )


def _key(headline):
    return pair_key("DIXON", THESIS, headline)


def _entry(cache, headline):
    return json.load(open(cache))["entries"][_key(headline)]


# ---------------------------------------------------------------------------
# what is quoted
# ---------------------------------------------------------------------------

ITEM = {"headline": DOWNGRADE, "text": ARTICLE, "thesis": THESIS}


def test_the_call_its_reasons_and_the_claim_are_kept_when_quoted():
    r = reasons.ground(ITEM, _downgrade(ARTICLE))
    assert r == {
        "call": "downgrades the stock to hold",
        "brokerage": "Jefferies",
        "reasons": [
            "mobile export margins are under pressure from new entrants",
            "the display fab will take longer to pay back",
        ],
        "claim": "riding mobile exports and a display fab",
    }


def test_words_the_story_never_says_are_dropped():
    r = reasons.ground(
        ITEM,
        {
            "call": "downgrades the stock to hold",
            "brokerage": "Morgan Stanley",
            "reasons": [
                "Dixon is losing its Samsung order",
                "the display fab will take longer to pay back",
                # Only the call again.
                "downgrades the stock",
            ],
            "claim": "a market leader in televisions",
        },
    )
    assert r["brokerage"] == ""
    assert r["reasons"] == ["the display fab will take longer to pay back"]
    assert r["claim"] == ""


def test_no_call_in_the_story_keeps_nothing():
    for raw in (
        {"call": "", "brokerage": "Jefferies", "reasons": ["x"], "claim": "EMS leader"},
        # A call the story does not make.
        {
            "call": "upgrades to buy",
            "brokerage": "Jefferies",
            "reasons": [],
            "claim": "",
        },
    ):
        assert reasons.ground(ITEM, raw) == {
            "call": "",
            "brokerage": "",
            "reasons": [],
            "claim": "",
        }


def test_at_most_three_reasons_and_a_list_only():
    text = "one reason here. two reason here. three reason here. four reason here."
    item = {
        "headline": "Jefferies upgrades Dixon to buy",
        "text": text,
        "thesis": THESIS,
    }
    raw = {
        "call": "upgrades Dixon to buy",
        "brokerage": "Jefferies",
        "reasons": [
            "one reason here",
            "two reason here",
            "three reason here",
            "four reason here",
        ],
        "claim": "",
    }
    assert len(reasons.ground(item, raw)["reasons"]) == reasons.MAX_REASONS
    assert reasons.ground(item, {**raw, "reasons": "one reason here"})["reasons"] == []


def test_only_a_support_or_challenge_that_may_be_a_call_is_asked():
    pair = {"headline": UPGRADE, "summary": UPGRADE_SUMMARY}
    assert reasons.wanted(pair, {"stance": "supports"})
    assert reasons.wanted(pair, {"stance": "contradicts"})
    assert not reasons.wanted(pair, {"stance": "unrelated"})
    # An order win: no call to give reasons for.
    assert not reasons.wanted({**pair, "headline": ORDER}, {"stance": "supports"})
    # Nothing of the story to read it in: a Google News copy.
    assert not reasons.wanted({"headline": UPGRADE}, {"stance": "supports"})


def test_the_prompt_gives_each_story_s_text_on_its_own_line():
    prompt = reasons._prompt(
        [(0, {"name": "Dixon Technologies", "ticker": "DIXON", **ITEM})]
    )
    assert "0: HOLDING: Dixon Technologies (DIXON, listed in India)" in prompt
    assert f"   TEXT: {ARTICLE}" in prompt
    assert "copied EXACTLY" in prompt


# ---------------------------------------------------------------------------
# the summary first, the article once
# ---------------------------------------------------------------------------


def test_a_summary_that_gives_the_reasons_is_all_that_is_read(cache):
    asked, seen = [], []
    readings, status = _read(
        cache, reader=fake_reasons(REASONS, seen), fetch=fake_fetch({}, asked)
    )
    call = readings[_key(UPGRADE)]["call"]
    assert call == {
        "call": "raises target price",
        "brokerage": "Motilal Oswal",
        "reasons": ["citing mobile exports and the display fab coming on stream"],
        "claim": "riding mobile exports and a display fab",
        "source": "summary",
    }
    # Only the downgrade, whose summary gives no reason, asks for its article.
    assert asked == [ARTICLE_URL]
    # The order win makes no call, and is not asked about.
    assert all(h != ORDER for h, _ in seen)
    assert "call" not in readings[_key(ORDER)]


def test_a_call_its_summary_gives_no_reason_for_is_read_in_the_article(cache):
    asked, seen = [], []
    readings, status = _read(
        cache,
        reader=fake_reasons(REASONS, seen),
        fetch=fake_fetch({ARTICLE_URL: ("ok", "", [ARTICLE])}, asked),
    )
    assert asked == [ARTICLE_URL]
    call = readings[_key(DOWNGRADE)]["call"]
    assert call["source"] == "article" and call["url"] == ARTICLE_URL
    assert call["reasons"] == [
        "mobile export margins are under pressure from new entrants",
        "the display fab will take longer to pay back",
    ]
    # The summary first, then the article.
    assert [t for h, t in seen if h == DOWNGRADE] == [DOWNGRADE_SUMMARY, ARTICLE]
    assert (status["reasons_read"], status["articles"]) == (2, 1)
    # Kept with the reading, and the reading stored beside the stance.
    entry = _entry(cache, DOWNGRADE)
    assert entry["reasons"]["text"] == ARTICLE
    assert entry["reasons"]["model"] == "reasons-model"
    assert entry["reading"]["stance"] == "contradicts"
    assert "call" not in entry["reading"]


def test_an_article_is_asked_for_once(cache):
    pages = {ARTICLE_URL: ("ok", "", [ARTICLE])}
    _read(cache, reader=fake_reasons(REASONS), fetch=fake_fetch(pages, []))
    asked, seen = [], []
    readings, status = _read(
        cache,
        today="2026-10-29",
        reader=fake_reasons(REASONS, seen),
        fetch=fake_fetch(pages, asked),
    )
    assert asked == [] and seen == []
    assert readings[_key(DOWNGRADE)]["call"]["source"] == "article"
    assert (status["reasons_read"], status["reasons_cached"]) == (0, 2)


def test_a_new_version_is_asked_of_the_article_s_kept_text(cache, monkeypatch):
    pages = {ARTICLE_URL: ("ok", "", [ARTICLE])}
    _read(cache, reader=fake_reasons(REASONS), fetch=fake_fetch(pages, []))
    monkeypatch.setattr(reasons, "REASONS_VERSION", "99")
    asked, seen = [], []
    readings, _ = _read(
        cache,
        today="2026-10-29",
        reader=fake_reasons(REASONS, seen),
        fetch=fake_fetch(pages, asked),
    )
    assert asked == []
    assert (DOWNGRADE, ARTICLE) in seen
    assert readings[_key(DOWNGRADE)]["call"]["source"] == "article"


def test_an_article_refused_is_never_asked_for_again(cache, monkeypatch):
    pages = {ARTICLE_URL: ("refused", "robots.txt", [])}
    readings, status = _read(
        cache, reader=fake_reasons(REASONS), fetch=fake_fetch(pages, [])
    )
    call = readings[_key(DOWNGRADE)]["call"]
    # The call stands, from the summary, with no reason given.
    assert call["call"] == "downgrades the stock to hold" and call["reasons"] == []
    assert _entry(cache, DOWNGRADE)["reasons"]["fetch"] == "refused: robots.txt"
    assert status["articles_refused"] == 1
    monkeypatch.setattr(reasons, "REASONS_VERSION", "99")
    asked = []
    _read(
        cache,
        today="2026-10-29",
        reader=fake_reasons(REASONS),
        fetch=fake_fetch(pages, asked),
    )
    assert asked == []


def test_an_article_not_asked_for_today_is_asked_for_next_run(cache):
    """robots.txt could not be read: the article was never requested."""
    waiting = {ARTICLE_URL: ("waiting", "robots.txt unread", [])}
    readings, status = _read(
        cache, reader=fake_reasons(REASONS), fetch=fake_fetch(waiting, [])
    )
    assert "call" not in readings[_key(DOWNGRADE)]
    assert status["reasons_pending"] == 1
    asked = []
    readings, _ = _read(
        cache,
        today="2026-10-29",
        reader=fake_reasons(REASONS),
        fetch=fake_fetch({ARTICLE_URL: ("ok", "", [ARTICLE])}, asked),
    )
    assert asked == [ARTICLE_URL]
    assert readings[_key(DOWNGRADE)]["call"]["source"] == "article"


def test_articles_asked_for_in_a_run_are_capped():
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    down = next(p for p in pairs if p["headline"] == DOWNGRADE)
    entries = {_key(DOWNGRADE): {"reading": STANCES[DOWNGRADE]}}
    status = {
        "reasons_read": 0,
        "reasons_pending": 0,
        "reasons_skipped": "",
        "articles": 0,
        "articles_refused": 0,
    }
    asked = []
    reasons.read_reasons(
        [(_key(DOWNGRADE), down)],
        entries,
        fake_reasons(REASONS),
        "2026-10-29",
        status,
        fake_fetch({ARTICLE_URL: ("ok", "", [ARTICLE])}, asked),
        article_limit=0,
    )
    assert asked == [] and status["reasons_pending"] == 1
    assert "reasons" not in entries[_key(DOWNGRADE)]


def test_an_article_fetched_for_a_reader_that_cannot_be_reached_is_kept(cache):
    asked = []
    readings, status = _read(
        cache,
        reader=fake_reasons(REASONS, refuse=lambda text: text == ARTICLE),
        fetch=fake_fetch({ARTICLE_URL: ("ok", "", [ARTICLE])}, asked),
    )
    assert status["reasons_skipped"] == "busy"
    assert "call" not in readings[_key(DOWNGRADE)]
    # The summary's reading made before the failure stands.
    assert readings[_key(UPGRADE)]["call"]["source"] == "summary"
    kept = _entry(cache, DOWNGRADE)["reasons"]
    assert kept["text"] == ARTICLE and kept["v"] == ""
    # The next run reads the kept text and asks the publisher nothing.
    asked = []
    readings, _ = _read(
        cache,
        today="2026-10-29",
        reader=fake_reasons(REASONS),
        fetch=fake_fetch({}, asked),
    )
    assert asked == []
    assert readings[_key(DOWNGRADE)]["call"]["reasons"]


def test_a_supplied_reader_never_asks_a_publisher(cache, monkeypatch):
    """Tests and cache-only scoring pass their own readers."""

    def no_network(*a, **k):
        raise AssertionError("a publisher was asked")

    monkeypatch.setattr("providers.publisher_feeds.fetch_article", no_network)
    readings, status = _read(cache, reader=fake_reasons(REASONS))
    assert readings[_key(UPGRADE)]["call"]["source"] == "summary"
    assert "call" not in readings[_key(DOWNGRADE)]
    assert status["reasons_pending"] == 1


def test_without_a_reasons_reader_the_calls_wait(cache):
    readings, status = _read(cache)
    assert status["reasons_skipped"] == "no reasons reader given"
    assert status["reasons_pending"] == 2
    assert all("call" not in r for r in readings.values())


def test_reasons_read_are_served_on_a_day_without_a_key(cache, monkeypatch):
    _read(
        cache,
        reader=fake_reasons(REASONS),
        fetch=fake_fetch({ARTICLE_URL: ("ok", "", [ARTICLE])}, []),
    )
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    readings, status = read_pairs(pairs, cache_path=cache, today="2026-10-29")
    assert "GEMINI_API_KEY" in status["skipped"]
    assert readings[_key(DOWNGRADE)]["call"]["source"] == "article"
    assert status["reasons_cached"] == 2


# ---------------------------------------------------------------------------
# where the reasons are shown
# ---------------------------------------------------------------------------


def test_a_pair_carries_the_story_s_summary_and_its_own_address():
    pairs, _ = thesis_pairs(WATCHLIST, COVERAGE)
    down = next(p for p in pairs if p["headline"] == DOWNGRADE)
    assert down["summary"] == DOWNGRADE_SUMMARY
    assert down["article_url"] == ARTICLE_URL
    # The article itself, rather than its Google News copy.
    assert down["link"] == ARTICLE_URL


def test_the_summary_the_digest_and_the_email_carry_the_reasons(cache):
    from analysis.company_digest import build_company_digest
    from emails.mailer import _build_companies_html, _build_thesis_check_html

    pairs, no_thesis = thesis_pairs(WATCHLIST, COVERAGE)
    readings, _ = read_pairs(
        pairs,
        fake_thesis(STANCES),
        cache,
        today="2026-10-28",
        reasons_transport=fake_reasons(REASONS),
        fetch_article=fake_fetch({ARTICLE_URL: ("ok", "", [ARTICLE])}, []),
    )
    check = summarise(pairs, readings, no_thesis)
    row = check["holdings"]["DIXON"]
    assert row["challenged"][0]["call"]["brokerage"] == "Jefferies"
    assert row["supported"][0]["call"]["brokerage"] == "Motilal Oswal"
    assert "call" not in next(i for i in row["supported"] if i["headline"] == ORDER)

    digest = build_company_digest(
        WATCHLIST, COVERAGE, {"thesis_check": check}, today="2026-10-28"
    )
    (company,) = digest["companies"]
    assert [(c["stance"], c["brokerage"]) for c in company["calls"]] == [
        ("supports", "Motilal Oswal"),
        ("challenges", "Jefferies"),
    ]
    html = _build_companies_html(digest)
    assert "Jefferies: downgrades the stock to hold" in html
    assert "&ldquo;the display fab will take longer to pay back&rdquo;" in html
    assert "Motilal Oswal: raises target price" in html
    email = _build_thesis_check_html(check)
    assert "Jefferies: downgrades the stock to hold" in email


def test_a_note_on_two_holdings_is_asked_for_once_and_each_read_in_its_part(cache):
    note = "https://www.livemint.com/market/jefferies-picks.html"
    amber_thesis = "Room AC components leader expanding into electronics"
    watchlist = {
        "manufacturing_electronics": [
            {"ticker": "DIXON", "name": "Dixon Technologies", "catalyst": THESIS},
            {"ticker": "AMBER", "name": "Amber Enterprises", "catalyst": amber_thesis},
        ]
    }
    headline = "Jefferies cuts targets on Dixon Technologies and Amber Enterprises"
    coverage = {
        t: [
            _item(
                headline,
                "2026-10-27",
                summary="Jefferies cut targets.",
                article_url=note,
            )
        ]
        for t in ("DIXON", "AMBER")
    }
    stance = {
        "stance": "contradicts",
        "claim": "",
        "because": "Jefferies cuts targets",
    }
    paragraphs = [
        "Jefferies cut its target on Dixon Technologies on slower mobile exports.",
        "Amber Enterprises' target was cut too, on a weak summer for room ACs.",
    ]
    asked, seen = [], []

    def thesis_reader(prompt):
        out, claim = [], None
        for line in prompt.splitlines():
            if line.startswith("THESIS: "):
                claim = line[len("THESIS: ") :].split(",")[0]
            head, _, text = line.strip().partition(": ")
            if head.isdigit() and text == headline:
                out.append({"id": int(head), **stance, "claim": claim})
        return json.dumps(out)

    def call(text):
        return {
            "call": "cuts targets",
            "brokerage": "Jefferies",
            "reasons": [],
            "claim": "",
        }

    pairs, _ = thesis_pairs(watchlist, coverage)
    read_pairs(
        pairs,
        thesis_reader,
        cache,
        today="2026-10-28",
        reasons_transport=fake_reasons({headline: call}, seen),
        fetch_article=fake_fetch({note: ("ok", "", paragraphs)}, asked),
    )
    assert asked == [note]
    article_texts = [t for h, t in seen if t != "Jefferies cut targets."]
    assert sorted(t.split()[0] for t in article_texts) == ["Amber", "Jefferies"]
    assert any(t.startswith("Amber Enterprises' target") for t in article_texts)


def test_a_reasons_reader_that_breaks_costs_the_thesis_check_nothing(cache):
    def broken(prompt):
        raise KeyError("a bug, not a busy model")

    readings, status = _read(cache, reader=broken, fetch=fake_fetch({}, []))
    assert "KeyError" in status["reasons_skipped"]
    assert readings[_key(DOWNGRADE)]["stance"] == "contradicts"
    assert status["reasons_pending"] == 2
