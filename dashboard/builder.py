from typing import Dict, Any
from analysis.graham import (
    check_enterprising_bargain,
    calculate_graham_intrinsic_value,
)
from analysis.buffett import calculate_owner_earnings, test_retained_earnings
from analysis.moat import score_economic_moat
from analysis.valuation import generate_valuation_alerts, check_hyper_growth_risk
from analysis.scoring import calculate_aggregate_score
from models.core import Company, CompanyFinancials, CompanyValuation

# Alert substrings that constitute a failure of Graham's Defensive Investor screen.
_DEFENSIVE_FAIL_MARKERS = ("Current Ratio", "Debt Limit", "P/E Screen", "Dividend")

# Clamp the Graham-derived fallback potential to a sane display band. The Graham
# formula can produce extreme intrinsic values for high-growth names; this keeps
# the headline "potential" figure realistic when we have no analyst target.
_FUNDAMENTAL_UPSIDE_FLOOR = -50.0
_FUNDAMENTAL_UPSIDE_CAP = 60.0


def _to_float(value):
    """Best-effort numeric coercion tolerant of None/strings/%/N/A."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace("+", "").replace(",", "")
        if not cleaned or cleaned.upper() in {"N/A", "NA", "-", "—"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _apply_potential_estimate(stock, price, graham_value):
    """Tag each stock's upside with how it was derived and refresh stale targets.

    Stocks with live analyst coverage keep their consensus target. Stocks without
    coverage fall back to a transparent Graham-based fundamental estimate instead
    of a frozen, manually-seeded target — and are clearly labelled as such so the
    two are never conflated.
    """
    has_analyst_coverage = bool(_to_float(stock.get("analyst_count"))) and bool(
        stock.get("target")
    )

    # Always expose the raw intrinsic value for reference.
    if graham_value and graham_value > 0:
        stock["fundamental_value"] = round(graham_value, 1)

    if has_analyst_coverage:
        stock["estimate_method"] = "Analyst Consensus"
        return

    stock["estimate_method"] = "Fundamental Estimate"

    # Derive a clamped upside from the Graham intrinsic value when we can.
    if price > 0 and graham_value and graham_value > 0:
        upside = (graham_value - price) / price * 100
        upside = max(_FUNDAMENTAL_UPSIDE_FLOOR, min(_FUNDAMENTAL_UPSIDE_CAP, upside))
        stock["growth_pct"] = f"{'+' if upside >= 0 else ''}{upside:.1f}%"
        stock["target"] = f"{price * (1 + upside / 100):.2f}"


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

            # Analyze (Graham, Buffett, Moat & dynamic valuation screens)
            is_bargain, ncav = check_enterprising_bargain(fin, price)
            owner_earnings = calculate_owner_earnings(fin)
            moat = score_economic_moat(fin)
            graham_value = calculate_graham_intrinsic_value(fin)
            retained_ratio = test_retained_earnings(fin)
            hyper_growth = check_hyper_growth_risk(fin)
            valuation_alerts = generate_valuation_alerts(fin, price)

            # Build Valuation Model
            val = CompanyValuation(
                pe_ratio=fin.pe_ratio,
                graham_intrinsic_value=graham_value,
                is_bargain=is_bargain,
                ncav_per_share=ncav,
                owner_earnings=owner_earnings,
                retained_earnings_ratio=retained_ratio,
                moat_status=moat,
                hyper_growth_warning=hyper_growth,
                valuation_alerts=valuation_alerts,
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

            # Graham's Defensive Investor screen passes when no defensive
            # criteria failed and we actually had the data to judge it.
            has_defensive_data = (
                fin.current_ratio is not None and fin.pe_ratio is not None
            )
            is_defensive_pass = has_defensive_data and not any(
                marker in alert
                for alert in valuation_alerts
                for marker in _DEFENSIVE_FAIL_MARKERS
            )
            passed_retained_test = retained_ratio >= 1.0

            # Persist the computed analytics back onto the stock so the dashboard
            # tabs (Graham / Buffett / Scoring / Caution) and the email digest,
            # which read these fields per-stock, are populated on every live run.
            if isinstance(stock.get("screener"), dict):
                stock["screener"].update(
                    {
                        "graham_intrinsic_value": graham_value,
                        "owner_earnings": owner_earnings,
                        "retained_earnings_ratio": retained_ratio,
                        "moat_status": moat,
                        "is_bargain": is_bargain,
                        "net_current_assets": fin.net_current_assets,
                        "hyper_growth_warning": hyper_growth,
                        "valuation_alerts": valuation_alerts,
                    }
                )
            stock["score"] = score_dict

            # Tag the upside source and refresh stale targets where there is no
            # live analyst coverage to back them.
            _apply_potential_estimate(stock, price, graham_value)

            # Add to Margin of Safety list if it passes the defensive screen,
            # is a deep-value bargain, or is conventionally cheap (PE < 15).
            pe_ratio = fin.pe_ratio or 0
            if is_defensive_pass or is_bargain or (pe_ratio > 0 and pe_ratio < 15):
                margin_of_safety.append(
                    {
                        "ticker": comp.ticker,
                        "name": comp.name,
                        "price": comp.price,
                        "pe_ratio": pe_ratio,
                        "ncav": ncav,
                        "graham_intrinsic_value": graham_value,
                        "is_bargain": is_bargain,
                        "is_defensive_pass": is_defensive_pass,
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
                    "moat_status": moat,
                    "retained_earnings_ratio": retained_ratio,
                    "passed_retained_test": passed_retained_test,
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
