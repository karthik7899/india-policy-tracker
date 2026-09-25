"""The LLM second reader: every guard it depends on, against a fake model.

No test here touches the network. The transport is a function from prompt to
JSON text, so each failure mode — an invented company, a rate limit, a
half-answered batch, an unreadable cache — is reproduced exactly.
"""

import datetime
import json

import pytest

from analysis import llm_reader
from analysis.llm_reader import (
    PROMPT_VERSION,
    ReaderUnavailable,
    ground,
    read_headlines,
    reconcile,
)

TODAY = datetime.date.today().isoformat()

WATCHLIST = {
    "midcap_it": [{"ticker": "PERSISTENT", "name": "Persistent Systems"}],
    "big_cap_industries": [{"ticker": "BPCL", "name": "B P C L"}],
    "manufacturing_electronics": [
        {"ticker": "SYRMA", "name": "Syrma SGS Tech."},
        {"ticker": "KAYNES", "name": "Kaynes Technology"},
    ],
    "clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}],
}

NAGARRO = "Persistent Systems Secures 83.25% Nagarro Ownership, Extends Acceptance to October 6"
SUZLON = "Suzlon bags 306 MW wind turbine orders from Yanara in Rajasthan"


def fake(answers_by_headline, calls=None):
    """A transport answering from a dict keyed by headline."""

    def call(prompt):
        if calls is not None:
            calls.append(prompt)
        out = []
        for line in prompt.splitlines():
            head, _, text = line.partition(": ")
            if head.isdigit() and text in answers_by_headline:
                out.append({"id": int(head), **answers_by_headline[text]})
        return json.dumps(out)

    return call


def _answer(event_type, parties, certainty="completed", amount=""):
    return {
        "event_type": event_type,
        "parties": parties,
        "certainty": certainty,
        "amount_text": amount,
    }


@pytest.fixture
def cache(tmp_path):
    return str(tmp_path / "llm_cache.json")


# ---------------------------------------------------------------------------
# grounding
# ---------------------------------------------------------------------------


def test_a_company_the_headline_never_names_is_dropped():
    reading = ground(
        NAGARRO,
        _answer("acquisition", ["Persistent Systems", "Nagarro", "Accenture"]),
    )
    assert reading["parties"] == ["Persistent Systems", "Nagarro"]


def test_an_amount_not_in_the_headline_is_dropped():
    reading = ground(SUZLON, _answer("order_win", ["Suzlon"], amount="Rs 2,000 crore"))
    assert reading["amount_text"] == ""


def test_an_unknown_type_or_certainty_takes_the_weakest_reading():
    reading = ground(
        SUZLON, {"event_type": "mega_deal", "parties": ["Suzlon"], "certainty": "sure"}
    )
    assert reading["event_type"] == "none" and reading["parties"] == []
    assert (
        ground(SUZLON, _answer("order_win", ["Suzlon"], certainty="sure"))["certainty"]
        == "reported"
    )


# ---------------------------------------------------------------------------
# reading and caching
# ---------------------------------------------------------------------------


