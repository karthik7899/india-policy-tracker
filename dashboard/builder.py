from typing import Dict, Any
from analysis.graham import check_enterprising_bargain
from analysis.buffett import calculate_owner_earnings
from analysis.moat import score_economic_moat
from analysis.scoring import calculate_aggregate_score
from models.core import Company, CompanyFinancials, CompanyValuation


def build_dashboard_views(data: Dict[str, Any], watchlist: Dict[str, Any]):
    """
    Compiles valuation and moat metrics into specialized views for the dashboard.
    """
    margin_of_safety = []
    buffett_valuation = []

    # Pre-compute policy events mapped by ticker/name
    policy_map = {}
    for ev in data.get("emerging_competitors", []):
        name = ev.get("name", ev.get("company", ""))
        policy_map.setdefault(name.upper(), []).append(
            {"event_type": "pli", "scheme": ev.get("scheme")}
        )

    for ev in data.get("corporate_agreements", []):
        name = ev.get("company", "")
        policy_map.setdefault(name.upper(), []).append(
            {"event_type": "agreement", "title": ev.get("title")}
        )

    for ev in data.get("product_launches", []):
        name = ev.get("company", "")
        policy_map.setdefault(name.upper(), []).append(
            {"event_type": "launch", "product": ev.get("product")}
        )

    for ev in data.get("corporate_filings", []):
        name = ev.get("company", "")
        policy_map.setdefault(name.upper(), []).append(
            {"event_type": "filing", "title": ev.get("filing")}
        )

    for ev in data.get("sebi_filings", []):
        name = ev.get("company", "")
        policy_map.setdefault(name.upper(), []).append(
            {"event_type": "sebi", "title": ev.get("title")}
        )

    for sector, stocks in watchlist.items():
        if sector == "macro_indicators":
            continue

        for stock in stocks:
            sc_data = stock.get("screener")
            if not sc_data:
                continue

            # Coerce into Pydantic model for analysis
            if isinstance(sc_data, dict):
                try:
                    fin = CompanyFinancials(**sc_data)
                except Exception as e:
                    # Ignore validation errors for missing fields on empty responses
                    continue
            else:
                fin = sc_data

            price = float(stock.get("price") or 0.0)

            # Create full Company model
            comp = Company(
                ticker=stock.get("ticker", ""), name=stock.get("name", ""), price=price
            )

            # Attach policy events
            comp_events = policy_map.get(comp.name.upper(), []) + policy_map.get(
                comp.ticker.upper(), []
            )
            comp.policy_events = comp_events

            # Analyze
            is_bargain, ncav = check_enterprising_bargain(fin, price)
            owner_earnings = calculate_owner_earnings(fin)
            moat = score_economic_moat(fin)

            # Build Valuation Model
            val = CompanyValuation(
                is_bargain=is_bargain,
                ncav_per_share=ncav,
                owner_earnings=owner_earnings,
                moat_status=moat,
            )

            comp.screener = fin
            comp.valuation = val

            # Calculate aggregate score
            score_obj = calculate_aggregate_score(comp)
            comp.score = score_obj
            score_dict = (
                score_obj.model_dump()
                if hasattr(score_obj, "model_dump")
                else score_obj.dict()
            )

            # Add to Margin of Safety list if it's a bargain or PE < 15
            pe_ratio = fin.pe_ratio or 0
            if is_bargain or (pe_ratio > 0 and pe_ratio < 15):
                margin_of_safety.append(
                    {
                        "ticker": comp.ticker,
                        "name": comp.name,
                        "price": comp.price,
                        "pe_ratio": pe_ratio,
                        "ncav": ncav,
                        "is_bargain": is_bargain,
                        "score": score_dict,
                    }
                )

            # Add to Buffett Valuation list
            buffett_valuation.append(
                {
                    "ticker": comp.ticker,
                    "name": comp.name,
                    "owner_earnings": owner_earnings,
                    "moat": moat,
                    "score": score_dict,
                }
            )

    # Sort and add to data dictionary
    data["margin_of_safety"] = sorted(
        margin_of_safety, key=lambda x: x["score"]["overall_score"], reverse=True
    )
    data["buffett_valuation"] = sorted(
        buffett_valuation, key=lambda x: x["score"]["overall_score"], reverse=True
    )
