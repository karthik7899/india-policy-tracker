from typing import List
from models.core import CompanyFinancials
from .graham import calculate_graham_intrinsic_value


def check_hyper_growth_risk(fin: CompanyFinancials) -> bool:
    """Hyper-Growth Reality Check (Prompt 8).

    Flags an expensive stock (P/E > 30) whose top-line growth is decelerating,
    warning of a potential valuation collapse. Deceleration is detected either
    from a sequential drop in the recent quarterly revenue trend or from a
    quarter-on-quarter growth rate that has cooled below the high-growth bar.
    """
    pe_ratio = fin.pe_ratio or 0
    if pe_ratio <= 30:
        return False

    trend = fin.quarterly_revenue_growth or []
    if len(trend) >= 2 and trend[-1] < trend[-2]:
        return True

    if fin.qoq_sales_growth is not None and fin.qoq_sales_growth < 15.0:
        return True

    return False


def generate_valuation_alerts(fin: CompanyFinancials, price: float) -> List[str]:
    alerts = []

    if fin.current_ratio is not None and fin.current_ratio < 2.0:
        alerts.append("Fails Current Ratio (< 2.0)")

    current_borrowings = fin.debt_trend[-1] if fin.debt_trend else 0
    net_current_assets = fin.net_current_assets or 0

    if current_borrowings > net_current_assets:
        alerts.append("Fails Debt Limit (Debt > Net Assets)")

    # Graham's defensive rule is P/E < 15 on its own terms; the intrinsic value
    # is the EXEMPTION from it, not the test. So a P/E above 15 still fails when
    # no intrinsic value is available to justify it — but the reason has to say
    # that, and it did not.
    #
    # calculate_graham_intrinsic_value returns 0.0 to mean "we cannot value this
    # company", and `price <= 0.0 * 1.2` is False for every positive price. Any
    # holding the model declined to value therefore collected an alert reading
    # "Price > Intrinsic" — a comparison that was never performed, against an
    # intrinsic value that does not exist. Six holdings carry that sentence in
    # the current payload.
    #
    # The VERDICT was right and is unchanged: P/E > 15 with no exemption
    # available still fails. What was wrong is the reason given for it, which
    # is the part a reader acts on — someone checking that claim would go
    # looking for an intrinsic value the model had explicitly refused to
    # produce.
    graham_value = calculate_graham_intrinsic_value(fin)
    pe_ratio = fin.pe_ratio or 0
    if pe_ratio > 15:
        if graham_value > 0:
            if price > graham_value * 1.2:
                alerts.append(
                    f"Fails P/E Screen (P/E {pe_ratio} > 15 & Price > Intrinsic)"
                )
        else:
            alerts.append(
                f"Fails P/E Screen (P/E {pe_ratio} > 15; no intrinsic value to "
                "justify it)"
            )

    div_yield = fin.dividend_yield or 0
    if div_yield == 0:
        alerts.append("No Dividend Yield")

    if check_hyper_growth_risk(fin):
        alerts.append(
            "Hyper-Growth Reality Check (P/E > 30 & revenue growth decelerating)"
        )

    return alerts
