from models.core import CompanyFinancials

def score_economic_moat(fin: CompanyFinancials) -> str:
    roce = fin.roce or 0
    roe = fin.roe or 0
    
    current_borrowings = fin.debt_trend[-1] if fin.debt_trend else 0
    de_ratio = current_borrowings / ((fin.market_cap or 1) * 0.5)
    
    moat_score = 0
    if roce > 15: moat_score += 1
    if roe > 15: moat_score += 1
    if de_ratio < 0.5: moat_score += 1
    
    if moat_score == 3: return "Strong (Wide Moat)"
    elif moat_score == 2: return "Medium (Narrow Moat)"
    return "Weak/None"
