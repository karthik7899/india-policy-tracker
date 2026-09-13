"""The daily workflow's `git add` list must cover everything the run writes.

This exists because it did not, and the cost was disproportionate to the
mistake. PR #142 started writing payload sidecars into data/ and committed the
first copies, but the workflow's add list was never extended. Every subsequent
run rewrote those 56 tracked files, left them unstaged, committed the staged
subset, and then hit:

    error: cannot pull with rebase: You have unstaged changes.

The email still sent — that happens before the git step — so the only symptom
was a failure alert with a git message that points at rebase rather than at the
add list. Two trading days of dashboard data never reached main.

The add list is an allow-list on purpose: it keeps caches, logs and scratch
files out of the repo. So the guard is not "stage everything", it is "every
output path the pipeline persists must be named in the list".
"""

import os
import re

import pytest

from dashboard.sidecars import DATA_DIR
from history.store import HISTORY_PATH, NEWS_DIR

WORKFLOW = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github",
    "workflows",
    "daily-brief.yml",
)


def _git_add_paths():
    """The pathspecs on the workflow's `git add` line."""
    with open(WORKFLOW, encoding="utf-8") as handle:
        source = handle.read()

    match = re.search(r"^\s*git add (.+)$", source, re.MULTILINE)
    assert match, "the daily workflow no longer has a `git add` line"
    return [p.rstrip("/") for p in match.group(1).split()]


@pytest.mark.parametrize(
    "path",
    [
        DATA_DIR,
        NEWS_DIR,
        HISTORY_PATH,
        "dashboard_data.json",
    ],
)
def test_every_persisted_path_is_staged(path):
    # Imported from the modules that own them rather than written out again,
    # so renaming a constant fails here instead of silently going unstaged.
    assert path.rstrip("/") in _git_add_paths(), (
        f"{path} is written by the pipeline but missing from the workflow's "
        "git add list; the run will commit without it and the rebase will fail"
    )


def test_sidecar_directories_are_tracked_not_generated_fresh():
    """A path only needs staging if it is checked in; confirm these are.

    If data/ were gitignored the add list would be irrelevant — and a future
    change that ignores it should break this test rather than quietly make the
    dashboard's sidecar fetches 404 on Pages.
    """
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ignore = os.path.join(repo, ".gitignore")
    if not os.path.exists(ignore):
        return

    with open(ignore, encoding="utf-8") as handle:
        patterns = {line.strip().strip("/") for line in handle if line.strip()}

    for directory in (DATA_DIR, NEWS_DIR):
        assert directory.rstrip("/") not in patterns, (
            f"{directory} is gitignored but the dashboard fetches it at "
            "runtime; ignoring it means the sidecars never reach Pages"
        )
