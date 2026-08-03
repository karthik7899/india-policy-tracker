"""Aggregate scoring: what the number is allowed to mean.

The score used to be purely additive. Every policy headline added 3-5 points
with no cap, no deduplication and no age limit, while the risk findings —
failed debt screens, failed P/E screens, margin collapse — were collected into
a list for display and subtracted nothing. BHEL scored 44 that way: eleven
news items worth ~42 points plus 2 for FII buying, zero from fundamentals, and
five risk flags worth nothing. Among the scored "policy events" were a 2013
project headline, two index-move stories that merely listed BHEL, and the same
transformer launch counted twice under different phrasings.

So the number was a press-clipping count wearing the name of a quality score.
It is now two numbers that are reported separately and summed:

  * ``fundamental_score`` — earned from returns, balance sheet and valuation,
    and *lost* to the risks that used to be cosmetic.
  * ``momentum_score``    — policy and news flow, deduplicated, age-filtered
    and capped so coverage volume cannot dominate the total.

``confidence`` remains a statement about how many inputs were available, not
about the company. The dashboard labels it as data completeness for that
reason — sitting unlabelled beside the score, "High" read as a verdict.
"""

import datetime
import re

from models.core import Company, CompanyScore
from config_scoring import SCORING_CONFIG

# News flow is a real signal but a bounded one. Past this, extra coverage says
# more about a company's press office than its prospects.
POLICY_POINT_CAP = 8
# Older than this it is history, not a catalyst.
POLICY_MAX_AGE_DAYS = 120

# Risk deductions. These mirror findings the pipeline already produces; the
# point is that they now move the number instead of only the prose.
PENALTY_FAILED_SCREEN = 2
PENALTY_HIGH_DEBT = 2
PENALTY_SHRINKING_REVENUE = 2
PENALTY_PROMOTER_EXIT = 2
PENALTY_POOR_LIQUIDITY = 1
PENALTY_INSTITUTIONAL_SELLING = 1
PENALTY_MARGIN_CONTRACTION = 1

_SCREEN_FAILURES = ("Debt Limit", "P/E Screen", "Hyper-Growth", "Current Ratio")


def _normalize(text: str) -> str:
    """Collapse a headline to a comparison key.

    The same event reaches us worded several ways ("BHEL unveils India's first
    indigenous 1200 kV transformer" / "BHEL unveils India's first 1200 kV
    homegrown transformer"), and each was scoring separately.
    """
    return re.sub(r"[^a-z0-9 ]+", "", (text or "").lower())


def _event_age_days(event, today):
    raw = event.get("date")
    if not raw:
        return None  # undated: allowed through, but see the dedup cap
    for parse in (
        lambda s: datetime.date.fromisoformat(str(s)[:10]),
        lambda s: datetime.datetime.strptime(str(s)[:16], "%a, %d %b %Y").date(),
    ):
        try:
            return (today - parse(raw)).days
        except Exception:
            continue
    return None


def _score_policy_events(company, today):
    """Points from policy/news flow: deduplicated, age-filtered, capped."""
    points = 0
    reasons = []
    seen = set()
    for ev in getattr(company, "policy_events", None) or []:
        title = ev.get("title") or ev.get("scheme") or ev.get("product") or ""
        key = _normalize(title)
        if not key or key in seen:
            continue
        seen.add(key)

        age = _event_age_days(ev, today)
        if age is not None and age > POLICY_MAX_AGE_DAYS:
            continue

        ev_type = (ev.get("event_type") or "").upper()
        if "PLI" in title.upper() or ev_type == "PLI":
            gain, label = SCORING_CONFIG.pli_approval, "PLI Approval / Target"
        elif "AGREEMENT" in ev_type or "MOU" in ev_type:
            gain, label = SCORING_CONFIG.government_contract, "Government Contract/MoU"
        elif "LAUNCH" in ev_type:
            gain, label = SCORING_CONFIG.policy_news, "Capacity/Product Launch"
        else:
            gain, label = SCORING_CONFIG.pib_announcement, "Policy Notification"

        if points + gain > POLICY_POINT_CAP:
            gain = POLICY_POINT_CAP - points
        if gain <= 0:
            break
        points += gain
        reasons.append(f"{label}: {title}")
    return points, reasons


