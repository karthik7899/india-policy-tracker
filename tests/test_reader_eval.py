"""The reader eval harness: recorded answers, replayed through the readers.

No test here touches the network. The "models" are functions from prompt to
JSON text and the recordings are written to tmp_path, except in the last
test, which replays the committed recordings and holds the committed
scorecards to them.
"""

import copy
import json
import os
import re

import pytest

from analysis import llm_reader, thesis_check
from analysis import reader_recordings as rr
from analysis.llm_reader import ReaderUnavailable, read_headlines
from scripts import reader_eval
from scripts.eval_events import LABELS_PATH, label_pairs, load_holdings, score

A = "Suzlon bags 306 MW wind turbine orders from Yanara in Rajasthan"
B = "Persistent Systems Secures 83.25% Nagarro Ownership"
C = "BPCL exits Numaligarh Refinery"
PAIR = {
    "ticker": "SUZLON",
    "name": "Suzlon Energy",
    "thesis": "Debt-free, with a record order book.",
    "headline": A,
}
OTHER = {
    "ticker": "BPCL",
    "name": "B P C L",
    "thesis": "Refining margins.",
    "headline": C,
}


def _events(*headlines):
    return llm_reader._prompt(list(enumerate(headlines)))


def _key(headline):
    return rr.EVENTS.items(_events(headline))[0][1]


def _model(answer, calls=None, name="test-model"):
    """A live model answering each item of an events prompt from its headline."""

    def call(prompt):
        if calls is not None:
            calls.append(prompt)
        return json.dumps(
            [{"id": i, **answer(text)} for i, _, text in rr.EVENTS.items(prompt)]
        )

    call.model = name
    return call


@pytest.fixture
def store(tmp_path):
    return rr.Recordings(str(tmp_path / "events.json"))


# ---------------------------------------------------------------------------
# codecs
# ---------------------------------------------------------------------------


def test_each_codec_reads_back_its_reader_s_own_prompt():
    assert [(i, t) for i, _, t in rr.EVENTS.items(_events(A, B))] == [(0, A), (1, B)]

    prompt = thesis_check._prompt([(0, PAIR), (1, dict(PAIR, headline=B)), (2, OTHER)])
    assert [(i, t) for i, _, t in rr.THESIS.items(prompt)] == [
        (0, f"SUZLON | {A}"),
        (1, f"SUZLON | {B}"),
        (2, f"BPCL | {C}"),
    ]

    prompt = thesis_check._check_prompt(
        [(0, PAIR, {"claim": "Debt-free"}), (1, OTHER, {"claim": ""})]
    )
    assert [t for _, _, t in rr.CHECK.items(prompt)] == [
        f"SUZLON | {A} | claim: Debt-free",
        f"BPCL | {C} | claim: ",
    ]


def test_an_item_is_known_by_everything_the_model_saw_of_it():
    def key(pair):
        return rr.THESIS.items(thesis_check._prompt([(0, pair)]))[0][1]

    assert key(PAIR) == key(dict(PAIR))
    assert key(PAIR) != key(dict(PAIR, thesis="Market leader."))
    assert key(PAIR) != key(dict(PAIR, name="Suzlon"))
    # Not its place in the batch: here it shares the holding above it.
    batch = thesis_check._prompt([(0, dict(PAIR, headline=B)), (1, PAIR)])
    assert rr.THESIS.items(batch)[1][1] == key(PAIR)


def test_the_fingerprint_is_the_prompt_and_schema_not_the_items(monkeypatch):
    before = rr.EVENTS.fingerprint()
    monkeypatch.setattr(
        llm_reader, "_INSTRUCTIONS", llm_reader._INSTRUCTIONS + "\nBe brief."
    )
    assert rr.EVENTS.fingerprint() != before
    monkeypatch.undo()
    assert rr.EVENTS.fingerprint() == before

    schema = copy.deepcopy(llm_reader._SCHEMA)
    schema["items"]["properties"]["event_type"]["enum"].append("divestment")
    monkeypatch.setattr(llm_reader, "_SCHEMA", schema)
    assert rr.EVENTS.fingerprint() != before

    # One codec's prompt is not another's.
    assert len({c.fingerprint() for c in rr.CODECS}) == 3


