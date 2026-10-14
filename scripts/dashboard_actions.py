"""Act on what the dashboard sends as a GitHub issue.

The dashboard is a static page on a public site. It cannot write to the
repository and must not hold a credential, so a decision made there (accept a
partner, move a holding, confirm or correct an eval label) travels as an issue
the owner submits under their own GitHub login. The workflow
.github/workflows/dashboard-actions.yml runs this on it.

A question asked on the dashboard's Ask view arrives the same way and is
answered (analysis/ask.py) as a comment on the issue. A comment the owner
adds to that issue afterwards is a follow-up, answered in turn with the
exchange so far in view.

Only the owner's issues and comments get here: the workflow checks
author_association before any step runs, because anyone can open an issue or
comment on a public repository and the job holds a write token. A follow-up
is read with the owner's other comments and the workflow's answers only;
anyone else's comments on the issue are left out. The body is read from the
event file, never through a shell.

Everything in the request is validated against what the files can hold. An
item that does not fit (an unknown ticker, a stance that is not a stance, a
proposal already decided) is skipped and named in the reply, never guessed at.

    python scripts/dashboard_actions.py "$GITHUB_EVENT_PATH"
"""

import datetime
import html
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

MARKER_RE = re.compile(r"<!--\s*tracker:(decisions|question)\s+v1\s*-->")
QUESTION_LABEL = "dashboard-question"
# An answer to a follow-up names the comments it answers, in a marker GitHub
# does not show, so a later run knows which are left.
ANSWERED_RE = re.compile(r"<!--\s*tracker:answered\s+([\d\s]+?)\s*-->")
FOOTER_RE = re.compile(r"\n-{3,}\n(?=<sub>)")
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

LABEL_FILES = {
    "event": "eval/event_labels.json",
    "policy": "eval/policy_labels.json",
    "thesis": "eval/thesis_labels.json",
}
DIRECTIONS = ("tailwind", "headwind", "mixed")
MAX_NOTE = 300
MAX_NAME = 80
TICKER_RE = re.compile(r"^[A-Z0-9&_-]{1,20}$")


# ---------------------------------------------------------------------------
# identifying a label row
# ---------------------------------------------------------------------------


def fnv1a(text: str) -> str:
    """32-bit FNV-1a of the UTF-8 bytes, as 8 hex digits.

    src/core/review.js computes the same thing in the browser, so a row is
    named by the same id on both sides without the headline travelling in the
    issue. tests pin a shared vector.
    """
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def row_key(kind: str, row: Dict[str, Any]) -> str:
    if kind == "thesis":
        return f"{row.get('ticker', '')}\n{row.get('headline', '')}"
    return str(row.get("headline", ""))


def row_id(kind: str, row: Dict[str, Any]) -> str:
    return fnv1a(row_key(kind, row))


# ---------------------------------------------------------------------------
# reading the request
# ---------------------------------------------------------------------------


def parse_request(body: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], str]:
    """``(kind, payload, error)``; kind None when this is not ours."""
    marker = MARKER_RE.search(body or "")
    if not marker:
        return None, None, ""
    block = JSON_BLOCK_RE.search(body[marker.end() :])
    if not block:
        return marker.group(1), None, "no ```json block after the marker"
    try:
        payload = json.loads(block.group(1))
    except ValueError as e:
        return marker.group(1), None, f"the json block does not parse: {e}"
    if not isinstance(payload, dict) or payload.get("v") != 1:
        return marker.group(1), None, "the json block is not a version 1 request"
    return marker.group(1), payload, ""


def _text(value: Any, limit: int) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value[:limit] if value else None


# ---------------------------------------------------------------------------
# applying decisions
# ---------------------------------------------------------------------------


