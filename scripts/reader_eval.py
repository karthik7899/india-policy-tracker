"""Score the readers on recorded answers, and record new answers live.

    python scripts/reader_eval.py                     # replay and print the scores
    python scripts/reader_eval.py --update            # ... and rewrite eval/scorecards/
    python scripts/reader_eval.py --record --update   # first record what has no answer
                                                      # for today's prompts (GEMINI_API_KEY)
    python scripts/reader_eval.py --compare origin/main [--summary out.md]

scripts/eval_events.py scores the AI readers on whatever the caches hold:
answers from whichever model was up on the day each headline was first read,
and only where a key was set. This scores them on recorded answers
(analysis/reader_recordings.py) instead, so:

  * CI scores every reader without a key, on the same answers each run. A
    change to grounding, reconcile or the rules is measured on those answers
    alone.
  * Each reader has a scorecard (eval/scorecards/) listing every labelled
    row and what the reader made of it, and a change is compared with its
    base row by row: the rows it fixed, the rows it broke, the rows read
    differently.
  * The holdout split is a gate. A change that lowers a holdout score,
    leaves a holdout row unread that was read before, or adds, removes or
    relabels holdout rows, fails unless the PR carries the accept-regression
    label.
  * A prompt change is measured live. Label the PR reader-eval and
    .github/workflows/reader-eval.yml records the new answers, rescores and
    posts the comparison on the PR.

The scorecards are what the readers make of the labels today. Rewrite them
(--update) with any change that moves them, and the tests check that they
match a replay.
"""

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SCORECARD_DIR = os.path.join(ROOT, "eval", "scorecards")
READERS = ("rules", "llm", "combined", "policy", "thesis")
SPLITS = ("holdout", "dev", "all")
# Bumped if a scorecard's shape changes; a base in another format is not
# compared row by row.
FORMAT = 1

_EVENT_METRICS = ("recall", "precision", "actors_exact", "partners")
# Holdout metrics a change may not lower, and those it may not raise.
HIGHER = {
    "rules": _EVENT_METRICS,
    "llm": _EVENT_METRICS,
    "combined": _EVENT_METRICS,
    "policy": ("recall", "precision", "effect_recall", "effect_precision"),
    "thesis": (
        "challenge_recall",
        "challenge_precision",
        "support_recall",
        "support_precision",
        "namesake_recall",
        "namesake_precision",
    ),
}
LOWER = {"thesis": ("false_alarms",)}

# Exit status for a holdout regression, apart from an error's.
REGRESSED = 3

# Between live calls while recording. The readers' own pause is a second,
# and a rate limit then hands the rest of a batch run to the next model in
# the chain: one recording made by several models, which a comparison
# cannot tell from a change in the prompt. A recording is made rarely; it
# can wait.
LIVE_SPACING_S = 5.0

# Rows listed per kind of change in the summary; a PR comment holds 65,536
# characters, and a prompt change can move most rows.
MAX_LISTED = 25
MAX_SUMMARY = 60000


# ---------------------------------------------------------------------------
# reading the labels
# ---------------------------------------------------------------------------


def _labels() -> Dict[str, List[Dict[str, Any]]]:
    from scripts.eval_events import LABELS_PATH, POLICY_LABELS_PATH, THESIS_LABELS_PATH

    out = {}
    for kind, path in (
        ("event", LABELS_PATH),
        ("policy", POLICY_LABELS_PATH),
        ("thesis", THESIS_LABELS_PATH),
    ):
        with open(path, encoding="utf-8") as f:
            out[kind] = json.load(f)["labels"]
    return out


@contextlib.contextmanager
def _without_pauses():
    """The readers pause after every batch. Here most batches are answered
    from the recordings and reach no API; the live calls are spaced by the
    harness instead (LIVE_SPACING_S)."""
    from analysis import llm_reader, thesis_check

    saved = llm_reader.BATCH_PAUSE_S, thesis_check.BATCH_PAUSE_S
    llm_reader.BATCH_PAUSE_S = thesis_check.BATCH_PAUSE_S = 0
    try:
        yield
    finally:
        llm_reader.BATCH_PAUSE_S, thesis_check.BATCH_PAUSE_S = saved


