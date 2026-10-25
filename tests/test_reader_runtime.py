"""The runtime under every AI reader (analysis/reader_runtime.py): one
model's transport, the chain of models, the key's model list, and the run
that joins the readers.

No test here touches the network. requests is replaced where a transport is
built for real, and elsewhere each "model" is a function from prompt to
text. tests/conftest.py starts every test as a new run.
"""

import pytest

from analysis import llm_reader
from analysis import reader_runtime as rt
from analysis.reader_runtime import ReaderUnavailable

# ---------------------------------------------------------------------------
# one model's transport
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, status, body=None, text=""):
        self.status_code = status
        self._body = body
        self.text = text
        self.headers = {}

    def json(self):
        return self._body


_EMPTY = {"candidates": [{"content": {"parts": [{"text": "[]"}]}}]}


def test_the_request_is_deterministic_and_schema_bound(monkeypatch):
    import requests

    seen = {}

    def post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, body=json)
        return _Resp(200, _EMPTY)

    monkeypatch.setattr(requests, "post", post)
    transport = rt.gemini_transport("k", "some-model", llm_reader._SCHEMA)
    assert transport("prompt") == "[]"
    assert "some-model:generateContent" in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "k"
    config = seen["body"]["generationConfig"]
    assert config["temperature"] == 0
    assert config["responseMimeType"] == "application/json"
    assert config["responseSchema"]["type"] == "ARRAY"


def test_a_question_is_answered_in_prose(monkeypatch):
    import requests

    seen = {}

    def post(url, headers=None, json=None, timeout=None):
        seen.update(body=json)
        return _Resp(200, _EMPTY)

    monkeypatch.setattr(requests, "post", post)
    rt.gemini_transport("k", "m", text=True)("question")
    assert seen["body"]["generationConfig"] == {"temperature": 0}


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

    monkeypatch.setattr(rt.time, "sleep", lambda s: None)
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(status, text="err"))
    with pytest.raises(ReaderUnavailable, match=phrase):
        rt.gemini_transport("k", "m")("prompt")


def test_a_busy_model_is_retried_before_the_run_gives_up(monkeypatch):
    """The first live run lost its whole day to one 503."""
    import requests

    waits = []
    monkeypatch.setattr(rt.time, "sleep", waits.append)
    replies = [_Resp(503, text="high demand"), _Resp(200, _EMPTY)]
    monkeypatch.setattr(requests, "post", lambda *a, **k: replies.pop(0))
    assert rt.gemini_transport("k", "m")("prompt") == "[]"
    assert waits == [rt.RETRY_BASE_S]


def test_a_model_that_stays_busy_ends_the_pass_cleanly(monkeypatch):
    import requests

    monkeypatch.setattr(rt.time, "sleep", lambda s: None)
    calls = []

    def post(*a, **k):
        calls.append(1)
        return _Resp(503, text="high demand")

    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(ReaderUnavailable, match="after 3 attempts; resuming next run"):
        rt.gemini_transport("k", "m")("prompt")
    assert len(calls) == rt.RETRY_ATTEMPTS


def _raising(exc):
    def post(*a, **k):
        raise exc

    return post


def test_a_model_that_times_out_hands_over_to_the_next(monkeypatch):
    """7 Oct: gemini-3.8-flash timed out three times and, read as "no
    network", ended the thesis check with nothing read, while the next model
    in the chain was serving the same run."""
    import requests

    monkeypatch.setattr(rt.time, "sleep", lambda s: None)
    monkeypatch.setattr(
        requests, "post", _raising(requests.exceptions.ReadTimeout("read timed out"))
    )
    with pytest.raises(ReaderUnavailable) as raised:
        rt.gemini_transport("k", "m")("prompt")
    assert raised.value.model_specific


def test_no_network_still_stops_the_whole_chain(monkeypatch):
    """A refused connection fails every model alike; trying each spends the run."""
    import requests

    monkeypatch.setattr(rt.time, "sleep", lambda s: None)
    monkeypatch.setattr(
        requests, "post", _raising(requests.exceptions.ConnectionError("refused"))
    )
    with pytest.raises(ReaderUnavailable) as raised:
        rt.gemini_transport("k", "m")("prompt")
    assert not raised.value.model_specific


# ---------------------------------------------------------------------------
# the chain of models
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


def _busy(why="busy"):
    return ReaderUnavailable(why, model_specific=True)


