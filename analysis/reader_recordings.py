"""The AI readers' answers to the labelled items, recorded once and replayed.

WHY. The event reader and the thesis check are scored against hand labels
(eval/), and a score needs the model's answers. The model needs a key, a
network and quota, none of which CI has, and it does not give the same
answer twice. So each labelled item's raw answer is recorded exactly as the
model returned it, under the prompt that asked for it. Replayed through the
readers' own code (the prompt, JSON parsing, grounding, the cache,
reconcile), the answers give the same readings every run with no key, and a
change to any of that code is measured on the same answers. A change to a
prompt makes its recordings stale, and they are recorded again live
(scripts/reader_eval.py --record).

The seam is the transport, the function every reader already calls with a
prompt and gets JSON text back from (analysis/llm_reader.Transport). A codec
per prompt reads it back into its items: a headline, a holding's thesis and
headline, a challenge to check. Each item's answer is stored on its own, so
a batch of any make-up can be answered from them.

  replaying(codec, store)        answers from the recordings. An item with no
                                 recording for this prompt, or one its reader
                                 would refuse, is left out, and the reader
                                 counts it as pending.
  replaying(codec, store, live)  the same, but a batch with such an item goes
                                 to the model, and the answers to those items
                                 are recorded. The rest are still served from
                                 the recordings, so recording again never
                                 changes an answer that was already there.
"""

import collections
import datetime
import hashlib
import json
import os
import re
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDINGS_DIR = os.path.join(ROOT, "eval", "recordings")

_ABOUT = (
    "Raw answers from the AI readers to the labelled items in eval/, recorded "
    "by scripts/reader_eval.py --record and replayed by the tests. Each is "
    "stored under the fingerprint of the prompt and schema that asked for it; "
    "a prompt change leaves them stale until they are recorded again."
)


class PromptNotUnderstood(Exception):
    """A codec could not read a prompt back into its items: the reader's
    prompt format changed and the codec here must change with it."""


