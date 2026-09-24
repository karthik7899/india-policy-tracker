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

import collections
import os
import re

import pytest

from analysis.entity_graph import GRAPH_PATH, PROPOSALS_PATH
from analysis.llm_reader import CACHE_PATH as LLM_CACHE_PATH
from dashboard.sidecars import DATA_DIR
from history.store import HISTORY_PATH, NEWS_DIR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKFLOW = os.path.join(
    ROOT,
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
        # Absolute in their module, and at the repo root.
        os.path.basename(GRAPH_PATH),
        os.path.basename(PROPOSALS_PATH),
        os.path.basename(LLM_CACHE_PATH),
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


# ---------------------------------------------------------------------------
# The probe workflow
# ---------------------------------------------------------------------------

PROBE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github",
    "workflows",
    "probe.yml",
)


def _probe_source():
    with open(PROBE, encoding="utf-8") as handle:
        return handle.read()


def test_the_probe_cannot_write_to_the_repository():
    """The whole difference between this workflow and the daily brief.

    A diagnosis tool that can commit is a second thing that can corrupt the
    payload, and it would be dispatched far more often than the brief. It
    declares read-only permissions and has no git step; both are load-bearing.
    """
    source = _probe_source()
    assert re.search(
        r"^permissions:\s*\n\s*contents:\s*read\s*$", source, re.M
    ), "probe.yml must declare contents: read"
    for forbidden in ("git commit", "git push", "git add"):
        assert forbidden not in source, f"probe.yml must not run {forbidden!r}"


def test_the_probe_does_not_send_email():
    """Diagnosis was coupled to delivery: six briefing emails went out on 13
    September purely because that was the only way to read an upstream. The
    probe must not be able to do that."""
    source = _probe_source()
    for forbidden in ("SMTP", "RECEIVER_EMAIL", "main.py"):
        assert forbidden not in source, f"probe.yml must not reference {forbidden!r}"


def test_every_probe_choice_is_a_real_source():
    """A dispatch option that names nothing runs, prints nothing and looks
    like a working probe with no findings."""
    from scripts.probe_upstream import SOURCES

    block = re.search(r"options:\n((?:\s+- .+\n)+)", _probe_source())
    assert block, "probe.yml lost its source choices"
    options = {line.strip("- \n") for line in block.group(1).splitlines()}
    assert options == set(SOURCES) | {"all"}, options


def test_no_one_points_at_a_probe_script_that_was_deleted():
    """A probe answers its question and then deserves deleting — but the
    comments citing it as evidence outlive it.

    Five probes were retired at once and left nine dangling citations behind,
    in provider docstrings, a runtime log message and a test. Each read as a
    live instruction to go and re-run something that is no longer there, which
    is worse than no citation at all: it sends the next reader looking for a
    file rather than to docs/upstream-findings.md, where the answer actually
    lives. Findings move to the doc; only references to scripts that still
    exist may name a script.
    """
    cited = collections.defaultdict(list)
    for directory in ("providers", "analysis", "scripts", "tests", "emails", ".github"):
        for dirpath, _dirs, filenames in os.walk(os.path.join(ROOT, directory)):
            if "__pycache__" in dirpath:
                continue
            for filename in filenames:
                if not filename.endswith((".py", ".yml", ".yaml")):
                    continue
                path = os.path.join(dirpath, filename)
                with open(path, encoding="utf-8") as handle:
                    for name in re.findall(r"scripts/(\w+\.py)", handle.read()):
                        cited[name].append(os.path.relpath(path, ROOT))

    missing = {
        name: sorted(set(where))
        for name, where in cited.items()
        if not os.path.exists(os.path.join(ROOT, "scripts", name))
    }
    assert not missing, (
        "these files cite a scripts/ probe that no longer exists; point them "
        f"at docs/upstream-findings.md instead: {missing}"
    )
