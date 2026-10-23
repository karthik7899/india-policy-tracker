"""Generic market-event engine: classify WHAT happened, route to WHO it touches.

Design rule zero: no entity name appears in this module. Companies, anchors
and commodities exist only as data — the watchlist, the Screener peer radar
and entity_graph.json. Routing is two-tier so the engine works with an empty
graph: Tier 1 maps an event's domain to sectors through vocabulary alone
("X commits $30B for custom chips" routes to electronics holdings whoever X
is); Tier 2 upgrades a signal to holding level when a typed edge exists.

Fully deterministic by decision (no LLM): the RSS queries are themselves
classifiers, and a material event generates many differently-phrased
headlines of which the engine only needs to catch one. Misses found in
production logs become vocabulary entries with regression tests — the same
loop that hardened the headline→company matcher.
"""

import datetime
import re
from typing import Any, Dict, List, Optional

from analysis.competitive_intel import (
    battleground_sectors,
    collect_headlines,
    collect_sources,
)
from analysis.event_evidence import article_date, evidence_level, headline_date
from analysis.parsing import title_matches_company
from config import SECTOR_METADATA
from logger import log

# What happened — each type is (vocabulary, direction-for-domain-sectors).
# Checked in this order, first match wins.
EVENT_VOCABULARY: Dict[str, tuple] = {
    # Before tie_up, whose "joint venture" it contains: "Vivo exits joint
    # venture with Dixon" was read as a new tie-up. Shapes in EVENT_PATTERNS.
    "partnership_end": (),
    "tie_up": (
        "joint venture",
        "strategic partnership",
        "partnership with",
        "partners with",
        "ties up with",
        "tie-up with",
        "joins hands",
        "alliance with",
        "mou with",
        "memorandum of understanding",
        "collaboration with",
        "technology transfer",
    ),
    "acquisition": (
        "acquires",
        "acquisition of",
        "buys stake",
        "stake purchase",
        "to acquire",
        "takeover of",
        "merger with",
    ),
    "order_win": (
        "wins order",
        "bags order",
        "secures order",
        "wins contract",
        "bags contract",
        "order worth",
        "letter of intent",
        "letter of award",
        "purchase order",
    ),
    "capacity_add": (
        "new plant",
        "new facility",
        "new factory",
        "groundbreaking",
        "capacity expansion",
        "expands capacity",
        "commercial production",
        "begins production",
        "starts production",
        "commissions",
        "sets up plant",
        "sets up unit",
        "multiyear commitment",
        "billion deal",
        "billion commitment",
    ),
    "supply_disruption": (
        "shortage",
        "supply crunch",
        "supply chain disruption",
        "export restriction",
        "export curb",
        "export ban",
        "halts production",
        "production halt",
        "plant shutdown",
        "force majeure",
        "embargo",
        "supply constraints",
    ),
    "input_cost_shock": (
        "prices surge",
        "prices soar",
        "prices spike",
        "prices jump",
        "price surge",
        "cost surge",
        "raw material cost",
        "freight rates",
        "input costs rise",
        "costlier imports",
    ),
    # One company's own business getting weaker. Without it "Corning sales
    # fall 12%" was no event at all, so nothing linked to Corning could hear
    # of it. Shapes with a verb in EVENT_PATTERNS.
    "business_weakness": (
        "profit warning",
        "misses estimates",
        "missed estimates",
        "misses expectations",
        "below estimates",
        "weak demand",
        "demand slowdown",
        "slowing demand",
        "swings to loss",
        "slips into loss",
        "posts net loss",
        "reports net loss",
        "widens loss",
        "loss widens",
        "layoffs",
        "lays off",
        "job cuts",
        "cuts jobs",
        # Entering it, not the word: "NCLT dismisses insolvency plea against
        # Suzlon" is good news for Suzlon.
        "files for bankruptcy",
        "files for insolvency",
        "bankruptcy filing",
        "chapter 11",
        "enters administration",
    ),
}

