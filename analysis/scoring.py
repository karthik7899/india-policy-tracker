from models.core import Company

def calculate_aggregate_score(company: Company) -> int:
    score = 0
    fin = company.screener
    val = company.valuation
    
    if not hasattr(fin, "q_sales"): 
        return 0
        
    # Growth Score
    if fin.qoq_sales_growth and fin.qoq_sales_growth > 15: score += 1
    
    # Financial Score
    if fin.debt_to_equity is not None and fin.debt_to_equity < 0.5: score += 1
    if fin.current_ratio is not None and fin.current_ratio > 2.0: score += 1
    
    # Institutional Score
    if fin.fii_change is not None and fin.fii_change > 0: score += 1
    if fin.dii_change is not None and fin.dii_change > 0: score += 1
    
    # Moat Score
    if val and val.moat_status == "Strong (Wide Moat)": score += 2
    elif val and val.moat_status == "Medium (Narrow Moat)": score += 1
    
    # Valuation Score
    if val and val.is_bargain: score += 2
    elif val and val.graham_intrinsic_value and company.price and company.price < val.graham_intrinsic_value: score += 1
        
    return score
