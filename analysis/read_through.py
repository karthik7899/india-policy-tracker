"""Second-order read-throughs: what an event about someone else means for us.

The pipeline was good at first-order attribution — a headline naming HAL
becomes a HAL signal — and blind to everything else. But the events that move
a holding most often never name it. Two shapes recur:

  Displacement.  Google announces a custom-silicon partnership with Marvell.
  Broadcom falls, because Broadcom is the incumbent on Google's TPU work and
  that relationship now looks less secure. Nothing in the headline names
  Broadcom, let alone anything we hold — but our semiconductors_equipment
  exposure tracks Broadcom's ecosystem, so the news is ours to read.

  Pass-through.  AI buyers absorb memory supply, DRAM goes scarce, device
  makers pay more until a new entrant fills the gap. Every EMS holding that
  buys memory carries that cost before it carries the recovery. Again the
  headline names none of them.

Both are walks over the entity graph. The graph already carried the demand
anchors; supplier_customer and competitor were declared and empty, which is
why only the first hop was ever possible.

WHAT THIS IS NOT. A read-through is a hypothesis, not a finding. It says "if
this relationship holds, this is the direction", and it always shows the chain
it walked so a reader can reject it in one glance. That is why:

  * every result carries its `chain`, in order, in plain words;
  * results are kept out of scoring, thesis health and the early-warning
    engine entirely. Those grade evidence. A chain of three curated edges and
    a keyword is not evidence, and letting it move a thesis would quietly
    convert speculation into a number nobody can argue with;
  * `confidence` is stated, and reflects the weakest link in the chain rather
    than the strongest.

Conservative by construction. A false read-through — telling someone their
holding is threatened when it is not — costs more trust than a miss costs
information, because the miss is invisible and the false alarm is not.

TRANSMISSION AND STRENGTH. Each result says how the news travels, whichever
way it pushes (its ``direction``):

  * demand_pull — a customer or demand anchor buys more or less from the
    holdings it reaches (anchor_pull, anchor_shift, most partner news);
  * competitive_threat — a rival, or a customer's choice of one, presses on
    share or margin (displacement, rival_move, a partner working with a
    rival);
  * input_shock — something the holdings buy gets dearer or cheaper
    (input_squeeze).

And how binding the triggering event is: ``strength`` is hard (a completed
award, order or approval), soft (an MoU, a lowest bid, an intention) or
reported (a rumour), and ``weight`` is that strength's multiplier
(event_engine.STRENGTH_WEIGHT) times the weakest link's. Results are ranked
by it, so a lowest bid never outranks the Letter of Award it may become.
"""

import datetime
import re
from typing import Any, Dict, List

from logger import log

# How many days of events a read-through may be drawn from. Shorter than the
# 45-day event retention: a second-order implication is a statement about
# what the market has not yet absorbed, and a three-week-old tie-up has been
# absorbed.
WINDOW_DAYS = 10

# Event types where one party gaining implies another party losing. A
# capacity_add or a supply_disruption is not a displacement — nobody is picked
# over anybody — so they never produce this mechanism.
_DISPLACEMENT_TYPES = ("tie_up", "order_win", "acquisition")

# The chain is read by a person, so it is written as English rather than
# assembled from the matched phrase — interpolating that gave "Google
# partnership Marvell", which states the relationship without naming it.
_DISPLACEMENT_VERB = {
    "tie_up": "tied up with",
    "order_win": "awarded work to",
    "acquisition": "moved to acquire",
}

# Vocabulary that makes an input scarcer or dearer, and the vocabulary that
# does the opposite. Both directions matter: a glut is as real a read-through
# as a shortage, and reporting only the bad news would make the feature a
# pessimism generator rather than a signal.
_SQUEEZE_MARKERS = (
    "shortage",
    "scarcity",
    "scarce",
    "supply crunch",
    "tight supply",
    "supply tightness",
    "constrained",
    "rationing",
    # "allocation" alone is not a supply word. "capital allocation" is
    # ordinary finance writing, and it turned a Morgan Stanley note on
    # Reliance into a risk flag against ten sectors at once. Kept only in the
    # phrase that actually means scarcity.
    "on allocation",
    "supply allocation",
    "price hike",
    "price rise",
    "price increase",
    "higher price",
    "prices rise",
    "prices surge",
    "prices jump",
    "costlier",
    "dearer",
    "sold out",
)
_EASING_MARKERS = (
    "glut",
    "oversupply",
    "supply glut",
    "price cut",
    "price fall",
    "prices fall",
    "prices drop",
    "cheaper",
    "capacity comes online",
    "eases",
    "easing",
)
# Duty on what is bought in moves its price the same way for every buyer
# here: "Centre Waives Cotton Import Duty" made cotton cheaper for every
# textile holding, and matched neither list. A change, not a mention:
# "importers challenge anti-dumping duty" reports no new cost. The verb
# governs the duty, a few words at most and no clause between ("cuts jobs as
# duty hike bites" cut no duty). Export duties and bans are left out: China
# curbing rare earths makes them scarcer here, India curbing sugar exports
# makes sugar cheaper here, and a headline rarely says which it is.
_DUTY = r"(?<!export\s)\bdut(?:y|ies)\b"
_DUTY_GAP = r"\s+(?:(?!(?:as|amid|after|while|but|and|despite)\b)[\w%&₹.-]+\s+){0,3}?"
_DUTY_SQUEEZE_RE = re.compile(
    r"\b(?:hikes?|hiked|raises?|raised|imposes?|imposed|increases?|increased|"
    r"levies|levied|slaps?|slapped)"
    + _DUTY_GAP
    + _DUTY
    + r"|"
    + _DUTY
    + r"\s+(?:hikes?|hiked|raised|imposed|increased|levied)\b",
    re.IGNORECASE,
)
_DUTY_EASING_RE = re.compile(
    r"\b(?:waives?|waived|cuts?|slashe?s|slashed|removes?|removed|scraps?|"
    r"scrapped|exempts?|exempted|lowers?|lowered)"
    + _DUTY_GAP
    + _DUTY
    + r"|"
    + _DUTY
    + r"\s+(?:cuts?|waived|slashed|removed|scrapped|lowered)\b"
    + r"|\bduty[\s-]free\b",
    re.IGNORECASE,
)
# A change said not to happen is none: "Centre will not impose import duty on
# copper". A hedged one ("may impose") is graded reported, like any rumour.
_DUTY_DENIED_RE = re.compile(
    r"\b(?:not|no|never|won't|unlikely\s+to|rules?\s+out|ruled\s+out|denies|"
    r"denied|refuses?\s+to|declines?\s+to)\s+(?:[\w-]+\s+){0,2}$",
    re.IGNORECASE,
)


