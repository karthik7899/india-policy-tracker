"""Who is on the other side of a tie-up?

A tie-up is a relationship by definition — two parties, one agreement — and
the event engine was recording half of it. ``actors`` keeps the watchlist
side, which is right for attribution, and the other party was discarded at
the same moment:

    CONCOR signs MoU with APEDA ...           actors=[CONCOR]
    Syrma SGS Forms PCB Joint Venture With Kaga Electronics
                                               actors=[SYRMA]

Kaga Electronics was named, parsed and thrown away, so the next headline about
Kaga could never be read across to Syrma. This module recovers the name.

It reads headline STRUCTURE rather than a list of company names, because the
counterparties worth knowing are exactly the ones no list anticipated. Four
shapes carry nearly every tie-up in the live corpus:

    "X partners with Y"                    the object of "with"
    "X and Y form joint venture"           a list of subjects
    "X, Y to form joint venture"           the same, comma-separated
    "X-Y joint venture"                    a hyphenated pair

Precision over recall, deliberately. What this returns becomes a PROPOSED
graph edge that a person reviews (see entity_graph.record_partner_proposals),
so a miss costs one headline's worth of learning while a wrong name costs a
reviewer's attention — and, if waved through, a plausible-sounding chain that
is false. So anything that reads as a person, a place, a regulator, an
advisor or a charity is dropped rather than proposed.
"""

import re
from typing import Iterable, List, Tuple

from analysis.parsing import (
    _FUNCTION_WORDS,
    _HEADLINE_VERBS,
    _PERSON_TITLES,
    title_matches_company,
)

# Words that end a name run. Title-Case headlines capitalise everything, so
# case alone cannot say where "Kaynes Technology Partners With BOSGAME" stops
# being a name — the vocabulary has to.
_BOUNDARY_WORDS = (
    set(_FUNCTION_WORDS)
    | set(_HEADLINE_VERBS)
    | {
        # tie-up vocabulary, in every inflection headlines use
        "partner",
        "partnered",
        "partnering",
        "partnership",
        "partnerships",
        "joint",
        "venture",
        "ventures",
        "jv",
        "mou",
        "memorandum",
        "understanding",
        "alliance",
        "collaboration",
        "collaborate",
        "collaborates",
        "strategic",
        "tie",
        "ties",
        "tie-up",
        "hands",
        "join",
        "joins",
        "agreement",
        "pact",
        "deal",
        "sign",
        "signed",
        "ink",
        "inked",
        "form",
        "forms",
        "formed",
        "forge",
        "forges",
        "forged",
        "inaugurate",
        "inaugurates",
        "inaugurated",
        "finalise",
        "finalises",
        "finalize",
        "finalizes",
        "approve",
        "approves",
        "approved",
        "clear",
        "clears",
        "cleared",
        "extend",
        "extends",
        "renew",
        "renews",
        "advance",
        "accelerate",
        "build",
        "develop",
        "produce",
        "launch",
        "crosses",
        "set",
        "sets",
        "board",
        "shares",
        "share",
        "stock",
        "stocks",
        "new",
        "technology",
        "transfer",
    }
)

# A name that is one of these is not a counterparty. States and regulators
# sign MoUs constantly and are not commercial relationships a holding's
# fortunes ride on; a country is a qualifier, not a party.
_NOT_A_COMPANY = {
    "india",
    "indian",
    "china",
    "chinese",
    "japan",
    "japanese",
    "us",
    "usa",
    "uk",
    "eu",
    "government",
    "govt",
    "centre",
    "center",
    "cabinet",
    "ministry",
    "state",
    "union",
    "sebi",
    "rbi",
    "nse",
    "bse",
    "exchange",
    "company",
    "firm",
    "group",
}

# Charities, universities and research institutes. A CSR partnership or an
# academic MoU is real, and is not a relationship that moves a share price.
_NON_COMMERCIAL = {
    "foundation",
    "trust",
    "university",
    "institute",
    "iit",
    "iim",
    "iisc",
    "college",
    "school",
    "ngo",
}

