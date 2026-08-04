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

        amount = value * multiplier

        # Dollar amounts convert; the currency marker may sit on the number
        # itself or immediately before it.
        marker = (match.group("cur") or "").lower()
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


def is_sized_event(event_type: str, title: str) -> bool:
    """Should this event carry a rupee figure at all?

    A PLI approval legitimately has none, so it must not be judged for
    lacking one.
    """
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
