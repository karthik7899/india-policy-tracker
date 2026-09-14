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

# A chain is only as strong as its weakest link.
_CONFIDENCE_ORDER = {"curated": 2, "harvested": 1}

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
    "steel" cannot match "Steelcase".
    """
    if not material:
        return False
    pattern = _MATERIAL_RE_CACHE.get(material)
    if pattern is None:
        pattern = re.compile(rf"\b{re.escape(str(material))}\d*\b", re.IGNORECASE)
        _MATERIAL_RE_CACHE[material] = pattern
    return bool(pattern.search(str(text or "")))


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
    return [
        e
        for e in events or []
        if isinstance(e, dict) and str(e.get("date", "")) >= cutoff
    ]


def _flag(event, mechanism, direction, sector, watchlist, chain, confidence, note):
    tickers = _sector_holdings(watchlist, sector)
    if not tickers:
        # Nothing held in the sector this chain lands on. The reasoning may be
        # perfectly sound and is still not actionable here, and reporting it
        # would be noise dressed as insight.
        return None
    return {
        "trigger": str(event.get("headline", ""))[:180],
        "date": event.get("date", ""),
        "mechanism": mechanism,
        "direction": direction,
        "sector": sector,
        "tickers": sorted(tickers),
        "chain": chain,
        "confidence": confidence,
        "certainty": event.get("certainty", ""),
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
    out = []
    headline = str(event.get("headline", ""))
    lower = headline.lower()

    squeezing = any(m in lower for m in _SQUEEZE_MARKERS)
    easing = any(m in lower for m in _EASING_MARKERS)
    # Both at once is a headline describing a turn ("shortage eases"), which
    # is an easing. Neither means this is not a price story at all.
    if easing:
        direction, verb = "opportunity", "cheaper or more available"
    elif squeezing:
        direction, verb = "risk", "scarcer or dearer"
    else:
        return out

    seen = set()
    for edge in _edges(graph, "input_cost"):
        material = str(edge.get("src", ""))
        # Word-boundary matched: "RAM" must not fire on "programme" or
        # "Gurugram", and "memory" must not fire on "memorial".
        if not material_in(headline, material):
            continue
        sector = edge.get("dst")
        if (material.lower(), sector) in seen:
            continue
        seen.add((material.lower(), sector))
        chain = [
            f"headline reports {material} {verb}",
            f"{material} is an input to our {str(sector).replace('_', ' ')} holdings",
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


def _dedupe(flags):
    """One row per (sector, mechanism, trigger).

    The same headline can reach one sector by several chains — two suppliers
    to the same customer, say. Showing it four times reads as four problems.
    The surviving row keeps the best-evidenced chain.
    """
    best = {}
    for flag in flags:
        key = (flag["sector"], flag["mechanism"], flag["trigger"])
        current = best.get(key)
        if current is None or _CONFIDENCE_ORDER.get(
            flag["confidence"], 1
        ) > _CONFIDENCE_ORDER.get(current["confidence"], 1):
            best[key] = flag
    return list(best.values())


def compute_read_throughs(
    events: List[Dict[str, Any]],
    graph: Dict[str, Any],
    watchlist: Dict[str, Any],
    window_days: int = WINDOW_DAYS,
    today: str = "",
    limit: int = 40,
    headlines: List[str] = None,
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

        # The raw corpus carries no dates — it is this run's collection — so
        # everything in it is today by construction.
        for headline in headlines or []:
            flags.extend(
                _input_squeeze(
                    {"headline": headline, "date": today, "certainty": ""},
                    graph,
                    watchlist,
                )
            )

        flags = _dedupe(flags)

        # Risk before opportunity, curated before harvested, then newest.
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
                -_CONFIDENCE_ORDER.get(flag["confidence"], 1),
                recency,
            )

        flags.sort(key=_rank)
        flags = flags[:limit]

        if flags:
            risks = sum(1 for f in flags if f["direction"] == "risk")
            mechanisms = sorted({f["mechanism"] for f in flags})
            log.info(
                f"Read-through: {len(flags)} second-order flag(s) across "
                f"{len({f['sector'] for f in flags})} sector(s) "
                f"({risks} risk, {len(flags) - risks} opportunity; "
                f"{', '.join(mechanisms)})."
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
