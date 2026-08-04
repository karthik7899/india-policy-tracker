"""Can a position actually be entered and exited at the price on screen?

Every valuation in this pipeline quotes a price that assumes someone will
trade there. For the larger holdings that assumption is free. For the
micro-caps in this book -- ASM Technologies, SPEL Semiconductor, Faze Three,
Precot, Diamond Power -- it is the whole question, and nothing here was
asking it. A stock can screen cheap on every fundamental measure and still be
untradeable in size, and the dashboard would rank it beside a name a hundred
times more liquid without comment.

What this computes:

  * **ADVT** -- average daily value traded over the recent window, in rupees
    crore. Volume alone is misleading across a price range this wide; a lakh
    shares of a Rs 20 stock and a lakh shares of a Rs 4,000 stock are not
    comparable positions.
  * **Days to liquidate** -- how long a given ticket takes to unwind at a
    realistic share of daily turnover. This is deliberately chosen over a
    modelled impact cost: a genuine impact-cost figure needs order-book depth
    that no free source gives us, and inventing one would repeat exactly the
    mistake this repository just spent a release undoing -- a precise-looking
    number with nothing behind it.

The participation rate is the one judgement call, and it is stated rather
than buried: taking more than a fifth of a day's volume moves the price
against you, so the estimate assumes a fifth and reports the result plainly.
"""

import math
from typing import Optional

# A rupee crore is 10^7 rupees. Yahoo gives price in rupees and volume in
# shares, so the product needs this divisor to land in the unit the rest of
# the dashboard speaks.
_RUPEES_PER_CRORE = 1e7

# Share of a session's turnover an exit can take before it is pushing the
# price rather than meeting it.
PARTICIPATION_RATE = 0.20

# Turnover bands, in rupees crore per day. The institutional floor is the
# threshold below which a fund cannot build or exit a position without the
# slippage exceeding any edge the thesis was supposed to capture.
ILLIQUID_CR = 1.0
THIN_CR = 5.0
ADEQUATE_CR = 25.0

# Ticket sizes the days-to-exit figure is quoted against.
_TICKETS_CR = (1.0, 5.0)


def average_daily_value_cr(closes, volumes) -> Optional[float]:
    """Mean daily traded value in rupees crore across the supplied sessions.

    Pairs each close with its own volume rather than multiplying averages --
    on a thin stock the heavy-volume days are usually the ones that gapped,
    and averaging the two series separately hides exactly that.
    """
    if closes is None or volumes is None:
        return None

    values = []
    for close, volume in zip(closes, volumes):
        if close is None or volume is None:
            continue
        try:
            close_f, volume_f = float(close), float(volume)
        except (TypeError, ValueError):
            continue
        # NaN is the shape a missing session actually arrives in from yfinance,
        # and it is not caught by a None check. Left in, one NaN row poisons the
        # mean to NaN, and because every NaN comparison is False the result then
        # falls through the bands and lands on "liquid" -- labelling a stock we
        # could not measure as the easiest kind to trade.
        if math.isnan(close_f) or math.isnan(volume_f):
            continue
        if close_f <= 0 or volume_f <= 0:
            continue  # holidays and halted sessions, not real zero-turnover days
        values.append(close_f * volume_f)

    if not values:
        return None
    return sum(values) / len(values) / _RUPEES_PER_CRORE


def classify(advt_cr: Optional[float]) -> str:
    # NaN must resolve to "unknown" and not fall through every comparison to
    # the most favourable band. Guarded here as well as at the source, because
    # this is public and a caller may hand it a figure computed elsewhere.
    if advt_cr is None or (isinstance(advt_cr, float) and math.isnan(advt_cr)):
        return "unknown"
    if advt_cr < ILLIQUID_CR:
        return "illiquid"
    if advt_cr < THIN_CR:
        return "thin"
    if advt_cr < ADEQUATE_CR:
        return "adequate"
    return "liquid"


def days_to_liquidate(ticket_cr: float, advt_cr: Optional[float]) -> Optional[float]:
    """Sessions needed to unwind ``ticket_cr`` at ``PARTICIPATION_RATE``."""
    if not advt_cr or advt_cr <= 0:
        return None
    return ticket_cr / (advt_cr * PARTICIPATION_RATE)


def assess(closes, volumes) -> dict:
    """Full liquidity verdict for one stock.

    Returns the turnover, its band, and the exit horizon for a couple of
    representative tickets, so the dashboard can show why a name is flagged
    instead of only that it is.
    """
    advt = average_daily_value_cr(closes, volumes)
    band = classify(advt)
    result = {
        "advt_cr": round(advt, 2) if advt is not None else None,
        "liquidity_band": band,
        "sessions": len([c for c in (closes or []) if c]),
    }
    for ticket in _TICKETS_CR:
        days = days_to_liquidate(ticket, advt)
        key = f"days_to_exit_{int(ticket)}cr"
        result[key] = round(days, 1) if days is not None else None
    return result


def liquidity_warning(ticker: str, assessment: dict) -> Optional[str]:
    """One plain sentence when the position is hard to trade, else None."""
    band = assessment.get("liquidity_band")
    advt = assessment.get("advt_cr")
    if band not in ("illiquid", "thin") or advt is None:
        return None

    days = assessment.get("days_to_exit_1cr")
    horizon = f", ~{days:.0f} sessions to exit Rs 1 Cr" if days else ""
    label = "Illiquid" if band == "illiquid" else "Thin"
    return f"{label}: Rs {advt:.2f} Cr traded daily{horizon}"