def test_a_prompt_the_codec_cannot_read_fails_loudly(monkeypatch):
    with pytest.raises(rr.PromptNotUnderstood):
        rr.EVENTS.items("Classify these: " + A)
    real = llm_reader._prompt
    monkeypatch.setattr(
        llm_reader,
        "_prompt",
        lambda batch: real([]) + "\n".join(f"[{i}] {h}" for i, h in batch),
    )
    with pytest.raises(rr.PromptNotUnderstood):
        rr.EVENTS.items(llm_reader._prompt([(0, A)]))


# ---------------------------------------------------------------------------
# replaying and recording
# ---------------------------------------------------------------------------


def test_replay_answers_by_the_batch_s_own_ids_and_leaves_out_the_rest(store):
    fp = rr.EVENTS.fingerprint()
    store.record(_key(A), fp, A, {"event_type": "order_win"}, "m", "2026-10-24")
    stats = {}
    transport = rr.replaying(rr.EVENTS, store, stats=stats)
    assert json.loads(transport(_events(B, A))) == [
        {"id": 1, "event_type": "order_win"}
    ]
    assert (stats["replayed"], stats["missing"], stats["live_calls"]) == (1, 1, 0)


def test_a_recording_made_for_another_prompt_is_not_served(store):
    store.record(_key(A), "older-prompt", A, {"event_type": "order_win"}, "m", "x")
    assert json.loads(rr.replaying(rr.EVENTS, store)(_events(A))) == []
    assert store.stale(rr.EVENTS.fingerprint()) == 1


def test_recording_asks_only_for_what_has_no_answer_and_keeps_what_was_there(store):
    fp = rr.EVENTS.fingerprint()
    store.record(_key(A), fp, A, {"event_type": "order_win"}, "old-model", "2026-10-01")
    calls = []
    live = _model(lambda text: {"event_type": "none"}, calls, "new-model")
    stats = {}
    transport = rr.replaying(rr.EVENTS, store, live, "2026-10-24", stats)

    transport(_events(A))
    assert calls == []
    out = json.loads(transport(_events(A, B)))
    assert len(calls) == 1
    # A keeps its recorded answer even though the model now says otherwise.
    assert out == [
        {"id": 0, "event_type": "order_win"},
        {"id": 1, "event_type": "none"},
    ]
    assert store.entries[_key(A)]["model"] == "old-model"
    assert store.entries[_key(B)] == {
        "input": B,
        "prompt": fp,
        "answer": {"event_type": "none"},
        "model": "new-model",
        "recorded": "2026-10-24",
    }
    assert stats["recorded"] == 1


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        '{"id": 0, "event_type": "order_win"}',
        '[{"id": "0", "event_type": "order_win"}]',
        '["order_win"]',
        "[]",
    ],
)
def test_an_answer_the_reader_would_drop_is_not_recorded(store, text):
    stats = {}
    out = rr.replaying(rr.EVENTS, store, lambda p: text, stats=stats)(_events(A))
    assert json.loads(out) == [] and store.entries == {}
    assert stats["unparseable"] == (text == "not json")


def test_a_doubled_answer_is_recorded_as_the_reader_reads_it(store, tmp_path):
    def live(prompt):
        return json.dumps(
            [
                {"id": 0, "event_type": "tie_up", "parties": ["Suzlon"]},
                {"id": 0, "event_type": "order_win", "parties": ["Suzlon"]},
            ]
        )

    rr.replaying(rr.EVENTS, store, live)(_events(A))
    assert store.entries[_key(A)]["answer"]["event_type"] == "order_win"
    readings, _ = read_headlines(
        [A], transport=live, cache_path=str(tmp_path / "cache.json")
    )
    assert readings[A]["event_type"] == "order_win"