def test_without_a_key_the_pass_is_skipped_and_says_why(cache, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    readings, status = read_headlines([NAGARRO], cache_path=cache)
    assert readings == {}
    assert status["skipped"] == "GEMINI_API_KEY not set"
    assert status["pending"] == 1


def test_a_headline_is_read_once_then_served_from_the_cache(cache):
    calls = []
    transport = fake(
        {NAGARRO: _answer("acquisition", ["Persistent Systems", "Nagarro"])}, calls
    )
    first, status = read_headlines([NAGARRO], transport=transport, cache_path=cache)
    assert status["read"] == 1 and len(calls) == 1

    second, status = read_headlines([NAGARRO], transport=transport, cache_path=cache)
    assert status == {"cached": 1, "read": 0, "pending": 0, "skipped": ""}
    assert len(calls) == 1  # no second request
    assert second == first


def test_a_new_prompt_version_rereads_old_headlines(cache, monkeypatch):
    transport = fake({NAGARRO: _answer("acquisition", ["Persistent Systems"])})
    read_headlines([NAGARRO], transport=transport, cache_path=cache)
    monkeypatch.setattr(llm_reader, "PROMPT_VERSION", PROMPT_VERSION + "-next")
    _, status = read_headlines([NAGARRO], transport=transport, cache_path=cache)
    assert status["read"] == 1 and status["cached"] == 0


def test_an_unanswered_headline_is_left_for_the_next_run(cache):
    transport = fake({NAGARRO: _answer("acquisition", ["Persistent Systems"])})
    readings, status = read_headlines(
        [NAGARRO, SUZLON], transport=transport, cache_path=cache
    )
    assert list(readings) == [NAGARRO]
    assert status["pending"] == 1
    with open(cache) as f:
        assert len(json.load(f)["entries"]) == 1


def test_a_rate_limit_keeps_what_was_already_read(cache, monkeypatch):
    monkeypatch.setattr(llm_reader, "BATCH_SIZE", 1)
    monkeypatch.setattr(llm_reader.time, "sleep", lambda s: None)
    answered = fake({NAGARRO: _answer("acquisition", ["Persistent Systems"])})
    state = {"n": 0}

    def flaky(prompt):
        state["n"] += 1
        if state["n"] > 1:
            raise ReaderUnavailable(
                "quota or rate limit reached (429); resuming next run"
            )
        return answered(prompt)

    readings, status = read_headlines(
        [NAGARRO, SUZLON], transport=flaky, cache_path=cache
    )
    assert list(readings) == [NAGARRO]
    assert "429" in status["skipped"] and status["pending"] == 1


def test_an_unreadable_cache_is_never_overwritten(cache):
    with open(cache, "w") as f:
        f.write('{"entries": {')
    readings, status = read_headlines([NAGARRO], transport=fake({}), cache_path=cache)
    assert status["skipped"] == "cache unreadable"
    with open(cache) as f:
        assert f.read() == '{"entries": {'


def test_the_run_is_capped_and_the_backlog_waits(cache, monkeypatch):
    monkeypatch.setattr(llm_reader.time, "sleep", lambda s: None)
    headlines = [f"Suzlon bags order number {i}" for i in range(5)]
    transport = fake({h: _answer("order_win", ["Suzlon"]) for h in headlines})
    _, status = read_headlines(
        headlines, transport=transport, cache_path=cache, max_new=3
    )
    assert status["read"] == 3 and status["pending"] == 2


# ---------------------------------------------------------------------------
# reconciling
# ---------------------------------------------------------------------------


def _rules_event(headline, event_type, actors):
    return {
        "headline": headline,
        "event_type": event_type,
        "phrase": "x",
        "certainty": "completed",
        "domains": [],
        "actors": actors,
        "external": [],
        "direction": "opportunity",
        "date": TODAY,
    }


def test_agreement_is_marked_corroborated():
    events = [_rules_event(SUZLON, "order_win", ["SUZLON"])]
    readings = {SUZLON: ground(SUZLON, _answer("order_win", ["Suzlon"]))}
    events, stats = reconcile(events, readings, WATCHLIST)
    assert events[0]["corroborated"] is True and stats["corroborated"] == 1


def test_on_disagreement_the_rules_stand_and_the_llm_view_is_attached():
    events = [_rules_event(SUZLON, "order_win", ["SUZLON"])]
    readings = {SUZLON: ground(SUZLON, _answer("tie_up", ["Suzlon", "Yanara"]))}
    events, stats = reconcile(events, readings, WATCHLIST)
    (event,) = events
    assert event["event_type"] == "order_win"
    assert event["corroborated"] is False
    assert event["llm_reading"]["event_type"] == "tie_up"
    assert stats["disagreed"] == 1


def test_what_only_the_llm_found_is_added_as_unverified():
    readings = {
        NAGARRO: ground(
            NAGARRO, _answer("acquisition", ["Persistent Systems", "Nagarro"])
        )
    }
    events, stats = reconcile([], readings, WATCHLIST)
    (event,) = events
    assert event["reader"] == "llm" and event["corroborated"] is False
    assert event["actors"] == ["PERSISTENT"]
    assert stats["llm_only"] == 1


def test_an_llm_tie_up_carries_its_counterparty_for_the_review_queue():
    headline = "Kaynes Technology Close To Finalising JV With Bosgame"
    readings = {
        headline: ground(
            headline, _answer("tie_up", ["Kaynes Technology", "Bosgame"], "reported")
        )
    }
    (event,), _ = reconcile([], readings, WATCHLIST)
    assert event["counterparties"] == ["Bosgame"]
    assert event["certainty"] == "reported"


def test_an_llm_event_naming_no_holding_is_not_added():
    headline = "Navitas Invests $5 Million in Magnachip"
    readings = {
        headline: ground(headline, _answer("acquisition", ["Navitas", "Magnachip"]))
    }
    assert reconcile([], readings, WATCHLIST)[0] == []


# ---------------------------------------------------------------------------
# unverified means unverified downstream
# ---------------------------------------------------------------------------


def _llm_event(**kw):
    event = {
        "headline": "BPCL exits Numaligarh Refinery amid supply shortage",
        "event_type": "supply_disruption",
        "phrase": None,
        "certainty": "completed",
        "domains": ["clean_energy"],
        "actors": ["BPCL"],
        "external": ["Vivo"],
        "direction": "risk",
        "date": TODAY,
        "reader": "llm",
    }
    event.update(kw)
    return event


def test_an_llm_only_event_raises_no_warning(monkeypatch):
    import analysis.entity_graph as eg
    from analysis.event_engine import market_event_signals

    monkeypatch.setattr(eg, "load_entity_graph", lambda path=None: {"edges": []})
    assert market_event_signals({"market_events": [_llm_event()]}, WATCHLIST) == []


def test_an_llm_only_event_adds_no_supply_stress():
    from analysis.event_engine import compute_supply_stress

    assert compute_supply_stress([_llm_event()], {"edges": []}) == {}


def test_an_llm_only_event_starts_no_read_through():
    from analysis.read_through import compute_read_throughs

    graph = {
        "edges": [{"src": "Vivo", "dst": "SYRMA", "type": "partner", "evidence": "h"}]
    }
    assert (
        compute_read_throughs([_llm_event(actors=[])], graph, WATCHLIST, today=TODAY)
        == []
    )


def test_refresh_keeps_the_llms_parties_rather_than_rematching_the_headline():
    """Re-matching would attribute every holding the headline mentions."""
    from analysis.event_engine import refresh_merged_events

    event = _llm_event(
        headline="Persistent Systems Secures Nagarro Ownership; Kaynes, Syrma rally",
        actors=["PERSISTENT"],
        event_type="acquisition",
    )
    (kept,) = refresh_merged_events([event], WATCHLIST, today=TODAY)
    assert kept["actors"] == ["PERSISTENT"]


# ---------------------------------------------------------------------------
# the Gemini transport
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, status, body=None, text=""):
        self.status_code = status
        self._body = body
        self.text = text
        self.headers = {}

    def json(self):
        return self._body


