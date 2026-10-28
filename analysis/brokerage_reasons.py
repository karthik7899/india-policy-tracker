"""Why a brokerage made its call, in the words of the story itself.

The thesis check (analysis/thesis_check.py) reads a brokerage's upgrade or
raised target as support for a holding's thesis, and its downgrade, cut
target or sell call as a challenge (prompt version 9), from the headline
alone: "Dixon Tech gains after JM Financial upgrades stock". Why the
brokerage made the call is in the story, which a Google News headline never
reaches. A publisher's own feed (providers/publisher_feeds.py) gives the
story's opening and its address, so each such call is read again here for
its reasons:

  from the summary, the story's opening as the publisher wrote it;
  else from the article, where the summary states the call but not why it
  was made: asked for once, where the publisher's robots.txt allows it, and
  its text kept with the reading, so a new version of the question is asked
  of the kept text and never of the publisher again.

The reader copies the call, the brokerage, each reason and the words of the
thesis the reasons bear on exactly, and a quote not found verbatim is
dropped, as the thesis check drops one. The reasons are shown beside the
support or challenge they explain, as the brokerage's case rather than this
pipeline's: they change no stance, score or status.
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from logger import log

# Bump when the question changes; a kept reading is asked again, of the
# summary or of the article's kept text.
REASONS_VERSION = "1"
BATCH = 8
# Calls read and articles asked for in a run. A day's brokerage calls on the
# holdings are a handful; the rest wait for the next run.
MAX_PER_RUN = 24
MAX_ARTICLES_PER_RUN = 8
MAX_REASONS = 3
REASON_CHARS = 300

# Headlines worth the question. Only a filter on cost: the reader itself says
# whether the story reports a call at all.
CALL_WORDS = re.compile(
    r"upgrad|downgrad|target|\bbuy\b|\bsell\b|\bhold\b|\badd\b|\breduce\b"
    r"|\baccumulate\b|outperform|underperform|overweight|underweight"
    r"|\bneutral\b|top pick|brokerage|\brating\b|initiat\w* coverage|upside"
    r"|downside|bullish|bearish",
    re.IGNORECASE,
)

_INSTRUCTIONS = """You read stories about brokerages' calls on a stock, for an investor who owns it.

Each numbered item below is a story about a HOLDING, with the investor's
THESIS (why they own it), the story's HEADLINE, and TEXT from the story
itself. For each item return:

call      — the words of the HEADLINE or the TEXT that state a brokerage's or
            an analyst's call on this company, copied EXACTLY and
            contiguously: a rating (buy, sell, hold, add, reduce,
            outperform, overweight), an upgrade or a downgrade, a target
            price raised, cut or set, coverage started. "" when the story
            reports no such call on this company: a call on another company,
            a list of stocks with no call on this one, a share-price move,
            results or any other news.
brokerage — the brokerage or analyst making the call, copied EXACTLY from the
            HEADLINE or the TEXT; "" when the story does not name one.
reasons   — the reasons the TEXT gives for the call, as the brokerage states
            them, each copied EXACTLY and contiguously from the TEXT: at most
            three, each a phrase or a sentence. Only the reasons for this
            call on this company: not the story's background, the share
            price's move or another company's case. [] when the TEXT gives
            none, and when there is no call.
claim     — the words of the THESIS the reasons bear on, copied EXACTLY and
            contiguously; "" when there are no reasons or they bear on no
            claim in it.

