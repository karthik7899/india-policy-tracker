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

    graham_value = calculate_graham_intrinsic_value(fin)
    is_graham_value_pass = price <= graham_value * 1.2

    pe_ratio = fin.pe_ratio or 0
    if pe_ratio > 15 and not is_graham_value_pass:
        alerts.append(f"Fails P/E Screen (P/E {pe_ratio} > 15 & Price > Intrinsic)")

    div_yield = fin.dividend_yield or 0
    if div_yield == 0:
        alerts.append("No Dividend Yield")

    if check_hyper_growth_risk(fin):
        alerts.append(
            "Hyper-Growth Reality Check (P/E > 30 & revenue growth decelerating)"
        )

    return alerts
