"""Headline hygiene: say the news, not the wrapper around it.

Exchange filings arrive in a fixed envelope —

    Lemon Tree Hotels Limited has informed the Exchange regarding a press
    release dated September 24, 2026, titled "LEMON TREE HOTELS EXPANDS
    MUMBAI FOOTPRINT; ACQUIRES LAND ...

— and the email was printing the envelope. The story is the quoted title.
Because the envelope never varies, stripping it is a text rule, not a job for
a model: it is exact, free, and cannot misquote.

Most filings are also not news at all. A company secretary resigning, an AGM
notice in a newspaper, a link to an earnings-call recording: statutory
housekeeping, which was being joined into "Active policy tailwind" alerts
beside a land acquisition as though they weighed the same. And one of them —
"Board comments on fine levied by the Exchange" — is bad news that was being
filed as a tailwind.

classify() sorts a filing into three kinds:

    routine      statutory housekeeping, an empty cover label, or market
                 commentary — carries no information about the business
    adverse      a regulator's or exchange's action against the company
    substantive  everything else — the default, so an unrecognised filing is
                 kept rather than hidden
"""

import re

# "X Limited has informed the Exchange regarding/about ..." and the NSE
# variants. Anchored at the start so a headline that merely mentions an
# exchange is untouched.
_ENVELOPE_RE = re.compile(
    r"^.{2,120}?\b(?:limited|ltd\.?)\s+has\s+informed\s+the\s+exchanges?\s+"
    r"(?:regarding|about|that)\s+",
    re.IGNORECASE,
)
# 'a press release dated September 22, 2026, titled "..."'
# The date contains its own comma ("September 24, 2026,"), so it is matched
# lazily up to the title verb rather than up to the first comma.
_PRESS_RELEASE_RE = re.compile(
    r"^(?:a\s+|the\s+)?press\s+release\s+(?:dated\s+.{0,40}?,?\s*)?(?:titled|"
    r"captioned|with\s+the\s+title)\s+",
    re.IGNORECASE,
)
# "'Press Release - TCS wins ...'" — the NSE subject-line form.
_PRESS_PREFIX_RE = re.compile(r"^press\s+release\s*[-–:]\s*", re.IGNORECASE)
_QUOTES = "\"'“”‘’"

_PROCEDURAL = re.compile(
    r"\b(?:"
    r"resignation|appointment\s+of|cessation|re-?appointment|"
    r"change\s+in\s+(?:directors?|kmp|(?:senior\s+)?management|auditors?|registrar|address)|"
    r"senior\s+management\s+personnel|"
    r"newspaper\s+(?:publication|advertisement)|copy\s+of\s+newspaper|"
    r"audio\s+recording|video\s+recording|transcript|"
    r"(?:investor|analyst)s?\s+(?:meet|call|presentation|conference)|"
    r"(?:institutional\s+investors?|analysts?)\s*/\s*(?:analysts?|institutional)|"
    r"interaction\s+with\s+(?:institutional\s+)?(?:investors|analysts)|"
    r"outcome\s+of\s+(?:analyst|investor|institutional)|"
    r"trading\s+window|allotment\s+of|esop|esps|"
    r"notice\s+of\s+(?:annual|extra-?ordinary)\s+general\s+meeting|"
    r"(?:agm|egm)\s+notice|annual\s+report|book\s+closure|record\s+date|"
    r"credit\s+rating|loss\s+of\s+share\s+certificates?|duplicate\s+share|"
    r"compliance\s+certificate|regulation\s+74\s*\(5\)|"
    r"shareholders?\s+meeting|voting\s+results?|scrutini[sz]er|"
    r"intimation\s+of\s+board\s+meeting|board\s+meeting\s+intimation|"
    r"schedules?\s+board\s+meeting|closure\s+of\s+trading|"
    r"schedule\s+of\s+(?:meet|analyst)|sought\s+clarification|"
    r"significant\s+movement\s+in\s+price|srutini[sz]ers?|"
    r"please\s+(?:find|refer)|link\s+of\s+recording|"
    r"investors?'?\s+(?:conference|meeting)|clarification\s+on|"
    r"reclassification|withholding\s+of\s+(?:final\s+)?dividend|"
    r"regulation\s+29\s*\(|^press\s+release\s+dated|"
    # Executive hires below the top job: "IKS Health Appoints Arun Nair as
    # Vice President – Human Resources" was listed as a corporate agreement.
    r"appoints?\b.{0,60}\b(?:vice\s+president|vp|head|director|officer|"
    r"chro|cfo|cto|coo|cio|secretary)|"
    r"names\b.{0,60}\b(?:vice\s+president|vp|head|chro|cfo|cto|coo|cio)"
    r")\b",
    re.IGNORECASE,
)

# Appointments and resignations are housekeeping — except at the top. A new
# CEO or MD, or one leaving, is news a shareholder acts on.
_TOP_JOB = re.compile(
    r"\b(?:ceo|chief\s+executive|md|managing\s+director|chairman|chairperson|"
    r"whole[-\s]time\s+director|cfo|chief\s+financial)\b",
    re.IGNORECASE,
)

# A filing whose whole text is a cover label says nothing on its own.
_EMPTY = re.compile(
    r"^(?:presentation|press\s+release|intimation\s+of\s+press\s+release|"
    r"general\s+updates?|updates?|disclosure|intimation|clarification|"
    r"pursuant\s+to\s+(?:the\s+provisions\s+of\s+)?regulations?\s+30\b.*)$",
    re.IGNORECASE,
)