def _load(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_labels(path: str, body: Dict[str, Any]) -> None:
    """Written the way the files are kept by hand: indent 1, a final newline."""
    import tempfile

    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(body, indent=1, ensure_ascii=False) + "\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def apply_proposals(items: List[Any], root: str, report: Dict[str, list]) -> bool:
    from analysis.entity_graph import _save_proposals, load_proposals

    path = os.path.join(root, "entity_graph_proposals.json")
    proposals = load_proposals(path)
    if proposals is None:
        report["skipped"].append("partner proposals: the queue file does not parse")
        return False
    by_key = {
        (str(p.get("holding", "")).upper(), str(p.get("proposed_as", "")).lower()): p
        for p in proposals
    }
    changed = False
    for item in items or []:
        if not isinstance(item, dict):
            continue
        holding = str(item.get("holding", "")).upper()
        proposed_as = str(item.get("proposed_as", ""))
        label = f"{holding} ↔ {proposed_as}"
        status = item.get("status")
        if status not in ("accepted", "rejected"):
            report["skipped"].append(
                f"partner {label}: status {status!r} is not accept or reject"
            )
            continue
        p = by_key.get((holding, proposed_as.lower()))
        if p is None:
            report["skipped"].append(f"partner {label}: not in the queue")
            continue
        if p.get("status") != "pending":
            report["skipped"].append(f"partner {label}: already {p.get('status')}")
            continue
        name = _text(item.get("counterparty"), MAX_NAME)
        if name and name != p.get("counterparty"):
            p["counterparty"] = name
            label += f" (as {name})"
        p["status"] = status
        report["applied"].append(f"partner {label}: {status}")
        changed = True
    if changed:
        _save_proposals(proposals, path)
    return changed


def apply_moves(items: List[Any], root: str, report: Dict[str, list]) -> bool:
    from config import SECTOR_METADATA

    path = os.path.join(root, "watchlist.json")
    watchlist = _load(path)
    where = {
        str(s.get("ticker", "")).upper(): sector
        for sector, stocks in watchlist.items()
        if sector != "macro_indicators" and isinstance(stocks, list)
        for s in stocks
        if isinstance(s, dict)
    }
    sectors = {k for k in SECTOR_METADATA if k != "macro_indicators"}
    changed = False
    for item in items or []:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker", "")).upper()
        current = where.get(ticker)
        if not current:
            report["skipped"].append(f"move {ticker}: not on the watchlist")
            continue
        stock = next(
            s
            for s in watchlist[current]
            if isinstance(s, dict) and str(s.get("ticker", "")).upper() == ticker
        )
        if item.get("keep") is True:
            # Recorded against the sector it was confirmed in, so a later move
            # by the rotation engine does not inherit the confirmation.
            stock["sector_confirmed"] = current
            report["applied"].append(f"{ticker}: kept in {current}")
            changed = True
            continue
        target = item.get("to")
        if target not in sectors:
            report["skipped"].append(f"move {ticker}: {target!r} is not a sector")
            continue
        if target == current:
            report["skipped"].append(f"move {ticker}: already in {current}")
            continue
        watchlist[current] = [s for s in watchlist[current] if s is not stock]
        stock.pop("sector_confirmed", None)
        watchlist.setdefault(target, []).append(stock)
        where[ticker] = target
        report["applied"].append(f"{ticker}: moved {current} → {target}")
        changed = True
    if changed:
        from utils import atomic_write_json

        atomic_write_json(watchlist, path)
    return changed


def _label_fields(
    kind: str, item: Dict[str, Any], sectors: set
) -> Tuple[Dict[str, Any], str]:
    """The corrected fields a reviewer sent, validated; (fields, error)."""
    from analysis.event_engine import EVENT_VOCABULARY
    from analysis.thesis_check import STANCES

    fields: Dict[str, Any] = {}
    if kind == "thesis":
        if "stance" in item:
            if item["stance"] not in STANCES:
                return {}, f"stance {item['stance']!r}"
            fields["stance"] = item["stance"]
        if "about" in item:
            if not isinstance(item["about"], bool):
                return {}, "about must be true or false"
            fields["about"] = item["about"]
    elif kind == "policy":
        if "is_policy" in item:
            if not isinstance(item["is_policy"], bool):
                return {}, "is_policy must be true or false"
            fields["is_policy"] = item["is_policy"]
        if "effects" in item:
            effects = []
            for e in item["effects"] if isinstance(item["effects"], list) else [None]:
                if (
                    not isinstance(e, dict)
                    or e.get("sector") not in sectors
                    or e.get("direction") not in DIRECTIONS
                ):
                    return {}, f"effect {e!r}"
                effects.append({"sector": e["sector"], "direction": e["direction"]})
            fields["effects"] = effects
    elif kind == "event":
        if "event_type" in item:
            if (
                item["event_type"] is not None
                and item["event_type"] not in EVENT_VOCABULARY
            ):
                return {}, f"event type {item['event_type']!r}"
            fields["event_type"] = item["event_type"]
        for key in ("actors", "counterparties"):
            if key in item:
                values = item[key]
                if not isinstance(values, list) or not all(
                    isinstance(v, str) for v in values
                ):
                    return {}, f"{key} must be a list of names"
                cleaned = [" ".join(v.split())[:MAX_NAME] for v in values if v.strip()]
                if key == "actors" and not all(TICKER_RE.match(v) for v in cleaned):
                    return {}, "actors must be tickers"
                fields[key] = cleaned
    note = _text(item.get("note"), MAX_NOTE)
    if note:
        fields["note"] = note
    return fields, ""


def apply_labels(
    groups: Dict[str, Any], root: str, report: Dict[str, list]
) -> List[str]:
    from config import SECTOR_METADATA

    sectors = {k for k in SECTOR_METADATA if k != "macro_indicators"}
    today = datetime.date.today().isoformat()
    changed_files = []
    for kind, items in (groups or {}).items():
        if kind not in LABEL_FILES or not isinstance(items, list):
            report["skipped"].append(f"labels: {kind!r} is not a label file")
            continue
        path = os.path.join(root, LABEL_FILES[kind])
        body = _load(path)
        rows = body.get("labels") or []
        by_id: Dict[str, list] = {}
        for row in rows:
            by_id.setdefault(row_id(kind, row), []).append(row)
        confirmed = corrected = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            rid = str(item.get("id", ""))
            found = by_id.get(rid) or []
            if len(found) != 1:
                report["skipped"].append(
                    f"{kind} label {rid}: "
                    + ("not found" if not found else "matches more than one row")
                )
                continue
            row = found[0]
            if item.get("ok") is True:
                row["reviewed"] = today
                confirmed += 1
                continue
            fields, error = _label_fields(kind, item, sectors)
            if error or not fields:
                report["skipped"].append(
                    f"{kind} label “{row.get('headline', '')[:60]}”: "
                    + (error or "nothing to change")
                )
                continue
            row.update(fields)
            row["reviewed"] = today
            corrected += 1
        if confirmed or corrected:
            body["reviewed"] = all(r.get("reviewed") for r in rows)
            _write_labels(path, body)
            changed_files.append(LABEL_FILES[kind])
            report["applied"].append(
                f"{kind} labels: {confirmed} confirmed, {corrected} corrected "
                f"({sum(1 for r in rows if r.get('reviewed'))} of {len(rows)} now reviewed)"
            )
    return changed_files


def apply_decisions(payload: Dict[str, Any], root: str = ROOT) -> Dict[str, list]:
    """Apply one request to the files under ``root``. Returns the report."""
    report: Dict[str, list] = {"applied": [], "skipped": []}
    apply_proposals(payload.get("proposals") or [], root, report)
    apply_moves(payload.get("moves") or [], root, report)
    apply_labels(payload.get("labels") or {}, root, report)
    return report


# ---------------------------------------------------------------------------
# the workflow side: wait, commit, reply
# ---------------------------------------------------------------------------


def _api(method: str, path: str, **kw) -> Any:
    import requests

    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    resp = requests.request(
        method,
        f"https://api.github.com/repos/{repo}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
        **kw,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else None


def daily_run_active() -> bool:
    """Whether the daily briefing is queued or running.

    It rewrites watchlist.json and the proposal queue and commits at the end
    with a rebase; a decision committed in between makes that rebase conflict
    and fails the day's run. So decisions wait for it.
    """
    for status in ("in_progress", "queued"):
        runs = _api(
            "GET", f"/actions/workflows/daily-brief.yml/runs?status={status}&per_page=5"
        )
        if (runs or {}).get("total_count"):
            return True
    return False


def wait_for_daily(limit_s: int = 40 * 60, step_s: int = 30) -> bool:
    waited = 0
    while daily_run_active():
        if waited >= limit_s:
            return False
        print(f"Daily briefing running; waiting ({waited}s so far).")
        time.sleep(step_s)
        waited += step_s
    return True


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def _set_output(name: str, value: str) -> None:
    """A step output for the workflow; nothing outside one."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def commit_and_push(payload: Dict[str, Any], number: int) -> Dict[str, list]:
    """Apply on the newest main and push, re-applying from scratch on a race.

    Re-applying rather than rebasing: a rebase of an edit to a JSON file the
    daily run also rewrites can conflict, while applying the same decisions
    to the new file cannot.
    """
    report: Dict[str, list] = {"applied": [], "skipped": []}
    for attempt in range(1, 6):
        _git("fetch", "-q", "origin", "main")
        _git("reset", "-q", "--hard", "origin/main")
        report = apply_decisions(payload)
        if not _git("status", "--porcelain").stdout.strip():
            return report
        _git("add", "-A")
        _git(
            "commit", "-q", "-m", f"Apply dashboard decisions from #{number} [skip ci]"
        )
        if _git("push", "-q", "origin", "HEAD:main").returncode == 0:
            # A push made with the workflow's token starts no workflow, so the
            # job asks for the site to be republished (dashboard-actions.yml).
            _set_output("pushed", "true")
            return report
        time.sleep(5 * attempt)
    report["skipped"].append("could not push after 5 attempts; nothing was saved")
    report["applied"] = []
    return report


def reply(number: int, report: Dict[str, list], error: str = "") -> None:
    lines = []
    if error:
        lines.append(f"Could not read this request: {error}.")
    if report.get("applied"):
        lines.append("**Applied**")
        lines += [f"- {a}" for a in report["applied"]]
    if report.get("skipped"):
        lines.append("**Skipped**")
        lines += [f"- {s}" for s in report["skipped"]]
    if not lines:
        lines.append("Nothing to change: every item was already in that state.")
    lines.append(
        "\nThe dashboard shows the change once GitHub Pages redeploys, usually "
        "within a few minutes."
    )
    _api("POST", f"/issues/{number}/comments", json={"body": "\n".join(lines)})
    _api(
        "PATCH",
        f"/issues/{number}",
        json={"state": "closed", "state_reason": "completed"},
    )


def _focus(payload: Dict[str, Any]) -> Optional[str]:
    """The holding the question was asked from, if it is a ticker at all."""
    focus = payload.get("focus")
    if isinstance(focus, str) and TICKER_RE.match(focus.upper()):
        return focus.upper()
    return None


def _md(text: Any) -> str:
    """Text placed in Markdown as itself: no tag, link or emphasis of its own."""
    text = html.escape(" ".join(str(text or "").split()), quote=False)
    return re.sub(r"([\\\[\]*_`])", r"\\\1", text)


def _url(link: str) -> str:
    """A link Markdown cannot end early: a bracket or space would cut it."""
    return re.sub(r"[()\s<>]", lambda m: "%{:02X}".format(ord(m.group(0))), link)


def format_answer(
    text: str,
    footer: str,
    news: Optional[Dict[str, Any]] = None,
    replies_to: List[int] = (),
) -> str:
    """The comment an answer is posted as.

    The headlines the news search found follow the answer in a collapsed
    list, numbered as the answer cites them. The dashboard reads the same
    layout back (src/core/ask.js answerBlocks). The model's text cannot
    carry that markup itself, so a headline that talked it into writing a
    marker or a list cannot pass one off as the workflow's.
    """
    parts = [
        re.sub(
            r"<!--.*?-->|</?(?:details|summary)\b[^>]*>", "", text, flags=re.S | re.I
        ).strip()
    ]
    items = (news or {}).get("items") or []
    if items:
        lines = [
            f"{n}. [{_md(i['headline'])}]({_url(i['link'])})"
            + "".join(f" · {_md(x)}" for x in (i.get("source"), i.get("date")) if x)
            for n, i in enumerate(items, 1)
        ]
        searched = " and ".join(f"“{html.escape(q)}”" for q in news["queries"])
        left_out = news.get("left_out") or 0
        parts.append(
            f"<details><summary>News searched: {len(items)} headline(s) from "
            f"{searched}"
            + (f"; {left_out} not naming the company left out" if left_out else "")
            + "</summary>\n\n"
            + "\n".join(lines)
            + "\n\n</details>"
        )
    if replies_to:
        parts.append(f"<!-- tracker:answered {' '.join(map(str, replies_to))} -->")
    body = "\n\n".join(parts)
    if footer:
        body += (
            f"\n\n---\n<sub>{footer} Comment on this issue to ask a follow-up.</sub>"
        )
    return body


def _log_answer(
    started: float, text: str, footer: str, news: Optional[Dict[str, Any]]
) -> None:
    """What the run did, for its log: the comment says less about the search."""
    print(f"Answered in {time.monotonic() - started:.0f}s: {footer or text}")
    if not news:
        print("News: no search.")
        return
    print(
        f"News: {len(news.get('items') or [])} headline(s) kept,"
        f" {news.get('left_out') or 0} not naming the company left out, from "
        + "; ".join(news.get("queries") or [])
        + (f" (failed: {news['error']})" if news.get("error") else "")
    )


def answer_question(number: int, payload: Dict[str, Any]) -> None:
    """Answer on the issue and close it. Nothing is committed.

    The label is how the dashboard finds questions to list, and how the
    workflow knows a later comment is a follow-up. It is created on first
    use, since a label that does not exist yet cannot be set from the
    new-issue link.
    """
    from analysis.ask import answer

    try:
        _api("POST", "/labels", json={"name": QUESTION_LABEL, "color": "2a78d6"})
    except Exception:  # noqa: BLE001 - it already exists
        pass
    _api("POST", f"/issues/{number}/labels", json={"labels": [QUESTION_LABEL]})
    started = time.monotonic()
    text, footer, news = answer(
        str(payload.get("question") or ""), focus=_focus(payload)
    )
    _log_answer(started, text, footer, news)
    _api(
        "POST",
        f"/issues/{number}/comments",
        json={"body": format_answer(text, footer, news)},
    )
    _api(
        "PATCH",
        f"/issues/{number}",
        json={"state": "closed", "state_reason": "completed"},
    )


def _is_bot(comment: Dict[str, Any]) -> bool:
    return (comment.get("user") or {}).get("type") == "Bot"


def _plain(body: str) -> str:
    """An answer as the exchange remembers it: no footer, news list or marker."""
    body = FOOTER_RE.split(body or "", maxsplit=1)[0]
    body = re.sub(r"<details>.*?</details>", "", body, flags=re.S)
    return re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()


def conversation(
    payload: Dict[str, Any],
    comments: List[Dict[str, Any]],
    comment: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Tuple[str, str]], List[Tuple[int, str]]]:
    """The exchange on a question issue: ``(history, pending)``.

    ``history`` is ``(role, text)`` oldest first, from the issue's own
    question on; ``pending`` the owner's comments no answer has replied to
    yet, as ``(id, text)``. Only the owner's comments and the workflow's
    answers count. ``comment`` is the one that triggered the run, added if
    the list does not have it yet.
    """
    comments = list(comments or [])
    if comment and comment.get("id") not in {c.get("id") for c in comments}:
        comments.append(comment)
    answered = {
        int(n)
        for c in comments
        if _is_bot(c)
        for m in ANSWERED_RE.finditer(c.get("body") or "")
        for n in m.group(1).split()
    }
    history = [("question", str(payload.get("question") or ""))]
    pending = []
    for c in comments:
        body = c.get("body") or ""
        if _is_bot(c):
            # An answer ends in its footer; "Could not answer this time" has
            # none, and is no part of the exchange.
            if FOOTER_RE.search(body):
                history.append(("answer", _plain(body)))
            continue
        if c.get("author_association") != "OWNER":
            continue
        text = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
        if not re.search(r"\w", text):
            continue
        if c.get("id") in answered:
            history.append(("question", text))
        else:
            pending.append((int(c.get("id") or 0), text))
    return history, pending


def answer_follow_up(
    number: int, payload: Dict[str, Any], comment: Dict[str, Any]
) -> bool:
    """Answer the owner's new comments on a question issue.

    Every comment not yet answered is answered together, so a follow-up
    posted while another was being answered is not lost, and a run that
    finds its comment already answered by an earlier one does nothing.
    """
    from analysis.ask import answer

    comments = _api("GET", f"/issues/{number}/comments?per_page=100") or []
    history, pending = conversation(payload, comments, comment)
    ids = [i for i, _ in pending]
    if comment.get("id") not in ids:
        print("This comment has been answered already; nothing to do.")
        return False
    started = time.monotonic()
    text, footer, news = answer(
        "\n\n".join(t for _, t in pending), focus=_focus(payload), history=history
    )
    _log_answer(started, text, footer, news)
    # A failure ("Could not answer this time") has no footer and answers
    # nothing, so the owner's next comment is answered along with these.
    replies_to = ids if footer else []
    _api(
        "POST",
        f"/issues/{number}/comments",
        json={"body": format_answer(text, footer, news, replies_to=replies_to)},
    )
    return True


def follow_up(event: Dict[str, Any]) -> int:
    issue = event.get("issue") or {}
    comment = event.get("comment") or {}
    labels = {str(lb.get("name")) for lb in issue.get("labels") or []}
    kind, payload, _ = parse_request(issue.get("body") or "")
    if (
        kind != "question"
        or payload is None
        or QUESTION_LABEL not in labels
        or issue.get("pull_request")
        or _is_bot(comment)
        or comment.get("author_association") != "OWNER"
    ):
        print("Not a follow-up to a dashboard question; nothing to do.")
        return 0
    answer_follow_up(int(issue.get("number") or 0), payload, comment)
    return 0


def main(event_path: str) -> int:
    event = _load(event_path)
    if event.get("comment"):
        return follow_up(event)
    issue = event.get("issue") or {}
    number = int(issue.get("number") or 0)
    kind, payload, error = parse_request(issue.get("body") or "")
    if kind is None:
        print("Not a dashboard request; nothing to do.")
        return 0
    if error or payload is None:
        reply(number, {"applied": [], "skipped": []}, error or "empty request")
        return 0
    if kind == "question":
        answer_question(number, payload)
        return 0
    if not wait_for_daily():
        reply(
            number,
            {
                "applied": [],
                "skipped": [
                    "the daily briefing ran for over 40 minutes; submit again later"
                ],
            },
        )
        return 0
    _git("config", "user.name", "github-actions[bot]")
    _git(
        "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"
    )
    report = commit_and_push(payload, number)
    print(json.dumps(report, indent=1))
    reply(number, report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