# Legal and geographic suffixes stripped so that "Kaga Electronics India" and
# "Kaga Electronics" propose one edge rather than two.
_SUFFIXES = {
    "india",
    "ltd",
    "limited",
    "pvt",
    "private",
    "inc",
    "corp",
    "corporation",
    "co",
    "llc",
    "plc",
    "ag",
    "gmbh",
    "sa",
    "bv",
    "nv",
}

# "SAM Advises Vivo Mobile India On Strategic Joint Venture With Dixon" — the
# subject is the advisor, not a party. Its object is the party instead. These
# are boundary words too, or Title Case would read "SAM Advises Vivo Mobile"
# as a single name.
_ADVISOR_VERBS = {"advises", "advised", "advising", "counsels"}
_BOUNDARY_WORDS |= _ADVISOR_VERBS

_TIE_UP_NOUN_RE = re.compile(
    r"^\s*(?:strategic\s+)?(?:joint\s+venture|jv\b|partnership|tie-?up|alliance)",
    re.IGNORECASE,
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9&.'’]*|&")
_POSSESSIVE_RE = re.compile(r"['’]s$", re.IGNORECASE)


def _clean(token: str) -> str:
    return _POSSESSIVE_RE.sub("", token.lower().rstrip("."))


def _is_name_token(token: str) -> bool:
    if token == "&":
        return True
    if _clean(token) in _BOUNDARY_WORDS:
        return False
    if token[0].isupper():
        return True
    # "3M", "20Microns": digit-led but plainly a name.
    return token[0].isdigit() and any(c.isalpha() for c in token)


def _runs(text: str) -> List[Tuple[int, int, str]]:
    """Maximal name runs as ``(start, end, text)``.

    A run breaks on any boundary word and on any punctuation between tokens —
    a comma, a hyphen, a colon — because in headline style those separate
    names rather than join them ("BHEL, Titagarh", "Dixon-Vivo").
    """
    runs: List[Tuple[int, int, str]] = []
    current: List[re.Match] = []

    def close():
        if current:
            # A run cannot end on "&" — "Tata & " is a truncation, not a name.
            while current and current[-1].group(0) == "&":
                current.pop()
            if current:
                start, end = current[0].start(), current[-1].end()
                runs.append((start, end, text[start:end]))
        current.clear()

    previous_end = None
    for match in _TOKEN_RE.finditer(text):
        token = match.group(0)
        gap = text[previous_end : match.start()] if previous_end is not None else ""
        if current and gap.strip():
            close()
        if _is_name_token(token):
            current.append(match)
        else:
            close()
        previous_end = match.end()
        # A possessive ends the name it is attached to: "China's Bosgame" is
        # a qualifier followed by a name, not a name called "China's Bosgame".
        if current and _POSSESSIVE_RE.search(token):
            close()
    close()
    return runs


def _normalise(name: str) -> str:
    tokens = name.split()
    while tokens and tokens[0].lower() == "the":
        tokens.pop(0)
    while len(tokens) > 1 and _clean(tokens[-1]) in _SUFFIXES:
        tokens.pop()
    return " ".join(tokens).strip(" .,&")


def _acceptable(name: str) -> bool:
    lowered = [_clean(t) for t in name.split()]
    if not lowered:
        return False
    if any(t in _PERSON_TITLES for t in lowered):
        return False  # "US President Trump" is a person, not a partner
    if any(t in _NON_COMMERCIAL for t in lowered):
        return False
    if all(t in _NOT_A_COMPANY for t in lowered):
        return False
    # One or two letters is an abbreviation too ambiguous to propose.
    return len(name.replace(" ", "")) >= 3


def _is_holding(name: str, holdings: Iterable[Tuple[str, str]]) -> bool:
    run = [_clean(t) for t in name.split()]
    for ticker, company in holdings:
        if title_matches_company(name, ticker, company):
            return True
        # The matcher finds a company's full name inside a headline; here the
        # run may be a truncation of it instead — "Kaynes Tech" for "Kaynes
        # Technology". Accepted as ours when it is a multi-word prefix of the
        # name. Not a first-word test: that would read "Tata Power" as TCS.
        core = [_clean(t) for t in str(company or "").split("(")[0].split()]
        if len(run) >= 2 and core[: len(run)] == run:
            return True
    return False


def extract_counterparties(
    clause: str, holdings: Iterable[Tuple[str, str]]
) -> List[str]:
    """Names on the other side of a tie-up clause from ``holdings``.

    ``holdings`` are the ``(ticker, name)`` pairs already attributed to this
    clause — the side we hold. Everything returned is a party that is NOT one
    of them. Empty when the clause is not about a holding at all: a
    counterparty is only meaningful relative to something we own.
    """
    holdings = list(holdings or [])
    if not clause or not holdings:
        return []

    # Parentheticals are qualifiers here — "Dixon (India)-Vivo (China)" — and
    # left in they would split into names of their own.
    text = re.sub(r"\([^)]*\)", " ", clause)
    runs = _runs(text)
    if not runs:
        return []

    candidates: List[str] = []

    def after(end: int) -> str:
        return text[end:]

    # Subject position. If the clause opens with a topic label — "Vande
    # Bharat Sleeper trains: BHEL, Titagarh to form joint venture" — the
    # parties follow the colon, and only when a name starts right there.
    subject_from = 0
    colon = text.rfind(":")
    if colon != -1:
        tail = text[colon + 1 :]
        first = next((r for r in runs if r[0] > colon), None)
        if first and not tail[: first[0] - colon - 1].strip():
            subject_from = colon + 1

    subject_runs = []
    for start, end, name in runs:
        if start < subject_from:
            continue
        between = (
            text[subject_from:start]
            if not subject_runs
            else text[subject_runs[-1][1] : start]
        )
        if not subject_runs:
            if between.strip():
                break  # the clause does not open with a name
        elif between.strip().lower() not in (",", "and", "&", "-"):
            break
        subject_runs.append((start, end, name))

    advisor = False
    if subject_runs:
        next_word = re.match(r"\s*([A-Za-z]+)", after(subject_runs[-1][1]))
        advisor = bool(next_word) and next_word.group(1).lower() in _ADVISOR_VERBS
        if advisor:
            # The advisor is not a party; the party is what it advises.
            follow = next((r for r in runs if r[0] > subject_runs[-1][1]), None)
            if follow:
                candidates.append(follow[2])
        else:
            candidates.extend(name for _, _, name in subject_runs)

    # Object of "with", optionally past a few lowercase descriptors: "with
    # trusted engineering partner Coforge" is a partnership with Coforge.
    for match in re.finditer(r"\bwith\b", text, re.IGNORECASE):
        follow = next((r for r in runs if r[0] >= match.end()), None)
        if not follow:
            continue
        gap = text[match.end() : follow[0]].split()
        if len(gap) > 3 or any(
            _clean(w) in _FUNCTION_WORDS or not w.isalpha() for w in gap
        ):
            continue
        # "with China's Bosgame": the possessive is a qualifier on the name
        # that follows it, so the party is the next run, not this one.
        if _POSSESSIVE_RE.search(follow[2]):
            nxt = next((r for r in runs if r[0] > follow[1]), None)
            if nxt and not text[follow[1] : nxt[0]].strip():
                follow = nxt
        candidates.append(follow[2])
        # "NTPC signs MoU with NHPC, PTC and TCS" — a list after "with".
        last_end = follow[1]
        for start, end, name in runs:
            if start <= last_end:
                continue
            if text[last_end:start].strip().lower() not in (",", "and"):
                break
            candidates.append(name)
            last_end = end

    # "Syrma SGS-Elemaster joint venture": a hyphenated pair before a tie-up
    # noun, wherever it sits in the clause.
    for (s1, e1, n1), (s2, e2, n2) in zip(runs, runs[1:]):
        if text[e1:s2].strip() == "-" and _TIE_UP_NOUN_RE.match(text[e2:]):
            candidates.extend([n1, n2])

    out: List[str] = []
    seen = set()
    for raw in candidates:
        name = _normalise(raw)
        if not name or not _acceptable(name) or _is_holding(name, holdings):
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            out.append(name)
    return out
