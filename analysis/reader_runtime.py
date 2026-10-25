"""One runtime under every AI reader: the models, what they did this run, and
the report of it.

WHY. The event reader, the thesis check, its second reading and Ask each built
their own chain of models, and nothing joined them. On 24 Oct a recording of
the readers took twelve minutes, most of it three chains each waiting out the
same busy gemini-3.8-flash and the two models after it. The second reading,
which leaves out the lite model that was answering, started again at the
busy one in every daily run. The event and thesis chains also held
text-to-speech and image models, and which models failed, and why, was
written nowhere. One record per run now answers all of it:

  * Every chain is ordered by what this run has seen: the model that last
    answered first, then the rest as configured, then any that failed this
    run. A later reader starts where an earlier one succeeded. A model that
    failed is still tried when everything else has failed too, so a
    passing fault cannot shut out the rest of the run.
  * Models built for other media never enter a chain.
  * The key's model list is asked for once a run, not once per reader.
  * Each reader's calls, the models that answered it and the ones that
    failed, with the reason, make the run's report: the log line, and the
    System view's AI readers panel.

A run is a process: the daily briefing, a reader-eval recording, an answer to
a question. reset_run() starts a new one (tests).
"""

import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from logger import log

# The model is configuration, not code: GEMINI_MODEL (a repository variable in
# the workflow) overrides this. Gemini 3.8 Flash is the model the key was
# issued for; the API ID below was written without access to Google's model
# list, so if it is wrong the API answers 404 and the log says to set
# GEMINI_MODEL.
DEFAULT_MODEL = "gemini-3.8-flash"

# Tried in order when the default is busy, retired or out of quota; override
# with GEMINI_FALLBACK_MODELS (comma-separated). Older, widely available
# models, named without access to Google's current list — one that has been
# retired answers 404 and the chain simply moves past it.
FALLBACK_MODELS = ("gemini-2.5-flash", "gemini-2.0-flash")
API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Models for other media, never asked to read text: the key's list on 24 Oct
# put gemini-3.8-flash-tts and gemini-3.1-flash-image in the event chain.
NOT_FOR_TEXT = ("tts", "image", "audio", "embedding")

TIMEOUT_S = 60
# Server-side failures worth retrying, and how.
_TRANSIENT = {500, 502, 503, 504}
RETRY_ATTEMPTS = 3
RETRY_BASE_S = 15
RETRY_CAP_S = 60


class ReaderUnavailable(Exception):
    """The API cannot be used this run. The message says why, for the log.

    ``model_specific`` marks failures another model might not share — this
    one busy, retired, or out of its own quota — so the fallback chain moves
    on. A refused key or a dead network would fail every model the same way,
    and trying the rest would only spend the run's time.
    """

    def __init__(self, message: str, model_specific: bool = False):
        super().__init__(message)
        self.model_specific = model_specific


# A transport takes the prompt text and returns the model's JSON text. Tests
# pass a fake; production uses gemini_transport().
Transport = Callable[[str], str]


def _backoff(resp, attempt: int) -> float:
    """Seconds before the next attempt: Retry-After if given, else doubling."""
    try:
        after = float((resp.headers or {}).get("Retry-After", ""))
    except (AttributeError, TypeError, ValueError):
        after = None
    wait = after if after is not None else RETRY_BASE_S * 2 ** (attempt - 1)
    return max(0.0, min(wait, RETRY_CAP_S))


def gemini_transport(
    api_key: str,
    model: str,
    schema: Optional[Dict[str, Any]] = None,
    text: bool = False,
) -> Transport:
    """One model's transport. ``schema`` is the reader's response schema;
    ``text`` asks for prose instead of JSON, for answering a question
    (scripts/dashboard_actions.py)."""
    import requests

    url = API_URL.format(model=model)

    def call(prompt: str) -> str:
        config: Dict[str, Any] = {"temperature": 0}
        if not text:
            config["responseMimeType"] = "application/json"
            if schema:
                config["responseSchema"] = schema
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config,
        }
        # 5xx is Google's side and usually brief: the first live run met
        # "503 This model is currently experiencing high demand" on its first
        # batch and, with no retry, skipped the whole day. A few spaced
        # attempts, honouring Retry-After, then give up until the next run.
        slow = False
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                resp = requests.post(
                    url,
                    headers={
                        "x-goog-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json=body,
                    timeout=TIMEOUT_S,
                )
            except requests.RequestException as e:
                resp, error = None, f"request failed: {e!r}"
                # A read timeout means the connection was made and this model
                # did not answer in time: busy, like a 503, so another may
                # answer. On 7 Oct gemini-3.8-flash timed out three times and,
                # read as "no network", ended the thesis check with nothing
                # read while gemini-flash-lite-latest was serving the same run.
                slow = isinstance(e, requests.exceptions.ReadTimeout)
            else:
                error = None
                if resp.status_code not in _TRANSIENT:
                    break
                error = f"Gemini unavailable ({resp.status_code})"
            if attempt < RETRY_ATTEMPTS:
                time.sleep(_backoff(resp, attempt))
        else:
            raise ReaderUnavailable(
                f"{error} after {RETRY_ATTEMPTS} attempts; resuming next run",
                model_specific=resp is not None or slow,
            )
        if resp.status_code == 404:
            raise ReaderUnavailable(
                f"model {model!r} not found (404) — set GEMINI_MODEL to a current model",
                model_specific=True,
            )
        if resp.status_code in (401, 403):
            raise ReaderUnavailable(f"key refused ({resp.status_code})")
        if resp.status_code == 429:
            # Gemini quotas are per model, so another may still have room.
            raise ReaderUnavailable(
                "quota or rate limit reached (429); resuming next run",
                model_specific=True,
            )
        if resp.status_code != 200:
            raise ReaderUnavailable(
                f"HTTP {resp.status_code}: {resp.text[:200]}", model_specific=True
            )
        try:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError) as e:
            # A blocked or empty candidate. Not worth failing the batch over.
            raise ReaderUnavailable(
                f"unexpected response shape: {e!r}", model_specific=True
            )

    return call


