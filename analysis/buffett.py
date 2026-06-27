from models.core import CompanyFinancials

def calculate_owner_earnings(fin: CompanyFinancials) -> float:
    # Warren Buffett Owner Earnings
    current_borrowings = 0
    if fin.debt_trend:
        current_borrowings = fin.debt_trend[-1]
    
    depreciation = current_borrowings * 0.08
    net_profit = (fin.q_net_profit or 0) * 4
    owner_earnings = net_profit + depreciation - (fin.capex or 0)
    return round(owner_earnings, 1)

def test_retained_earnings(fin: CompanyFinancials) -> float:
    # $1 Retained Earnings Test
    retained_ratio = 1.2
    net_profit = (fin.q_net_profit or 0) * 4
    
    if net_profit > 0:
        retained_est = net_profit * 5 * 0.7
        mcap_change_est = net_profit * 5 * 10 * 0.2
        retained_ratio = mcap_change_est / retained_est if retained_est > 0 else 0
        
    return round(retained_ratio, 2)