Judge only from the HEADLINE, the TEXT and the THESIS; do not use outside
knowledge."""

_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "INTEGER"},
            "call": {"type": "STRING"},
            "brokerage": {"type": "STRING"},
            "reasons": {"type": "ARRAY", "items": {"type": "STRING"}},
            "claim": {"type": "STRING"},
        },
        "required": ["id", "call", "brokerage", "reasons", "claim"],
    },
}

_NO_CALL = {"call": "", "brokerage": "", "reasons": [], "claim": ""}


def _line(text: Any) -> str:
    return " ".join(str(text or "").split())


def _prompt(batch: List[Tuple[int, Dict[str, Any]]]) -> str:
    """One item per story: the holding, its thesis, the headline and the text
    read, each on a line of its own."""
    lines = []
    for i, item in batch:
        lines.append(
            f"\n{i}: HOLDING: {item['name']} ({item['ticker']}, listed in India)"
        )
        lines.append(f"   THESIS: {_line(item['thesis'])}")
        lines.append(f"   HEADLINE: {_line(item['headline'])}")
        lines.append(f"   TEXT: {_line(item['text'])}")
    return (
        f"{_INSTRUCTIONS}\n\nReturn a JSON array, one object per numbered "
        "item.\n" + "\n".join(lines)
    )


def _quote(raw: Any) -> str:
    return re.sub(r"\s+", " ", str(raw or "")).strip(" .,;:")


def ground(item: Dict[str, Any], raw: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only what is quoted verbatim: the call and the brokerage from the
    headline or the text, each reason from the text, the claim from the
    thesis. No call, nothing else; no reason, no claim. A reason that only
    restates the call is no reason."""
    from analysis.thesis_check import _norm

    story = _norm(f"{item['headline']} {item['text']}")
    text = _norm(item["text"])
    call = _quote(raw.get("call"))
    if not _norm(call) or _norm(call) not in story:
        return dict(_NO_CALL)
    brokerage = _quote(raw.get("brokerage"))
    if _norm(brokerage) not in story:
        brokerage = ""
    reasons: List[str] = []
    given = raw.get("reasons")
    for reason in given if isinstance(given, list) else []:
        reason = _quote(reason)
        if (
            _norm(reason)
            and _norm(reason) in text
            and _norm(reason) not in _norm(call)
            and reason not in reasons
        ):
            reasons.append(reason[:REASON_CHARS])
    reasons = reasons[:MAX_REASONS]
    claim = _quote(raw.get("claim"))
    if not reasons or _norm(claim) not in _norm(item["thesis"]):
        claim = ""
    return {"call": call, "brokerage": brokerage, "reasons": reasons, "claim": claim}


def wanted(pair: Dict[str, Any], reading: Dict[str, Any]) -> bool:
    """A support or a challenge, served, of a headline that may report a
    call, with the story's own words to read it in."""
    return (
        reading.get("stance") in ("supports", "contradicts")
        and bool(CALL_WORDS.search(str(pair.get("headline") or "")))
        and bool(pair.get("summary") or pair.get("article_url"))
    )