def _duty_change(pattern, text):
    """Does the text report this duty change, rather than deny it?"""
    return any(
        not _DUTY_DENIED_RE.search(text[: m.start()]) for m in pattern.finditer(text)
    )


# A material named only to say who uses something else is not the thing in
# short supply. "Helium, key for semiconductor manufacturing, faces shortage"
# and "semiconductor skills shortage" both raised input risk on ten holdings,
# as though chips were scarce. Read off the word that follows the material.
_USED_BY = {
    "manufacturing", "manufacturer", "manufacturers", "maker", "makers",
    "making", "industry", "industries", "sector", "skills", "skill", "labour",
    "labor", "talent", "workforce", "workers", "worker", "engineers", "jobs",
    "design", "designers", "stocks", "stock", "shares", "companies",
    "company", "firms", "firm", "ecosystem", "mission", "policy", "plant",
    "plants", "fab", "fabs", "factory", "factories", "hub", "park",
    "packaging", "startup", "startups", "giant", "giants", "major", "majors",
    "estates", "estate",
}  # fmt: skip
# ...or the word before it: "blue-chip stocks" are not chips.
_NOT_AFTER = {"blue"}

# A chain is only as strong as its weakest link.
_CONFIDENCE_ORDER = {"curated": 2, "harvested": 1}
_LINK_WEIGHT = {"curated": 1.0, "harvested": 0.5}

# How each mechanism transmits; partner news decides per verdict.
_TRANSMISSION = {
    "displacement": "competitive_threat",
    "rival_move": "competitive_threat",
    "input_squeeze": "input_shock",
    "anchor_shift": "demand_pull",
    "anchor_pull": "demand_pull",
}
TRANSMISSIONS = ("demand_pull", "competitive_threat", "input_shock")

_MATERIAL_RE_CACHE: Dict[str, Any] = {}


def material_in(text, material):
    """Is this material named in the text?

    A material is not a company, and matching it with the company matcher was
    wrong in both directions.

    It missed real ones. That matcher guards a single-token match against a
    following capitalised word, so that "ITC Hotels" is not read as ITC — good
    for company names, wrong for materials, because "DRAM Inventory Falls" is
    still about DRAM. A live headline reading "HBM4 Shortage: DRAM Inventory
    Falls Below 10 Days" produced nothing at all, while the same story phrased
    "RAM shortage" matched only because the next word happened to be lower
    case.

    So: a plain word-boundary match, case-insensitive, with one addition —
    an optional trailing generation number, because HBM4 is HBM and DDR5 is
    DDR. Digits only, so "RAM" still cannot match "RAMP" or "Gurugram" and
    "steel" cannot match "Steelcase". A plural counts: "Memory Chips" and
    "PCBs" are the material.
    """
    pattern = _material_re(material)
    return bool(pattern and pattern.search(str(text or "")))


def _material_re(material):
    if not material:
        return None
    pattern = _MATERIAL_RE_CACHE.get(material)
    if pattern is None:
        pattern = re.compile(
            rf"\b{re.escape(str(material))}(?:\d+|e?s)?\b", re.IGNORECASE
        )
        _MATERIAL_RE_CACHE[material] = pattern
    return pattern


def input_named(text, material):
    """Is the text about this input itself — not naming it only to say who
    uses something else ("semiconductor manufacturing", "chip makers") or as
    part of another word ("blue-chip")?"""
    pattern = _material_re(material)
    if pattern is None:
        return False
    text = str(text or "")
    for m in pattern.finditer(text):
        after = re.match(r"[\s-]+([A-Za-z]+)", text[m.end() :])
        before = re.search(r"([A-Za-z]+)[\s-]+$", text[: m.start()])
        if after and after.group(1).lower() in _USED_BY:
            continue
        if before and before.group(1).lower() in _NOT_AFTER:
            continue
        return True
    return False


