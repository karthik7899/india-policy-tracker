"""Data-quality vocabulary for derived metrics.

Every number this pipeline *derives* (as opposed to fetches) is only as
trustworthy as the series behind it, and the failure mode that actually hurt
us was not a crash — it was a confidently-wrong figure sailing through to the
dashboard. A revenue CAGR computed across an odd number of quarters read
+94.6% for a business growing under 7%; an intrinsic value built on one
annualized quarter read 3x the share price. Both were displayed to three
significant figures with no indication that anything was wrong.

So a derived figure carries a quality verdict alongside its value:

* ``OK``                — enough observations, result inside a plausible band.
* ``INSUFFICIENT_DATA`` — too few observations to compute the measure honestly.
* ``OUT_OF_BAND``       — computed, but so extreme that it is far more likely
                          to be a data artifact than a real business result.

Consumers decide what to do with each verdict: the dashboard can render a
figure as "insufficient data" instead of a number, and rankings and screens
can require ``OK`` so a parsing artifact never sorts to the top of a list.
The point is that a bad number becomes *labelled* rather than silent.
"""

from typing import Any, List, Optional, Tuple

from utils import to_float

OK = "ok"
INSUFFICIENT_DATA = "insufficient_data"
OUT_OF_BAND = "out_of_band"

# Plausible bands for the measures this pipeline derives. These are
# deliberately wide: the job is to catch artifacts (a seasonal mismatch
# annualized into triple digits, an intrinsic value untethered from the
# share price), not to second-guess a genuinely fast-growing company.
REVENUE_GROWTH_BAND = (-95.0, 150.0)
# Intrinsic value is judged as a multiple of the live share price. Inside a
# factor of three either way, a gap between the model and the market is a
# disagreement worth reading. Outside it, the two are not talking about the
# same company: either the earnings behind the estimate are distorted, or the
# formula's assumptions do not fit the business (Graham's multiple cannot
# describe a name trading at 60x earnings, and saying so is a statement about
# the model rather than a view on the stock).
INTRINSIC_VALUE_MULTIPLE_BAND = (0.33, 3.0)


def clean_series(values: Any) -> List[float]:
    """Coerce an arbitrary trend field into a list of usable floats.

    Screener rows arrive as strings, occasionally with blanks or dashes where
    a company has no entry for a period. Anything that will not coerce is
    dropped rather than defaulted to zero — a zero would silently corrupt
    every ratio computed downstream.
    """
    out: List[float] = []
    for raw in values or []:
        num = to_float(raw)
        if num is not None:
            out.append(num)
    return out


def classify(
    value: Optional[float],
    *,
    band: Optional[Tuple[float, float]] = None,
    observations: Optional[int] = None,
    min_observations: Optional[int] = None,
) -> str:
    """Return the quality verdict for one derived figure.

    ``observations``/``min_observations`` express how much history the measure
    needed; ``band`` expresses what range of results is believable. A missing
    value is always ``INSUFFICIENT_DATA`` — there is no such thing as a
    trustworthy ``None``.
    """
    if min_observations is not None and (observations or 0) < min_observations:
        return INSUFFICIENT_DATA
    if value is None:
        return INSUFFICIENT_DATA
    if band is not None and not (band[0] <= value <= band[1]):
        return OUT_OF_BAND
    return OK


def is_trustworthy(quality: Optional[str]) -> bool:
    """Only ``OK`` figures may be ranked, screened, or alerted on."""
    return quality == OK
