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


def _sustainable_growth(fin: CompanyFinancials) -> float:
    """The growth rate to feed Graham's multiple, on a seasonally sound basis.

    Prefers trailing-twelve-month revenue growth (four quarters against the
    four before them, so every quarter of the year appears once on each side).
    Falls back to a conservative default rather than to sequential quarterly
    growth, which was the previous input: ``qoq_sales_growth`` compares one
    quarter with the quarter immediately before it, so it measured Indian
    fiscal-year seasonality more than it measured growth. Its observed range
    across the watchlist was -37% to +341%, which meant the clamp — not the
    business — decided the multiple for half the holdings.
    """
    series = clean_series(getattr(fin, "sales_trend", None))
    if len(series) >= 8:
        prior = sum(series[-8:-4])
        latest = sum(series[-4:])
        if prior > 0 and latest > 0:
            ttm_growth = (latest / prior - 1.0) * 100.0
            return max(_GROWTH_FLOOR, min(_GROWTH_CEILING, ttm_growth))
    return _DEFAULT_GROWTH


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
    growth = _sustainable_growth(fin)
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