def write_json(path: str, body: Any) -> None:
    """Sorted, indented and atomic, so a re-run that changes nothing leaves
    the file byte-identical and a diff shows only what moved."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(body, indent=1, ensure_ascii=False, sort_keys=True))
            f.write("\n")
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ---------------------------------------------------------------------------
# codecs: a prompt read back into its items
# ---------------------------------------------------------------------------

# Placeholder item for the fingerprint: the prompt around one item, so a
# change to the instructions or to how an item is written both count.
_SLOT = {
    "ticker": "<ticker>",
    "name": "<name>",
    "thesis": "<thesis>",
    "headline": "<headline>",
}

# (id, identity, readable): identity is everything the model saw of the item,
# readable is how the recordings file names it.
Item = Tuple[int, str, str]


class Codec:
    """How one reader's prompt is read back into the items it asks about.

    ``accepts`` is the reader's own test of an answer beyond its id. One it
    refuses is neither recorded nor served, so it is asked again rather than
    kept as an answer the reader never uses.
    """

    def __init__(
        self,
        name: str,
        template: Callable[[], str],
        schema: Callable[[], Dict[str, Any]],
        head: Callable[[], str],
        parse: Callable[[str], List[Item]],
        accepts: Callable[[Dict[str, Any]], bool] = lambda answer: True,
    ):
        self.name = name
        self._template = template
        self._schema = schema
        self._head = head
        self._parse = parse
        self.accepts = accepts

    def fingerprint(self) -> str:
        """The prompt around one placeholder item, and the response schema.
        What the model is asked, without what it is asked about."""
        text = self._template() + "\n" + json.dumps(self._schema(), sort_keys=True)
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]

    def items(self, prompt: str) -> List[Tuple[int, str, str]]:
        """``(id, key, readable)`` for each item in the prompt."""
        head = self._head()
        if not prompt.startswith(head):
            raise PromptNotUnderstood(f"{self.name}: the prompt's instructions differ")
        return [
            (i, item_key(identity), readable)
            for i, identity, readable in self._parse(prompt[len(head) :])
        ]


def item_key(identity: str) -> str:
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()[:16]


_EVENT_LINE = re.compile(r"(\d+): (.*)\Z", re.DOTALL)
_TICKER_IN = re.compile(r"\(([^()]+), listed in India\)\Z")


def _ticker(holding: str) -> str:
    m = _TICKER_IN.search(holding)
    return m.group(1) if m else holding


def _parse_events(body: str) -> List[Item]:
    out = []
    for line in body.split("\n") if body else []:
        m = _EVENT_LINE.match(line)
        if not m:
            raise PromptNotUnderstood(f"events: unexpected line {line[:80]!r}")
        out.append((int(m.group(1)), m.group(2), m.group(2)))
    return out


_THESIS_ITEM = re.compile(r"  (\d+): (.*)\Z", re.DOTALL)


def _parse_thesis(body: str) -> List[Item]:
    out, holding, thesis = [], None, None
    for line in body.split("\n"):
        if not line:
            continue
        if line.startswith("HOLDING: "):
            holding, thesis = line[len("HOLDING: ") :], None
        elif line.startswith("THESIS: "):
            thesis = line[len("THESIS: ") :]
        else:
            m = _THESIS_ITEM.match(line)
            if not m or holding is None or thesis is None:
                raise PromptNotUnderstood(f"thesis: unexpected line {line[:80]!r}")
            headline = m.group(2)
            identity = f"HOLDING: {holding}\nTHESIS: {thesis}\n{headline}"
            out.append((int(m.group(1)), identity, f"{_ticker(holding)} | {headline}"))
    return out


_CHECK_START = re.compile(r"(\d+): HOLDING: (.*)\Z", re.DOTALL)
_CHECK_FIELDS = ("THESIS", "CLAIM", "HEADLINE")


def _parse_check(body: str) -> List[Item]:
    out: List[Item] = []
    current: Optional[Dict[str, Any]] = None

    def close():
        if current is None:
            return
        if set(current) != {"id", "HOLDING", *_CHECK_FIELDS}:
            raise PromptNotUnderstood(f"check: item {current.get('id')} is incomplete")
        identity = "\n".join(f"{k}: {current[k]}" for k in ("HOLDING", *_CHECK_FIELDS))
        readable = (
            f"{_ticker(current['HOLDING'])} | {current['HEADLINE']} "
            f"| claim: {current['CLAIM']}"
        )
        out.append((current["id"], identity, readable))

    for line in body.split("\n"):
        if not line:
            continue
        start = _CHECK_START.match(line)
        if start:
            close()
            current = {"id": int(start.group(1)), "HOLDING": start.group(2)}
            continue
        field = next((f for f in _CHECK_FIELDS if line.startswith(f"   {f}: ")), None)
        if current is None or field is None or field in current:
            raise PromptNotUnderstood(f"check: unexpected line {line[:80]!r}")
        current[field] = line[len(f"   {field}: ") :]
    close()
    return out


def _events_template() -> str:
    from analysis import llm_reader

    return llm_reader._prompt([(0, _SLOT["headline"])])


def _events_head() -> str:
    from analysis import llm_reader

    return llm_reader._prompt([])


def _events_schema() -> Dict[str, Any]:
    from analysis import llm_reader

    return llm_reader._SCHEMA


def _thesis_template() -> str:
    from analysis import thesis_check

    return thesis_check._prompt([(0, dict(_SLOT))])


def _thesis_head() -> str:
    from analysis import thesis_check

    return thesis_check._prompt([])


def _thesis_schema() -> Dict[str, Any]:
    from analysis import thesis_check

    return thesis_check._SCHEMA


def _check_template() -> str:
    from analysis import thesis_check

    return thesis_check._check_prompt([(0, dict(_SLOT), {"claim": "<claim>"})])


def _check_head() -> str:
    from analysis import thesis_check

    return thesis_check._check_prompt([])


def _check_schema() -> Dict[str, Any]:
    from analysis import thesis_check

    return thesis_check._CHECK_SCHEMA


def _check_accepts(answer: Dict[str, Any]) -> bool:
    """check_challenges counts any other verdict as no answer at all."""
    from analysis import thesis_check

    return answer.get("verdict") in thesis_check.VERDICTS


EVENTS = Codec("events", _events_template, _events_schema, _events_head, _parse_events)
THESIS = Codec("thesis", _thesis_template, _thesis_schema, _thesis_head, _parse_thesis)
CHECK = Codec(
    "check", _check_template, _check_schema, _check_head, _parse_check, _check_accepts
)
CODECS = (EVENTS, THESIS, CHECK)


# ---------------------------------------------------------------------------
# the recordings
# ---------------------------------------------------------------------------


class Recordings:
    """One codec's recorded answers: ``{key: {input, prompt, answer, model,
    recorded}}`` in eval/recordings/<codec>.json.

    ``fresh`` ignores what is there, so every item is asked again; an answer
    recorded in this run is served as usual.
    """

    def __init__(self, path: str, fresh: bool = False):
        self.path = path
        self.fresh = fresh
        self.entries: Dict[str, Dict[str, Any]] = self._load()
        self.asked: Set[str] = set()
        self.served: Set[str] = set()
        self.renewed: Set[str] = set()
        self.changed = False

    def _load(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.path, encoding="utf-8") as f:
                return dict(json.load(f).get("items") or {})
        except FileNotFoundError:
            return {}

    def answer(
        self,
        key: str,
        fingerprint: str,
        accepts: Callable[[Dict[str, Any]], bool] = lambda answer: True,
    ) -> Optional[Dict[str, Any]]:
        """The recorded answer to serve, or None: none recorded for this
        prompt, ``fresh``, or one the reader would refuse (asked again)."""
        self.asked.add(key)
        entry = self.entries.get(key)
        if not entry or entry.get("prompt") != fingerprint:
            return None
        if self.fresh and key not in self.renewed:
            return None
        if not accepts(entry["answer"]):
            return None
        self.served.add(key)
        return entry["answer"]

    def record(
        self,
        key: str,
        fingerprint: str,
        readable: str,
        answer: Dict[str, Any],
        model: Optional[str],
        today: str,
    ) -> None:
        self.entries[key] = {
            "input": readable,
            "prompt": fingerprint,
            "answer": answer,
            "model": model or "unknown",
            "recorded": today,
        }
        self.renewed.add(key)
        self.served.add(key)
        self.changed = True

    def stale(self, fingerprint: str) -> int:
        """Items asked for this run whose recording is for another prompt."""
        return sum(
            1
            for k in self.asked
            if k in self.entries and self.entries[k].get("prompt") != fingerprint
        )

    def models(self) -> Dict[str, int]:
        """Which models gave the answers served this run."""
        counts = collections.Counter(
            self.entries[k].get("model") or "unknown" for k in self.served
        )
        return dict(sorted(counts.items()))

    def prune(self) -> int:
        """Drop recordings no labelled item asked for (a label removed, a
        challenge no longer raised). Only after a run that asked for all."""
        gone = [k for k in self.entries if k not in self.asked]
        for k in gone:
            del self.entries[k]
        self.changed |= bool(gone)
        return len(gone)

    def save(self) -> None:
        write_json(self.path, {"_about": _ABOUT, "items": self.entries})


def stores(
    fresh: bool = False, directory: str = RECORDINGS_DIR
) -> Dict[str, Recordings]:
    return {
        c.name: Recordings(os.path.join(directory, f"{c.name}.json"), fresh)
        for c in CODECS
    }


# ---------------------------------------------------------------------------
# the transport
# ---------------------------------------------------------------------------


class Pacer:
    """Keeps live calls at least ``seconds`` apart, across every transport
    that shares it; a batch answered from the recordings waits for nothing."""

    def __init__(self, seconds: float):
        self.seconds = seconds
        self.last: Optional[float] = None

    def wait(self) -> None:
        if self.last is not None:
            delay = self.seconds - (time.monotonic() - self.last)
            if delay > 0:
                time.sleep(delay)
        self.last = time.monotonic()


def replaying(
    codec: Codec,
    store: Recordings,
    live: Optional[Callable[[str], str]] = None,
    today: str = "",
    stats: Optional[Dict[str, Any]] = None,
    pacer: Optional[Pacer] = None,
) -> Callable[[str], str]:
    """A transport answering from ``store``; see the module docstring.

    Answers are looked up exactly as the readers look them up — by the
    batch's own ids, the last answer for an id winning — so an answer the
    reader would have dropped is not recorded either. When ``live`` fails,
    the rest of the run is answered from the recordings alone and the
    failure is kept in ``stats["live_failed"]``.
    """
    from analysis.llm_reader import ReaderUnavailable

    today = today or datetime.date.today().isoformat()
    stats = stats if stats is not None else {}
    for k in (
        "replayed",
        "recorded",
        "missing",
        "live_calls",
        "unparseable",
        "refused",
    ):
        stats.setdefault(k, 0)
    stats.setdefault("live_failed", "")

    def call(prompt: str) -> str:
        fingerprint = codec.fingerprint()
        items = codec.items(prompt)
        answers: Dict[int, Dict[str, Any]] = {}
        for i, key, _ in items:
            found = store.answer(key, fingerprint, codec.accepts)
            if found is not None:
                answers[i] = found
        stats["replayed"] += len(answers)
        missing = [(i, key, readable) for i, key, readable in items if i not in answers]
        if missing and live is not None and not stats["live_failed"]:
            stats["live_calls"] += 1
            if pacer is not None:
                pacer.wait()
            try:
                text = live(prompt)
            except ReaderUnavailable as e:
                stats["live_failed"] = str(e)
            else:
                try:
                    fresh = json.loads(text)
                except ValueError:
                    fresh = None
                    stats["unparseable"] += 1
                by_id = (
                    {a.get("id"): a for a in fresh if isinstance(a, dict)}
                    if isinstance(fresh, list)
                    else {}
                )
                model = getattr(live, "model", None)
                for i, key, readable in missing:
                    raw = by_id.get(i)
                    if raw is None:
                        continue
                    answer = {k: v for k, v in raw.items() if k != "id"}
                    if not codec.accepts(answer):
                        stats["refused"] += 1
                        continue
                    store.record(key, fingerprint, readable, answer, model, today)
                    answers[i] = answer
                    stats["recorded"] += 1
        stats["missing"] += sum(1 for i, _, _ in items if i not in answers)
        return json.dumps(
            [{**answers[i], "id": i} for i, _, _ in items if i in answers],
            ensure_ascii=False,
        )

    call.model = None
    return call
