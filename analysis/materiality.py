"""How big is this event, relative to the company it happened to?

The event engine can tell you a company won an order. It could not tell you
whether that mattered. A Rs 500 crore win is a rounding error for a company
turning over Rs 2,50,000 crore and a company-defining catalyst for one
turning over Rs 2,000 crore, and both were scoring identically.

The consequence was visible in the score distribution. Once news flow was
capped at 8 points, momentum stopped being a ranking at all and became a
flag: 38 holdings sat at the no-news floor of 1 and 17 sat exactly at the
cap, with only nine anywhere in between. Suzlon, TCS, HAL, Siemens, Dixon,
Reliance and Coforge were indistinguishable on news. Capping the inflation
fixed the arithmetic and left the signal saturated.

This module supplies the missing denominator. It pulls the money figure out
of a headline, expresses it against trailing revenue, and returns a weight
that pushes immaterial announcements down without touching events whose size
we genuinely cannot read.

Two deliberate limits:

  * Only *transactional* events are weighted — orders, contracts, deals.
    A PLI approval or a policy notification has no order value to find, and
    scoring it as immaterial because no rupee figure appeared in the
    headline would be a parsing artefact masquerading as judgement.
  * An unparseable amount returns ``None``, not zero. "Wins large order"
    carries no number; the honest answer is that materiality is unknown, and
    unknown must not be treated as small.
"""

import re
from typing import Optional

# Everything is normalised to rupees crore, which is the unit Screener
# reports revenue in, so the ratio needs no further conversion.
_CRORE = 1.0
_LAKH = 0.01
_MULTIPLIERS = {
    "crore": _CRORE,
    "cr": _CRORE,
    "crores": _CRORE,
    "lakh": _LAKH,
    "lakhs": _LAKH,
    "lac": _LAKH,
    "million": 0.1,
    "mn": 0.1,
    "billion": 100.0,
    "bn": 100.0,
    "trillion": 100000.0,
}

# "Rs 1.2 lakh crore" is 1.2 x 10^5 crore, not 1.2 lakh. The compound unit
# has to be matched before the bare one or the multiplier is read wrong by a
# factor of ten million.
_COMPOUND = {
    ("lakh", "crore"): 100000.0,
    ("lakh", "cr"): 100000.0,
    ("lac", "crore"): 100000.0,
    ("thousand", "crore"): 1000.0,
}

# Foreign-currency deals are quoted in dollars often enough to matter for EMS
# and defence exporters. The rate is a coarse constant on purpose: this feeds
# a size *bucket*, and no bucket boundary is tight enough for a live FX rate
# to change the answer. Revisit if it is ever used for a valuation.
_USD_INR = 83.0
_FOREIGN = ("$", "usd", "us$", "dollar")

_UNIT_ALT = "|".join(sorted(_MULTIPLIERS, key=len, reverse=True))
_AMOUNT_RE = re.compile(
    r"(?P<cur>(?:rs\.?|inr|₹|usd|us\$|\$)\s*)?"
    r"(?P<num>\d[\d,]*(?:\.\d+)?)"
    r"[\s-]*"
    r"(?P<unit>" + _UNIT_ALT + r")"
    r"(?:[\s-]*(?P<unit2>crore|cr)\b)?",
    re.IGNORECASE,
)

# "Pledges 3.70 Lakh Equity Shares" is a share count, not Rs 0.037 crore, and
# "5 crore equity shares" is not Rs 5 crore. The multiplier words are shared
# between money and plain counting in Indian usage, so the unit alone cannot
# tell them apart -- what follows it can. Without this the pledge headline
# above was extracted as a rupee figure; it happened to be filtered later for
# being the wrong event kind, which is luck rather than correctness.
_COUNT_NOUN_RE = re.compile(
    r"^[\s-]*(?:equity\s+|preference\s+|bonus\s+)?"
    r"(?:shares?|share[s]?\b|units?|nos\.?|tonnes?|tons?|kg|mw|gw|kwh|"
    r"litres?|liters?|sq\.?\s*ft|square\s+feet|employees?|customers?|"
    r"subscribers?|users?|vehicles?|seats?|rooms?|barrels?)\b",
    re.IGNORECASE,
)