def test_the_request_is_deterministic_and_schema_bound(monkeypatch):
    import requests

    seen = {}

    def post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, body=json)
        return _Resp(200, {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]})

    monkeypatch.setattr(requests, "post", post)
    assert llm_reader.gemini_transport("k", "some-model")("prompt") == "[]"
    assert "some-model:generateContent" in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "k"
    config = seen["body"]["generationConfig"]
    assert config["temperature"] == 0
    assert config["responseMimeType"] == "application/json"
    assert config["responseSchema"]["type"] == "ARRAY"


@pytest.mark.parametrize(
    "status, phrase",
    [
        (404, "set GEMINI_MODEL"),
        (403, "key refused"),
        (429, "rate limit"),
        (500, r"unavailable \(500\) after 3 attempts"),
        (418, "HTTP 418"),
    ],
)
def test_each_api_failure_explains_itself(monkeypatch, status, phrase):
    import requests

    monkeypatch.setattr(llm_reader.time, "sleep", lambda s: None)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(status, text="err"))
    with pytest.raises(ReaderUnavailable, match=phrase):
        llm_reader.gemini_transport("k", "m")("prompt")


def test_the_committed_cache_is_well_formed():
    with open(llm_reader.CACHE_PATH, encoding="utf-8") as f:
        body = json.load(f)
    assert isinstance(body.get("entries"), dict)
    for entry in body["entries"].values():
        assert entry["reading"]["event_type"] in llm_reader.EVENT_TYPES + ("none",)


# ---------------------------------------------------------------------------
# scoring the readers
# ---------------------------------------------------------------------------


def test_the_scorer_grades_the_llm_and_the_combination():
    from scripts.eval_events import combined_predictor, llm_predictor, score

    labels = [
        {
            "headline": NAGARRO,
            "event_type": "acquisition",
            "actors": ["PERSISTENT"],
            "split": "holdout",
        },
        {
            "headline": SUZLON,
            "event_type": "order_win",
            "actors": ["SUZLON"],
            "split": "holdout",
        },
    ]
    readings = {
        NAGARRO: ground(
            NAGARRO, _answer("acquisition", ["Persistent Systems", "Nagarro"])
        )
    }
    llm = score(labels, WATCHLIST, llm_predictor(readings, WATCHLIST))["holdout"]
    assert llm["recall"] == 0.5  # caught Nagarro, has no reading for Suzlon
    both = score(labels, WATCHLIST, combined_predictor(readings, WATCHLIST))["holdout"]
    assert both["recall"] == 1.0  # rules catch Suzlon, the LLM catches Nagarro