def edge_input_named(text, edge):
    """Does the text name this input_cost edge's input, in a sense the edge
    covers? An edge's ``not_scope`` lists the kinds it does not: the EMS
    holdings buy mature-node parts, so "China's AI Chip Supply Shortage" is
    not a chip squeeze on them."""
    if not input_named(text, str(edge.get("src", ""))):
        return False
    return not any(
        material_in(text, str(t)) for t in edge.get("not_scope") or [] if str(t)
    )


def _edges(graph, etype):
    return [e for e in (graph or {}).get("edges", []) if e.get("type") == etype]


def _same(a, b):
    return str(a or "").strip().lower() == str(b or "").strip().lower()


def _weakest(*edges):
    """The confidence of a chain: its least well-evidenced edge."""
    ranks = [
        _CONFIDENCE_ORDER.get(str(e.get("evidence", "")).lower(), 1) for e in edges if e
    ]
    if not ranks:
        return "harvested"
    return "curated" if min(ranks) >= 2 else "harvested"


def _sector_holdings(watchlist, sector):
    return [
        s.get("ticker")
        for s in (watchlist or {}).get(sector, []) or []
        if isinstance(s, dict) and s.get("ticker")
    ]


def _recent(events, window_days, today):
    cutoff = (
        datetime.date.fromisoformat(today) - datetime.timedelta(days=window_days)
    ).isoformat()
    # An LLM-only event is unverified, and a read-through built on it would be
    # a hypothesis resting on a hypothesis.
    return [
        e
        for e in events or []
        if isinstance(e, dict)
        and str(e.get("date", "")) >= cutoff
        and e.get("reader") != "llm"
    ]


def _flag(
    event,
    mechanism,
    direction,
    sector,
    watchlist,
    chain,
    confidence,
    note,
    tickers=None,
    transmission=None,
):
    # A sector-level chain lands on every holding in the sector; a chain that
    # ends at one company (a partner edge, or an edge whose destination is a
    # holding: coal → ADANIPOWER) lands on that company only, and widening it
    # to the sector would assert exposure nobody has shown.
    held = _holding_sectors(watchlist)
    if not tickers and str(sector).upper() in held:
        tickers = [str(sector).upper()]
        sector = held[str(sector).upper()]
    tickers = tickers or _sector_holdings(watchlist, sector)
    if not tickers:
        # Nothing held in the sector this chain lands on. The reasoning may be
        # perfectly sound and is still not actionable here, and reporting it
        # would be noise dressed as insight.
        return None
    from analysis.event_engine import STRENGTH_SAYS, STRENGTH_WEIGHT, event_strength

    strength = event_strength(event)
    return {
        "trigger": str(event.get("headline", ""))[:180],
        "date": event.get("date", ""),
        "mechanism": mechanism,
        "transmission": transmission or _TRANSMISSION.get(mechanism, "demand_pull"),
        "direction": direction,
        "sector": sector,
        "tickers": sorted(tickers),
        "chain": chain,
        "confidence": confidence,
        "certainty": event.get("certainty", ""),
        "strength": strength,
        "strength_note": STRENGTH_SAYS.get(strength, ""),
        "weight": round(
            STRENGTH_WEIGHT.get(strength, 1.0) * _LINK_WEIGHT.get(confidence, 0.5), 3
        ),
        "note": note,
    }


def _displacement(event, graph, watchlist):
    """Our anchor just picked a rival of a supplier we are exposed to.

    Google (anchor for our electronics sector) ties up with Marvell; Marvell
    competes with Broadcom; Broadcom sells to Google and anchors our
    semiconductor-equipment exposure. The loser is the incumbent, and the
    sector that tracks the incumbent is the one that reads across.
    """
    out = []
    named = event.get("external") or []
    if len(named) < 2 or event.get("event_type") not in _DISPLACEMENT_TYPES:
        return out

    supplier_edges = _edges(graph, "supplier_customer")
    competitor_edges = _edges(graph, "competitor")
    anchor_edges = _edges(graph, "anchor_demand")

    for customer in named:
        for challenger in named:
            if _same(customer, challenger):
                continue
            # Who currently sells to this customer?
            for supply in supplier_edges:
                if not _same(supply.get("dst"), customer):
                    continue
                incumbent = supply.get("src")
                if _same(incumbent, challenger) or _same(incumbent, customer):
                    continue
                # Is the newly-chosen party a rival of that incumbent? The
                # pair is checked both ways because competition is symmetric
                # and the graph stores it once.
                rivalry = next(
                    (
                        c
                        for c in competitor_edges
                        if (
                            _same(c.get("src"), challenger)
                            and _same(c.get("dst"), incumbent)
                        )
                        or (
                            _same(c.get("src"), incumbent)
                            and _same(c.get("dst"), challenger)
                        )
                    ),
                    None,
                )
                if not rivalry:
                    continue
                # Which of our sectors tracks the incumbent?
                for anchor in anchor_edges:
                    if not _same(anchor.get("src"), incumbent):
                        continue
                    sector = anchor.get("dst")
                    verb = _DISPLACEMENT_VERB.get(
                        event.get("event_type"), "tied up with"
                    )
                    chain = [
                        f"{customer} {verb} {challenger}",
                        f"{challenger} competes with {incumbent}"
                        + (f" ({rivalry['note']})" if rivalry.get("note") else ""),
                        f"{incumbent} supplies {customer}"
                        + (f" ({supply['note']})" if supply.get("note") else ""),
                        f"our {sector.replace('_', ' ')} holdings track {incumbent}"
                        + (f" ({anchor['note']})" if anchor.get("note") else ""),
                    ]
                    flag = _flag(
                        event,
                        "displacement",
                        "risk",
                        sector,
                        watchlist,
                        chain,
                        _weakest(supply, rivalry, anchor),
                        f"{incumbent}'s position at {customer} looks less secure, "
                        f"which reads across to what we hold here.",
                    )
                    if flag:
                        out.append(flag)
    return out


