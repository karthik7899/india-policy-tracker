"""Score the market-event classifier against hand labels.

    python scripts/eval_events.py            # summary per split
    python scripts/eval_events.py --misses   # and every disagreement

Why this exists: every error the classifier had was found by someone
happening to read the right headline. A miss is invisible by construction —
"Persistent Systems Secures 83.25% Nagarro Ownership" matched no vocabulary,
so it produced nothing, which looks exactly like a quiet day. A labelled set
turns "it seems to work" into a number, and it is the only fair way to decide
whether any second reader (an LLM included) actually improves on the rules.

What is scored, for headlines that name a holding:

  recall      labelled events the rules found, with the right type and at
              least one right holding
  precision   events the rules raised that match a labelled event
  actors      of the found events, how many named exactly the right holdings
  partners    of labelled tie-ups with a known counterparty, how many the
              rules named

The split matters. Vocabulary may be tuned against 'dev'. 'holdout' is only
ever measured — tune against it and its score stops meaning anything.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

LABELS_PATH = os.path.join(ROOT, "eval", "event_labels.json")


def _same_party(a: str, b: str) -> bool:
    """Whole-word prefix either way: "Titagarh" is "Titagarh Rail Systems"."""
    x, y = a.lower().split(), b.lower().split()
    shorter, longer = sorted((x, y), key=len)
    return bool(shorter) and longer[: len(shorter)] == shorter


def predict(headline: str, watchlist: Dict[str, Any]) -> Dict[str, Any]:
    """What the rules make of one headline, on its own."""
    from analysis.event_engine import classify_headlines

    events = classify_headlines(
        {"corporate_agreements": [{"title": headline}]}, watchlist, {"edges": []}
    )
    return events[0] if events else {}


def llm_predictor(readings: Dict[str, Dict[str, Any]], watchlist: Dict[str, Any]):
    """What the LLM alone makes of a headline, from its (grounded) reading."""
    from analysis.llm_reader import _holdings, resolve_parties

    holdings = _holdings(watchlist)

    def predict_llm(headline: str, _watchlist) -> Dict[str, Any]:
        reading = readings.get(headline)
        if not reading or reading["event_type"] == "none":
            return {}
        actors, others = resolve_parties(reading["parties"], holdings)
        out = {"event_type": reading["event_type"], "actors": actors}
        if reading["event_type"] == "tie_up":
            out["counterparties"] = others
        return out

    return predict_llm


def combined_predictor(readings: Dict[str, Dict[str, Any]], watchlist: Dict[str, Any]):
    """What the pipeline shows after reconcile(): the rules' event where there
    is one, otherwise an LLM-only event naming a holding."""
    from analysis.llm_reader import reconcile

    def predict_combined(headline: str, wl) -> Dict[str, Any]:
        rules = predict(headline, wl)
        events = [rules] if rules else []
        reading = readings.get(headline)
        if reading:
            events, _ = reconcile(events, {headline: reading}, wl)
        return events[0] if events else {}

    return predict_combined


def score(
    labels: List[Dict[str, Any]],
    watchlist: Dict[str, Any],
    predictor=None,
) -> Dict[str, Any]:
    """Per-split metrics plus the rows behind every miss."""
    predictor = predictor or predict
    out: Dict[str, Any] = {}
    for split in ("dev", "holdout", "all"):
        rows = [r for r in labels if split == "all" or r.get("split") == split]
        positives = found = raised = correct = exact = 0
        partner_total = partner_hit = 0
        misses, false_alarms, wrong_type = [], [], []

        for row in rows:
            pred = predictor(row["headline"], watchlist)
            want_type = row.get("event_type")
            want = set(row.get("actors") or [])
            got = set(pred.get("actors") or [])
            is_positive = bool(want_type and want)
            is_raised = bool(pred and got)

            match = (
                is_raised and pred.get("event_type") == want_type and bool(want & got)
            )
            if is_positive:
                positives += 1
                if match:
                    found += 1
                    exact += got == want
                elif is_raised and want & got:
                    wrong_type.append((row, pred))
                else:
                    misses.append((row, pred))
            if is_raised:
                raised += 1
                if match:
                    correct += 1
                elif not is_positive or not (want & got):
                    false_alarms.append((row, pred))

            known = row.get("counterparties") or []
            if want_type == "tie_up" and known:
                partner_total += 1
                named = pred.get("counterparties") or []
                if any(_same_party(k, n) for k in known for n in named):
                    partner_hit += 1

        def ratio(a, b):
            return round(a / b, 3) if b else None

        out[split] = {
            "rows": len(rows),
            "labelled_events": positives,
            "recall": ratio(found, positives),
            "precision": ratio(correct, raised),
            "actors_exact": ratio(exact, found),
            "partners": ratio(partner_hit, partner_total),
            "misses": misses,
            "wrong_type": wrong_type,
            "false_alarms": false_alarms,
        }
    return out


def _print(result: Dict[str, Any], label: str) -> None:
    for split in ("dev", "holdout", "all"):
        r = result[split]
        print(
            f"{label:9}{split:8} rows={r['rows']:3}  events={r['labelled_events']:3}  "
            f"recall={r['recall']}  precision={r['precision']}  "
            f"actors_exact={r['actors_exact']}  partners={r['partners']}"
        )


def main() -> int:
    import logging

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--misses", action="store_true", help="list disagreements")
    parser.add_argument(
        "--reader",
        choices=("rules", "llm", "combined", "all"),
        default="rules",
        help="which reader to score (llm/combined use llm_cache.json)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="read uncached labelled headlines from the API (needs GEMINI_API_KEY)",
    )
    args = parser.parse_args()

    logging.disable(logging.INFO)
    with open(LABELS_PATH, encoding="utf-8") as f:
        body = json.load(f)
    with open(os.path.join(ROOT, "watchlist.json"), encoding="utf-8") as f:
        watchlist = json.load(f)
    labels = body["labels"]

    if not body.get("reviewed"):
        print("NOTE: labels are a draft nobody has reviewed yet.\n")

    readers = ["rules", "llm", "combined"] if args.reader == "all" else [args.reader]
    readings: Dict[str, Dict[str, Any]] = {}
    if any(r != "rules" for r in readers):
        from analysis.llm_reader import read_headlines

        headlines = [r["headline"] for r in labels]
        if args.live:
            readings, status = read_headlines(headlines)
        else:
            # Cache only: a scoring run must not spend quota by accident.
            readings, status = read_headlines(headlines, transport=_no_calls)
        print(
            f"LLM readings available for {len(readings)} of {len(labels)} labelled "
            f"headlines{'' if args.live else ' (cache only; --live to fill the rest)'}."
        )
        if status.get("skipped") and args.live:
            print(f"LLM reader skipped: {status['skipped']}")
        print()

    for name in readers:
        if name == "rules":
            result = score(labels, watchlist)
        else:
            covered = [r for r in labels if r["headline"] in readings]
            if not covered:
                print(f"{name:9}no readings to score yet\n")
                continue
            make = llm_predictor if name == "llm" else combined_predictor
            result = score(covered, watchlist, make(readings, watchlist))
            if len(covered) < len(labels):
                print(f"{name:9}(scored on the {len(covered)} rows with a reading)")
        _print(result, name)
        print()
        if args.misses:
            r = result["all"]
            for title, items in (
                ("MISSED", r["misses"]),
                ("WRONG TYPE", r["wrong_type"]),
                ("FALSE ALARM", r["false_alarms"]),
            ):
                print(f"  {title} ({len(items)})")
                for row, pred in items:
                    print(
                        f"    [{row.get('split')}] want {row.get('event_type')} "
                        f"{row.get('actors')} · got {pred.get('event_type')} "
                        f"{pred.get('actors')} | {row['headline'][:90]}"
                    )
            print()
    return 0


def _no_calls(prompt: str) -> str:
    from analysis.llm_reader import ReaderUnavailable

    raise ReaderUnavailable("cache-only scoring")


if __name__ == "__main__":
    sys.exit(main())