# Shapes the literal phrases above cannot express, because headlines put
# words between the verb and its object. "Suzlon bags 306 MW wind turbine
# orders" and "Coforge Wins $230M AI Transformation Contract" matched nothing:
# "bags order" and "wins contract" are in the vocabulary, but only as
# adjacent words. Found by scoring the rules against eval/event_labels.json
# (see scripts/eval_events.py), where they were the largest single class of
# miss. Tuned on the 'dev' split only.
#
# The gap is bounded — at most six words — so a verb in one statement cannot
# reach an "order" several phrases later.
_GAP = r"(?:\W+[\w$₹.%'-]+){0,6}?\W+"
# A tighter gap where a loose one reads across statements: "Sensex ends
# higher as TCS signs agreement" is not TCS ending an agreement.
_SHORT_GAP = r"(?:\s+[\w$₹.%:'-]+){0,3}?\s+"
_PARTNERSHIP = r"(?:joint\s+ventures?|jvs?|partnerships?|alliances?|tie-?ups?|collaborations?|mous?|pacts?|agreements?)"
# What a weaker business reports falling, and the ways it falls.
_WEAK_SUBJECT = (
    r"(?:sales|revenues?|net\s+profits?|profits?|earnings|net\s+income|ebitda|"
    r"margins?|shipments|orders|order\s+inflows?|demand)"
)
_WEAK_VERB = (
    r"(?:falls?|fell|fallen|declines?|declined|drops?|dropped|slumps?|slumped|"
    r"plunges?|plunged|slides?|slid|shrinks?|shrank|contracts?|contracted|"
    r"dips?|dipped|tumbles?|tumbled|sinks?|sank|weakens?|weakened|"
    r"slows?|slowed|down|lower)"
)
EVENT_PATTERNS: Dict[str, tuple] = {
    "partnership_end": (
        re.compile(
            r"\b(?:exits?|exited|exiting|quits?|ends|ended|terminates?|terminated|"
            r"suspends?|suspended|"
            r"dissolves?|dissolved|winds?\s+up|wound\s+up|calls?\s+off|called\s+off|"
            r"scraps?|scrapped|cancels?|cancell?ed|pulls?\s+out\s+of|"
            r"pulled\s+out\s+of|walks?\s+away\s+from|walked\s+away\s+from)"
            + _SHORT_GAP
            + _PARTNERSHIP
            + r"\b"
        ),
        # Two companies: "Dixon and Vivo part ways". Not "parts ways", which
        # is mostly an executive leaving.
        re.compile(r"\bpart\s+ways\b"),
        re.compile(
            r"\b"
            + _PARTNERSHIP
            + r"\s+(?:ends|ended|terminated|dissolved|collapses|collapsed|"
            r"falls\s+through|fell\s+through|called\s+off|scrapped)\b"
        ),
    ),
    "business_weakness": (
        # "Q3 sales fall 12%", "net profit declines sharply", "revenue lower".
        re.compile(
            r"\b"
            + _WEAK_SUBJECT
            + r"(?:\s+(?:sharply|steeply|further|marginally|slightly|again))?\s+"
            + _WEAK_VERB
            + r"\b"
        ),
        # "a decline in quarterly revenue"
        re.compile(
            r"\b(?:fall|decline|drop|slump|dip|plunge|slide)\s+in\s+(?:\w+\s+)?"
            + _WEAK_SUBJECT
            + r"\b"
        ),
        # "NCLT admits insolvency plea against ..."
        re.compile(r"\b(?:admits?|admitted)\s+(?:an?\s+)?insolvency\b"),
        # "cuts full-year revenue guidance", "lowers FY27 outlook"
        re.compile(
            r"\b(?:cuts?|lowers?|lowered|slashe?s|slashed|trims?|trimmed|"
            r"reduces?|reduced|withdraws?|withdrew)\s+(?:its\s+)?"
            r"(?:[\w-]+\s+){0,2}?(?:guidance|outlook|forecast)\b"
        ),
    ),
    "tie_up": (
        # "Dixon Technologies and Gemtek Form Optical Transceiver JV": what
        # the venture makes sits between the verb and "JV".
        re.compile(
            r"\b(?:forms?|formed|forming|to form)\s+(?:an?\s+)?"
            r"(?:(?!(?:to|for|with)\b)[\w&₹.-]+\s+){0,3}?(?:jv|joint venture)s?\b"
        ),
        re.compile(r"\bjv with\b"),
        re.compile(r"\b(?:signs?|signed|inks?|inked)\s+(?:an?\s+)?mous?\b"),
        # Headlines call an MoU a pact: "BHEL signs strategic pact with
        # thyssenkrupp nucera", "Dixon Technologies' subsidiary signs pact with
        # Longcheer" were no event at all. Graded announced, as an MoU is.
        re.compile(
            r"\b(?:signs?|signed|inks?|inked)\s+(?:an?\s+)?(?:[\w-]+\s+){0,2}?pacts?\b"
        ),
        # "LTTS and Anthropic Partner to Transform Engineering": a plural
        # subject takes the bare verb, which "partners with" never matches.
        re.compile(r"\band\s+[\w.&' -]{1,40}?\s+partner\s+(?:to|for|on|in)\b"),
    ),
    "acquisition": (
        re.compile(r"\bstake acquisition\b"),
        # A divestment is the same transaction seen from the seller.
        re.compile(r"\b(?:divests?|divested|divestment|stake sale|sells stake)\b"),
    ),
    "order_win": (
        re.compile(
            r"\b(?:wins?|won|bags?|bagged|secures?|secured|lands?|landed|"
            r"receives?|received)" + _GAP + r"(?:orders?|contracts?|bid)\b"
        ),
        # Not "order win from X": there X is the customer. "Defence stock
        # jumps... Order win from BEL" is another company's win.
        re.compile(r"\border win\b(?!\s+from\b)"),
        # How Indian infrastructure, railway and defence awards are filed:
        # "Receipt of LoA from NHAI", "RVNL emerges L1 bidder for...".
        re.compile(
            r"\b(?:receives?|received|receipt of|gets?|bags?)\s+(?:an?\s+)?loa\b"
        ),
        # "Declared L-1 bidder" and "L1 bidder for" too. All of them are
        # graded announced, not completed (_CERTAINTY_PATTERNS).
        re.compile(
            r"\b(?:emerges?|emerged|declared|becomes?|became)\s+(?:as\s+)?(?:the\s+)?"
            r"(?:l[\s-]?1|lowest\s+bidder)\b"
        ),
        re.compile(r"\bl[\s-]?1\s+bidder\b"),
    ),
    "capacity_add": (
        re.compile(
            r"\b(?:inaugurat\w*|opens|opened)"
            + _GAP
            + r"(?:facility|plant|factory|unit)\b"
        ),
        # "Vivo sets up own smartphone plant": the literal "sets up plant"
        # needs the words side by side.
        re.compile(
            r"\b(?:sets?|setting)\s+up" + _GAP + r"(?:facility|plant|factory|unit)\b"
        ),
    ),
    "supply_disruption": (
        # "Corning halts Gorilla Glass production": the same, for a stoppage.
        re.compile(
            r"\b(?:halts?|halted|suspends?|suspended)"
            + _GAP
            + r"(?:production|operations|output|manufacturing)\b"
        ),
    ),
}


def match_event_type(clause_lower: str):
    """``(event_type, phrase)`` for the first type whose vocabulary or
    pattern appears in the clause, else ``(None, None)``.

    The phrase is the matched text itself, so it can be found in the clause
    again later (event_clause relies on that).
    """
    for etype, vocabulary in EVENT_VOCABULARY.items():
        hit = next((v for v in vocabulary if v in clause_lower), None)
        if hit:
            return etype, hit
        for pattern in EVENT_PATTERNS.get(etype, ()):
            m = pattern.search(clause_lower)
            if m:
                return etype, m.group(0)
    return None, None


# How settled the event is. The engine used to record every match as though
# it had happened: "Schneider Electric Announces Intention To Acquire Cognite"
# and "Dixon Tech Up ... on Reports of Govt Approval Likely to Vivo Joint
# Venture" were both filed as completed events, and 16% of a live run's events
# were intentions or rumours read as fact. Order matters — the weakest reading
# that fits wins, so a reported intention is reported, not announced.
CERTAINTY_MARKERS = (
    (
        "reported",
        (
            "reportedly",
            "reports of",
            "report says",
            "sources say",
            "rumour",
            "rumor",
            "speculation",
            "likely to",
            "could ",
            "may ",
            "in talks",
            "exploring",
            "mulls",
            "weighing",
            "considering",
        ),
    ),
    (
        "announced",
        (
            "intention to",
            "intends to",
            "plans to",
            "planning to",
            "proposed",
            "proposes",
            "set to",
            "to acquire",
            "to buy",
            "agreed to",
            "in principle",
            "signs mou",
            "mou with",
            "memorandum of understanding",
            # The lowest bid, not yet the award.
            "lowest bidder",
            "l1 bidder",
            "emerges l1",
            "emerged l1",
            "emerges as l1",
            "emerged as l1",
        ),
    ),
)

