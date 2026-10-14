"""Move the pipeline's state between the working tree and its own branch.

Until this, the daily run committed what it wrote straight to main: the news
corpus (history.json), the dashboard payload and its sidecars
(dashboard_data.json, data/, news/) and the two LLM caches. Git keeps every
version of every file, so main grew by about 5 MB a month of them, 83% of all
its growth (measured 14 Oct 2026). They now live on ``data-state``, a branch
holding one commit, the latest state, which each run replaces. Main keeps the
code and the files people edit or review: watchlist.json, the entity graph,
the label sets and rotation_ledger.json, the track record.

    python scripts/state.py pull   # put the latest state in the working tree
    python scripts/state.py push   # make the working tree's state the latest

Everything that reads these files reads them where it always did; ``pull``
puts them there, and .gitignore keeps them off main. Before ``data-state``
exists (the first runs after the move) ``pull`` takes them from main's
history, as they were when they left it.

To roll back a bad run, download an earlier run's ``state-<number>``
artifact (each is kept 14 days), unpack it at the repository root, and
``push``.
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRANCH = "data-state"
REMOTE = "origin"
PATHS = (
    "history.json",
    "dashboard_data.json",
    "llm_cache.json",
    "thesis_cache.json",
    "data",
    "news",
)
# Removed from main with the rest in the commit that moved them. The version
# before that commit is where the state starts.
MARKER = "history.json"
# The data-state commit a pull started from, so a push can refuse to replace
# a state it never saw. Kept in the git directory, never in a commit.
_BASE = "data-state-base"

_BOT = ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com")


class StateError(RuntimeError):
    pass


def _git(args, root, env=None, check=True):
    result = subprocess.run(["git", *args], cwd=root, env=env, capture_output=True)
    if check and result.returncode != 0:
        err = result.stderr.decode(errors="replace").strip()
        raise StateError(f"git {' '.join(args)}: {err}")
    return result


def _text(args, root, env=None):
    return _git(args, root, env).stdout.decode().strip()


def remote_tip(root=ROOT, remote=REMOTE):
    """The branch's commit on the remote; None when there is no such branch.

    Any other failure is an error, never "no branch": answering a network
    blip with the state from the day of the move would roll every file back
    weeks, and the next push would make that permanent.
    """
    listed = _git(
        ["ls-remote", "--exit-code", remote, f"refs/heads/{BRANCH}"], root, check=False
    )
    if listed.returncode == 2:
        return None
    if listed.returncode != 0:
        err = listed.stderr.decode(errors="replace").strip()
        raise StateError(f"could not ask {remote} for {BRANCH}: {err}")
    return listed.stdout.decode().split()[0]


def _base_path(root):
    return os.path.join(root, _text(["rev-parse", "--git-path", _BASE], root))


def _write_base(root, commit):
    with open(_base_path(root), "w", encoding="utf-8") as f:
        f.write(commit)


def _read_base(root):
    try:
        with open(_base_path(root), encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def _seed(root, remote):
    """The newest commit in this checkout's history that still had the state."""
    if _git(["cat-file", "-e", f"HEAD:{MARKER}"], root, check=False).returncode == 0:
        return _text(["rev-parse", "HEAD"], root)
    # A CI checkout has one commit; the move is further back.
    if _text(["rev-parse", "--is-shallow-repository"], root) == "true":
        _git(["fetch", "--quiet", "--no-tags", "--unshallow", remote], root)
    moved = _text(
        ["log", "-1", "--format=%H", "--diff-filter=D", "HEAD", "--", MARKER], root
    )
    return _text(["rev-parse", f"{moved}^"], root) if moved else None


def _clear(root):
    for path in PATHS:
        full = os.path.join(root, path)
        if os.path.isdir(full):
            shutil.rmtree(full)
        elif os.path.exists(full):
            os.remove(full)


def _extract(commit, paths, root):
    archive = _git(["archive", "--format=tar", commit, "--", *paths], root).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(root, filter="data")
        else:  # pragma: no cover - Python without extraction filters
            tar.extractall(root)


def pull(root=ROOT, remote=REMOTE):
    """Put the latest state in the working tree, replacing what is there.

    Returns the commit it came from, or None when there is no state anywhere
    yet (a new installation): the pipeline then starts from nothing.
    """
    tip = remote_tip(root, remote)
    if tip:
        _git(
            [
                "fetch",
                "--quiet",
                "--no-tags",
                "--depth=1",
                remote,
                f"refs/heads/{BRANCH}",
            ],
            root,
        )
        source = _text(["rev-parse", "FETCH_HEAD"], root)
        base, where = source, f"{BRANCH} at {source[:12]}"
    else:
        source = _seed(root, remote)
        base, where = "", f"main's history at {(source or '')[:12]}"
    if source is None:
        _write_base(root, "")
        print(f"No saved state: no {BRANCH} branch and none in main's history.")
        return None
    listed = _text(["ls-tree", "--name-only", source, "--", *PATHS], root)
    present = [p for p in PATHS if p in listed.split("\n")]
    _clear(root)
    if present:
        _extract(source, present, root)
    _write_base(root, base)
    print(f"State from {where}: {', '.join(present) or 'nothing'}.")
    return source


def _identity_env():
    env = dict(os.environ)
    configured = _git(["config", "user.email"], ROOT, check=False).stdout.strip()
    if not configured and "GIT_AUTHOR_EMAIL" not in env:
        env.update(
            GIT_AUTHOR_NAME=_BOT[0],
            GIT_AUTHOR_EMAIL=_BOT[1],
            GIT_COMMITTER_NAME=_BOT[0],
            GIT_COMMITTER_EMAIL=_BOT[1],
        )
    return env


def push(root=ROOT, remote=REMOTE, message=None):
    """Make the working tree's state the branch's one commit.

    Refuses when a path is missing, which would erase it from the branch,
    and when the branch moved after this checkout pulled it, which would
    throw away a newer state.
    """
    missing = [p for p in PATHS if not os.path.exists(os.path.join(root, p))]
    if missing:
        raise StateError(
            f"not pushing: {', '.join(missing)} missing from the working tree, "
            f"and pushing would erase them from {BRANCH}"
        )
    base = _read_base(root)
    if base is None:
        # Never pulled here: pushed by hand, over whatever is there.
        base = remote_tip(root, remote) or ""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=os.path.join(tmp, "index"))
        _git(["add", "--force", "--", *PATHS], root, env)
        tree = _text(["write-tree"], root, env)
    run = os.environ.get("GITHUB_RUN_NUMBER")
    message = message or (
        f"State after daily briefing run {run}" if run else "State pushed by hand"
    )
    commit = _text(["commit-tree", tree, "-m", message], root, _identity_env())
    pushed = _git(
        [
            "push",
            "--quiet",
            f"--force-with-lease=refs/heads/{BRANCH}:{base}",
            remote,
            f"{commit}:refs/heads/{BRANCH}",
        ],
        root,
        check=False,
    )
    if pushed.returncode != 0:
        err = pushed.stderr.decode(errors="replace").strip()
        raise StateError(
            f"{BRANCH} is no longer the state this checkout pulled "
            f"({base[:12] or 'no branch'}); not replacing it: {err}"
        )
    _write_base(root, commit)
    print(f"State pushed to {BRANCH}: {commit[:12]}.")
    return commit


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=("pull", "push"))
    args = ap.parse_args(argv)
    try:
        pull() if args.command == "pull" else push()
    except StateError as e:
        prefix = "::error::" if os.environ.get("GITHUB_ACTIONS") else "error: "
        print(f"{prefix}{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