# Market commentary that reached a filings or agreements feed: a price move or
# a stock tip describes the market's reaction, never the business.
_COMMENTARY = re.compile(
    r"\b(?:share\s+price\s+target|stocks?\s+to\s+watch|stocks?\s+in\s+focus|"
    r"stock\s+leads|edges?\s+(?:higher|lower)|key\s+support|"
    r"what'?s\s+triggering|upper\s+circuit|lower\s+circuit|52-week|"
    r"top\s+(?:gainers?|losers?)|catalyst\s+picks|volume\s+gainers|"
    r"analysts\s+are\s+forecasting|tell\s+the\s+whole\s+story|"
    r"stocks?\s+slide|slides?\s+up\s+to|share\s+price(?:\s+today)?$|"
    r"stock\s+prediction|bright\s+future|\d+\s+\w+\s+stocks\b)",
    re.IGNORECASE,
)

_ADVERSE = re.compile(
    r"\b(?:"
    r"fine\s+levied|fines?\s+imposed|penalt(?:y|ies)|show[-\s]cause|"
    r"sebi\s+order|adjudicat\w+|search\s+and\s+seizure|raid|"
    r"non-?compliance|suspension\s+of\s+trading|default(?:ed)?\s+on|"
    r"insolvency|winding\s+up"
    r")\b",
    re.IGNORECASE,
)


def _unshout(text: str) -> str:
    """Headline case for a title written in capitals; anything else as is.

    "LEMON TREE HOTELS EXPANDS MUMBAI FOOTPRINT" reads as shouting in a list
    of ordinary headlines. Only a mostly-capitals title is touched, so an
    acronym inside a normal headline ("BEL bags order") keeps its case.
    """
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 20 or sum(c.isupper() for c in letters) / len(letters) < 0.8:
        return text
    return re.sub(r"'S\b", "'s", text.title())


def tidy(text: str) -> str:
    """The news inside an exchange-filing envelope; other text unchanged
    beyond whitespace, a "Press Release -" prefix and all-capitals titles."""
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    s = s.replace("''", "'")
    body = _ENVELOPE_RE.sub("", s, count=1)
    body = _PRESS_RELEASE_RE.sub("", body, count=1).strip(_QUOTES + " ")
    body = _PRESS_PREFIX_RE.sub("", body, count=1).strip(_QUOTES + " ")
    if body != s:
        body = body.rstrip(".").strip(_QUOTES + " ").rstrip(".")
    if not body:
        return s
    body = _unshout(body)
    return _sentence_start(body) if body != s else body


def classify(text: str) -> str:
    """``routine``, ``adverse`` or ``substantive``.

    Adverse is checked first: "Board comments on fine levied by the Exchange"
    is a board filing and also the one thing in it that matters.
    """
    body = tidy(text)
    if _ADVERSE.search(body):
        return "adverse"
    if _PROCEDURAL.search(body) and not _TOP_JOB.search(body):
        return "routine"
    if _EMPTY.match(body.strip(" .")):
        return "routine"
    if _COMMENTARY.search(body):
        return "routine"
    from analysis.materiality import _PRICE_MOVE_RE

    if _PRICE_MOVE_RE.search(body):
        return "routine"
    return "substantive"


def display(text: str, reading: dict = None, holdings=()) -> str:
    """What to print for a headline: the LLM's verbatim gist when it has one,
    otherwise the tidied text.

    The gist is only ever a passage of the original (llm_reader.ground()
    enforces that), so this shortens without rewording: whatever the reader
    sees, the source said in those words.

    ``holdings`` are the ``(ticker, name)`` pairs the headline names. A gist
    that drops every one of them is refused: the first live run shortened
    "ideaForge Now Has a Drone Taking Off Every 2 Minutes; Q1 Revenue Reaches
    ₹68.6 Cr" to "Q1 Revenue Reaches ₹68.6 Cr", and 33 of 153 gists on
    holding headlines lost the company that way. A shorter line that no
    longer says whose news it is costs more than the words it saves.
    """
    gist = (reading or {}).get("gist") or ""
    if gist and holdings and not any(_mentions(gist, t, n) for t, n in holdings):
        gist = ""
    if gist:
        return _sentence_start(gist)
    return tidy(text)


def _mentions(text: str, ticker: str, name: str) -> bool:
    """Does the line still say whose news it is?

    A plain word match on the ticker or the first word of the name, not the
    full company matcher: that one reads "ideaForge Now Has ..." as a longer
    company name starting with ideaForge, which is right for attribution and
    wrong for asking whether a shortened line kept the company in it.
    """
    words = [str(ticker or "")]
    first = str(name or "").split("(")[0].split()
    if first and len(first[0]) >= 3:
        words.append(first[0])
    return any(
        w and re.search(rf"\b{re.escape(w)}\b", text, re.IGNORECASE) for w in words
    )


def _sentence_start(text: str) -> str:
    """Capitalise a line that starts mid-sentence ("acquires land ..."), but
    never a brand written with an internal capital — "ideaForge", "iPhone"."""
    first = text.split(" ", 1)[0]
    if first.islower():
        return text[0].upper() + text[1:]
    return text