# Shapes of the same grades that substrings cannot express. "X and Y sign MoU"
# has the plural verb, which "signs mou" never matched: 11 of the 34 MoUs in
# the October 2026 corpus were graded completed, as firm as a Letter of
# Award. "RVNL emerges L-1 bidder" has the hyphen, which "emerges l1" never
# matched, so a lowest bid written that way became a won order.
_CERTAINTY_PATTERNS = {
    "reported": (
        # Looking for a deal is not one: "AMD CEO says continues to explore
        # foundry partnership with Samsung" was filed as a completed tie-up.
        re.compile(
            r"\bexplor(?:e|es|ed)\s+(?:an?\s+|the\s+)?(?:[\w-]+\s+){0,4}?"
            r"(?:partnerships?|tie-?ups?|alliances?|jvs?|joint\s+ventures?|"
            r"deals?|mergers?|acquisitions?|collaborations?|stake|options)\b"
        ),
        # "Weighs" and "considers" as "weighing" and "considering" are, but
        # only over what follows to the end of the statement: "X weighs stake
        # sale" is a thought, while "LS MnM weighs copper concentrate cuts as
        # shortages squeeze smelter profits" states the shortage as fact. Not
        # "weighs on", which is pressure.
        re.compile(
            r"\b(?:weighs|considers)\b(?!\s+on\b)"
            r"(?![^,;:]*\b(?:as|amid|after|while|despite)\b)"
        ),
    ),
    "announced": (
        # An MoU is an intention whatever verb signs it.
        re.compile(r"\bmous?\b"),
        # A pact signed, as headlines call an MoU.
        re.compile(
            r"\b(?:signs?|signed|inks?|inked)\s+(?:an?\s+)?(?:[\w-]+\s+){0,2}?pacts?\b"
        ),
        # The lowest bid, however written: L1, L-1, L 1.
        re.compile(r"\bl[\s-]?1\s+(?:bidder|bid|position)\b"),
        re.compile(
            r"\b(?:emerges?|emerged|declared|becomes?|became)\s+(?:as\s+)?"
            r"(?:the\s+)?l[\s-]?1\b"
        ),
        # Not there yet: "Dixon-Vivo JV inches close to final approval".
        re.compile(r"\binch(?:es|ed)?\s+clos(?:e|er)\b|\bnears\b|\bnearing\b"),
    ),
}

CERTAINTY_COMPLETED = "completed"
_CERTAINTY_RANK = {"reported": 0, "announced": 1, CERTAINTY_COMPLETED: 2}


def _weaker(stored: Optional[str], seen: str) -> str:
    """The less settled of two grades; ``seen`` when nothing was stored."""
    if stored not in _CERTAINTY_RANK:
        return seen
    return min(stored, seen, key=lambda g: _CERTAINTY_RANK.get(g, 2))


# How binding an event is, in the words policy_impact uses for a measure
# (PR #211): a completed award, order or approval is hard; an MoU, a lowest
# bid or a stated intention is soft; a rumour is reported. Read-throughs and
# graph-routed signals weigh them by STRENGTH_WEIGHT, as the policy balance
# weighs a draft at half a notified rule.
EVENT_STRENGTH = {"completed": "hard", "announced": "soft", "reported": "reported"}
STRENGTH_WEIGHT = {"hard": 1.0, "soft": 0.5, "reported": 0.25}
# What a reader is told about a trigger that is not binding. A read-through
# carries it as ``strength_note``, so the email, the dashboard and Ask say it
# in the same words.
STRENGTH_SAYS = {
    "soft": "not yet binding: an MoU, a lowest bid or an intention",
    "reported": "reported, not confirmed",
}


def event_strength(event: Dict[str, Any]) -> str:
    """``hard`` / ``soft`` / ``reported`` for an event, from its certainty."""
    certainty = event.get("certainty") or classify_certainty(event_clause(event))
    return EVENT_STRENGTH.get(certainty, "hard")


# Clause boundaries. Semicolons and dashes separate independent statements in
# headline style; a comma followed by a market-reaction verb usually does too.
_CLAUSE_RE = re.compile(r"\s*[;—–]\s*|\s+-\s+|\s*\|\s*")

# A negated move is not a move — "denies plans to enter" must classify as
# nothing rather than as an entry. Scoped to a clause, so a denial in one
# statement no longer cancels a genuine event in another.
_DENIALS = (
    "denies",
    "rules out",
    "no plans",
    "refutes",
    "dismisses report",
)
NEGATION_MARKERS = _DENIALS + (
    "calls off",
    "cancels",
    "scraps",
    "shelves",
)

# A scarcity said not to exist: "US Tariff Threat Reprices Copper Without a
# Global Shortage" was a supply disruption, and a copper squeeze on five
# holdings. At most one qualifier between, and never a preposition, so "no end
# to the shortage" and "no relief from shortage" still are one.
_NEGATED_SCARCITY_RE = re.compile(
    r"\b(?:without|no|not|avert(?:s|ed|ing)?|avoid(?:s|ed|ing)?)\s+"
    r"(?:an?\s+|any\s+)?(?:(?!(?:to|of|from|in|for|on|with|the)\b)[\w-]+\s+)?"
    r"(?:shortages?|scarcity|crunch)\b",
    re.IGNORECASE,
)


def without_negated_scarcity(text: str) -> str:
    """The text with any scarcity it says is absent taken out."""
    return _NEGATED_SCARCITY_RE.sub(" ", text or "")


# Spared, not hit: "Nvidia and Broadcom Insulated from US Data Centre Power
# Shortage" was a supply disruption at two demand anchors, and raised risk on
# six electronics and semiconductor holdings. Only the statement that says so
# is skipped, not its whole clause: "Nvidia insulated from chip shortage as
# TSMC halts production" holds TSMC's stoppage, read as a statement of its
# own so that Nvidia is no party to it.
_SPARED = (
    "insulated from",
    "shielded from",
    "immune to",
    "unaffected by",
    "unscathed by",
)
_STATEMENT_RE = re.compile(
    r"\s*,\s*|\s+(?:as|while|but|amid|after|despite|though|although|because|"
    r"since|whereas)\s+",
    re.IGNORECASE,
)