def record_of(entry: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The entry's reasons reading, if made with this version."""
    record = (entry or {}).get("reasons")
    return record if (record or {}).get("v") == REASONS_VERSION else None


def served(entry: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The call as the drawer, the Companies view and the email show it, or
    None where the story reported none."""
    record = record_of(entry)
    if not record or not record.get("call"):
        return None
    return {
        "call": record["call"],
        **({"brokerage": record["brokerage"]} if record.get("brokerage") else {}),
        "reasons": list(record.get("reasons") or []),
        **({"claim": record["claim"]} if record.get("claim") else {}),
        "source": record.get("source") or "summary",
        **({"url": record["url"]} if record.get("url") else {}),
    }


# (outcome, detail, paragraphs) for an article's address
# (providers.publisher_feeds.fetch_article).
Fetch = Callable[[str], Tuple[str, str, List[str]]]


def read_reasons(
    items: List[Tuple[str, Dict[str, Any]]],
    entries: Dict[str, Any],
    transport,
    today: str,
    status: Dict[str, Any],
    fetch: Fetch,
    limit: Optional[int] = None,
    article_limit: Optional[int] = None,
) -> bool:
    """Read the reasons for each ``(key, pair)`` call and store them on its
    thesis cache entry, beside the first reading and its check.

    The summary is read first, and the article only where the summary gives
    the call without its reasons (or there is no summary). ``fetch(url)``
    asks for an article (publisher_feeds.fetch_article), once a run however
    many holdings its story names, each read in its own part of it; what it
    answered is stored, so no article is asked for twice, and the part read
    is kept for later versions.

    Never raises, so the reasons can never cost the thesis check its run: an
    item no model could be reached for waits for the next run, with any
    article fetched for it kept. At most ``limit`` (MAX_PER_RUN) items are
    read and ``article_limit`` (MAX_ARTICLES_PER_RUN) articles asked for.
    Returns whether an entry changed.
    """
    from analysis.reader_runtime import ReaderUnavailable
    from providers.publisher_feeds import excerpt

    limit = MAX_PER_RUN if limit is None else limit
    article_limit = MAX_ARTICLES_PER_RUN if article_limit is None else article_limit
    todo = items[:limit]
    status["reasons_pending"] += len(items) - len(todo)
    changed = False

    def store(key: str, result: Dict[str, Any], source: str, **kept: Any) -> None:
        nonlocal changed
        served_by = getattr(transport, "model", None)
        entries[key]["reasons"] = {
            "v": REASONS_VERSION,
            "source": source,
            **result,
            "date": today,
            **({"model": served_by} if served_by else {}),
            **kept,
        }
        status["reasons_read"] += 1
        changed = True

    def ask(batch: List[Tuple[str, Dict[str, Any], str]]):
        """Each item's grounded result in order, None where none came back:
        a batch at a time, so what one batch read is kept if the next cannot
        reach a model."""
        for start in range(0, len(batch), BATCH):
            chunk = batch[start : start + BATCH]
            items_read = [{**pair, "text": text} for _, pair, text in chunk]
            reply = transport(_prompt(list(enumerate(items_read))))
            try:
                answers = json.loads(reply)
            except ValueError:
                answers = []
            by_id = {a.get("id"): a for a in answers if isinstance(a, dict)}
            for i, item in enumerate(items_read):
                raw = by_id.get(i)
                yield None if raw is None else ground(item, raw)

    # What is read first: an article's kept text, or the summary.
    first: List[Tuple[str, Dict[str, Any], str]] = []
    kept_of: Dict[str, Dict[str, Any]] = {}
    need_article: List[Tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]] = []
    for key, pair in todo:
        prior = entries[key].get("reasons") or {}
        if prior.get("text"):
            kept_of[key] = {k: prior[k] for k in ("url", "fetch", "text") if k in prior}
            first.append((key, pair, prior["text"]))
        elif pair.get("summary"):
            first.append((key, pair, pair["summary"]))
        else:
            need_article.append((key, pair, None))

    try:
        for (key, pair, _), result in zip(first, ask(first)):
            if result is None:
                status["reasons_pending"] += 1
            elif key in kept_of:
                store(key, result, "article", **kept_of[key])
            elif not result["call"] or result["reasons"] or not pair.get("article_url"):
                store(key, result, "summary")
            else:
                need_article.append((key, pair, result))

        # The article, for a call its summary gives no reasons for.
        fetched: Dict[str, Tuple[str, str, List[str]]] = {}
        to_read: List[Tuple[str, Dict[str, Any], str]] = []
        for key, pair, fallback in need_article:
            url = pair["article_url"]
            prior = entries[key].get("reasons") or {}
            source = "summary" if fallback else "article"
            if prior.get("fetch") and prior.get("url") == url:
                # Asked for before, and it gave no text: never again.
                store(
                    key,
                    fallback or dict(_NO_CALL),
                    source,
                    url=url,
                    fetch=prior["fetch"],
                )
                continue
            if url not in fetched:
                if len(fetched) >= article_limit:
                    status["reasons_pending"] += 1
                    continue
                fetched[url] = fetch(url)
                if fetched[url][0] == "ok":
                    status["articles"] += 1
                elif fetched[url][0] != "waiting":
                    status["articles_refused"] += 1
            outcome, detail, paragraphs = fetched[url]
            if outcome == "ok":
                text = excerpt(paragraphs, pair["ticker"], pair["name"])
                to_read.append((key, pair, text))
                kept_of[key] = {"url": url, "fetch": "ok", "text": text}
            elif outcome == "waiting":
                status["reasons_pending"] += 1
            else:
                store(
                    key,
                    fallback or dict(_NO_CALL),
                    source,
                    url=url,
                    fetch=f"{outcome}: {detail}",
                )
        for (key, pair, _), result in zip(to_read, ask(to_read)):
            if result is None:
                # Kept for the next run, which asks again of this text.
                entries[key]["reasons"] = {"v": "", **kept_of[key]}
                status["reasons_pending"] += 1
                changed = True
            else:
                store(key, result, "article", **kept_of[key])
    except Exception as e:  # noqa: BLE001 - never the thesis check's undoing
        status["reasons_skipped"] = (
            str(e) if isinstance(e, ReaderUnavailable) else repr(e)
        )
        if not isinstance(e, ReaderUnavailable):
            log.warning(f"Brokerage reasons failed safely: {e!r}")
        # Anything fetched and not yet read is kept for the next run.
        for key, info in kept_of.items():
            if record_of(entries[key]) is None and info.get("fetch") == "ok":
                entries[key]["reasons"] = {"v": "", **info}
                changed = True
        status["reasons_pending"] = sum(
            1 for key, _ in items if record_of(entries[key]) is None
        )
    return changed
