"""The data-state branch (scripts/state.py), against real git repositories.

A bare repository stands in for GitHub; each "checkout" is a shallow clone,
as actions/checkout makes one. Main starts with its state committed, as it
was until the move, and the move is the commit that removes it.
"""

import json
import os
import subprocess

import pytest

from scripts import state


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def write(root, path, value):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(value, f)


def read(root, path):
    with open(os.path.join(root, path), encoding="utf-8") as f:
        return json.load(f)


def write_state(root, day):
    for path in ("history.json", "dashboard_data.json", "llm_cache.json"):
        write(root, path, {"day": day})
    write(root, "thesis_cache.json", {"day": day})
    write(root, "data/results.json", {"day": day})
    write(root, "data/stock_topics/HAL.json", {"day": day})
    write(root, "news/HAL.json", {"day": day})


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """``(remote, clone)``: main as it is just after the move."""
    for key, value in {
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }.items():
        monkeypatch.setenv(key, value)
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    seed = tmp_path / "seed"
    git(tmp_path, "clone", "-q", str(remote), str(seed))
    write(seed, "watchlist.json", {"held": ["HAL"]})
    write_state(seed, "before the move")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "a daily run, committing its state")
    with open(seed / ".gitignore", "w") as f:
        f.write("\n".join(state.PATHS) + "\n")
    git(seed, "rm", "-q", "-r", "--cached", *state.PATHS)
    git(seed, "add", ".gitignore")
    git(seed, "commit", "-q", "-m", "the move")
    git(seed, "push", "-q", "origin", "main")

    def clone(name):
        path = tmp_path / name
        git(tmp_path, "clone", "-q", "--depth=1", f"file://{remote}", str(path))
        return str(path)

    return remote, clone


def test_the_first_pull_takes_the_state_from_before_the_move(repo):
    _remote, clone = repo
    ci = clone("ci")
    assert not os.path.exists(os.path.join(ci, "history.json"))
    state.pull(ci)
    assert read(ci, "history.json") == {"day": "before the move"}
    assert read(ci, "news/HAL.json") == {"day": "before the move"}
    # Nothing staged, nothing to commit on main.
    assert git(ci, "status", "--porcelain") == ""


def test_a_push_makes_one_commit_holding_only_the_state(repo):
    remote, clone = repo
    ci = clone("ci")
    state.pull(ci)
    write_state(ci, "day 1")
    state.push(ci)
    files = git(remote, "ls-tree", "-r", "--name-only", state.BRANCH).split("\n")
    assert sorted(files) == sorted(
        [
            "dashboard_data.json",
            "data/results.json",
            "data/stock_topics/HAL.json",
            "history.json",
            "llm_cache.json",
            "news/HAL.json",
            "thesis_cache.json",
        ]
    )
    assert git(remote, "rev-list", "--count", state.BRANCH) == "1"
    assert git(ci, "status", "--porcelain") == ""
    # Each run replaces the commit rather than adding to it.
    write_state(ci, "day 2")
    state.push(ci)
    assert git(remote, "rev-list", "--count", state.BRANCH) == "1"


def test_the_next_checkout_pulls_the_latest_state_and_nothing_stale(repo):
    _remote, clone = repo
    first = clone("first")
    state.pull(first)
    write_state(first, "day 1")
    state.push(first)
    second = clone("second")
    write(second, "news/GONE.json", {"day": "a holding sold yesterday"})
    state.pull(second)
    assert read(second, "history.json") == {"day": "day 1"}
    assert not os.path.exists(os.path.join(second, "news/GONE.json"))


def test_a_push_never_replaces_a_state_it_did_not_start_from(repo):
    _remote, clone = repo
    slow, fast = clone("slow"), clone("fast")
    state.pull(slow)
    state.pull(fast)
    write_state(fast, "the newer run")
    state.push(fast)
    write_state(slow, "the older run")
    with pytest.raises(state.StateError, match="not replacing it"):
        state.push(slow)
    newest = clone("check")
    state.pull(newest)
    assert read(newest, "history.json") == {"day": "the newer run"}


def test_a_push_missing_a_path_is_refused(repo):
    _remote, clone = repo
    ci = clone("ci")
    state.pull(ci)
    os.remove(os.path.join(ci, "llm_cache.json"))
    with pytest.raises(state.StateError, match="llm_cache.json missing"):
        state.push(ci)


def test_an_unreachable_remote_is_an_error_not_an_empty_branch(repo, tmp_path):
    """Read as "no branch yet", a network failure would bring back the state
    from the day of the move, and the run's push would make it stick."""
    _remote, clone = repo
    ci = clone("ci")
    state.pull(ci)
    write_state(ci, "day 1")
    state.push(ci)
    git(ci, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    write_state(ci, "this run's")
    with pytest.raises(state.StateError, match="could not ask"):
        state.pull(ci)
    assert read(ci, "history.json") == {"day": "this run's"}


def test_a_checkout_from_before_the_move_already_has_its_state(repo):
    remote, _clone = repo
    old = os.path.join(os.path.dirname(remote), "old")
    git(os.path.dirname(remote), "clone", "-q", str(remote), old)
    git(old, "checkout", "-q", "HEAD~1")
    state.pull(old)
    assert read(old, "history.json") == {"day": "before the move"}
    assert git(old, "status", "--porcelain") == ""


def test_the_moved_paths_are_ignored_on_main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".gitignore"), encoding="utf-8") as f:
        ignored = {line.strip().rstrip("/") for line in f}
    assert set(state.PATHS) <= ignored