# An amount is only this company's if the headline is about this company.
#
# The first production run showed why that needs enforcing. "BEL, HAL, Bharat
# Dynamics: Defence stocks rally as DAC clears Rs 52,000 crore defence
# acquisition proposals" was read as a HAL transaction worth 157% of HAL's
# revenue, scored "transformative", and given the maximum weight -- and it
# would have done the same for BEL and for Bharat Dynamics. The figure is a
# government procurement programme spanning the sector and belongs to none of
# them individually. A confidently wrong bull signal is worse than no signal,
# so both shapes below are excluded.

# Market commentary: reports a price move, never a transaction, even when it
# quotes a real number.
_COMMENTARY_MARKERS = (
    "stocks rally",
    "stock rally",
    "shares rally",
    "stocks gain",
    "stocks jump",
    "stocks surge",
    "stocks slip",
    "stocks fall",
    "shares jump",
    "shares surge",
    "share price",
    "top gainer",
    "top loser",
    "midcap loser",
    "index rejig",
    "hits 52-week",
    "target price",
    "upper circuit",
    "lower circuit",
)

# The literal list above only ever caught the plural forms a sub-editor
# happened to use -- "shares jump" but not "jumps 9%". The move itself has a
# regular shape, so match that instead: a verb of price movement next to a
# percentage. "Zen Technologies jumps 9%, ideaForge hits upper circuit as
# India eyes Rs 20,000 crore drone buy" is commentary wrapped around a sector
# figure, and was reaching the extractor because none of its words were on
# the list.
_PRICE_MOVE_RE = re.compile(
    r"\b(?:jump|jumps|jumped|surge|surges|surged|rally|rallies|rallied|"
    r"soar|soars|soared|zoom|zooms|zoomed|slip|slips|slipped|plunge|plunges|"
    r"plunged|crash|crashes|crashed|tank|tanks|tanked|gain|gains|gained|"
    r"fall|falls|fell|rise|rises|rose|climb|climbs|climbed|drop|drops|"
    r"dropped|declines?|declined)\b[^.;]{0,30}?\d+(?:\.\d+)?\s*%",
    re.IGNORECASE,
)

# A number the market or the state is contemplating is nobody's booked
# order. "India eyes Rs 20,000 crore drone buy" sizes an opportunity, not a
# transaction.
_PROSPECTIVE_MARKERS = (
    "eyes rs",
    "eyes ₹",
    "eyeing",
    "set to award",
    "plans to award",
    "market to reach",
    "opportunity worth",
    "pipeline worth",
    "expected to award",
)

# Programme-level approvals: the amount is a budget or a sector allocation
# handed down by a ministry or council, not an order booked by one company.
_PROGRAMME_MARKERS = (
    "dac clears",
    "dac approves",
    "cabinet approves",
    "cabinet clears",
    "ccs approves",
    "ccs clears",
    "acquisition proposals",
    "procurement proposals",
    "capital acquisition",
    "outlay",
    "budget allocation",
    "allocates",
    "sanctions",
)

# A headline that opens with a list of companies before a colon -- "BEL, HAL,
# Bharat Dynamics: ..." -- is about a group, so no amount in it is assignable
# to any single member.
_COMPANY_LIST_RE = re.compile(r"^[^:]{0,80}?,[^:]{0,80}?:")

# A jointly-owned vehicle's capitalisation belongs to its partners in
# proportions the headline never states. "Syrma SGS, Kaga Electronics Form
# Rs 250 Million EMS Joint Venture" is a real figure, but booking all of it
# against Syrma's revenue overstates it by whatever Kaga put in -- the same
# error as reading a sector procurement budget as one company's order. The
# list guard above misses these because the colon lands before the comma
# ("Agreement: A, B Form ..."), so the shape has to be matched on its own.
_SHARED_VEHICLE_MARKERS = (
    "joint venture",
    "consortium",
    "partnership with",
)

# "Vivo JV Targeting Rs 30,000 Cr" and "JV with" both abbreviate it. Matched
# as a word so "JVs" and bare "JV" count but no longer word does.
_JV_RE = re.compile(r"\bjvs?\b", re.IGNORECASE)

