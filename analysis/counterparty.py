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

The first review of the queue (36 proposals) found five ways a wrong name
got through, each guarded below and pinned in tests/test_partner_graph.py:

    "IIEST, Shibpur partners with TCS"         a place read as a second party
    "JV with French company Safran"            a nationality read as the party
    "L&T Technology Services Partners with"    a piece of our own name
    "... to Advance Engineering Intelligence   a "with" that is not the tie-up's
     with Industrial AI"
    "TCS renews title partnership with         a name built on our own
     Jaguar TCS Racing"
"""

import re
from typing import Iterable, List, Set, Tuple

from analysis.parsing import (
    _FUNCTION_WORDS,
    _HEADLINE_VERBS,
    _PERSON_TITLES,
    _abbreviates,
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
    # Nationalities and the countries headlines most often qualify a partner
    # with: "JV with French company Safran" is a JV with Safran.
    "american",
    "british",
    "canadian",
    "dutch",
    "european",
    "french",
    "german",
    "israeli",
    "italian",
    "korean",
    "russian",
    "saudi",
    "singaporean",
    "spanish",
    "swedish",
    "swiss",
    "taiwanese",
    "emirati",
    "uae",
    "france",
    "germany",
    "israel",
    "korea",
    "russia",
    "singapore",
    "taiwan",
    "foreign",
    "global",
    "south",
    "north",
}

# Charities, universities, research institutes and industry bodies. A CSR
# partnership, an academic MoU or a council's showcase is real, and is not a
# relationship that moves a share price.
_NON_COMMERCIAL = {
    "foundation",
    "trust",
    "university",
    "institute",
    "iit",
    "iim",
    "iisc",
    "iiit",
    "iiest",
    "iiser",
    "nit",
    "college",
    "school",
    "ngo",
    "council",
    "association",
    "federation",
    "chamber",
}

# The word right before "with" when its object is the other party: "partners
# with", "MoU with", "joint venture with", "ties up with", "joins hands with".
# Any other "with" belongs to something else in the headline — "to Advance
# Engineering Intelligence with Industrial AI", "take centre stage with" a
# designer — and its object is not a party to anything.
_TIE_UP_BEFORE_WITH = {
    "partner",
    "partners",
    "partnered",
    "partnering",
    "partnership",
    "partnerships",
    "venture",
    "ventures",
    "jv",
    "jvs",
    "mou",
    "mous",
    "pact",
    "pacts",
    "agreement",
    "agreements",
    "understanding",
    "alliance",
    "alliances",
    "collaboration",
    "collaborations",
    "collaborate",
    "collaborates",
    "collaborated",
    "collaborating",
    "tie-up",
    "tie-ups",
    "tieup",
    "ties",
    "up",
    "hands",
    "forces",
    "teams",
    "teamed",
    "deal",
    "deals",
    "association",
    "consortium",
    "cooperation",
    "co-operation",
}

# Words that may follow our own name and still be our name: "Siemens Ltd",
# "Cummins India".
_OWN_NAME_TAIL = {"ltd", "limited", "india", "inc", "corp", "corporation"}

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


def _own_spans(text: str, holdings) -> Set[Tuple[int, int]]:
    """Where the clause names the holdings themselves, as character spans.

    Kept whole when the clause is split into names. Our own name can carry a
    boundary word — "L&T Technology Services", "Kaynes Technology" — and
    split there it left "L&T" looking like somebody else, and cut "Kaynes
    Technology, BOSGAME" into pieces that no longer read as a list.

    Each mention is confirmed with title_matches_company on the words around
    it, so its guards hold here too: the "TCS" in "Jaguar TCS Racing" is the
    start of a longer name, not TCS, and is left inside that name.
    """
    tokens = list(_TOKEN_RE.finditer(text))
    spans: Set[Tuple[int, int]] = set()
    for ticker, company in holdings:
        core = _TOKEN_RE.findall(str(company or "").split("(")[0])
        own = {_clean(t) for t in _TOKEN_RE.findall(str(company or ""))}
        starts = {str(ticker or "").lower(), _clean(core[0]) if core else ""} - {""}
        for i, match in enumerate(tokens):
            if _clean(match.group(0)) not in starts:
                continue
            j = i
            while j + 1 < len(tokens):
                nxt = tokens[j + 1]
                word = _clean(nxt.group(0))
                if text[tokens[j].end() : nxt.start()].strip() or not (
                    word in own or word in _OWN_NAME_TAIL or _abbreviates(word, own)
                ):
                    break
                j += 1
            start, end = match.start(), tokens[j].end()
            window_start = tokens[i - 1].start() if i else start
            window_end = tokens[j + 1].end() if j + 1 < len(tokens) else end
            if title_matches_company(text[window_start:window_end], ticker, company):
                spans.add((start, end))
    return spans


def _runs(
    text: str, own: Set[Tuple[int, int]] = frozenset()
) -> List[Tuple[int, int, str]]:
    """Maximal name runs as ``(start, end, text)``.

    A run breaks on any boundary word and on any punctuation between tokens —
    a comma, a hyphen, a colon — because in headline style those separate
    names rather than join them ("BHEL, Titagarh", "Dixon-Vivo"). A span in
    ``own`` (see _own_spans) is one run whatever words it contains.
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
    skip_until = -1
    for match in _TOKEN_RE.finditer(text):
        if match.start() < skip_until:
            continue
        span = next((s for s in own if s[0] <= match.start() < s[1]), None)
        if span:
            close()
            runs.append((span[0], span[1], text[span[0] : span[1]]))
            skip_until = previous_end = span[1]
            continue
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
    # "Ashish N Soni": a given name, a middle initial and a surname is a
    # person. No title precedes a designer's name for the check above to see.
    words = name.split()
    if (
        len(words) == 3
        and re.fullmatch(r"[A-Za-z]\.?", words[1])
        and all(w.isalpha() and len(w) > 1 for w in (words[0], words[2]))
    ):
        return False
    # One or two letters is an abbreviation too ambiguous to propose.
    return len(name.replace(" ", "")) >= 3