def _statements(clause: str) -> List[str]:
    """A clause as it is read: whole, or split into its statements when one
    of them says someone is spared."""
    if not any(s in clause.lower() for s in _SPARED):
        return [clause]
    return [p for p in _STATEMENT_RE.split(clause) if p.strip()] or [clause]


# Which way an event leans for the sectors whose turf it lands on.
_EVENT_DIRECTION = {
    "partnership_end": "risk",
    "tie_up": "opportunity",
    "acquisition": "opportunity",
    "order_win": "opportunity",
    "capacity_add": "opportunity",
    "supply_disruption": "risk",
    "input_cost_shock": "risk",
    "business_weakness": "risk",
}

_RISK_TYPES = ("supply_disruption", "input_cost_shock")
# About one company, so never a warning on a sector's holdings, by
# vocabulary or by an anchor edge: "smartphone sales fall" is not a supply
# shock for every electronics holding. They reach other holdings only as
# read-throughs along a link in the graph (analysis/read_through.py): a
# partner's news through the partner screen, and a demand anchor's weaker
# business through _anchor_shift. Read-throughs are never graded.
_COMPANY_ONLY_TYPES = ("partnership_end", "business_weakness")
# What an anchor does that changes how much it buys from the sectors its
# edges reach: builds, orders, loses supply, pays more. Its tie-ups and
# purchases are not among them: "TCS and Google partner on an AI centre" is
# not demand for electronics holdings, and who an anchor picks over whom is
# read_through's displacement, not a signal.
_DEMAND_TYPES = ("capacity_add", "order_win") + _RISK_TYPES
_MAX_SIGNALS_PER_SECTOR = 3


def split_clauses(headline: str) -> List[str]:
    """Break a headline into independent statements.

    Falls back to the whole headline when there is nothing to split on, so a
    single-clause headline behaves exactly as before.
    """
    parts = [p.strip() for p in _CLAUSE_RE.split(headline or "") if p and p.strip()]
    return parts or ([headline] if headline else [])


def classify_certainty(text: str) -> str:
    """``reported`` / ``announced`` / ``completed`` for one clause."""
    lower = (text or "").lower()
    for level, markers in CERTAINTY_MARKERS:
        if any(m in lower for m in markers) or any(
            p.search(lower) for p in _CERTAINTY_PATTERNS.get(level, ())
        ):
            return level
    return CERTAINTY_COMPLETED


def first_event_clause(headline: str):
    """``(clause, event_type, phrase)`` for the first clause of a headline that
    holds an event and is not a denial; None when no clause does.

    Within a clause, not across the whole headline: one routinely carries two
    statements ("ITC Hotels to acquire GHK for Rs 155 crore; shares decline
    5%"), and matching across both lets one claim or cancel the other.
    """
    for clause in (s for c in split_clauses(headline) for s in _statements(c)):
        clause_lower = clause.lower()
        if any(s in clause_lower for s in _SPARED):
            continue  # spared, not hit
        hit_type, hit_phrase = match_event_type(clause_lower)
        if hit_type == "supply_disruption":
            # Read again without any scarcity the clause says is absent;
            # whatever else it holds may still count.
            hit_type, hit_phrase = match_event_type(
                without_negated_scarcity(clause_lower)
            )
        if any(neg in clause_lower for neg in NEGATION_MARKERS):
            # A denial; others may still count. Calling off a partnership is
            # not one: there the ending is the news.
            if hit_type == "partnership_end" and not any(
                d in clause_lower for d in _DENIALS
            ):
                return clause, hit_type, hit_phrase
            continue
        if hit_type:
            return clause, hit_type, hit_phrase
    return None


def headline_certainty(headline: str) -> Optional[str]:
    """How settled a headline's event is (reported / announced / completed),
    read from its event clause as classify_headlines reads it; None when it
    holds no event. An L-1 bid is "announced": the award is not yet made."""
    found = first_event_clause(headline)
    return classify_certainty(found[0]) if found else None


# Where an order comes from: "from" and the name that follows, up to the next
# preposition or punctuation. "from BHEL and DEE VEE" keeps both names.
_FROM_PARTY_RE = re.compile(
    r"\bfrom\s+(.+?)(?=\s+(?:for|to|in|at|worth|under|towards|on|with|as|via|"
    r"across|after|amid|over)\b|[,;:(]|$)",
    re.IGNORECASE,
)


def _named_as_customer(clause: str, phrase: str, ticker: str, name: str) -> bool:
    """Is this holding named in an order win only as the one placing it?

    "Ellenbarrie bags Rs. 481-crore BHEL contract" and "Cranex Receives Orders
    Worth Rs. 71.7 mn from BHEL" were both filed as BHEL's order wins. A
    holding named before the win ("BHEL bags ...") won it. One named only
    after it, as what the contract is or where the order comes from, placed
    it. Named after the win in any other way ("Order worth Rs 500 crore for
    RVNL"), it is still read as the winner.
    """
    lower = clause.lower()
    start = lower.find(phrase or "\0")
    # Slices of the clause stand for slices of its lower-cased copy.
    if start < 0 or len(lower) != len(clause):
        return False
    if title_matches_company(clause[:start], ticker, name):
        return False
    # Between the verb and "contract": "bags Rs. 481-crore BHEL contract".
    win = clause[start : start + len(phrase)].split(None, 1)
    if len(win) == 2 and title_matches_company(win[1], ticker, name):
        return True
    return any(
        title_matches_company(m.group(1), ticker, name)
        for m in _FROM_PARTY_RE.finditer(clause[start:])
    )


def clause_actors(
    clause: str, event_type: Optional[str], phrase: Optional[str], holdings
) -> List[str]:
    """The holdings an event's clause names as its parties.

    Named in the clause itself, not merely somewhere in the headline: the
    attribution is relational. An order win's customer is not a party to the
    win (_named_as_customer).
    """
    return [
        ticker
        for ticker, name in holdings
        if title_matches_company(clause, ticker, name)
        and not (
            event_type == "order_win"
            and _named_as_customer(clause, phrase, ticker, name)
        )
    ]