def model_chain() -> List[str]:
    """Models to try, in order: the configured one, then the fallbacks.

    GEMINI_MODEL replaces the first; GEMINI_FALLBACK_MODELS (comma-separated)
    replaces the rest. Duplicates are dropped so a model set in both is not
    tried twice.
    """
    first = os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
    raw = os.environ.get("GEMINI_FALLBACK_MODELS", "").strip()
    rest = [m.strip() for m in raw.split(",")] if raw else list(FALLBACK_MODELS)
    return list(dict.fromkeys(m for m in [first, *rest] if m))


def _version_key(name: str):
    """Sort key putting the newest model first: gemini-3.8 before gemini-2.5.

    Numbers are compared as numbers, so 3.10 sorts after 3.8. Stable ("-001")
    and unsuffixed names come before previews and experiments of the same
    version, which change without notice.
    """
    nums = [
        int(n) for n in re.findall(r"\d+", name.split("-", 2)[1] if "-" in name else "")
    ]
    unstable = any(t in name for t in ("preview", "exp", "latest"))
    return ([-n for n in nums], unstable, name)


def discover_models(api_key: str) -> List[str]:
    """Flash models this key can call, newest first; [] if the list is unavailable.

    The fallback names used to be fixed in code, chosen without access to
    Google's catalogue, and both turned out retired: the first run with the
    chain got 404 for gemini-2.5-flash and gemini-2.0-flash. Asking the API
    which models the key can use replaces the guess with the answer.

    Flash models only: the reader classifies short headlines, and the larger
    models cost more for no gain on that task. Only models that support
    generateContent, since that is the method the reader calls.
    """
    import requests

    try:
        resp = requests.get(
            MODELS_URL,
            headers={"x-goog-api-key": api_key},
            params={"pageSize": 200},
            timeout=TIMEOUT_S,
        )
        if resp.status_code != 200:
            log.info(f"LLM reader: model list unavailable ({resp.status_code}).")
            return []
        found = []
        for m in resp.json().get("models") or []:
            name = str(m.get("name") or "").removeprefix("models/")
            methods = m.get("supportedGenerationMethods") or []
            if "flash" in name and "generateContent" in methods:
                found.append(name)
        found.sort(key=_version_key)
        log.info(
            "LLM reader: key can use "
            + (", ".join(found) if found else "no flash models")
            + "."
        )
        return found
    except Exception as e:  # noqa: BLE001 - discovery is a convenience
        log.info(f"LLM reader: model list unavailable ({e!r}).")
        return []


# ---------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------


class Run:
    """What this run's readers have learned about the models, and spent."""

    def __init__(self) -> None:
        self.listed: Optional[List[str]] = None
        self.last: Optional[str] = None
        self.failed: Dict[str, str] = {}
        self.readers: Dict[str, Dict[str, Any]] = {}

    def models(self, api_key: str) -> List[str]:
        """The key's flash models, asked for once a run."""
        if self.listed is None:
            self.listed = discover_models(api_key)
        return self.listed

    def order(self, names: List[str]) -> List[str]:
        """``names`` as this run has found them: the model that last answered
        first, then the rest in their order, then any that failed."""
        fresh = [n for n in names if n not in self.failed]
        if self.last in fresh:
            fresh = [self.last] + [n for n in fresh if n != self.last]
        return fresh + [n for n in names if n in self.failed]

    def record(self, reader: str) -> Dict[str, Any]:
        return self.readers.setdefault(
            reader, {"calls": 0, "seconds": 0.0, "answered": {}, "failed": {}}
        )

    def answered(self, reader: str, model: str) -> None:
        self.last = model
        self.failed.pop(model, None)
        counts = self.record(reader)["answered"]
        counts[model] = counts.get(model, 0) + 1

    def refused(self, reader: str, model: str, error: ReaderUnavailable) -> None:
        """A model's failure. Only one of its own sets it aside for the run;
        a refused key or a dead network says nothing about the model."""
        if error.model_specific:
            self.failed[model] = str(error)
        failed = self.record(reader)["failed"]
        entry = failed.setdefault(model, {"count": 0, "reason": ""})
        entry["count"] += 1
        entry["reason"] = str(error)