def _builds_on_holding(name: str, holdings: Iterable[Tuple[str, str]]) -> bool:
    """A name with our ticker or our whole name inside it is ours, not a party.

    "Jaguar TCS Racing" is the team TCS sponsors and "Tata Power Renewable
    Energy" is Tata Power's own arm: either way not somebody else. The ticker
    must appear as written, in capitals, so a ticker that is also an
    ordinary word ("CAMPUS") cannot claim "Google Campus".
    """
    words = name.split()
    lowered = [_clean(w) for w in words]
    for ticker, company in holdings:
        if ticker and ticker in words:
            return True
        core = [_clean(w) for w in str(company or "").split("(")[0].split()]
        while len(core) > 1 and core[-1] in _SUFFIXES:
            core.pop()
        n = len(core)
        if n and any(lowered[i : i + n] == core for i in range(len(lowered) - n + 1)):
            return True
    return False


def _past_qualifier(run, runs, text):
    """The name a nationality introduces: "French company Safran" -> Safran.

    A run made only of qualifier words, followed by at most three lowercase
    descriptors and then a name, stands for that name. Anything else is
    returned unchanged for the usual checks to judge.
    """
    if not all(_clean(t) in _NOT_A_COMPANY for t in run[2].split()):
        return run
    nxt = next((r for r in runs if r[0] > run[1]), None)
    if not nxt:
        return run
    gap = text[run[1] : nxt[0]].split()
    if len(gap) <= 3 and all(
        w.isalpha() and w.islower() and w not in _FUNCTION_WORDS for w in gap
    ):
        return nxt
    return run


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
    own = _own_spans(text, holdings)
    runs = _runs(text, own)
    if not runs:
        return []

    def ours(run) -> bool:
        return (run[0], run[1]) in own or _is_holding(run[2], holdings)

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

    # "BHEL, Titagarh to form JV" lists two parties, one of them ours. "IIEST,
    # Shibpur partners with TCS" names one party and where it is: with none
    # of ours in the list and only commas between, the first name is the
    # party and the rest say where it is.
    if len(subject_runs) > 1 and not any(ours(r) for r in subject_runs):
        separators = {
            text[a[1] : b[0]].strip() for a, b in zip(subject_runs, subject_runs[1:])
        }
        if separators == {","}:
            subject_runs = subject_runs[:1]

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
        before = re.findall(r"[A-Za-z][A-Za-z-]*", text[: match.start()])
        if not before or before[-1].lower() not in _TIE_UP_BEFORE_WITH:
            continue
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
        follow = _past_qualifier(follow, runs, text)
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

    own_names = {text[s:e] for s, e in own}
    out: List[str] = []
    seen = set()
    for raw in candidates:
        name = _normalise(raw)
        if (
            not name
            or raw in own_names
            or not _acceptable(name)
            or _is_holding(name, holdings)
            or _builds_on_holding(name, holdings)
        ):
            continue
        key = name.lower()
        if key not in seen:
            seen.add(key)
            out.append(name)
    return out