def _input_squeeze(event, graph, watchlist):
    """A tracked input got scarcer or dearer — or the reverse.

    The cost lands on whoever buys the part, which is never the company in the
    headline. "iPhone priced higher on RAM shortage" is a statement about
    every device assembler's bill of materials, ours included.
    """
    from analysis.event_engine import without_negated_scarcity

    out = []
    headline = str(event.get("headline", ""))
    # "Reprices Copper Without a Global Shortage" reports no shortage. One
    # company spared from a shortage still reports it, and every other buyer
    # of the input still pays.
    lower = without_negated_scarcity(headline).lower()

    squeezing = any(m in lower for m in _SQUEEZE_MARKERS) or _duty_change(
        _DUTY_SQUEEZE_RE, headline
    )
    easing = any(m in lower for m in _EASING_MARKERS) or _duty_change(
        _DUTY_EASING_RE, headline
    )
    # Both at once is a headline describing a turn ("shortage eases"), which
    # is an easing. Neither means this is not a price story at all.
    if easing:
        direction, verb = "opportunity", "cheaper or more available"
    elif squeezing:
        direction, verb = "risk", "scarcer or dearer"
    else:
        return out

    held = _holding_sectors(watchlist)
    # Word-boundary matched: "RAM" must not fire on "programme" or
    # "Gurugram", and "memory" must not fire on "memorial". And named as the
    # thing in short supply, not as who uses it (input_named), and not as a
    # kind the edge rules out (edge_input_named).
    named = [e for e in _edges(graph, "input_cost") if edge_input_named(headline, e)]
    # A holding whose own sector buys the same input is already in that
    # sector's row: Diamond Power, moved into data-centre support, came out
    # twice for every copper headline.
    sector_rows = {
        (str(e.get("src", "")).lower(), e.get("dst"))
        for e in named
        if str(e.get("dst") or "").upper() not in held
    }
    seen = set()
    for edge in named:
        material = str(edge.get("src", ""))
        sector = edge.get("dst")
        own = str(sector or "").upper()
        if own in held and (material.lower(), held[own]) in sector_rows:
            continue
        if (material.lower(), sector) in seen:
            continue
        seen.add((material.lower(), sector))
        buyer = (
            str(sector).upper()
            if str(sector).upper() in held
            else f"our {str(sector).replace('_', ' ')} holdings"
        )
        chain = [
            f"headline reports {material} {verb}",
            f"{material} is an input to {buyer}"
            + (f" ({edge['note']})" if edge.get("note") else ""),
        ]
        flag = _flag(
            event,
            "input_squeeze",
            direction,
            sector,
            watchlist,
            chain,
            _weakest(edge),
            f"Input cost moves before reported margin does, so this leads the "
            f"OPM ladder rather than confirming it.",
        )
        if flag:
            out.append(flag)
    return out


def _anchor_shift(event, graph, watchlist):
    """A demand anchor itself had a risk event.

    The weakest of the three mechanisms and the broadest, so it only fires on
    risk-direction events with a named anchor — an anchor announcing good news
    is already covered by first-order attribution wherever it touches us.
    """
    out = []
    if event.get("direction") != "risk":
        return out
    # An anchor ending a partnership says nothing settled about demand: Apple
    # leaving one assembler can send the work to ours. Its weaker business
    # does — "iPhone sales fall" is less to build for every EMS holding.
    if event.get("event_type") == "partnership_end":
        return out
    named = event.get("external") or []
    if not named:
        return out

    for anchor in _edges(graph, "anchor_demand"):
        if not any(_same(anchor.get("src"), n) for n in named):
            continue
        sector = anchor.get("dst")
        chain = [
            f"{anchor.get('src')} hit by {str(event.get('event_type', '')).replace('_', ' ')}",
            f"{anchor.get('src')} anchors demand for our "
            f"{str(sector).replace('_', ' ')} holdings"
            + (f" ({anchor['note']})" if anchor.get("note") else ""),
        ]
        flag = _flag(
            event,
            "anchor_shift",
            "risk",
            sector,
            watchlist,
            chain,
            _weakest(anchor),
            f"Demand anchor disturbance, not a company-specific signal.",
        )
        if flag:
            out.append(flag)
    return out