def graph_entities(clause: str, graph: Dict[str, Any]) -> List[str]:
    """Graph entities named in this clause — Google, Apple, Broadcom, Marvell.

    ``actors`` records only watchlist tickers, which is right for direct
    attribution and useless for second-order reasoning: a headline about
    Google tying up with Marvell names nothing we hold, so both names were
    discarded and there was no way to walk the entity graph from the event.
    Recording them is what makes a read-through derivable at all.

    input_cost sources are excluded — they are commodity keywords ("copper",
    "memory chip"), not companies, and read_through matches them separately
    with vocabulary suited to a material rather than to a corporate name.

    Matched with the same word-boundary and person-guard rules as every other
    attribution here, so "Mr Apple" or "Broadcom Institute" cannot enrol an
    entity that is not really the subject. An alias counts as its entity
    ("Taiwan Semiconductor" is TSMC) and is recorded under the canonical name,
    which is the name the edges use.
    """
    from analysis.entity_graph import names_mentioned

    names = sorted(
        {
            str(edge.get("src"))
            for edge in (graph or {}).get("edges", [])
            if edge.get("type") != "input_cost" and edge.get("src")
        }
        | {
            str(edge.get("dst"))
            for edge in (graph or {}).get("edges", [])
            if edge.get("type") in ("competitor", "supplier_customer")
            and edge.get("dst")
            # A scoped competitor edge runs from a rival to a holding, and a
            # holding is an actor, not an outside entity.
            and not (edge.get("type") == "competitor" and edge.get("scope"))
        }
    )
    return names_mentioned(clause, names, graph)


def _counterparties(event_type, clause, actors, holdings):
    """The other side of a tie-up, or None when the question does not apply.

    Only a tie-up has a counterparty in the sense that matters here — a party
    whose later news reads across to ours. None for every other event type,
    kept distinct from [] ("a tie-up, and nobody else could be named") so the
    two are never confused downstream.
    """
    if event_type != "tie_up":
        return None
    from analysis.counterparty import extract_counterparties

    named = set(actors or [])
    return extract_counterparties(
        clause, [(ticker, name) for ticker, name in holdings if ticker in named]
    )


def _evidence_note(event: Dict[str, Any]) -> str:
    """How the alert text states its evidence, in words a reader can check."""
    level = evidence_level(event)
    if level == "confirmed":
        c = event["confirmation"]
        return f"confirmed by {c.get('ticker')}'s {c.get('source')} filing of {c.get('date')}"
    if level == "multi-source":
        return f"reported by {event.get('reports')} outlets"
    return "single report, not yet confirmed"


