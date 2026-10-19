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
):
    # A sector-level chain lands on every holding in the sector; a chain that
    # ends at one company (a partner edge) lands on that company only, and
    # widening it to the sector would assert exposure nobody has shown.
    tickers = tickers or _sector_holdings(watchlist, sector)
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

    ``(direction, reason, verdict)`` or None. Built on three questions, each
    answered from the headline:

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
        if place == "venture":
            return (
                "risk",
                "in the venture's own line",
                f"bad for {holding}: trouble in the venture's line reaches the venture",
            )
        return (
            "risk",
            f"about {partner} as a whole",
            f"bad for {holding}, less directly: a partner under pressure invests "
            f"less in its ventures",
        )
    if etype in ("tie_up", "acquisition", "order_win") and rival:
        return (
            "risk",
            f"{rival} competes with {holding}",
            f"bad for {holding}: its partner is working with a competitor",
        )
    if place != "venture":
        return None
    if etype == "order_win":
        if _named_as_customer(clause, event.get("phrase"), "", partner):
            return (
                "risk",
                f"{partner} is the customer, in the venture's line",
                f"bad for {holding}: work in the venture's line is going elsewhere",
            )
        if in_india:
            return (
                "opportunity",
                "work in the venture's line, in India",
                f"good for {holding}: it can flow through the venture",
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
        )
    if etype in ("capacity_add", "tie_up", "acquisition"):
        return (
            "mixed",
            "in the venture's line, in India",
            f"either way for {holding}: the venture's own business, or {partner} "
            f"going round it",
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
            direction, reason, judgement = verdict
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
            )
            if flag:
                out.append(flag)
    return out


def _dedupe(flags):
    """One row per (sector, mechanism, trigger, tickers).

    The same headline can reach one sector by several chains — two suppliers
    to the same customer, say. Showing it four times reads as four problems.
    The surviving row keeps the best-evidenced chain.
    """
    best = {}
    for flag in flags:
        # Tickers are part of the key because a partner chain is scoped to one
        # company: Vivo hitting two EMS holdings' ventures is two rows, and
        # keying on sector alone would silently keep one and drop the other.
        # Sector-wide flags carry the whole sector, so nothing changes there.
        key = (
            flag["sector"],
            flag["mechanism"],
            flag["trigger"],
            tuple(flag.get("tickers") or ()),
        )
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
            flags.extend(_partner_news(event, graph, watchlist, peers))

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
            by_direction = {
                d: sum(1 for f in flags if f["direction"] == d)
                for d in ("risk", "opportunity", "mixed")
            }
            mechanisms = sorted({f["mechanism"] for f in flags})
            log.info(
                f"Read-through: {len(flags)} second-order flag(s) across "
                f"{len({f['sector'] for f in flags})} sector(s) "
                f"({by_direction['risk']} risk, {by_direction['opportunity']} "
                f"opportunity"
                + (f", {by_direction['mixed']} mixed" if by_direction["mixed"] else "")
                + f"; {', '.join(mechanisms)})."
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