# What a demand anchor does that is more work for its suppliers.
_PULL_TYPES = ("capacity_add", "order_win")
_PULL_SAYS = {"capacity_add": "is adding capacity", "order_win": "won an order"}


def _anchor_pull(event, graph, watchlist):
    """A demand anchor builds or wins work in a line one of our sectors
    supplies: the good-news mirror of _anchor_shift.

    Held to more than its mirror, because good news is cheap: the headline
    must be about the line the edge reaches — that sector's own vocabulary
    (``domains``) — since an anchor's money spent on something else is
    nobody's demand here ("Vascon receives Letter of Intent for an office"
    names Qualcomm as the client). An order the anchor placed went to whoever
    won it, not to us. Never a rumour, and never when a holding is named:
    first-order attribution has that.
    """
    out = []
    etype = event.get("event_type")
    if etype not in _PULL_TYPES or event.get("actors"):
        return out
    from analysis.event_engine import _named_as_customer, event_clause, event_strength

    if event_strength(event) == "reported":
        return out
    domains = set(event.get("domains") or [])
    held = _holding_sectors(watchlist)
    clause = event_clause(event)
    for anchor in _edges(graph, "anchor_demand"):
        src = anchor.get("src")
        if not any(_same(src, n) for n in event.get("external") or []):
            continue
        dst = str(anchor.get("dst") or "")
        if held.get(dst.upper(), dst) not in domains:
            continue
        if etype == "order_win" and _named_as_customer(
            clause, event.get("phrase"), "", str(src)
        ):
            continue
        reach = (
            dst.upper()
            if dst.upper() in held
            else f"our {dst.replace('_', ' ')} holdings"
        )
        chain = [
            f"{src} {_PULL_SAYS[etype]}",
            f"{src} anchors demand for {reach}"
            + (f" ({anchor['note']})" if anchor.get("note") else ""),
        ]
        flag = _flag(
            event,
            "anchor_pull",
            "opportunity",
            dst,
            watchlist,
            chain,
            _weakest(anchor),
            f"More work for {src} is more to buy from its suppliers; a "
            f"hypothesis until it shows in their orders.",
        )
        if flag:
            out.append(flag)
    return out


# What a rival does that gains it ground.
_RIVAL_GAINS = ("capacity_add", "order_win", "tie_up", "acquisition")
_RIVAL_SAYS = {
    "capacity_add": "is adding capacity",
    "order_win": "won work",
    "tie_up": "tied up with a partner",
    "acquisition": "is acquiring",
}


def _rival_move(event, graph, watchlist):
    """A rival of a holding gains ground in the line where they compete.

    A curated competitor edge that ends at a holding carries the ``scope``
    of the rivalry: Tata Electronics competes with SPEL in chip assembly and
    test, not in phones. The rival adding capacity, winning work, tying up or
    buying in that line is pressure on the holding's share or margin. News
    about the rival's other lines is not ours, and news naming the holding
    is first-order.
    """
    out = []
    etype = event.get("event_type")
    if etype not in _RIVAL_GAINS:
        return out
    from analysis.event_engine import _named_as_customer, event_clause

    held = _holding_sectors(watchlist)
    actors = {str(a).upper() for a in event.get("actors") or []}
    headline = str(event.get("headline", ""))
    clause = event_clause(event)
    for edge in _edges(graph, "competitor"):
        if not edge.get("scope"):
            continue
        rival, ours = edge.get("src"), str(edge.get("dst") or "").upper()
        if ours not in held or ours in actors:
            continue
        if not any(_same(rival, n) for n in event.get("external") or []):
            continue
        if etype == "order_win" and _named_as_customer(
            clause, event.get("phrase"), "", str(rival)
        ):
            continue  # the rival placed the order; someone else won it
        # The rival's own name is not its line ("Tata Electronics" holds no
        # packaging word), as for a partner.
        place = PartnerScope(edge, held[ours]).place(
            re.sub(rf"\b{re.escape(str(rival))}\b", " ", headline, flags=re.IGNORECASE)
        )
        if place != "venture":
            continue
        chain = [
            f"{rival} {_RIVAL_SAYS[etype]}, in the line where it competes with {ours}",
            f"{rival} competes with {ours}"
            + (f" ({edge['note']})" if edge.get("note") else ""),
        ]
        flag = _flag(
            event,
            "rival_move",
            "risk",
            held[ours],
            watchlist,
            chain,
            _weakest(edge),
            f"A stronger rival in {ours}'s line presses on its share or its "
            f"pricing; the headline does not say how much of the market.",
            tickers=[ours],
        )
        if flag:
            out.append(flag)
    return out


def _holding_sectors(watchlist):
    return {
        str(s.get("ticker")).upper(): sector
        for sector, stocks in (watchlist or {}).items()
        if sector != "macro_indicators"
        for s in stocks or []
        if isinstance(s, dict) and s.get("ticker")
    }


