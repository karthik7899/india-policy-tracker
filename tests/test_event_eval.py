"""The labelled event set, and the floor the rules must stay above.

eval/event_labels.json is how a vocabulary change is judged: before it, one
could only say a new phrase "catches more"; now there is a recall and a
precision to hold it to. These tests keep the file honest and keep the
numbers from sliding back without anyone noticing.

The floors are measured on the HOLDOUT split, which no vocabulary was tuned
against. They sit just under the score when they were set, so an ordinary
change passes and a regression fails. Raise them when the rules genuinely
improve; never lower them to make a change pass without saying why.
"""

import json
import logging
import os

import pytest

from config import SECTOR_METADATA
from scripts.eval_events import LABELS_PATH, score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EVENT_TYPES = {
    "tie_up",
    "acquisition",
    "order_win",
    "capacity_add",
    "supply_disruption",
    "input_cost_shock",
}

# Holdout recall was 0.60 before the gap-tolerant patterns and 0.83 after.
HOLDOUT_RECALL_FLOOR = 0.80
HOLDOUT_PRECISION_FLOOR = 0.95


@pytest.fixture(scope="module")
def labels():
    with open(LABELS_PATH, encoding="utf-8") as f:
        return json.load(f)["labels"]


@pytest.fixture(scope="module")
def watchlist():
    with open(os.path.join(ROOT, "watchlist.json"), encoding="utf-8") as f:
        return json.load(f)


def test_every_label_is_well_formed(labels, watchlist):
    held = {
        s["ticker"]
        for sector, stocks in watchlist.items()
        if sector in SECTOR_METADATA
        for s in stocks or []
        if isinstance(s, dict) and s.get("ticker")
    }
    seen = set()
    for row in labels:
        assert row["headline"] not in seen, f"duplicate: {row['headline']}"
        seen.add(row["headline"])
        assert row["split"] in ("dev", "holdout"), row
        assert row["event_type"] in EVENT_TYPES | {None}, row
        for ticker in row["actors"]:
            assert ticker in held, f"{ticker} is not a holding: {row}"


def test_the_holdout_split_is_large_enough_to_mean_something(labels):
    holdout = [r for r in labels if r["split"] == "holdout"]
    assert sum(1 for r in holdout if r["event_type"] and r["actors"]) >= 25


def test_the_rules_stay_above_the_holdout_floor(labels, watchlist):
    logging.disable(logging.INFO)
    try:
        result = score(labels, watchlist)["holdout"]
    finally:
        logging.disable(logging.NOTSET)
    assert result["recall"] >= HOLDOUT_RECALL_FLOOR, result["misses"]
    assert result["precision"] >= HOLDOUT_PRECISION_FLOOR, result["false_alarms"]