def test_a_busy_model_hands_over_to_the_next_and_the_next_one_stays():
    calls = []
    busy = _busy("Gemini unavailable (503) after 3 attempts")
    chain = rt.chained_transport(
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
    gone = _busy("model 'x' not found (404)")
    chain = rt.chained_transport(
        [("x", _named("x", [gone], calls)), ("y", _named("y", ["[]"], calls))]
    )
    assert chain("p") == "[]" and chain.model == "y"


def test_a_refused_key_stops_at_once_rather_than_trying_every_model():
    calls = []
    refused = ReaderUnavailable("key refused (403)")
    chain = rt.chained_transport(
        [("a", _named("a", [refused], calls)), ("b", _named("b", ["[]"], calls))]
    )
    with pytest.raises(ReaderUnavailable, match="key refused"):
        chain("p")
    assert calls == ["a"]


def test_when_every_model_fails_the_log_names_each_one():
    chain = rt.chained_transport(
        [("a", _named("a", [_busy()], [])), ("b", _named("b", [_busy()], []))]
    )
    with pytest.raises(
        ReaderUnavailable, match=r"every model failed — a: busy; b: busy"
    ):
        chain("p")


def test_the_chain_is_configurable_and_never_repeats_a_model(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)
    assert rt.model_chain() == ["gemini-2.5-flash", "gemini-2.0-flash"]
    monkeypatch.delenv("GEMINI_MODEL")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "m1, m2")
    assert rt.model_chain() == [rt.DEFAULT_MODEL, "m1", "m2"]


# ---------------------------------------------------------------------------
# asking the API which models the key can use
# ---------------------------------------------------------------------------


def _catalogue(names, status=200):
    return _Resp(
        status,
        {
            "models": [
                {"name": f"models/{n}", "supportedGenerationMethods": methods}
                for n, methods in names
            ]
        },
    )


def test_discovery_lists_usable_flash_models_newest_first(monkeypatch):
    """The fixed fallbacks were both retired (404); the key's own list is not."""
    import requests

    listing = _catalogue(
        [
            ("gemini-2.5-flash", ["generateContent"]),
            ("gemini-3.8-flash-lite", ["generateContent"]),
            ("gemini-3.8-pro", ["generateContent"]),  # not flash
            ("text-embedding-004", ["embedContent"]),  # cannot generate
            ("gemini-3.10-flash-preview", ["generateContent"]),
            ("gemini-3.10-flash", ["generateContent"]),
        ]
    )
    monkeypatch.setattr(requests, "get", lambda *a, **k: listing)
    assert rt.discover_models("k") == [
        "gemini-3.10-flash",
        "gemini-3.10-flash-preview",
        "gemini-3.8-flash-lite",
        "gemini-2.5-flash",
    ]


def test_an_unavailable_list_is_empty_not_an_error(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(403, text="no"))
    assert rt.discover_models("k") == []


@pytest.fixture
def key(monkeypatch):
    """A key, the default model, and no fallbacks named."""
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_FALLBACK_MODELS", raising=False)


def _lists(monkeypatch, names, asked=None):
    def discover(api_key):
        if asked is not None:
            asked.append(api_key)
        return list(names)

    monkeypatch.setattr(rt, "discover_models", discover)


def test_the_chain_puts_discovered_models_after_the_configured_default(
    key, monkeypatch
):
    _lists(monkeypatch, ["gemini-3.8-flash", "gemini-3.8-flash-lite"])
    _, chain = rt.default_transport()
    assert chain.split(" → ") == [
        "gemini-3.8-flash",
        "gemini-3.8-flash-lite",
        *rt.FALLBACK_MODELS,
    ]


