import os
from typing import Optional, Tuple

from analysis.data_quality import clean_series
from models.core import CompanyFinancials

# Graham's revised formula divides by the prevailing high-grade bond yield,
# because an equity's fair multiple depends on what riskless capital earns.
# The original text used the 4.4% AAA yield of the day as the numerator and
# the current yield as the denominator. Omitting that correction entirely —
# as this module used to — leaves every valuation quoted in 1962 interest
# rates, which in Indian conditions inflates fair value by roughly 60%.
_GRAHAM_BASE_YIELD = 4.4
_CURRENT_BOND_YIELD = float(os.environ.get("INDIA_BOND_YIELD", "7.0"))

# Graham's ``g`` is expected annual earnings growth sustained over 7-10 years,
# so it has to be capped well below what a single good year can print. The
# band's floor is zero rather than negative: the formula's shape stops being
# meaningful once the multiple goes to pieces, and a shrinking company is
# better described by the valuation alerts than by a negative multiple.
_GROWTH_FLOOR = 0.0
_GROWTH_CEILING = 15.0
_DEFAULT_GROWTH = 6.0


_MIN_CAGR_PERIODS = 4


def _cagr(values) -> Optional[float]:
    """Compound annual growth across a series of annual periods, as a percent.

    ``None`` unless there are enough periods and both ends are positive: a
    negative or zero endpoint makes the root either imaginary or infinite, and
    a company that was losing money is not described by a growth rate anyway.

    Two things about the series this reads, both measured rather than assumed:

    * Screener's P&L row ends with a TTM column, not a fiscal year. HAL's last
      annual_sales_trend entry is 33785 and its four trailing quarters sum to
      exactly 33785. That endpoint is still a full twelve-month period, so it
      is the right thing to compound to; it just means the span is ``len - 1``
      years only approximately, since TTM ends wherever the last reported
      quarter does.
    * A CAGR sees two points and ignores everything between them, so it is
      blind to a peak. ZENTEC's revenue ran 70 -> 974 -> 671: first-to-last
      compounds to 57% a year while the business is in fact well off its high.
      That is why the caller floors this with the recent trend rather than
      trusting it alone.
    """
    series = clean_series(values)
    if len(series) < _MIN_CAGR_PERIODS:
        return None
    first, last = series[0], series[-1]
    if first <= 0 or last <= 0:
        return None
    return ((last / first) ** (1.0 / (len(series) - 1)) - 1.0) * 100.0


def _ttm_growth(values) -> Optional[float]:
    """Trailing-twelve-month growth: four quarters against the four before.

    Every quarter of the year appears once on each side, so Indian fiscal-year
    seasonality cancels instead of being read as growth.
    """
    series = clean_series(values)
    if len(series) < 8:
        return None
    prior, latest = sum(series[-8:-4]), sum(series[-4:])
    if prior <= 0 or latest <= 0:
        return None
    return (latest / prior - 1.0) * 100.0


def _sustainable_growth(fin: CompanyFinancials) -> Tuple[float, str]:
    """Graham's ``g``, and an honest label for what it was actually measured on.

    Graham's ``g`` is EARNINGS growth expected to be sustained over 7-10 years.
    This used to be fed one year of REVENUE growth — the wrong quantity over
    the wrong span, twice removed from what the formula asks for. Revenue
    growth flatters any company growing the top line faster than the bottom,
    which is most of them during an expansion.

    Earnings is preferred to revenue, and where both a long record and a recent
    trend exist the LOWER of the two is taken. Graham does not pay for growth
    that only one of them can see, and each failure mode is real in this
    watchlist:

    * STLTECH's revenue is flat across five years (0.7% compounded) but up 36%
      on the trailing year. The old one-year input priced it at the 15% ceiling
      — a rebound read as a trend.
    * ZENTEC compounds at 57% first-to-last, from a base of 70, while its
      revenue has fallen from a peak of 974 to 671. A CAGR alone would have
      handed a shrinking company the maximum multiple.

    Taking the minimum answers both: neither a one-year bounce nor an old boom
    survives a check against the other.

    The basis is returned rather than inferred, because these are not
    interchangeable and a multiple derived from revenue deserves less weight
    than one derived from earnings. Nothing downstream could previously tell
    them apart.

    A note on the clamp, because the numbers invite a wrong conclusion.
    Measured across the watchlist, roughly half the holdings hit the 15%
    ceiling on every one of these bases. That is not the clamp misfiring: very
    few businesses compound earnings above 15% for a decade, and refusing to
    extrapolate a boom is the conservatism the ceiling exists to impose. What
    was wrong with the original ``qoq_sales_growth`` input was that its clamp
    fired on SEASONALITY — noise, not growth. A multi-year earnings CAGR at the
    ceiling has earned its way there.
    """
    families = (
        ("annual_eps_trend", "eps_trend", "EPS", ""),
        ("annual_sales_trend", "sales_trend", "revenue", " (earnings proxy)"),
    )

    # Every multi-year basis is tried before any single-year one, INCLUDING a
    # multi-year revenue CAGR ahead of single-year earnings growth. "Sustained"
    # is the load-bearing word in Graham's definition of g, so when only one of
    # span and quantity can be had, span wins. It is also the steadier of the
    # two empirically: across this watchlist a single year of EPS growth clamps
    # at one end or the other for two holdings in three, against under half for
    # the multi-year revenue CAGR.
    for annual, quarterly, label, proxy in families:
        long_run = _cagr(getattr(fin, annual, None))
        if long_run is None:
            continue
        recent = _ttm_growth(getattr(fin, quarterly, None))
        if recent is not None:
            return (
                _clamp(min(long_run, recent)),
                f"{label} CAGR floored by trailing year{proxy}",
            )
        return _clamp(long_run), f"{label} CAGR{proxy}"

    for _annual, quarterly, label, proxy in families:
        recent = _ttm_growth(getattr(fin, quarterly, None))
        if recent is not None:
            return _clamp(recent), f"trailing-year {label} growth{proxy}"

    return _DEFAULT_GROWTH, "default (no usable series)"