def classify_headlines(
    data: Dict[str, Any], watchlist: Dict[str, Any], graph: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """Classify every collected headline into typed market events.

    Returns [{headline, event_type, phrase, certainty, domains, actors,
    external, direction, date}] — ``domains`` are watchlist sectors whose
    battleground vocabulary the headline touches (Tier 1); ``actors`` are
    watchlist tickers named in the same clause as the event (direct
    attribution); ``external`` are entity-graph names in that clause, which is
    what second-order read-throughs are derived from; ``certainty`` is how
    settled the event is (reported / announced / completed).
    """
    events: List[Dict[str, Any]] = []
    today = datetime.date.today().isoformat()
    try:
        holdings = [
            (s.get("ticker", ""), s.get("name", ""))
            for stocks in (watchlist or {}).values()
            for s in stocks or []
            if isinstance(s, dict)
        ]
        sources = collect_sources(data, watchlist)
        for headline in collect_headlines(data, watchlist):
            # Classified within its event clause (first_event_clause), so
            # the actors and any negation are that statement's own.
            found = first_event_clause(headline)
            if not found:
                continue
            clause, event_type, phrase = found
            certainty = classify_certainty(clause)
            actors = clause_actors(clause, event_type, phrase, holdings)
            external = graph_entities(clause, graph)
            counterparties = _counterparties(event_type, clause, actors, holdings)

            # Domains stay headline-wide: unlike actors they are topical
            # rather than relational, and Tier 1 routing is deliberately loose.
            domains = battleground_sectors(headline)
            # An event naming a graph entity is kept even when it touches no
            # sector vocabulary and none of our tickers. That is exactly the
            # shape of the events worth reading through — "Google taps Marvell
            # for custom silicon" mentions nothing we hold, and the whole point
            # is to derive what it means for what we do hold. Before this, such
            # a headline was classified and then dropped on this line.
            if not domains and not actors and not external:
                continue  # classified, but touches nothing we track

            # The citation, looked up on the full headline before it is
            # truncated for storage. An event that names a headline but cannot
            # be traced back to the article is an assertion the reader has to
            # take on faith, which is the one thing this pipeline tries never
            # to ask of them. Absent when the feed carried no link — omitted
            # rather than written as "", so "no link" and "" stay distinct.
            citation = sources.get(headline.lower()) or {}

            events.append(
                {
                    "headline": headline[:HEADLINE_KEPT],
                    "event_type": event_type,
                    "phrase": phrase,
                    "certainty": certainty,
                    "domains": domains,
                    "actors": actors,
                    "external": external,
                    **(
                        {"counterparties": counterparties}
                        if counterparties is not None
                        else {}
                    ),
                    "direction": _EVENT_DIRECTION.get(event_type, "opportunity"),
                    # The article's own date, not the run's. Every run
                    # re-reads the accumulated news history, so the run date
                    # re-stamped months-old stories as today's on every run.
                    # Where the feed gives none, the date the headline gives
                    # itself (event_evidence.headline_date).
                    "date": article_date(citation.get("date"))
                    or headline_date(headline, today)
                    or today,
                    "first_seen": today,
                    **(
                        {"link": citation["link"], "source": citation.get("source", "")}
                        if citation.get("link")
                        else {}
                    ),
                }
            )
        if events:
            counts: Dict[str, int] = {}
            for e in events:
                counts[e["event_type"]] = counts.get(e["event_type"], 0) + 1
            log.info(
                f"Event engine: {len(events)} market events classified "
                f"({', '.join(f'{k}={v}' for k, v in sorted(counts.items()))})."
            )
    except Exception as e:
        log.warning(f"Event engine failed safely: {e!r}")
    return events


def event_clause(event: Dict[str, Any]) -> str:
    """The clause the event was classified from — the whole headline if the
    stored phrase is no longer found in any one clause."""
    headline = event.get("headline") or ""
    return next(
        (
            s
            for c in split_clauses(headline)
            for s in _statements(c)
            if event.get("phrase") and event["phrase"] in s.lower()
        ),
        headline,
    )


# Events older than this leave the corpus. Without it the list only ever
# grows, and entries classified by an older version of the engine outlive
# every fix made since.
EVENT_RETENTION_DAYS = 45

# A stored event keeps this much of its headline.
HEADLINE_KEPT = 180

# The most events kept, newest first, once the stale ones have gone.
EVENTS_KEPT = 120


def refresh_merged_events(
    events: List[Dict[str, Any]],
    watchlist: Dict[str, Any],
    today: str = "",
    graph: Dict[str, Any] = None,
    sources: Dict[str, Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Re-derive attribution on the accumulated event list, and drop stale rows.

    Events merge across runs, so a correction to the matcher or the vocabulary
    only ever applies to what is classified *today* — yesterday's mistakes are
    carried forward untouched. That is not hypothetical: after the entity
    boundary fix, three ITC Hotels events stayed attributed to ITC, and since
    per-stock coverage reads these actors directly, they were still showing on
    ITC's card the next day.

    So every merged event is re-attributed with the current rules. An event
    that no longer names anything we track is dropped, which is how those
    three finally disappear. It is read again with the current vocabulary
    too: one it now reads as no event at all ("Nvidia and Broadcom Insulated
    from US Data Centre Power Shortage") is dropped, one it reads as another
    type is retyped ("Amazon suspends partnership" ended one), and every one
    is graded again, so an MoU or lowest bid that older rules filed as
    completed does not keep full weight for its 45 days.

    Then the newest EVENTS_KEPT are kept, by article date. The cap used to be
    applied before this, to the merged list in classification order: a run
    re-reads months of stored agreements and launches, so on 19 Oct old
    articles filled all 120 places, were then dropped here as stale, and the
    day's one global event (classified last) had already been cut. 44 events
    survived, none of them global.
    """
    if not events:
        return []
    refreshed: List[Dict[str, Any]] = []
    try:
        holdings = [
            (s.get("ticker", ""), s.get("name", ""))
            for stocks in (watchlist or {}).values()
            for s in stocks or []
            if isinstance(s, dict)
        ]
        today = today or datetime.date.today().isoformat()
        cutoff = (
            datetime.date.fromisoformat(today)
            - datetime.timedelta(days=EVENT_RETENTION_DAYS)
        ).isoformat()

        dropped_stale = dropped_orphan = reattributed = redated = 0
        dropped_unread = retyped = 0
        for event in events:
            if not isinstance(event, dict):
                continue
            # Stored events carry the run date they were last re-classified
            # on; the article's own date replaces it wherever the feed still
            # has the article. Done before the retention check, so a story
            # that was only ever "today" by accident now ages out properly.
            published = article_date(
                ((sources or {}).get(str(event.get("headline", "")).lower()) or {}).get(
                    "date"
                )
            ) or headline_date(event.get("headline"), today)
            if published and published != event.get("date"):
                event.setdefault("first_seen", event.get("date"))
                event["date"] = published
                redated += 1
            if str(event.get("date", "")) < cutoff:
                dropped_stale += 1
                continue

            if event.get("reader") == "llm":
                # The LLM's parties, not the matcher's reading of the whole
                # headline — re-deriving would attribute every holding the
                # headline mentions. Only pruned to what is still held.
                held = {str(t).upper() for t, _ in holdings}
                event["actors"] = [a for a in event.get("actors") or [] if a in held]
                if event["actors"]:
                    refreshed.append(event)
                else:
                    dropped_orphan += 1
                continue
            # Read again, as classify_headlines would read it today — unless
            # the headline was cut when it was stored: what was cut (the
            # phrase, a "reportedly", a denial) may be what decided it, so the
            # stored reading stands.
            headline = str(event.get("headline") or "")
            whole = len(headline) < HEADLINE_KEPT
            found = first_event_clause(headline) if whole else None
            if found:
                clause, etype, phrase = found
                if etype != event.get("event_type"):
                    event["direction"] = _EVENT_DIRECTION.get(etype, "opportunity")
                    retyped += 1
                event["event_type"], event["phrase"] = etype, phrase
                event["certainty"] = classify_certainty(clause)
            elif whole:
                dropped_unread += 1
                continue
            else:
                clause = event_clause(event)
                # Graded from what is left, but never firmer than it was:
                # the weakest reading wins, so the cut part could only have
                # weakened it. An MoU an older version filed as completed is
                # soft; a "reportedly" past the cut stays reported.
                event["certainty"] = _weaker(
                    event.get("certainty"), classify_certainty(clause)
                )
            actors = clause_actors(
                clause, event.get("event_type"), event.get("phrase"), holdings
            )
            # Re-derived for the same reason actors are: an event carried over
            # from before the graph knew about Marvell would otherwise keep an
            # empty external list for its whole 45-day retention, and the fix
            # that taught the graph about Marvell would never reach it.
            external = (
                graph_entities(clause, graph)
                if graph
                else (event.get("external") or [])
            )

            if actors != (event.get("actors") or []):
                reattributed += 1
            if not actors and not (event.get("domains") or []) and not external:
                dropped_orphan += 1
                continue

            event["actors"] = actors
            event["external"] = external
            # Re-derived like actors, so the 45 days of tie-ups already in the
            # corpus gain their counterparty on the first run after this
            # shipped rather than only the ones classified from then on.
            counterparties = _counterparties(
                event.get("event_type"), clause, actors, holdings
            )
            if counterparties is None:
                event.pop("counterparties", None)
            else:
                event["counterparties"] = counterparties
            refreshed.append(event)

        # A stored copy retyped to what today's run read the same headline as
        # is that event twice; the first is kept, as the merge keeps it.
        seen = set()
        unique = []
        for event in refreshed:
            key = (event.get("headline"), event.get("event_type"))
            if key not in seen:
                seen.add(key)
                unique.append(event)
        refreshed = unique

        if any(
            (dropped_stale, dropped_orphan, dropped_unread, reattributed)
            + (redated, retyped)
        ):
            log.info(
                f"Event corpus refresh: {reattributed} re-attributed, "
                f"{redated} re-dated to the article's date, "
                f"{retyped} retyped, "
                f"{dropped_unread} no longer read as an event, "
                f"{dropped_orphan} no longer touch the watchlist, "
                f"{dropped_stale} past {EVENT_RETENTION_DAYS}d retention."
            )
        # Stable, so events of one day keep their order.
        refreshed.sort(key=lambda e: str(e.get("date", "")), reverse=True)
    except Exception as e:  # noqa: BLE001 - housekeeping must not break a run
        log.warning(f"Event corpus refresh failed safely: {e!r}")
        return events[:EVENTS_KEPT]
    return refreshed[:EVENTS_KEPT]


def _financials_by_ticker(watchlist: Dict[str, Any]) -> Dict[str, Any]:
    from models.core import CompanyFinancials

    fins: Dict[str, Any] = {}
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        for stock in stocks or []:
            if not isinstance(stock, dict) or not stock.get("ticker"):
                continue
            sc = stock.get("screener")
            if isinstance(sc, dict):
                try:
                    fins[str(stock["ticker"]).upper()] = CompanyFinancials(**sc)
                except Exception:
                    continue
    return fins


def annotate_event_materiality(
    events: List[Dict[str, Any]], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """How big each event is, against the holding it happened to.

    analysis/materiality.py made this argument for scoring and for alerts and
    was never applied here, so "bags orders worth ₹94 crore" and "₹15,000
    crore acquisition" reached the event list as indistinguishable rows. Two
    fields, both ABSENT rather than null when nothing could be measured, so
    "not sized" never reads as "sized at zero":

      amount_cr     the figure, in crore, once the materiality guards have
                    agreed it belongs to one company — not a sector budget, a
                    share-price move or a joint venture's capital
      materiality   {TICKER: {pct_of_revenue, band}} per actor with revenue

    Measured on the event's own clause, not the whole headline. "X wins Rs
    500 crore order; stock rallies 5%" is two statements, and the price-move
    guard in the second would otherwise veto the order in the first — the
    same clause discipline the classifier already applies.

    Recomputed on every run, like attribution, because revenue moves and the
    guards get fixed. Never raises.
    """
    from analysis import materiality

    sized = 0
    try:
        fins = _financials_by_ticker(watchlist)
        for event in events or []:
            if not isinstance(event, dict):
                continue
            event.pop("amount_cr", None)
            event.pop("materiality", None)

            clause = event_clause(event)
            etype = event.get("event_type") or ""
            if not materiality.is_sized_event(etype, clause):
                continue
            amount = materiality.extract_amount_cr(clause)
            if amount is None:
                continue
            event["amount_cr"] = round(amount, 2)

            by_holding = {}
            for ticker in event.get("actors") or []:
                verdict = materiality.assess(
                    clause, etype, fins.get(str(ticker).upper())
                )
                if verdict.get("pct_of_revenue") is None:
                    continue
                by_holding[str(ticker).upper()] = {
                    "pct_of_revenue": verdict["pct_of_revenue"],
                    "band": verdict["band"],
                }
            if by_holding:
                event["materiality"] = by_holding
                sized += 1

        amounts = sum(
            1 for e in events or [] if isinstance(e, dict) and "amount_cr" in e
        )
        log.info(
            f"Event materiality: {amounts} event(s) carry an attributable amount; "
            f"{sized} sized against a holding's revenue."
        )
    except Exception as e:  # noqa: BLE001 - an enrichment must never break a run
        log.warning(f"Event materiality failed safely: {e!r}")
    return events


def compute_supply_stress(
    events: List[Dict[str, Any]], graph: Dict[str, Any], window_days: int = 14
) -> Dict[str, int]:
    """Rolling count of supply-side events per sector — the forward-looking
    counterpart of the (lagging) reported-OPM margin ladder. Domains come
    from Tier-1 vocabulary plus the graph's input_cost edges (a headline
    naming a tracked input routes to the sectors exposed to it).

    An input is named as a word, not a substring — "RAM" was found in
    "programme" — not where it only says who uses something else
    ("semiconductor manufacturing"), and not as a kind its edge rules out;
    read_through.edge_input_named decides, as it does for read-throughs.
    An edge that ends at one holding (coal → ADANIPOWER) adds nothing here:
    stress is per sector, and the edge says the rest of the sector is not
    exposed."""
    from analysis.read_through import edge_input_named

    stress: Dict[str, int] = {}
    try:
        cutoff = (
            datetime.date.today() - datetime.timedelta(days=window_days)
        ).isoformat()
        input_edges = [
            e for e in (graph or {}).get("edges", []) if e.get("type") == "input_cost"
        ]
        for event in events or []:
            if not isinstance(event, dict):
                continue
            if event.get("event_type") not in _RISK_TYPES:
                continue
            # A rumoured disruption is not a disruption. Counting one toward
            # a sector's stress score would let speculation trip a threshold
            # built to measure things that actually happened.
            if event.get("certainty") == "reported":
                continue
            if event.get("reader") == "llm":
                continue  # unverified; see analysis/llm_reader.reconcile
            if str(event.get("date", "")) < cutoff:
                continue
            sectors = set(event.get("domains") or [])
            headline = str(event.get("headline", ""))
            for edge in input_edges:
                if edge_input_named(headline, edge):
                    sectors.add(edge.get("dst"))
            for sector in sectors:
                if sector in SECTOR_METADATA:
                    stress[sector] = stress.get(sector, 0) + 1
        if stress:
            worst = max(stress.items(), key=lambda kv: kv[1])
            log.info(
                f"Supply-chain stress ({window_days}d window): "
                f"{len(stress)} sector(s) touched; highest {worst[0]}={worst[1]}."
            )
    except Exception as e:
        log.warning(f"Supply-stress computation failed safely: {e!r}")
    return stress


# Stress level (events in window) at which a forward margin warning fires.
_STRESS_WARN_AT = 2


def market_event_signals(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Early-warning signals from classified events, two-tier routed.

    - Direct (actor is a holding): "Corporate Move" info signal on it.
    - Tier 2 (graph anchor edge): "Ecosystem Signal" naming the path.
    - Tier 1 (domain only): supply-side risks hit every holding in the
      exposed sector; positive ecosystem events surface at Low severity.
    - Sustained supply stress (rolling window) escalates to a forward
      "Supply Stress" warning — the leading pair of Margin Compression.
    """
    from analysis.entity_graph import load_entity_graph, match_anchor_edges

    alerts: List[Dict[str, Any]] = []
    try:
        events = data.get("market_events") or []
        graph = load_entity_graph()
        names = {}
        sector_of: Dict[str, str] = {}
        by_sector: Dict[str, list] = {}
        for sector, stocks in (watchlist or {}).items():
            for s in stocks or []:
                if isinstance(s, dict) and s.get("ticker"):
                    names[s["ticker"]] = s.get("name")
                    sector_of.setdefault(s["ticker"], sector)
                    by_sector.setdefault(sector, []).append(s["ticker"])

        emitted_per_sector: Dict[str, int] = {}

        def sector_label(sector):
            return SECTOR_METADATA.get(sector, {}).get("label", sector)

        for event in events:
            if not isinstance(event, dict):
                continue

            # External-only events are read-through material, not warning
            # material. They exist in the corpus because a headline naming a
            # graph entity and nothing else is now kept, which is what makes a
            # second-order chain derivable — but the anchor matching below
            # would turn a Google/Marvell tie-up into Ecosystem Signals on
            # every held sector, and that is exactly the hypothesis-into-
            # evidence leak read_through.py exists to avoid. Before those
            # events were kept they could not reach here at all; skipping them
            # restores that boundary rather than inventing a new one.
            if not (event.get("actors") or event.get("domains")):
                continue
            # Found only by the LLM reader: shown, never graded as evidence.
            if event.get("reader") == "llm":
                continue

            headline = event.get("headline", "")
            etype = event.get("event_type", "event")

            # Direct attribution: a holding named in the headline. The
            # certainty qualifier travels with the signal, so a rumour is
            # never read as a done deal.
            certainty = event.get("certainty") or ""
            qualifier = (
                f" ({certainty})" if certainty and certainty != "completed" else ""
            )
            # A holding's own weaker quarter is graded from its filed numbers
            # (Screener's margin and revenue warnings). The headline stays its
            # news; warning on it as well would count the same quarter twice.
            attributed = (
                [] if etype == "business_weakness" else event.get("actors") or []
            )
            for ticker in attributed:
                alerts.append(
                    {
                        "ticker": ticker,
                        "name": names.get(ticker, ticker),
                        # Its own sector, not "—": the email groups "sectors
                        # moving" by this field and printed "— (6)".
                        "sector": sector_label(sector_of.get(ticker, "")) or "—",
                        "severity": "Low",
                        "direction": event.get("direction", "opportunity"),
                        "category": "Corporate Move",
                        "signal": (
                            f"{etype.replace('_', ' ').title()}{qualifier}: "
                            f"“{headline}” ({_evidence_note(event)})"
                        ),
                        # The clause, kept apart from the prose, so the
                        # order-materiality pass sizes this alert by the same
                        # rule as every other headline-backed one. Without it a
                        # Corporate Move stayed Low whatever the deal was
                        # worth: that pass skips alerts with no source.
                        #
                        # Sized, and so escalated, only when the story is
                        # corroborated: the holding filed it with the
                        # exchange, or more than one outlet reported it. A
                        # single report can still be wrong about the amount
                        # or the company, and escalation is the one place a
                        # wrong number reaches the top of the email. Never
                        # for a reported (rumoured) deal.
                        **(
                            {
                                "source_headlines": [
                                    {"title": event_clause(event), "kind": etype}
                                ]
                            }
                            if certainty != "reported"
                            and evidence_level(event) != "single report"
                            else {}
                        ),
                        "evidence": evidence_level(event),
                        # Weighs its size when the alert is escalated: a
                        # lowest bid is not yet the award.
                        "strength": event_strength(event),
                    }
                )

            # Tier 2: anchor edges (typed relationships from the graph).
            # Never back to a holding the headline already names: direct
            # attribution above has that event, and "Syrma and Elemaster open
            # a plant" read again down the Elemaster → Syrma partner edge
            # would count it twice. The same rule as read_through's partner
            # exposure.
            #
            # Not for a partner's news: whether that is good or bad for the
            # holding is a judgement (read_through.screen_partner_news), and
            # passing the partner's own direction along read Vivo opening its
            # own plant as good news for Dixon. Nor for news about one
            # company's own fortunes, which only a named link carries.
            named_here = set(event.get("actors") or [])
            # Only what moves an anchor's demand or supply, and never a
            # rumour: a hypothesis carried down an edge onto holdings that
            # are not named is a hypothesis about a hypothesis.
            strength = event_strength(event)
            anchor_edges = (
                []
                if etype not in _DEMAND_TYPES or strength == "reported"
                else [
                    e
                    for e in match_anchor_edges(headline, graph)
                    if e.get("type") == "anchor_demand"
                ]
            )
            for edge in anchor_edges:
                dst = edge.get("dst")
                dst_tickers = [dst] if dst in names else by_sector.get(dst, [])
                dst_tickers = [t for t in dst_tickers if t not in named_here]
                for ticker in dst_tickers[:_MAX_SIGNALS_PER_SECTOR]:
                    alerts.append(
                        {
                            "ticker": ticker,
                            "name": names.get(ticker, ticker),
                            "sector": sector_label(dst) if dst not in names else "—",
                            "severity": "Low",
                            "direction": event.get("direction", "opportunity"),
                            "category": "Ecosystem Signal",
                            "signal": (
                                f"{edge.get('src')} → {edge.get('type')} edge"
                                f"{qualifier}: “{headline}”"
                            ),
                            "strength": strength,
                        }
                    )

            # Tier 1: supply-side risks propagate to every exposed sector.
            if etype in _RISK_TYPES:
                for sector in event.get("domains") or []:
                    if emitted_per_sector.get(sector, 0) >= _MAX_SIGNALS_PER_SECTOR:
                        continue
                    emitted_per_sector[sector] = emitted_per_sector.get(sector, 0) + 1
                    for ticker in by_sector.get(sector, []):
                        alerts.append(
                            {
                                "ticker": ticker,
                                "name": names.get(ticker, ticker),
                                "sector": sector_label(sector),
                                "severity": "Medium",
                                "direction": "risk",
                                "category": "Supply Chain",
                                "signal": f"Sector input exposure: “{headline}”",
                            }
                        )

        # Forward margin watch on sustained stress.
        for sector, count in (data.get("supply_stress") or {}).items():
            if count >= _STRESS_WARN_AT:
                for ticker in by_sector.get(sector, []):
                    alerts.append(
                        {
                            "ticker": ticker,
                            "name": names.get(ticker, ticker),
                            "sector": sector_label(sector),
                            "severity": "Medium",
                            "direction": "risk",
                            "category": "Supply Stress (Forward)",
                            "signal": (
                                f"{count} supply-side events touched this sector "
                                f"in 14 days — margin pressure may be building "
                                f"before it shows in reported OPM."
                            ),
                        }
                    )
    except Exception as e:
        log.warning(f"Market-event signals failed safely: {e!r}")
    return alerts