class PartnerScope:
    """What a venture makes, so a partner's news can be placed: in the
    venture's own line, in another of the partner's lines, or about the
    partner as a whole.

    A curated edge says so itself (``scope``, ``not_scope``): Corning's
    venture with Optiemus is cover glass for phones, and Corning's optical
    fibre is another business. Otherwise the line is read off the headline
    that proposed the edge ("... Joint Venture With Kaga Electronics To
    Produce PCBs"), falling back to the holding's own sector. Any other
    sector's vocabulary is another line.
    """

    def __init__(self, edge, holding_sector):
        from analysis.competitive_intel import (
            SECTOR_BATTLEGROUNDS,
            _terms_re,
            battleground_sectors,
        )

        terms = [str(t) for t in edge.get("scope") or [] if str(t).strip()]
        if not terms:
            sectors = set(battleground_sectors(edge.get("evidence")))
            sectors |= {holding_sector} & set(SECTOR_BATTLEGROUNDS)
            terms = [t for s in sorted(sectors) for t in SECTOR_BATTLEGROUNDS[s]]
        own = {t.lower() for t in terms}
        others = [str(t) for t in edge.get("not_scope") or [] if str(t).strip()] + [
            t
            for vocabulary in SECTOR_BATTLEGROUNDS.values()
            for t in vocabulary
            if t.lower() not in own
        ]
        self._line = _terms_re(terms) if terms else None
        self._other = _terms_re(others) if others else None

    def place(self, text):
        """'venture', 'other' or 'whole'."""
        if self._line and self._line.search(text or ""):
            return "venture"
        if self._other and self._other.search(text or ""):
            return "other"
        return "whole"


# Risk events that reach a venture through its partner.
_PARTNER_TROUBLE = ("business_weakness", "supply_disruption", "input_cost_shock")

_WHAT = {
    "business_weakness": "a weaker business",
    "supply_disruption": "a supply disruption",
    "input_cost_shock": "an input-cost shock",
    "partnership_end": "a partnership ending",
    "tie_up": "a new tie-up",
    "acquisition": "an acquisition",
    "order_win": "an order",
    "capacity_add": "new capacity",
}


def screen_partner_news(event, partner, holding, scope, rivals=()):
    """Is this news about a partner good, bad or mixed for our holding — or
    not the holding's to read at all?

    ``(direction, reason, verdict, transmission)`` or None. Built on three
    questions, each answered from the headline:

      * Where does it land? In the venture's own line, in another of the
        partner's lines, or on the partner as a whole (PartnerScope).
      * Is it in India? Partner news elsewhere moves the partner, not
        necessarily a venture here.
      * Who else is in it? A rival of the holding (another holding in its
        sector, a Screener peer) turns a partner's deal against us.

    The rules, in order:

      * The partner in trouble (weaker results, a supply disruption, an input
        shock): bad, unless it is about another of its lines. Company-wide
        trouble is bad too, less directly: a partner under pressure invests
        less in its ventures.
      * The partner dealing with a rival of the holding: bad.
      * The partner placing work in the venture's line elsewhere (it is the
        customer in the order): bad.
      * The partner winning work in the venture's line in India: good — that
        work can flow through the venture.
      * The partner adding capacity, tying up or buying in the venture's line
        in India: mixed — the venture's own plant, or the partner going round
        it; the headline rarely says which.
      * The partner ending a partnership in the venture's line in India: bad
        if it is this venture.
      * Anything else is the partner's news, not ours: Kaga winning a
        Japanese order says nothing about the Syrma venture.

    ``transmission`` is how it reaches the holding: through the work the
    venture gets (demand_pull), a rival's gain (competitive_threat), or the
    partner's input costs (input_shock).
    """
    etype = event.get("event_type")
    headline = str(event.get("headline", ""))
    # The partner's name is not its line: "vivo" is electronics vocabulary,
    # and "Vivo wins large order" says nothing about phones.
    place = scope.place(
        re.sub(rf"\b{re.escape(str(partner))}\b", " ", headline, flags=re.IGNORECASE)
    )
    from analysis.competitive_intel import mentions_india
    from analysis.event_engine import _named_as_customer, event_clause
    from analysis.parsing import title_matches_company

    in_india = mentions_india(headline)
    clause = event_clause(event)
    rival = next(
        (
            name or ticker
            for ticker, name in rivals
            if not _same(name, partner)
            and title_matches_company(clause, ticker or "", name or "")
        ),
        None,
    )

    if etype in _PARTNER_TROUBLE:
        if place == "other":
            return None
        channel = "input_shock" if etype == "input_cost_shock" else "demand_pull"
        if place == "venture":
            return (
                "risk",
                "in the venture's own line",
                f"bad for {holding}: trouble in the venture's line reaches the venture",
                channel,
            )
        return (
            "risk",
            f"about {partner} as a whole",
            f"bad for {holding}, less directly: a partner under pressure invests "
            f"less in its ventures",
            channel,
        )
    if etype in ("tie_up", "acquisition", "order_win") and rival:
        return (
            "risk",
            f"{rival} competes with {holding}",
            f"bad for {holding}: its partner is working with a competitor",
            "competitive_threat",
        )
    if place != "venture":
        return None
    if etype == "order_win":
        if _named_as_customer(clause, event.get("phrase"), "", partner):
            return (
                "risk",
                f"{partner} is the customer, in the venture's line",
                f"bad for {holding}: work in the venture's line is going elsewhere",
                "competitive_threat",
            )
        if in_india:
            return (
                "opportunity",
                "work in the venture's line, in India",
                f"good for {holding}: it can flow through the venture",
                "demand_pull",
            )
        return None
    if not in_india:
        return None
    if etype == "partnership_end":
        return (
            "risk",
            "a partnership in the venture's line, in India",
            f"bad for {holding} if this is the venture: check whether it names "
            f"{holding}'s",
            "demand_pull",
        )
    if etype in ("capacity_add", "tie_up", "acquisition"):
        return (
            "mixed",
            "in the venture's line, in India",
            f"either way for {holding}: the venture's own business, or {partner} "
            f"going round it",
            "demand_pull",
        )
    return None


