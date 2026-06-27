from typing import Tuple
from models.core import CompanyFinancials

def calculate_graham_intrinsic_value(fin: CompanyFinancials) -> float:
    eps = (fin.q_eps or 0) * 4
    expected_growth = 12.0
    if fin.qoq_sales_growth is not None:
        expected_growth = max(5.0, min(25.0, fin.qoq_sales_growth))
    return round(eps * (8.5 + 2 * expected_growth), 1)

def check_enterprising_bargain(fin: CompanyFinancials, price: float) -> Tuple[bool, float]:
    shares_outstanding = 1.0
    if price > 0:
        mcap = fin.market_cap or 0
        shares_outstanding = mcap / price
    
    ncav_per_share = (fin.net_current_assets or 0) / shares_outstanding if shares_outstanding > 0 else 0
    ncav_per_share = round(ncav_per_share, 1)
    is_bargain = (price < ncav_per_share) if price > 0 else False
    
    return is_bargain, ncav_per_share