def calculate_aggregate_score(company: Company) -> CompanyScore:
    fin = company.screener
    val = company.valuation
    today = datetime.date.today()

    momentum, reasons = _score_policy_events(company, today)
    if not reasons:
        momentum += SCORING_CONFIG.sector_mapping_fallback
        reasons.append("Sector benefits from macro policy tailwinds (Fallback)")

    fundamental = 0
    risks = []

    # Data Completeness Confidence Check
    data_points = 0
    if fin is not None and getattr(fin, "q_sales", None) is not None:
        data_points += 1
    if fin and fin.debt_to_equity is not None:
        data_points += 1
    if fin and getattr(fin, "sales_trend", None):
        data_points += 1
    if fin and fin.roce is not None:
        data_points += 1
    if val and val.moat_status is not None:
        data_points += 1
    if val and val.graham_intrinsic_value is not None:
        data_points += 1

    if data_points == 0:
        return CompanyScore(
            overall_score=momentum,
            fundamental_score=0,
            momentum_score=momentum,
            confidence="Very Low",
            reasons=reasons,
            risks=["No financial data available for scoring."],
            recommendations=["Monitor (Data Unavailable)"],
        )

    confidence = (
        "High" if data_points >= 5 else ("Medium" if data_points >= 3 else "Low")
    )

    # Growth momentum, on the seasonally sound measure. The sequential
    # quarter-on-quarter figure this used to read called BHEL a contraction
    # (-37.5%) while the business grew 27% year on year.
    growth = getattr(fin, "revenue_ttm_growth_pct", None)
    if growth is not None:
        if growth >= SCORING_CONFIG.min_qoq_sales_growth:
            fundamental += 1
            reasons.append(f"Strong revenue growth (TTM {growth:+.1f}%)")
        elif growth < 0:
            fundamental -= PENALTY_SHRINKING_REVENUE
            risks.append(f"Revenue shrinking (TTM {growth:+.1f}%)")

    if fin.opm_expansion is not None:
        if fin.opm_expansion >= SCORING_CONFIG.min_operating_margin_expansion:
            fundamental += 1
            reasons.append(f"Operating Margin Expansion (+{fin.opm_expansion}%)")
        elif fin.opm_expansion <= -SCORING_CONFIG.min_operating_margin_expansion:
            fundamental -= PENALTY_MARGIN_CONTRACTION
            risks.append(f"Operating margin contracted ({fin.opm_expansion}pp)")

    # Financial Strength
    if fin.debt_to_equity is not None:
        if fin.debt_to_equity < SCORING_CONFIG.max_debt_to_equity:
            fundamental += 1
            reasons.append(f"Low Debt to Equity ({fin.debt_to_equity})")
        elif fin.debt_to_equity > 1.0:
            fundamental -= PENALTY_HIGH_DEBT
            risks.append(f"High Debt to Equity ({fin.debt_to_equity})")

    if fin.current_ratio is not None:
        if fin.current_ratio >= SCORING_CONFIG.min_current_ratio:
            fundamental += 1
            reasons.append(f"Strong Liquidity (Current Ratio: {fin.current_ratio})")
        elif fin.current_ratio < 1.0:
            fundamental -= PENALTY_POOR_LIQUIDITY
            risks.append("Poor Liquidity (Current Ratio < 1)")

    # Capital Allocation
    if fin.roce is not None and fin.roce >= SCORING_CONFIG.min_roce:
        fundamental += 1
        reasons.append(f"High Return on Capital (ROCE: {fin.roce}%)")
    if fin.roe is not None and fin.roe >= SCORING_CONFIG.min_roe:
        fundamental += 1
        reasons.append(f"High Return on Equity (ROE: {fin.roe}%)")

    # Ownership and institutional flow
    if fin.promoter_change is not None and fin.promoter_change <= -1.0:
        fundamental -= PENALTY_PROMOTER_EXIT
        risks.append(f"Promoters cut their stake ({fin.promoter_change}%)")

    if fin.fii_change is not None and fin.fii_change > 0:
        fundamental += SCORING_CONFIG.fii_accumulation_points
        reasons.append(f"FII Accumulation (+{fin.fii_change}%)")
    elif fin.fii_change is not None and fin.fii_change < -1.0:
        fundamental -= PENALTY_INSTITUTIONAL_SELLING
        risks.append(f"FII Selling ({fin.fii_change}%)")

    if fin.dii_change is not None and fin.dii_change > 0:
        fundamental += SCORING_CONFIG.dii_accumulation_points
        reasons.append(f"DII Accumulation (+{fin.dii_change}%)")

    # Moat
    if val and val.moat_status == "Strong (Wide Moat)":
        fundamental += SCORING_CONFIG.wide_moat_points
        reasons.append("Wide Economic Moat (Sustained Margin Expansion)")
    elif val and val.moat_status == "Medium (Narrow Moat)":
        fundamental += SCORING_CONFIG.narrow_moat_points
        reasons.append("Narrow Economic Moat")

    # Valuation
    if val and val.is_bargain:
        fundamental += SCORING_CONFIG.bargain_points
        reasons.append("Deep Value Bargain (Price < NCAV)")
    elif (
        val
        and val.graham_intrinsic_value
        and company.price
        and company.price < val.graham_intrinsic_value
    ):
        fundamental += SCORING_CONFIG.graham_undervalued_points
        reasons.append(
            f"Trading below Graham Intrinsic Value ({val.graham_intrinsic_value})"
        )

    # Every failed screen now costs points. These are the findings that used to
    # be listed beside a high score without ever reducing it.
    for alert in (val.valuation_alerts if val else []) or []:
        if any(marker in str(alert) for marker in _SCREEN_FAILURES):
            fundamental -= PENALTY_FAILED_SCREEN
            risks.append(str(alert))

    overall = fundamental + momentum
    if overall >= SCORING_CONFIG.strong_buy_threshold:
        recommendation = "Strong Buy Candidate"
    elif overall >= SCORING_CONFIG.buy_threshold:
        recommendation = "Buy Candidate"
    elif overall >= SCORING_CONFIG.hold_threshold:
        recommendation = "Hold / Monitor"
    else:
        recommendation = "Avoid / High Risk"

    return CompanyScore(
        overall_score=overall,
        fundamental_score=fundamental,
        momentum_score=momentum,
        confidence=confidence,
        reasons=reasons,
        risks=risks,
        recommendations=[recommendation],
    )