# Results are not transactions. The event kinds below come from the name of
# the feed a headline arrived in -- "corporate_agreements" is a news query,
# not a classification -- so an earnings headline sitting in that feed was
# being read as a sized deal: "CONCOR Q1 Revenue Reaches Rs 2,160 Crore" was
# scored as a Rs 2,160 crore transaction, and "MRPL Annual Report FY 2025-26:
# Profit After Tax Surges to Rs 1,931 Crore" as a Rs 1,931 crore one. Both are
# the company's own reported performance, already counted elsewhere.
_RESULTS_MARKERS = (
    "q1 results",
    "q2 results",
    "q3 results",
    "q4 results",
    "q1 revenue",
    "q2 revenue",
    "q3 revenue",
    "q4 revenue",
    "quarterly results",
    "annual report",
    "net profit",
    "profit after tax",
    "net loss",
    "revenue rises",
    "revenue reaches",
    "revenue grows",
    "earnings summary",
    "results:",
    # "ITC Hotels Q4 profit up 23% at Rs 317 cr; to acquire Zuri Hotels" has
    # a real acquisition in it, but the only figure printed is the profit --
    # so the extractor sized the deal at the earnings number. Better to read
    # nothing than to read the wrong quantity confidently.
    "profit up",
    "profit rises",
    "profit surges",
    "profit falls",
    "profit jumps",
)

# A figure covering several projects, or promised rather than transacted, is
# not a booked order. "Eight coal gasification projects to draw Rs 65,365
# crore investment" is the HAL sector-procurement shape wearing different
# words. A guarantee is a contingent liability, not revenue.
_AGGREGATE_MARKERS = (
    "projects to draw",
    "combined investment",
    "cumulative investment",
    "total investment of",
    "guarantee",
    "guarantees",
)

# Event vocabulary that implies a transaction with a readable size. Anything
# outside this set is left unweighted -- see the module docstring.
_SIZED_EVENT_TYPES = frozenset(
    {"order_win", "agreement", "acquisition", "contract", "tie_up"}
)
_SIZED_PHRASES = (
    "order",
    "contract",
    "deal",
    "acquisition",
    "acquires",
    # The list held only the third-person form, so "to acquire ... for Rs
    # 1,119 crore" was left unsized while "acquires" was sized -- a grammar
    # accident deciding whether a real transaction counted. Divestments are
    # the same event seen from the other side and were missing outright.
    "acquire",
    "to sell",
    "divest",
    "stake sale",
    "sells stake",
    "buyout",
    "stake",
    "investment",
    "invest",
    "capex",
    "tender",
    "bid",
    "letter of intent",
    "purchase order",
    "supply agreement",
)

# Share of trailing revenue at which an event stops being noise. The bands are
# coarse because the underlying number is coarse -- a headline rounds, and the
# order may span several years of delivery.
IMMATERIAL_PCT = 2.0
MATERIAL_PCT = 5.0
TRANSFORMATIVE_PCT = 15.0

# Weights applied to an event's base score. Immaterial events are damped, not
# deleted: a small order is still a real order, and a company announcing many
# of them is still doing business.
WEIGHT_IMMATERIAL = 0.25
WEIGHT_MINOR = 0.5
WEIGHT_MATERIAL = 1.0
WEIGHT_TRANSFORMATIVE = 1.5


def extract_amount_cr(text: str) -> Optional[float]:
    """Largest money figure in ``text``, in rupees crore, or None.

    Takes the largest rather than the first because headlines routinely carry
    a second, smaller number that is not the deal size -- "wins Rs 900 crore
    order; stock up 5%" is fine, but "Rs 12 crore per unit for a Rs 900 crore
    contract" would otherwise read as a Rs 12 crore event.
    """
    if not text:
        return None

    best = None
    for match in _AMOUNT_RE.finditer(text):
        raw = match.group("num").replace(",", "")
        try:
            value = float(raw)
        except ValueError:
            continue

        unit = match.group("unit").lower()
        unit2 = (match.group("unit2") or "").lower()
        multiplier = _COMPOUND.get((unit, unit2)) if unit2 else None
        if multiplier is None:
            multiplier = _MULTIPLIERS.get(unit)
        if multiplier is None:
            continue

        # A counted noun straight after the unit means the number counts
        # things, not rupees -- unless the headline put a currency marker on
        # it, which settles the question the other way.
        marker = (match.group("cur") or "").lower()
        if not marker and _COUNT_NOUN_RE.match(text[match.end() :]):
            continue

        amount = value * multiplier

        # Dollar amounts convert; the currency marker may sit on the number
        # itself or immediately before it.
        window = text[max(0, match.start() - 6) : match.start()].lower()
        if any(f in marker for f in _FOREIGN) or any(f in window for f in _FOREIGN):
            amount *= _USD_INR

        if best is None or amount > best:
            best = amount

    return best