def _rivals(watchlist, sector, holding, peers):
    """(ticker, name) of whoever competes with ``holding``: the other holdings
    in its sector and the sector's Screener peers."""
    out = [
        (s.get("ticker"), s.get("name"))
        for s in (watchlist or {}).get(sector) or []
        if isinstance(s, dict) and s.get("ticker") and s.get("ticker") != holding
    ]
    out += [
        (p.get("ticker"), p.get("name"))
        for p in (peers or {}).get(sector) or []
        if isinstance(p, dict) and (p.get("ticker") or p.get("name"))
    ]
    return out


def _partner_news(event, graph, watchlist, peers=None):
    """News that names a holding's partner and not the holding.

    "Vivo faces export curbs" names Vivo and nobody we hold. Dixon's smartphone
    joint venture is with Vivo, so the news is Dixon's to read — and nothing
    else in the pipeline can see that, because the relationship lived in a
    headline that was classified and forgotten. Partner edges are where it is
    remembered (see entity_graph.record_partner_proposals). Whether the news
    is good or bad for the holding is screen_partner_news's judgement, not the
    partner's own direction.

    Never when the holding is named: first-order attribution already has that
    event, and repeating it as a hypothesis would count it twice.
    """
    out = []
    named = event.get("external") or []
    actors = {str(a).upper() for a in event.get("actors") or []}
    sectors = _holding_sectors(watchlist)
    what = _WHAT.get(event.get("event_type"), "news")

    for edge in _edges(graph, "partner"):
        # Undirected: either end may be the holding.
        for partner, ours in (
            (edge.get("src"), edge.get("dst")),
            (edge.get("dst"), edge.get("src")),
        ):
            ours = str(ours or "").upper()
            if ours not in sectors or ours in actors:
                continue
            if not (
                any(_same(partner, n) for n in named)
                or str(partner or "").upper() in actors
            ):
                continue
            scope = PartnerScope(edge, sectors[ours])
            verdict = screen_partner_news(
                event,
                partner,
                ours,
                scope,
                _rivals(watchlist, sectors[ours], ours, peers),
            )
            if not verdict:
                continue
            direction, reason, judgement, transmission = verdict
            basis = str(edge.get("evidence") or "")
            chain = [
                f"{partner}: {what}",
                f"{partner} is a partner of {ours}"
                + (
                    f" (“{basis[:90]}”)"
                    if basis and basis.lower() != "curated"
                    else (f" ({edge['note']})" if edge.get("note") else "")
                ),
                f"{reason[:1].upper()}{reason[1:]}: {judgement}",
            ]
            flag = _flag(
                event,
                "partner_exposure",
                direction,
                sectors[ours],
                watchlist,
                chain,
                _weakest(edge),
                f"{judgement[:1].upper()}{judgement[1:]}. The headline does not "
                f"say how much of {ours}'s business the venture is.",
                tickers=[ours],
                transmission=transmission,
            )
            if flag:
                out.append(flag)
    return out


