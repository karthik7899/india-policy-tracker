from models.core import Company, CompanyScore
from config_scoring import SCORING_CONFIG

def calculate_aggregate_score(company: Company) -> CompanyScore:
    score = 0
    reasons = []
    risks = []
    
    fin = company.screener
    val = company.valuation
    
    # Policy Tailwind Evaluation
    if hasattr(company, 'policy_events') and company.policy_events:
        for ev in company.policy_events:
            ev_type = ev.get('event_type') or ''
            ev_title = ev.get('title') or ev.get('scheme') or ev.get('product') or ''
            
            if 'PLI' in ev_title.upper() or ev_type == 'pli':
                score += SCORING_CONFIG.pli_approval
                reasons.append(f"PLI Approval / Target: {ev_title}")
            elif 'AGREEMENT' in ev_type.upper() or 'MOU' in ev_type.upper():
                score += SCORING_CONFIG.government_contract
                reasons.append(f"Government Contract/MoU: {ev_title}")
            elif 'LAUNCH' in ev_type.upper():
                score += SCORING_CONFIG.policy_news
                reasons.append(f"Capacity/Product Launch: {ev_title}")
            else:
                score += SCORING_CONFIG.pib_announcement
                reasons.append(f"Policy Notification: {ev_title}")
    else:
        # Fallback to Sector categorization
        score += SCORING_CONFIG.sector_mapping_fallback
        reasons.append("Sector benefits from macro policy tailwinds (Fallback)")

    # Data Completeness Confidence Check
    data_points = 0
    total_data_points = 6
    if hasattr(fin, "q_sales") and fin.q_sales is not None: data_points += 1
    if fin and fin.debt_to_equity is not None: data_points += 1
    if fin and fin.qoq_sales_growth is not None: data_points += 1
    if fin and fin.roce is not None: data_points += 1
    if val and val.moat_status is not None: data_points += 1
    if val and val.graham_intrinsic_value is not None: data_points += 1
    
    if data_points == 0:
        return CompanyScore(
            overall_score=score,
            confidence="Very Low",
            reasons=reasons,
            risks=["No financial data available for scoring."],
            recommendations=["Monitor (Data Unavailable)"]
        )
    
    confidence = "High" if data_points >= 5 else ("Medium" if data_points >= 3 else "Low")
        
    # Growth Momentum
    if fin.qoq_sales_growth and fin.qoq_sales_growth >= SCORING_CONFIG.min_qoq_sales_growth: 
        score += 1
        reasons.append(f"Strong QoQ Sales Growth ({fin.qoq_sales_growth}%)")
    elif fin.qoq_sales_growth and fin.qoq_sales_growth < 0:
        risks.append(f"Negative QoQ Sales Growth ({fin.qoq_sales_growth}%)")
        
    if fin.opm_expansion and fin.opm_expansion >= SCORING_CONFIG.min_operating_margin_expansion:
        score += 1
        reasons.append(f"Operating Margin Expansion (+{fin.opm_expansion}%)")
    
    # Financial Strength
    if fin.debt_to_equity is not None:
        if fin.debt_to_equity < SCORING_CONFIG.max_debt_to_equity:
            score += 1
            reasons.append(f"Low Debt to Equity ({fin.debt_to_equity})")
        elif fin.debt_to_equity > 1.0:
            risks.append(f"High Debt to Equity ({fin.debt_to_equity})")
            
    if fin.current_ratio is not None:
        if fin.current_ratio >= SCORING_CONFIG.min_current_ratio:
            score += 1
            reasons.append(f"Strong Liquidity (Current Ratio: {fin.current_ratio})")
        elif fin.current_ratio < 1.0:
            risks.append(f"Poor Liquidity (Current Ratio < 1)")
    
    # Capital Allocation
    if fin.roce is not None and fin.roce >= SCORING_CONFIG.min_roce:
        score += 1
        reasons.append(f"High Return on Capital (ROCE: {fin.roce}%)")
    if fin.roe is not None and fin.roe >= SCORING_CONFIG.min_roe:
        score += 1
        reasons.append(f"High Return on Equity (ROE: {fin.roe}%)")
    
    # Institutional Interest
    if fin.fii_change is not None and fin.fii_change > 0: 
        score += SCORING_CONFIG.fii_accumulation_points
        reasons.append(f"FII Accumulation (+{fin.fii_change}%)")
    elif fin.fii_change is not None and fin.fii_change < -1.0:
        risks.append(f"FII Selling ({fin.fii_change}%)")
        
    if fin.dii_change is not None and fin.dii_change > 0: 
        score += SCORING_CONFIG.dii_accumulation_points
        reasons.append(f"DII Accumulation (+{fin.dii_change}%)")
    
    # Moat Score (Competitive Advantage)
    if val and val.moat_status == "Strong (Wide Moat)": 
        score += SCORING_CONFIG.wide_moat_points
        reasons.append("Wide Economic Moat (Sustained Margin Expansion)")
    elif val and val.moat_status == "Medium (Narrow Moat)": 
        score += SCORING_CONFIG.narrow_moat_points
        reasons.append("Narrow Economic Moat")
    
    # Valuation Score
    if val and val.is_bargain: 
        score += SCORING_CONFIG.bargain_points
        reasons.append("Deep Value Bargain (Price < NCAV)")
    elif val and val.graham_intrinsic_value and company.price and company.price < val.graham_intrinsic_value: 
        score += SCORING_CONFIG.graham_undervalued_points
        reasons.append(f"Undervalued vs Graham Intrinsic Value ({val.graham_intrinsic_value})")
    elif val and val.graham_intrinsic_value and company.price and company.price > val.graham_intrinsic_value * 1.5:
        risks.append(f"Overvalued vs Graham Intrinsic Value ({val.graham_intrinsic_value})")
        
    if val and hasattr(val, "valuation_alerts") and val.valuation_alerts:
        for alert in val.valuation_alerts:
            risks.append(alert)
            
    # Generate Recommendations
    recommendations = []
    if score >= SCORING_CONFIG.strong_buy_threshold:
        recommendations.append("Strong Buy Candidate")
    elif score >= SCORING_CONFIG.buy_threshold:
        recommendations.append("Buy / Accumulate Candidate")
    elif score >= SCORING_CONFIG.hold_threshold:
        recommendations.append("Hold / Neutral")
    else:
        recommendations.append("Monitor / Underweight")
        
    if risks:
        recommendations.append("Ensure risks are hedged or sizing is adjusted appropriately.")

    return CompanyScore(
        overall_score=score,
        confidence=confidence,
        reasons=reasons,
        risks=risks,
        recommendations=recommendations
    )