RUN = Run()


def reset_run() -> Run:
    """Start a new run: nothing known about any model, nothing spent."""
    global RUN
    RUN = Run()
    return RUN


def chained_transport(
    transports: List[Tuple[str, Transport]], reader: str = "reader"
) -> Transport:
    """Try each model in turn, in the order this run has found them.

    Three runs in a row, gemini-3.8-flash answered every attempt with "503
    high demand" across six hours, and the reader read nothing. A model that
    fails in its own right (busy, retired, over its quota) hands over to the
    next; a failure every model would share (a refused key, no network) ends
    the pass at once. Once a model answers, later batches go straight to it,
    so a run does not re-queue behind a busy model forty times, and nor does
    the next reader (Run.order).

    The model that served is exposed as ``call.model`` for the log line.
    """
    by_name = dict(transports)
    names = list(by_name)

    def call(prompt: str) -> str:
        run = RUN
        record = run.record(reader)
        record["calls"] += 1
        failures = []
        started = time.monotonic()
        try:
            for name in run.order(names):
                try:
                    text = by_name[name](prompt)
                except ReaderUnavailable as e:
                    failures.append(f"{name}: {e}")
                    run.refused(reader, name, e)
                    if not e.model_specific:
                        raise ReaderUnavailable("; ".join(failures))
                    continue
                run.answered(reader, name)
                call.model = name
                return text
            raise ReaderUnavailable("every model failed — " + "; ".join(failures))
        finally:
            record["seconds"] += time.monotonic() - started

    call.model = None
    return call


def default_transport(
    schema: Optional[Dict[str, Any]] = None,
    text: bool = False,
    exclude: Tuple[str, ...] = (),
    reader: str = "reader",
) -> Tuple[Optional[Transport], str]:
    """The model chain for one reader. ``exclude`` drops any model whose name
    contains one of the strings: the thesis check's second reading leaves
    out the lite models that made the first. ``reader`` names it in the
    run's report."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        return None, "GEMINI_API_KEY not set"
    configured = model_chain()
    # Configured models first (the default, then any named fallbacks), then
    # whatever the key can actually use. Asked for only when fallbacks were
    # not named explicitly: an explicit list is the user's decision.
    discovered = (
        [] if os.environ.get("GEMINI_FALLBACK_MODELS", "").strip() else RUN.models(key)
    )
    chain = list(dict.fromkeys(configured[:1] + discovered + configured[1:]))
    chain = [m for m in chain if not any(x in m for x in NOT_FOR_TEXT + exclude)]
    if not chain:
        return None, "no model left after excluding " + ", ".join(
            exclude + NOT_FOR_TEXT
        )
    transport = chained_transport(
        [(m, gemini_transport(key, m, schema, text)) for m in chain], reader
    )
    return transport, " → ".join(RUN.order(chain))


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------


def note(reader: str, counts: Dict[str, Any], skipped: str = "") -> None:
    """A reader's own account of its run, for its line in the report: its
    counts (read, cached, left pending; for the second reading, confirmed
    and refused) and, when it called no model, why. A reader with neither
    did not run, and gets no line from it."""
    counts = {k: v for k, v in counts.items() if isinstance(v, int)}
    if not counts and not skipped:
        return
    record = RUN.record(reader)
    record["counts"] = counts
    if skipped:
        record["skipped"] = skipped


def report() -> Dict[str, Any]:
    """The run so far: per reader, its calls, time, the models that answered
    and the ones that failed with why, and its counts; and the models set
    aside for the rest of the run."""
    readers = {}
    for name, record in RUN.readers.items():
        readers[name] = {
            **record,
            "seconds": round(record["seconds"], 1),
            "answered": dict(sorted(record["answered"].items())),
            "failed": dict(sorted(record["failed"].items())),
        }
    return {"readers": readers, "set_aside": dict(sorted(RUN.failed.items()))}


def summary() -> str:
    """The report in a line, for the run log: each reader's calls and the
    models that answered them, then the models set aside and why."""
    run = report()
    parts = []
    for name, r in run["readers"].items():
        if not r["calls"]:
            continue
        served = ", ".join(f"{m} ×{n}" for m, n in r["answered"].items()) or "none"
        parts.append(f"{name} {r['calls']} call(s) in {r['seconds']}s by {served}")
    text = "; ".join(parts) or "no reader called a model"
    if run["set_aside"]:
        text += "; set aside: " + "; ".join(
            f"{m} ({why[:120]})" for m, why in run["set_aside"].items()
        )
    return text