def _dedupe(flags):
    """One row per claim: what happened (the chain's first link), how it
    travels and which way, and the holdings it lands on.

    The same headline can reach one sector by several chains — two suppliers
    to the same customer, say — and the same story reaches the corpus from
    several outlets: on 20 Oct two reports of one LS MnM copper cut were six
    of the ten rows. Showing it twice reads as two problems. The surviving
    row keeps the best-weighted chain, then the newest report, and counts
    the reports behind it (``reports``).
    """
    # Tickers are part of the key because a partner chain is scoped to one
    # company: Vivo hitting two EMS holdings' ventures is two rows, and keying
    # on sector alone would silently keep one and drop the other. Sector-wide
    # flags carry the whole sector, so nothing changes there.
    groups: Dict[Any, List[Dict[str, Any]]] = {}
    for flag in flags:
        key = (
            flag["sector"],
            flag["mechanism"],
            flag["direction"],
            tuple(flag.get("tickers") or ()),
        )
        groups.setdefault(key, []).append(flag)

    out = []
    for rows in groups.values():
        # Within a group, rows are one claim if they share a headline (one
        # story naming memory, memory chips and chips) or a first link (one
        # story in two outlets' words): joined either way, transitively.
        parent = list(range(len(rows)))

        def root(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        first_with = {}
        for i, flag in enumerate(rows):
            for mark in (
                ("trigger", flag["trigger"]),
                ("claim", (flag.get("chain") or [flag["trigger"]])[0]),
            ):
                if mark in first_with:
                    parent[root(i)] = root(first_with[mark])
                else:
                    first_with[mark] = i
        claims: Dict[int, List[Dict[str, Any]]] = {}
        for i, flag in enumerate(rows):
            claims.setdefault(root(i), []).append(flag)
        for claim in claims.values():
            best = max(
                claim, key=lambda f: (f.get("weight", 0), str(f.get("date", "")))
            )
            out.append(dict(best, reports=len({f["trigger"] for f in claim})))
    return out


def compute_read_throughs(
    events: List[Dict[str, Any]],
    graph: Dict[str, Any],
    watchlist: Dict[str, Any],
    window_days: int = WINDOW_DAYS,
    today: str = "",
    limit: int = 40,
    headlines: List[str] = None,
    peers: Dict[str, Any] = None,
) -> List[Dict[str, Any]]:
    """Second-order implications of recent news for what we actually hold.

    `events` are typed and attributed; `headlines` is the raw corpus. Both are
    used, for different mechanisms, and the split is not incidental:

    Displacement and anchor-shift are statements about a transaction — someone
    picked someone — so they need the event engine to have recognised a
    transaction and named its parties.

    A price pass-through is not a transaction. "iPhone priced higher on RAM
    shortage" reports a cost, matches no event vocabulary, and so never became
    an event at all — which meant the single most common shape of second-order
    news was invisible to a feature built to catch it. It is read straight
    from the headline instead.

    Returns [] rather than raising on any problem: this is an enhancement
    layer, and a briefing that renders without it is far better than one that
    does not render.
    """
    flags: List[Dict[str, Any]] = []
    try:
        today = today or datetime.date.today().isoformat()
        recent = _recent(events, window_days, today)
        for event in recent:
            flags.extend(_displacement(event, graph, watchlist))
            flags.extend(_input_squeeze(event, graph, watchlist))
            flags.extend(_anchor_shift(event, graph, watchlist))
            flags.extend(_anchor_pull(event, graph, watchlist))
            flags.extend(_rival_move(event, graph, watchlist))
            flags.extend(_partner_news(event, graph, watchlist, peers))

        # The raw corpus carries no dates — it is this run's collection — so
        # everything in it is today, unless the headline dates itself:
        # "Market Preview, June 22, 2026: ..." is not this week's news.
        from analysis.event_evidence import headline_date

        cutoff = (
            datetime.date.fromisoformat(today) - datetime.timedelta(days=window_days)
        ).isoformat()
        for headline in headlines or []:
            dated = headline_date(headline, today) or today
            if dated < cutoff:
                continue
            flags.extend(
                _input_squeeze(
                    {"headline": headline, "date": dated, "certainty": ""},
                    graph,
                    watchlist,
                )
            )

        flags = _dedupe(flags)

        # Risk before opportunity, then by weight (how binding the event,
        # times how well evidenced its weakest link: a lowest bid never
        # outranks a Letter of Award), then newest.
        #
        # The date has to be inverted rather than sorted as a string: ISO dates
        # ascend, so the obvious tuple put the OLDEST flag first while the
        # comment claimed newest. With the dashboard capping the feed and the
        # email showing four rows, a busy run would have buried today's
        # read-through behind a ten-day-old one.
        def _rank(flag):
            try:
                recency = -datetime.date.fromisoformat(
                    str(flag.get("date", ""))
                ).toordinal()
            except ValueError:
                recency = 1  # undated sorts last, never ahead of a real date
            return (
                flag["direction"] != "risk",
                -flag.get("weight", 0),
                recency,
            )

        flags.sort(key=_rank)
        flags = flags[:limit]

        if flags:
            by_direction = {
                d: sum(1 for f in flags if f["direction"] == d)
                for d in ("risk", "opportunity", "mixed")
            }
            mechanisms = sorted({f["mechanism"] for f in flags})
            by_channel = {
                t: sum(1 for f in flags if f.get("transmission") == t)
                for t in TRANSMISSIONS
            }
            soft = sum(1 for f in flags if f.get("strength") != "hard")
            log.info(
                f"Read-through: {len(flags)} second-order flag(s) across "
                f"{len({f['sector'] for f in flags})} sector(s) "
                f"({by_direction['risk']} risk, {by_direction['opportunity']} "
                f"opportunity"
                + (f", {by_direction['mixed']} mixed" if by_direction["mixed"] else "")
                + f"; {', '.join(mechanisms)}; "
                + ", ".join(f"{t.replace('_', ' ')} {n}" for t, n in by_channel.items())
                + (f"; {soft} from soft or reported news, weighed down" if soft else "")
                + ")."
            )
        else:
            # Stated even when empty. A silent zero here is indistinguishable
            # from the step never having run, which is the confusion this
            # codebase spends most of its comments avoiding.
            log.info(
                f"Read-through: no second-order flags from "
                f"{len(recent)} event(s) in the last {window_days} days."
            )
    except Exception as e:  # noqa: BLE001 - enhancement must never break a run
        log.warning(f"Read-through computation failed safely: {e!r}")
        return []
    return flags