def live_transports() -> Dict[str, Any]:
    """Each reader's own model chain, as production builds it."""
    from analysis import thesis_check
    from analysis.llm_reader import default_transport

    chains = {
        "events": default_transport(),
        "thesis": default_transport(thesis_check._SCHEMA),
        "check": default_transport(
            thesis_check._CHECK_SCHEMA, exclude=thesis_check.CHECK_EXCLUDE
        ),
    }
    refused = [f"{k}: {detail}" for k, (t, detail) in chains.items() if t is None]
    if refused:
        raise SystemExit("Cannot record: " + "; ".join(refused))
    for name, (_, detail) in chains.items():
        print(f"{name:7}live via {detail}")
    return {name: t for name, (t, _) in chains.items()}


def run(
    record: bool = False,
    fresh: bool = False,
    today: str = "",
    live: Optional[Dict[str, Any]] = None,
    recordings_dir: Optional[str] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Every labelled item through the readers, answered from the
    recordings (and, with ``record``, live where they have no answer), then
    scored. Returns ``(scorecards, report)``; the report says, per prompt,
    how many answers were replayed, recorded, stale or missing.

    The readers run as in production, but on scratch caches: a cached
    reading would bypass the recordings, and the real caches are left
    alone. ``live`` replaces the model chains, for tests.
    """
    import datetime

    from analysis import llm_reader, thesis_check
    from analysis.reader_recordings import CHECK, CODECS, EVENTS, THESIS
    from analysis.reader_recordings import RECORDINGS_DIR, Pacer, replaying, stores
    from scripts.eval_events import label_pairs, load_holdings

    today = today or datetime.date.today().isoformat()
    labels = _labels()
    holdings = load_holdings()
    store = stores(fresh, recordings_dir or RECORDINGS_DIR)
    if record and live is None:
        live = live_transports()
    live = live or {}
    stats: Dict[str, Dict[str, Any]] = {c.name: {} for c in CODECS}
    pacer = Pacer(LIVE_SPACING_S)

    def transport(codec):
        return replaying(
            codec,
            store[codec.name],
            live.get(codec.name),
            today,
            stats[codec.name],
            pacer,
        )

    headlines = list(
        dict.fromkeys(r["headline"] for r in labels["event"] + labels["policy"])
    )
    pairs = label_pairs(labels["thesis"], holdings)
    with tempfile.TemporaryDirectory() as tmp, _without_pauses():
        events, _ = llm_reader.read_headlines(
            headlines,
            transport=transport(EVENTS),
            cache_path=os.path.join(tmp, "llm_cache.json"),
            max_new=len(headlines),
            today=today,
        )
        theses, _ = thesis_check.read_pairs(
            pairs,
            transport=transport(THESIS),
            cache_path=os.path.join(tmp, "thesis_cache.json"),
            max_new=len(pairs),
            today=today,
            check_transport=transport(CHECK),
        )
    for codec in CODECS:
        s = store[codec.name]
        stats[codec.name]["stale"] = s.stale(codec.fingerprint())
        if record:
            stats[codec.name]["pruned"] = s.prune()
            if s.changed:
                s.save()
    cards = scorecards(labels, holdings, events, theses, store)
    return cards, stats


# ---------------------------------------------------------------------------
# scorecards
# ---------------------------------------------------------------------------


def _headline(row):
    return row["headline"]


def _pair_name(row):
    return f"{row['ticker']} | {row['headline']}"


def _card(
    reader: str,
    rows: List[Dict[str, Any]],
    result: Dict[str, Any],
    key,
    want,
    prompt: Optional[Dict[str, str]] = None,
    models: Optional[Dict[str, Dict[str, int]]] = None,
) -> Dict[str, Any]:
    """One reader's scorecard: the metrics per split, and every labelled
    row with what the reader made of it ("pending": it has no answer)."""
    scored = {key(r): (outcome, got) for r, outcome, got in result["all"]["outcomes"]}
    out_rows = {}
    for r in rows:
        outcome, got = scored.get(key(r), ("pending", ""))
        out_rows[key(r)] = {
            "split": r.get("split"),
            "want": want(r),
            "got": got,
            "outcome": outcome,
        }
    metrics = {}
    for split in SPLITS:
        m = {k: v for k, v in result[split].items() if not isinstance(v, list)}
        m["pending"] = sum(
            1
            for r in out_rows.values()
            if r["outcome"] == "pending" and split in ("all", r["split"])
        )
        metrics[split] = m
    card: Dict[str, Any] = {
        "format": FORMAT,
        "reader": reader,
        "metrics": metrics,
        "rows": out_rows,
    }
    if prompt is not None:
        card["prompt"] = prompt
    if models is not None:
        card["models"] = models
    return card


def scorecards(labels, holdings, events, theses, store) -> Dict[str, Dict[str, Any]]:
    """Scorecards for the five readers from one replayed run."""
    from analysis.reader_recordings import CHECK, EVENTS, THESIS
    from scripts.eval_events import (
        combined_predictor,
        event_text,
        llm_predictor,
        policy_text,
        score,
        score_policy,
        score_thesis,
        thesis_text,
    )

    def want_event(r):
        return event_text(
            r.get("event_type"), r.get("actors") or [], r.get("counterparties") or ()
        )

    rows = labels["event"]
    covered = [r for r in rows if r["headline"] in events]
    event_prompt = {"events": EVENTS.fingerprint()}
    event_models = {"events": store["events"].models()}
    cards = {
        "rules": _card("rules", rows, score(rows, holdings), _headline, want_event)
    }
    for name, make in (("llm", llm_predictor), ("combined", combined_predictor)):
        result = score(covered, holdings, make(events, holdings))
        cards[name] = _card(
            name, rows, result, _headline, want_event, event_prompt, event_models
        )
    cards["policy"] = _card(
        "policy",
        labels["policy"],
        score_policy(labels["policy"], events),
        _headline,
        policy_text,
        event_prompt,
        event_models,
    )
    cards["thesis"] = _card(
        "thesis",
        labels["thesis"],
        score_thesis(labels["thesis"], theses),
        _pair_name,
        thesis_text,
        {"thesis": THESIS.fingerprint(), "check": CHECK.fingerprint()},
        {"thesis": store["thesis"].models(), "check": store["check"].models()},
    )
    return cards


def write_cards(cards: Dict[str, Dict[str, Any]], directory: str = SCORECARD_DIR):
    from analysis.reader_recordings import write_json

    for name, card in cards.items():
        write_json(os.path.join(directory, f"{name}.json"), card)


def load_cards(directory: str = SCORECARD_DIR) -> Dict[str, Dict[str, Any]]:
    cards = {}
    for name in READERS:
        try:
            with open(os.path.join(directory, f"{name}.json"), encoding="utf-8") as f:
                cards[name] = json.load(f)
        except FileNotFoundError:
            pass
    return cards


def cards_at(ref: str) -> Dict[str, Dict[str, Any]]:
    """The scorecards committed at a git ref; a reader without one there is
    simply absent (the base predates it)."""
    cards = {}
    for name in READERS:
        shown = subprocess.run(
            ["git", "show", f"{ref}:eval/scorecards/{name}.json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if shown.returncode == 0:
            cards[name] = json.loads(shown.stdout)
    return cards


def differing(now: Dict[str, Any], committed: Dict[str, Any]) -> List[str]:
    """Readers whose committed scorecard is not what a replay gives."""
    return [name for name in READERS if now.get(name) != committed.get(name)]


def refresh() -> List[str]:
    """Rescore from the recordings and rewrite the scorecards that changed;
    for label edits (scripts/dashboard_actions.py), which move scores without
    a new answer. Returns the readers rewritten."""
    cards, _ = run()
    changed = differing(cards, load_cards())
    write_cards({name: cards[name] for name in changed})
    return changed


# ---------------------------------------------------------------------------
# comparing with a base
# ---------------------------------------------------------------------------


def _transition(old: Optional[Dict[str, Any]], new: Dict[str, Any]) -> Optional[str]:
    from scripts.eval_events import RIGHT

    if old is None:
        return "added"
    if (old["want"], old["split"]) != (new["want"], new["split"]):
        return "relabelled"
    was, now = old["outcome"], new["outcome"]
    if was == now == "pending":
        return None
    if was == "pending":
        return "newly_read"
    if now == "pending":
        return "unread"
    if (was in RIGHT) != (now in RIGHT):
        return "fixed" if now in RIGHT else "broken"
    if was != now or old["got"] != new["got"]:
        return "changed"
    return None


def _holdout_moved(rows: Dict[str, list]) -> str:
    """How the holdout rows themselves changed, or "". A row moved into or
    out of the split counts as relabelled."""
    counts = {
        "added": sum(1 for _, _, new in rows["added"] if new["split"] == "holdout"),
        "removed": sum(1 for _, old, _ in rows["removed"] if old["split"] == "holdout"),
        "relabelled": sum(
            1
            for _, old, new in rows["relabelled"]
            if "holdout" in (old["split"], new["split"])
        ),
    }
    return ", ".join(f"{n} {kind}" for kind, n in counts.items() if n)


def compare(base: Dict[str, Any], now: Dict[str, Any]) -> Dict[str, Any]:
    """Row-by-row and metric-by-metric differences, and the regressions the
    gate fails on: a holdout metric that got worse, a holdout row that was
    read and now is not, or a change to the holdout rows themselves. Removing
    a hard row or relabelling a missed one raises a score with no reader
    improving, and adding an easy row hides a fall, so the holdout is held
    fixed unless the change is accepted."""
    out: Dict[str, Any] = {"readers": {}, "regressions": []}
    for name in READERS:
        card, old = now.get(name), base.get(name)
        if card is None:
            continue
        if old is None or old.get("format") != FORMAT:
            out["readers"][name] = {"new": True}
            continue
        rows = defaultdict(list)
        for key, row in card["rows"].items():
            kind = _transition(old["rows"].get(key), row)
            if kind:
                rows[kind].append((key, old["rows"].get(key), row))
        for key, row in old["rows"].items():
            if key not in card["rows"]:
                rows["removed"].append((key, row, None))
        metrics = {
            (split, m): (old["metrics"][split].get(m), card["metrics"][split].get(m))
            for split in SPLITS
            for m in HIGHER[name] + LOWER.get(name, ()) + ("pending",)
        }
        for m in HIGHER[name] + LOWER.get(name, ()):
            was, is_ = metrics[("holdout", m)]
            if was is None or is_ is None or was == is_:
                continue
            if (is_ < was) == (m in HIGHER[name]):
                out["regressions"].append(f"{name}: holdout {m} {was} → {is_}")
        unread = [k for k, _, row in rows["unread"] if row["split"] == "holdout"]
        if unread:
            out["regressions"].append(
                f"{name}: {len(unread)} holdout row(s) that were read have no "
                "answer now — record again (label the PR reader-eval)"
            )
        moved = _holdout_moved(rows)
        if moved:
            out["regressions"].append(
                f"{name}: the holdout rows changed ({moved}), so its scores are "
                "not like for like with the base's"
            )
        out["readers"][name] = {
            "rows": {kind: items for kind, items in rows.items() if items},
            "metrics": metrics,
        }
    return out


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


def _metric_line(name: str, metrics: Dict[str, Any]) -> str:
    shown = HIGHER[name] + LOWER.get(name, ())
    return "  ".join(f"{m}={metrics.get(m)}" for m in shown) + (
        f"  rows={metrics.get('rows')}  pending={metrics.get('pending')}"
    )


def print_scores(cards: Dict[str, Any], report: Dict[str, Any]) -> None:
    for codec, s in report.items():
        print(
            f"{codec:7}{s.get('replayed', 0)} replayed, {s.get('recorded', 0)} "
            f"recorded, {s.get('missing', 0)} without an answer "
            f"({s.get('stale', 0)} recorded for an older prompt)"
            + (
                f"; live reader failed: {s['live_failed']}"
                if s.get("live_failed")
                else ""
            )
        )
    print()
    for name in READERS:
        for split in SPLITS:
            print(
                f"{name:9}{split:8} {_metric_line(name, cards[name]['metrics'][split])}"
            )
        print()


def _change(name: str, metric: str, was, is_) -> str:
    if was == is_:
        return f"{metric} {is_}"
    if was is None or is_ is None:
        return f"{metric} {was} → {is_}"
    better = (is_ > was) == (metric not in LOWER.get(name, ()) + ("pending",))
    return f"{metric} {was} → **{is_}** {'▲' if better else '▼'}"


_ROW_TITLES = (
    ("broken", "Broken"),
    ("fixed", "Fixed"),
    ("changed", "Read differently"),
    ("unread", "No answer any more"),
    ("newly_read", "Newly read"),
    ("relabelled", "Relabelled"),
    ("added", "New labels"),
    ("removed", "Labels removed"),
)


def _row_line(key: str, old, new) -> str:
    row = new or old
    text = key if len(key) <= 110 else key[:107] + "…"
    if old is None:
        return (
            f"- `{row['split']}` {text} — want {row['want']} · got {row['got'] or '—'}"
        )
    if new is None:
        return f"- `{row['split']}` {text}"
    return (
        f"- `{row['split']}` {text} — want {new['want']} · was {old['got'] or '—'} "
        f"({old['outcome']}) · now {new['got'] or '—'} ({new['outcome']})"
    )


def summary(
    comparison: Optional[Dict[str, Any]],
    cards: Dict[str, Any],
    report: Dict[str, Any],
    ref: str = "",
    allowed: bool = False,
) -> str:
    """The comparison as Markdown, for the PR comment and the job summary."""
    lines = ["## Reader eval", ""]
    if ref:
        lines += [f"Compared with `{ref}`.", ""]
    for codec, s in report.items():
        lines.append(
            f"- **{codec}** answers: {s.get('replayed', 0)} replayed, "
            f"{s.get('recorded', 0)} recorded live, {s.get('missing', 0)} without "
            f"an answer ({s.get('stale', 0)} recorded for an older prompt)"
            + (
                f"; live reader failed: {s['live_failed']}"
                if s.get("live_failed")
                else ""
            )
        )
    lines += ["", "| Reader | Holdout | Dev |", "|---|---|---|"]
    for name in READERS:
        entry = (comparison or {}).get("readers", {}).get(name, {})
        cells = []
        for split in ("holdout", "dev"):
            now = cards[name]["metrics"][split]
            parts = []
            for m in HIGHER[name] + LOWER.get(name, ()) + ("pending",):
                was = entry.get("metrics", {}).get((split, m), (now.get(m),))[0]
                parts.append(_change(name, m, was, now.get(m)))
            cells.append(" · ".join(parts))
        lines.append(f"| {name} | {cells[0]} | {cells[1]} |")
    if comparison is not None:
        lines.append("")
        for name in READERS:
            entry = comparison["readers"].get(name)
            if not entry:
                continue
            if entry.get("new"):
                lines.append(f"**{name}**: no scorecard at the base to compare with.")
                continue
            counts = [
                f"{len(entry['rows'][kind])} {title.lower()}"
                for kind, title in _ROW_TITLES
                if entry["rows"].get(kind)
            ]
            lines.append(f"**{name}**: " + (", ".join(counts) or "no row changed"))
            for kind, title in _ROW_TITLES:
                items = entry["rows"].get(kind)
                if not items:
                    continue
                lines += [
                    "",
                    f"<details><summary>{name}: {title} ({len(items)})</summary>",
                    "",
                ]
                lines += [_row_line(*item) for item in items[:MAX_LISTED]]
                if len(items) > MAX_LISTED:
                    lines.append(
                        f"- …and {len(items) - MAX_LISTED} more "
                        f"(eval/scorecards/{name}.json has every row)"
                    )
                lines += ["", "</details>", ""]
        lines.append("")
        regressions = comparison["regressions"]
        if not regressions:
            lines.append("✅ No holdout score fell.")
        else:
            verdict = "accepted (accept-regression)" if allowed else "fails the gate"
            lines.append(f"❌ Holdout regression, {verdict}:")
            lines += [f"- {r}" for r in regressions]
            if not allowed:
                lines += [
                    "",
                    "To accept it, add the `accept-regression` label to the PR "
                    "and re-run the check.",
                ]
    text = "\n".join(lines) + "\n"
    if len(text) > MAX_SUMMARY:
        # Cut the row lists, never the verdict at the end.
        end = max(text.rfind("\n✅"), text.rfind("\n❌"))
        tail = text[end:] if end >= 0 else ""
        cut = "\n\n…cut to fit a PR comment; eval/scorecards/ has every row.\n"
        head = text[: MAX_SUMMARY - len(tail) - len(cut) - len("</details>\n")]
        if head.count("<details>") > head.count("</details>"):
            cut += "</details>\n"
        text = head + cut + tail
    return text


def main(argv: Optional[List[str]] = None) -> int:
    import logging

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--record",
        action="store_true",
        help="ask the models live for every item with no answer for the "
        "current prompt (needs GEMINI_API_KEY)",
    )
    parser.add_argument(
        "--fresh", action="store_true", help="with --record, ask again for every item"
    )
    parser.add_argument(
        "--update", action="store_true", help="rewrite eval/scorecards/"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if eval/scorecards/ is not what a replay gives",
    )
    parser.add_argument(
        "--compare", metavar="REF", help="compare with the scorecards at a git ref"
    )
    parser.add_argument(
        "--allow-regression",
        action="store_true",
        help="with --compare, report a holdout regression without failing",
    )
    parser.add_argument(
        "--summary", metavar="PATH", help="append the comparison as Markdown"
    )
    args = parser.parse_args(argv)
    if args.fresh and not args.record:
        parser.error("--fresh needs --record")

    logging.disable(logging.INFO)
    cards, report = run(record=args.record, fresh=args.fresh)
    print_scores(cards, report)

    status = 0
    stale = differing(cards, load_cards())
    if args.update:
        write_cards({name: cards[name] for name in stale})
        print(
            "Rewrote eval/scorecards/ for: " + ", ".join(stale)
            if stale
            else "eval/scorecards/ was already up to date."
        )
    elif stale:
        print(
            "eval/scorecards/ differs from this replay for: "
            + ", ".join(stale)
            + " — run with --update."
        )
        if args.check:
            status = 1

    comparison = None
    if args.compare:
        comparison = compare(cards_at(args.compare), cards)
        if comparison["regressions"] and not args.allow_regression:
            status = REGRESSED
    if args.compare or args.summary:
        text = summary(
            comparison, cards, report, args.compare or "", args.allow_regression
        )
        print(text)
        if args.summary:
            with open(args.summary, "a", encoding="utf-8") as f:
                f.write(text)
    return status


if __name__ == "__main__":
    sys.exit(main())