def test_when_the_model_fails_the_run_goes_on_from_the_recordings(store):
    store.record(
        _key(A), rr.EVENTS.fingerprint(), A, {"event_type": "order_win"}, "m", "x"
    )
    calls = []

    def live(prompt):
        calls.append(prompt)
        raise ReaderUnavailable("quota or rate limit reached (429)")

    stats = {}
    transport = rr.replaying(rr.EVENTS, store, live, stats=stats)
    assert json.loads(transport(_events(B))) == []
    assert json.loads(transport(_events(A, C))) == [
        {"id": 0, "event_type": "order_win"}
    ]
    assert len(calls) == 1 and "429" in stats["live_failed"]


def test_live_calls_are_spaced_and_recorded_batches_wait_for_nothing(
    store, monkeypatch
):
    clock = {"now": 100.0}
    waits = []
    monkeypatch.setattr(rr.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(rr.time, "sleep", waits.append)
    store.record(_key(A), rr.EVENTS.fingerprint(), A, {"event_type": "none"}, "m", "x")
    transport = rr.replaying(
        rr.EVENTS, store, _model(lambda t: {"event_type": "none"}), pacer=rr.Pacer(5)
    )

    transport(_events(B))  # the first live call goes at once
    clock["now"] += 2
    transport(_events(A))  # answered from the recordings
    transport(_events(C))  # live, 2s after the last one
    assert waits == [3]


def test_fresh_asks_again_for_every_item(tmp_path):
    path = str(tmp_path / "events.json")
    old = rr.Recordings(path)
    old.record(
        _key(A), rr.EVENTS.fingerprint(), A, {"event_type": "order_win"}, "m", "x"
    )
    old.save()

    store = rr.Recordings(path, fresh=True)
    calls = []
    transport = rr.replaying(
        rr.EVENTS, store, _model(lambda t: {"event_type": "none"}, calls)
    )
    assert json.loads(transport(_events(A))) == [{"id": 0, "event_type": "none"}]
    # Asked once: what this run recorded is served like any recording.
    assert json.loads(transport(_events(A))) == [{"id": 0, "event_type": "none"}]
    assert len(calls) == 1


def test_recordings_no_label_asks_for_are_dropped(tmp_path):
    path = str(tmp_path / "events.json")
    old = rr.Recordings(path)
    for h in (A, B):
        old.record(
            _key(h), rr.EVENTS.fingerprint(), h, {"event_type": "none"}, "m", "x"
        )
    old.save()

    store = rr.Recordings(path)
    rr.replaying(rr.EVENTS, store)(_events(A))
    assert store.prune() == 1
    store.save()
    assert list(rr.Recordings(path).entries) == [_key(A)]


# ---------------------------------------------------------------------------
# a whole run
# ---------------------------------------------------------------------------


def _fakes(calls):
    """Deterministic stand-ins for the three readers' models."""

    def events(prompt):
        calls["events"] += 1
        out = []
        for i, _, text in rr.EVENTS.items(prompt):
            wins = "order" in text.lower()
            out.append(
                {
                    "id": i,
                    "event_type": "order_win" if wins else "none",
                    "parties": [text.split()[0]] if wins else [],
                    "certainty": "completed",
                    "amount_text": "",
                    "material": wins,
                    "gist": "",
                    "policy_measure": "none",
                    "policy_status": "proposed",
                    "sector_effects": [],
                }
            )
        return json.dumps(out)

    def thesis(prompt):
        calls["thesis"] += 1
        out = []
        body = prompt[len(thesis_check._prompt([])) :]
        for i, identity, _ in rr._parse_thesis(body):
            _, thesis_line, headline = identity.split("\n", 2)
            bad = any(w in headline.lower() for w in ("cut", "cancel", "scrap"))
            out.append({"id": i, "stance": "unrelated", "claim": "", "because": ""})
            if bad:
                # The whole thesis may be quoted as its one claim.
                claim = thesis_line[len("THESIS: ") :]
                out[-1].update(stance="contradicts", claim=claim, because=headline)
            out[-1].update(about=True, group=False)
        return json.dumps(out)

    def check(prompt):
        calls["check"] += 1
        return json.dumps(
            [
                {"id": i, "verdict": "does_not", "because": ""}
                for i, _, _ in rr.CHECK.items(prompt)
            ]
        )

    return {"events": events, "thesis": thesis, "check": check}


def test_a_recorded_run_replays_to_the_same_scorecards(tmp_path, monkeypatch):
    monkeypatch.setattr(reader_eval, "LIVE_SPACING_S", 0)
    caches = (llm_reader.CACHE_PATH, thesis_check.CACHE_PATH)
    before = [os.stat(p).st_mtime_ns if os.path.exists(p) else None for p in caches]
    calls = {"events": 0, "thesis": 0, "check": 0}

    cards, report = reader_eval.run(
        record=True,
        live=_fakes(calls),
        recordings_dir=str(tmp_path),
        today="2026-10-24",
    )
    replayed, again = reader_eval.run(recordings_dir=str(tmp_path))

    assert replayed == cards
    assert all(calls.values()), calls
    assert all(s["recorded"] for s in report.values()), report
    assert all(s["recorded"] == s["missing"] == 0 for s in again.values()), again
    labels = reader_eval._labels()
    assert len(cards["llm"]["rows"]) == len(labels["event"])
    assert len(cards["policy"]["rows"]) == len(labels["policy"])
    assert len(cards["thesis"]["rows"]) == len(labels["thesis"])
    assert cards["llm"]["models"] == {
        "events": {
            "unknown": len(
                set(r["headline"] for r in labels["event"] + labels["policy"])
            )
        }
    }
    # Scratch caches only: the pipeline's own are not touched.
    assert [
        os.stat(p).st_mtime_ns if os.path.exists(p) else None for p in caches
    ] == before


def test_the_thesis_labels_are_asked_with_the_holding_s_name():
    holdings = {"clean_energy": [{"ticker": "SUZLON", "name": "Suzlon Energy"}]}
    rows = [{"ticker": "SUZLON", "thesis": "x", "headline": "y"}, {"ticker": "ZZ"}]
    assert [p["name"] for p in label_pairs(rows, holdings)] == ["Suzlon Energy", "ZZ"]


def test_every_scored_row_has_one_outcome_that_agrees_with_the_metrics():
    with open(LABELS_PATH, encoding="utf-8") as f:
        labels = json.load(f)["labels"]
    result = score(labels, load_holdings())["all"]
    outcomes = [o for _, o, _ in result["outcomes"]]
    assert len(outcomes) == len(labels)
    assert set(outcomes) <= {"found", "missed", "wrong_type", "false_alarm", "quiet"}
    assert (
        round(outcomes.count("found") / result["labelled_events"], 3)
        == result["recall"]
    )


# ---------------------------------------------------------------------------
# comparing with a base
# ---------------------------------------------------------------------------


def _row(outcome, got="", want="acquisition BPCL", split="holdout"):
    return {"split": split, "want": want, "got": got, "outcome": outcome}


def _card(rows=None, reader="llm", **holdout):
    metrics = {}
    for split in reader_eval.SPLITS:
        m = {
            k: None
            for k in reader_eval.HIGHER[reader] + reader_eval.LOWER.get(reader, ())
        }
        m["pending"] = 0
        if split == "holdout":
            m.update(holdout)
        metrics[split] = m
    return {
        "format": reader_eval.FORMAT,
        "reader": reader,
        "metrics": metrics,
        "rows": rows or {},
    }


def test_rows_are_compared_one_by_one():
    base = _card(
        {
            "fixed": _row("missed", "none"),
            "broken": _row("found", "acquisition BPCL"),
            "changed": _row("found", "acquisition BPCL"),
            "same": _row("quiet", "none", want="none"),
            "relabelled": _row("missed", "none"),
            "read": _row("pending"),
            "unread": _row("found", "acquisition BPCL"),
            "gone": _row("found", "acquisition BPCL"),
        }
    )
    now = _card(
        {
            "fixed": _row("found", "acquisition BPCL"),
            "broken": _row("missed", "none"),
            "changed": _row("found", "acquisition BPCL+IOC"),
            "same": _row("quiet", "none", want="none"),
            "relabelled": _row("missed", "none", want="divestment BPCL"),
            "read": _row("found", "acquisition BPCL"),
            "unread": _row("pending"),
            "new": _row("quiet", "none"),
        }
    )
    entry = reader_eval.compare({"llm": base}, {"llm": now})["readers"]["llm"]
    assert {
        kind: [k for k, _, _ in items] for kind, items in entry["rows"].items()
    } == {
        "fixed": ["fixed"],
        "broken": ["broken"],
        "changed": ["changed"],
        "relabelled": ["relabelled"],
        "newly_read": ["read"],
        "unread": ["unread"],
        "added": ["new"],
        "removed": ["gone"],
    }


def test_a_holdout_score_that_falls_fails_the_gate():
    base = {"llm": _card(recall=0.9, precision=0.9)}
    assert (
        reader_eval.compare(base, {"llm": _card(recall=0.9, precision=0.95)})[
            "regressions"
        ]
        == []
    )
    assert reader_eval.compare(base, {"llm": _card(recall=0.85, precision=0.95)})[
        "regressions"
    ] == ["llm: holdout recall 0.9 → 0.85"]
    # Unmeasured on either side is not a fall.
    assert (
        reader_eval.compare(base, {"llm": _card(recall=None, precision=0.9)})[
            "regressions"
        ]
        == []
    )


def test_a_dev_score_that_falls_does_not_fail_the_gate():
    base = _card(recall=0.9)
    base["metrics"]["dev"]["recall"] = 0.9
    now = _card(recall=0.9)
    now["metrics"]["dev"]["recall"] = 0.5
    assert reader_eval.compare({"llm": base}, {"llm": now})["regressions"] == []


def test_more_false_alarms_on_the_holdout_fail_the_gate():
    base = {"thesis": _card(reader="thesis", false_alarms=0)}
    now = {"thesis": _card(reader="thesis", false_alarms=2)}
    assert reader_eval.compare(base, now)["regressions"] == [
        "thesis: holdout false_alarms 0 → 2"
    ]


def test_a_holdout_row_left_without_an_answer_fails_the_gate():
    base = {"llm": _card({"r": _row("found", "acquisition BPCL")})}
    now = {"llm": _card({"r": _row("pending")})}
    (regression,) = reader_eval.compare(base, now)["regressions"]
    assert regression.startswith("llm: 1 holdout row(s) that were read")
    dev = {"llm": _card({"r": _row("pending", split="dev")})}
    dev_base = {"llm": _card({"r": _row("found", "x", split="dev")})}
    assert reader_eval.compare(dev_base, dev)["regressions"] == []


def test_a_reader_the_base_has_no_scorecard_for_is_not_compared():
    out = reader_eval.compare({}, {"llm": _card({"r": _row("missed", "none")})})
    assert out == {"readers": {"llm": {"new": True}}, "regressions": []}


def _all_cards(**holdout):
    return {
        name: _card({"r": _row("found", "x")}, reader=name, **holdout.get(name, {}))
        for name in reader_eval.READERS
    }


def test_a_long_comparison_is_cut_to_fit_a_comment_and_keeps_its_verdict():
    rows = {f"headline {i:03}": _row("found", "acquisition BPCL") for i in range(400)}
    broken = {k: _row("missed", "none") for k in rows}
    cards = {name: _card(reader=name) for name in reader_eval.READERS}
    base = dict(cards, llm=_card(rows, recall=0.9))
    now = dict(cards, llm=_card(broken, recall=0.1))
    report = {"events": {}, "thesis": {}, "check": {}}
    comparison = reader_eval.compare(base, now)

    text = reader_eval.summary(comparison, now, report, "base")
    assert "…and 375 more" in text
    assert text.rstrip().endswith("and re-run the check.")
    assert text.count("<details>") == text.count("</details>")

    for name in ("rules", "combined", "policy"):
        base[name], now[name] = _card(rows, reader=name), _card(broken, reader=name)
    comparison = reader_eval.compare(base, now)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(reader_eval, "MAX_LISTED", 400)
        text = reader_eval.summary(comparison, now, report, "base")
    assert len(text) <= reader_eval.MAX_SUMMARY
    assert "cut to fit a PR comment" in text
    assert text.rstrip().endswith("and re-run the check.")
    head = text[: text.index("cut to fit")]
    assert head.count("<details>") - head.count("</details>") == 1  # closed after


def test_the_command_exits_3_on_a_holdout_regression_unless_allowed(
    monkeypatch, tmp_path
):
    now = _all_cards(llm={"recall": 0.8})
    report = {"events": {}, "thesis": {}, "check": {}}
    monkeypatch.setattr(reader_eval, "run", lambda **kw: (now, report))
    monkeypatch.setattr(reader_eval, "load_cards", lambda *a: now)
    monkeypatch.setattr(
        reader_eval, "cards_at", lambda ref: _all_cards(llm={"recall": 0.9})
    )
    out = tmp_path / "summary.md"

    assert reader_eval.main(["--compare", "base", "--summary", str(out)]) == 3
    text = out.read_text()
    assert "llm: holdout recall 0.9 → 0.8" in text and "fails the gate" in text
    assert reader_eval.main(["--compare", "base", "--allow-regression"]) == 0
    monkeypatch.setattr(reader_eval, "cards_at", lambda ref: now)
    assert reader_eval.main(["--compare", "base"]) == 0


def test_the_check_fails_when_the_scorecards_are_stale(monkeypatch):
    now = _all_cards()
    monkeypatch.setattr(reader_eval, "run", lambda **kw: (now, {}))
    monkeypatch.setattr(
        reader_eval, "load_cards", lambda *a: _all_cards(llm={"recall": 1})
    )
    assert reader_eval.main(["--check"]) == 1
    monkeypatch.setattr(reader_eval, "load_cards", lambda *a: now)
    assert reader_eval.main(["--check"]) == 0


def test_the_live_workflow_runs_only_for_its_label_on_this_repository_s_branches():
    """It holds the model key and pushes to the branch: a fork's PR must not
    reach it, and nothing from the event may be pasted into a shell line."""
    path = os.path.join(reader_eval.ROOT, ".github", "workflows", "reader-eval.yml")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert "github.event.label.name == 'reader-eval'" in text
    assert "github.event.pull_request.head.repo.full_name == github.repository" in text
    # Expressions only as a whole env value or action input, never in a
    # script, where a branch name would become shell.
    whole_value = re.compile(r"\s*[A-Za-z_][\w-]*: \$\{\{[^}]*\}\}\s*\Z")
    for line in text.splitlines():
        if "${{" in line and not line.strip().startswith(("#", "group:")):
            assert whole_value.match(line), line


# ---------------------------------------------------------------------------
# the committed scorecards
# ---------------------------------------------------------------------------


def test_the_committed_scorecards_are_what_the_recordings_give():
    """eval/scorecards/ must be what a replay of eval/recordings/ gives, so a
    PR's diff of them is the change it makes to every reader's scores."""
    cards, report = reader_eval.run()
    committed = reader_eval.load_cards()
    stale = reader_eval.differing(cards, committed)
    if not stale:
        return
    comparison = reader_eval.compare(committed, cards)
    rows = [
        f"  {name}: none committed"
        for name, entry in comparison["readers"].items()
        if entry.get("new")
    ] + [
        f"  {name} {kind}: {key[:90]}"
        for name, entry in comparison["readers"].items()
        if not entry.get("new")
        for kind, items in entry["rows"].items()
        for key, _, _ in items[:3]
    ]
    older = {k: s["stale"] for k, s in report.items() if s.get("stale")}
    pytest.fail(
        "eval/scorecards/ is not what the recorded answers give for: "
        + ", ".join(stale)
        + ".\n"
        + "\n".join(rows)
        + "\nIf a reader's code, the rules or the labels changed, run "
        "`python scripts/reader_eval.py --update` and commit the scorecards. "
        + (
            f"Answers recorded for an older prompt: {older} — add the reader-eval "
            "label to the PR to record them again."
            if older
            else ""
        )
    )