def test_a_busy_model_is_retried_before_the_run_gives_up(monkeypatch):
    """The first live run lost its whole day to one 503."""
    import requests

    waits = []
    monkeypatch.setattr(llm_reader.time, "sleep", waits.append)
    replies = [
        _Resp(503, text="high demand"),
        _Resp(200, {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}),
    ]
    monkeypatch.setattr(requests, "post", lambda *a, **k: replies.pop(0))
    assert llm_reader.gemini_transport("k", "m")("prompt") == "[]"
    assert waits == [llm_reader.RETRY_BASE_S]


def test_a_model_that_stays_busy_ends_the_pass_cleanly(monkeypatch):
    import requests

    monkeypatch.setattr(llm_reader.time, "sleep", lambda s: None)
    calls = []

    def post(*a, **k):
        calls.append(1)
        return _Resp(503, text="high demand")

    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(ReaderUnavailable, match="after 3 attempts; resuming next run"):
        llm_reader.gemini_transport("k", "m")("prompt")
    assert len(calls) == llm_reader.RETRY_ATTEMPTS


# ---------------------------------------------------------------------------
# model fallback
# ---------------------------------------------------------------------------


def _named(name, outcomes, calls):
    """A transport whose successive calls raise or return from ``outcomes``."""

    def call(prompt):
        calls.append(name)
        outcome = outcomes.pop(0) if outcomes else "[]"
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return call


def test_a_busy_model_hands_over_to_the_next_and_the_next_one_stays():
    calls = []
    busy = ReaderUnavailable(
        "Gemini unavailable (503) after 3 attempts", model_specific=True
    )
    chain = llm_reader.chained_transport(
        [
            ("gemini-3.8-flash", _named("gemini-3.8-flash", [busy], calls)),
            ("gemini-2.5-flash", _named("gemini-2.5-flash", ["[]", "[]"], calls)),
        ]
    )
    assert chain("batch 1") == "[]"
    assert chain("batch 2") == "[]"
    assert chain.model == "gemini-2.5-flash"
    # The busy model is not queued behind again for the second batch.
    assert calls == ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.5-flash"]


def test_a_retired_model_is_skipped_like_a_busy_one():
    calls = []
    gone = ReaderUnavailable("model 'x' not found (404)", model_specific=True)
    chain = llm_reader.chained_transport(
        [("x", _named("x", [gone], calls)), ("y", _named("y", ["[]"], calls))]
    )
    assert chain("p") == "[]" and chain.model == "y"


def test_a_refused_key_stops_at_once_rather_than_trying_every_model():
    calls = []
    refused = ReaderUnavailable("key refused (403)")
    chain = llm_reader.chained_transport(
        [("a", _named("a", [refused], calls)), ("b", _named("b", ["[]"], calls))]
    )
    with pytest.raises(ReaderUnavailable, match="key refused"):
        chain("p")
    assert calls == ["a"]


def test_when_every_model_fails_the_log_names_each_one():
    busy = ReaderUnavailable("busy", model_specific=True)
    chain = llm_reader.chained_transport(
        [("a", _named("a", [busy], [])), ("b", _named("b", [busy], []))]
    )
    with pytest.raises(
        ReaderUnavailable, match=r"every model failed — a: busy; b: busy"
    ):
        chain("p")


def test_the_chain_is_configurable_and_never_repeats_a_model(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)
    assert llm_reader.model_chain() == ["gemini-2.5-flash", "gemini-2.0-flash"]
    monkeypatch.delenv("GEMINI_MODEL")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "m1, m2")
    assert llm_reader.model_chain() == [llm_reader.DEFAULT_MODEL, "m1", "m2"]


def test_the_serving_model_is_recorded_with_each_reading(cache):
    busy = ReaderUnavailable("busy", model_specific=True)
    answer = json.dumps([{"id": 0, **_answer("order_win", ["Suzlon"])}])
    chain = llm_reader.chained_transport(
        [("a", _named("a", [busy], [])), ("b", _named("b", [answer], []))]
    )
    _, status = read_headlines([SUZLON], transport=chain, cache_path=cache)
    assert status["model"] == "b"
    with open(cache) as f:
        (entry,) = json.load(f)["entries"].values()
    assert entry["model"] == "b"
