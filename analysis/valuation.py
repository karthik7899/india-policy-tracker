from typing import List
from models.core import CompanyFinancials
from .graham import calculate_graham_intrinsic_value


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

    return alerts