def ttm_revenue_cr(fin) -> Optional[float]:
    """Trailing twelve months of revenue in crore, or None.

    Prefers the four most recent quarters. Falls back to the latest annual
    figure, which is staler but still the right order of magnitude -- and
    order of magnitude is all a materiality bucket needs.
    """
    if fin is None:
        return None

    quarterly = getattr(fin, "sales_trend", None) or []
    numeric = [v for v in quarterly if isinstance(v, (int, float))]
    if len(numeric) >= 4:
        total = sum(numeric[-4:])
        if total > 0:
            return float(total)

    annual = getattr(fin, "annual_sales_trend", None) or []
    numeric = [v for v in annual if isinstance(v, (int, float))]
    if numeric and numeric[-1] > 0:
        return float(numeric[-1])
    return None


def amount_is_attributable(title: str) -> bool:
    """Could any amount in this headline belong to one company?

    Applies before the event type is even considered: a headline about a whole
    sector, or about a price move, carries figures that are real but are not
    this company's, and treating them as such produces a maximum-confidence
    signal built on somebody else's number.
    """
    lowered = (title or "").lower()
    if any(marker in lowered for marker in _COMMENTARY_MARKERS):
        return False
    if _PRICE_MOVE_RE.search(lowered):
        return False
    if any(marker in lowered for marker in _PROGRAMME_MARKERS):
        return False
    if any(marker in lowered for marker in _PROSPECTIVE_MARKERS):
        return False
    if any(marker in lowered for marker in _SHARED_VEHICLE_MARKERS):
        return False
    if _JV_RE.search(lowered):
        return False
    if any(marker in lowered for marker in _RESULTS_MARKERS):
        return False
    if any(marker in lowered for marker in _AGGREGATE_MARKERS):
        return False
    return not _COMPANY_LIST_RE.match(title or "")


def is_sized_event(event_type: str, title: str) -> bool:
    """Should this event carry a rupee figure at all?

    A PLI approval legitimately has none, so it must not be judged for
    lacking one.
    """
    if not amount_is_attributable(title):
        return False
    if (event_type or "").lower().strip() in _SIZED_EVENT_TYPES:
        return True
    lowered = (title or "").lower()
    return any(phrase in lowered for phrase in _SIZED_PHRASES)


def classify(pct: Optional[float]) -> str:
    if pct is None:
        return "unknown"
    if pct >= TRANSFORMATIVE_PCT:
        return "transformative"
    if pct >= MATERIAL_PCT:
        return "material"
    if pct >= IMMATERIAL_PCT:
        return "minor"
    return "immaterial"


def weight_for(band: str) -> float:
    return {
        "transformative": WEIGHT_TRANSFORMATIVE,
        "material": WEIGHT_MATERIAL,
        "minor": WEIGHT_MINOR,
        "immaterial": WEIGHT_IMMATERIAL,
    }.get(band, WEIGHT_MATERIAL)


def assess(title: str, event_type: str, fin) -> dict:
    """Materiality verdict for one event against one company.

    Returns ``band``, the ``weight`` to apply to its score, and the inputs
    behind them so the dashboard can show its working rather than presenting
    a bare multiplier.
    """
    sized = is_sized_event(event_type, title)
    amount = extract_amount_cr(title) if sized else None
    revenue = ttm_revenue_cr(fin)

    pct = None
    if amount is not None and revenue:
        pct = amount / revenue * 100

    band = classify(pct) if sized else "unknown"
    return {
        "band": band,
        "weight": weight_for(band) if pct is not None else WEIGHT_MATERIAL,
        "amount_cr": amount,
        "ttm_revenue_cr": revenue,
        "pct_of_revenue": round(pct, 2) if pct is not None else None,
    }