def _clamp(growth: float) -> float:
    return max(_GROWTH_FLOOR, min(_GROWTH_CEILING, growth))


def graham_growth_basis(fin: CompanyFinancials) -> str:
    """Which series the multiple's growth term was measured on."""
    return _sustainable_growth(fin)[1]


def _trailing_eps(fin: CompanyFinancials) -> Optional[float]:
    """Earnings per share over the trailing four quarters.

    Returns ``None`` when a full year of quarters is not available, so callers
    can decline to value the company rather than quietly annualizing whichever
    single quarter happened to be reported last.
    """
    ttm = getattr(fin, "ttm_eps", None)
    if ttm is not None:
        return float(ttm)
    series = clean_series(getattr(fin, "eps_trend", None))
    if len(series) >= 4:
        return sum(series[-4:])
    return None


def _earning_power_is_intact(fin: CompanyFinancials) -> bool:
    """Is there stable earning power here at all?

    Graham's formula prices a durable stream of profits. Two states refute
    that premise outright, and the formula returns nonsense for both:

    * A loss over the trailing year. ideaForge's trailing EPS is -3.96, and
      the multiple duly produced an intrinsic value of *negative* Rs 95.8,
      which was stored and displayed as though it meant something.
    * A latest quarter that has swung to an operating loss. BPCL's trailing
      EPS of 39.48 still contains profitable quarters, so the model valued it
      at Rs 823 against a Rs 320 price — a 129% "upside" on a company losing
      money at the operating line this quarter (-2.7% margin, down 10.7pp).
      Trailing profit is stale evidence once the current quarter turns.
    """
    q_eps = getattr(fin, "q_eps", None)
    q_opm = getattr(fin, "q_opm", None)
    if q_eps is not None and q_eps < 0:
        return False
    if q_opm is not None and q_opm < 0:
        return False
    return True


def calculate_graham_intrinsic_value(fin: CompanyFinancials) -> float:
    """Graham's revised intrinsic value: ``EPS x (8.5 + 2g) x 4.4 / Y``.

    Returns 0.0 when the company cannot be valued this way — no full trailing
    year of earnings, a trailing loss, or a latest quarter that has turned
    down. That is an explicit "we cannot say" which callers gate on, rather
    than a confident number derived from earnings that no longer exist.
    """
    eps = _trailing_eps(fin)
    if eps is None or eps <= 0:
        return 0.0
    if not _earning_power_is_intact(fin):
        return 0.0
    growth, _basis = _sustainable_growth(fin)
    multiple = (8.5 + 2 * growth) * (_GRAHAM_BASE_YIELD / _CURRENT_BOND_YIELD)
    return round(eps * multiple, 1)


def check_enterprising_bargain(
    fin: CompanyFinancials, price: float
) -> Tuple[bool, float]:
    shares_outstanding = 1.0
    if price > 0:
        mcap = fin.market_cap or 0
        shares_outstanding = mcap / price

    ncav_per_share = (
        (fin.net_current_assets or 0) / shares_outstanding
        if shares_outstanding > 0
        else 0
    )
    ncav_per_share = round(ncav_per_share, 1)
    is_bargain = (price < ncav_per_share) if price > 0 else False

    return is_bargain, ncav_per_share