def test_an_explicit_fallback_list_is_not_second_guessed(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("GEMINI_FALLBACK_MODELS", "mine")
    monkeypatch.setattr(
        rt, "discover_models", lambda key: pytest.fail("should not be asked")
    )
    _, chain = rt.default_transport()
    assert chain.endswith("mine")


def test_no_key_is_no_chain(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert rt.default_transport() == (None, "GEMINI_API_KEY not set")


# ---------------------------------------------------------------------------
# the run: what one reader learns, the next one uses
# ---------------------------------------------------------------------------


def test_the_key_is_asked_for_its_models_once_a_run(key, monkeypatch):
    """24 Oct: the event reader, the thesis check and its second reading each
    asked for the list."""
    asked = []
    _lists(monkeypatch, ["gemini-3.8-flash"], asked)
    rt.default_transport(reader="events")
    rt.default_transport(reader="thesis")
    rt.default_transport(exclude=("lite",), reader="check")
    assert asked == ["k"]
    rt.reset_run()
    rt.default_transport(reader="events")
    assert asked == ["k", "k"]


def test_models_for_other_media_never_enter_a_chain(key, monkeypatch):
    """24 Oct: the key's list put a text-to-speech and an image model in the
    event reader's chain."""
    _lists(
        monkeypatch,
        [
            "gemini-3.8-flash",
            "gemini-3.8-flash-tts",
            "gemini-3.1-flash-image",
            "gemini-2.5-flash-native-audio",
            "gemini-flash-embedding",
        ],
    )
    _, chain = rt.default_transport()
    assert chain.split(" → ") == ["gemini-3.8-flash", *rt.FALLBACK_MODELS]


def test_a_later_reader_starts_with_the_model_that_answered(key, monkeypatch):
    """The event reader finds out which model is up and which is not; the
    thesis check, minutes later in the same run, starts with the one that
    answered and tries the one that failed last."""
    _lists(monkeypatch, ["gemini-3.8-flash", "gemini-flash-lite-latest"])
    first = rt.chained_transport(
        [
            ("gemini-3.8-flash", _named("gemini-3.8-flash", [_busy()], [])),
            ("gemini-flash-lite-latest", _named("lite", ["[]"], [])),
        ],
        reader="events",
    )
    assert first("event batch") == "[]"

    _, chain = rt.default_transport(reader="thesis")
    assert chain.split(" → ") == [
        "gemini-flash-lite-latest",
        *rt.FALLBACK_MODELS,
        "gemini-3.8-flash",
    ]


def test_a_chain_already_built_follows_what_the_run_learns_later():
    """The second reading's chain is built before the first reading's
    batches run; each of its calls takes the order as it stands."""
    calls = []
    check = rt.chained_transport(
        [("a", _named("a", ["[]"], calls)), ("c", _named("c", ["[]"], calls))],
        reader="check",
    )
    first = rt.chained_transport(
        [("a", _named("a", [_busy()], calls)), ("b", _named("b", ["[]"], calls))],
        reader="thesis",
    )
    first("batch")
    calls.clear()
    assert check("challenge") == "[]"
    assert calls == ["c"]


def test_a_model_set_aside_is_still_tried_when_all_else_fails():
    """A passing fault must not shut a model out of the rest of the run."""
    first = rt.chained_transport(
        [("a", _named("a", [_busy()], [])), ("b", _named("b", ["[]"], []))]
    )
    first("batch")
    assert rt.RUN.failed == {"a": "busy"}
    calls = []
    later = rt.chained_transport(
        [("a", _named("a", ["[]"], calls)), ("c", _named("c", [_busy()], calls))]
    )
    assert later("batch") == "[]" and later.model == "a"
    assert calls == ["c", "a"]
    assert rt.RUN.failed == {"c": "busy"}


def test_a_refused_key_sets_no_model_aside():
    """It says nothing about the model, so the next reader still starts there."""
    chain = rt.chained_transport(
        [("a", _named("a", [ReaderUnavailable("key refused (403)")], []))],
        reader="events",
    )
    with pytest.raises(ReaderUnavailable):
        chain("batch")
    assert rt.RUN.failed == {}
    assert rt.report()["readers"]["events"]["failed"] == {
        "a": {"count": 1, "reason": "key refused (403)"}
    }


def test_a_chain_can_leave_out_the_lite_models(key, monkeypatch):
    """The thesis check's second reading must not be made by the kind of model
    that made the first, even when that model is the one answering."""
    _lists(monkeypatch, ["gemini-3.8-flash", "gemini-flash-lite-latest"])
    rt.RUN.last = "gemini-flash-lite-latest"
    _, chain = rt.default_transport(exclude=("lite",))
    assert chain.split(" → ")[0] == "gemini-3.8-flash"
    assert "lite" not in chain

    rt.reset_run()
    monkeypatch.setattr(rt, "FALLBACK_MODELS", ())
    _lists(monkeypatch, [])
    monkeypatch.setenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    transport, detail = rt.default_transport(exclude=("lite",))
    assert transport is None and "no model left" in detail


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------


def test_the_report_gives_each_readers_calls_models_and_failures():
    events = rt.chained_transport(
        [("a", _named("a", [_busy()], [])), ("b", _named("b", ["[]", "[]"], []))],
        reader="events",
    )
    events("batch 1")
    events("batch 2")
    rt.note("events", {"read": 80, "cached": 400, "pending": 0})
    rt.note(
        "check",
        {"confirmed": None, "refused": None, "pending": 3},
        "every model failed",
    )

    report = rt.report()
    line = report["readers"]["events"]
    assert line["calls"] == 2 and isinstance(line["seconds"], float)
    assert line["answered"] == {"b": 2}
    assert line["failed"] == {"a": {"count": 1, "reason": "busy"}}
    assert line["counts"] == {"read": 80, "cached": 400, "pending": 0}
    assert report["readers"]["check"]["counts"] == {"pending": 3}
    assert report["readers"]["check"]["skipped"] == "every model failed"
    assert report["set_aside"] == {"a": "busy"}

    text = rt.summary()
    assert text.startswith("events 2 call(s) in ")
    assert "by b ×2" in text and text.endswith("set aside: a (busy)")
    assert "check" not in text  # called no model


def test_a_reader_that_did_not_run_has_no_line():
    rt.note("thesis", {"read": None, "cached": None, "pending": None})
    assert rt.report() == {"readers": {}, "set_aside": {}}
    assert rt.summary() == "no reader called a model"
