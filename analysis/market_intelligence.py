"""Structured market intelligence and transparent opportunity prioritisation.

This module consolidates fields already fetched by the pipeline. It does not
invent MTF exposure: stock-level MTF data is explicitly marked unavailable
until a reliable exchange/provider feed is integrated.

Priority order follows the research brief strictly:
business impact -> market reaction -> market opportunity -> financial strength.
The dimensions are exposed separately and sorted lexicographically, so a
lower-priority dimension cannot outweigh a higher-priority one.
"""

import datetime
from typing import Any, Dict, List, Optional

_EVENT_IMPACT = {
    "order": 100,
    "capacity": 85,
    "acquisition": 80,
    "tie-up": 70,
    "launch": 60,
    "state policy": 55,
    "news": 35,
    "filing": 25,
    "supply disruption": 20,
    "input cost": 15,
    "weaker business": 0,
    "partnership ended": 0,
    "divestment": 0,
    "adverse": 0,
}


def _number(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return round(max(low, min(high, value)), 2)


def _four_week_reaction(company: Dict[str, Any]) -> Optional[float]:
    prices = company.get("prices") or []
    closes = []
    for row in prices:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        close = _number(row[1])
        if close is not None and close > 0:
            closes.append(close)
    if len(closes) < 5 or closes[-5] <= 0:
        return None
    return round((closes[-1] / closes[-5] - 1) * 100, 2)


def _business_impact(company: Dict[str, Any]) -> float:
    activity = company.get("activity") or []
    scores = []
    for item in activity:
        kind = str(item.get("kind") or "news").lower()
        base = _EVENT_IMPACT.get(kind, 30)
        certainty = str(item.get("certainty") or "").lower()
        if certainty in ("completed", "awarded", "executed"):
            base = min(100, base + 10)
        elif certainty in ("proposed", "bid", "announced"):
            base *= 0.75
        scores.append(base)
    policies = company.get("policies") or []
    for policy in policies:
        direction = policy.get("direction")
        if direction == "tailwind":
            scores.append(65 if policy.get("names_company") else 40)
        elif direction == "headwind":
            scores.append(20 if policy.get("names_company") else 10)
    if not scores:
        return 0.0
    # Recent, evidenced developments count, but a flood of headlines cannot
    # drown out the quality of the most material business event.
    scores.sort(reverse=True)
    return _clamp(scores[0] * 0.7 + (sum(scores[1:4]) / max(1, len(scores[1:4]))) * 0.3)


def _market_opportunity(stock: Dict[str, Any], company: Dict[str, Any]) -> float:
    sc = stock.get("screener") or {}
    share_change = _number(sc.get("industry_share_change_pp"))
    growth = _number(sc.get("revenue_ttm_growth_pct"))
    policy_net = _number(company.get("policy_net"))
    components = []
    if share_change is not None:
        components.append(_clamp(50 + share_change * 12))
    if growth is not None:
        components.append(_clamp(50 + growth * 1.25))
    if policy_net is not None:
        components.append(_clamp(50 + policy_net * 10))
    return round(sum(components) / len(components), 2) if components else 0.0


def _financial_strength(stock: Dict[str, Any]) -> float:
    score = stock.get("score") or {}
    fundamental = _number(score.get("fundamental_score"))
    if fundamental is None:
        return 0.0
    # Keep the raw score alongside the bounded display dimension.
    return _clamp(50 + fundamental * 3.0)


def build_market_intelligence(
    watchlist: Dict[str, Any],
    company_digest: Dict[str, Any],
    institutional_activity: List[Dict[str, Any]] = None,
    graph: Dict[str, Any] = None,
    as_of: str = None,
) -> Dict[str, Any]:
    """Return per-ticker ownership/tradeability snapshots and ranked ideas."""
    as_of = as_of or datetime.date.today().isoformat()
    digest_by_ticker = {
        str(c.get("ticker", "")).upper(): c
        for c in (company_digest or {}).get("companies", [])
        if c.get("ticker")
    }
    deal_rows = {}
    for deal in institutional_activity or []:
        ticker = str(deal.get("ticker") or "").upper()
        if ticker:
            deal_rows.setdefault(ticker, []).append(deal)

    snapshots, priorities = [], []
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for stock in stocks:
            if not isinstance(stock, dict) or not stock.get("ticker"):
                continue
            ticker = str(stock["ticker"]).upper()
            sc = stock.get("screener") or {}
            company = digest_by_ticker.get(ticker, {})
            ownership = {
                "promoter_pct": _number(sc.get("promoter_pct")),
                "promoter_change_pp": _number(sc.get("promoter_change")),
                "fii_pct": _number(sc.get("fii_pct")),
                "fii_change_pp": _number(sc.get("fii_change")),
                "dii_pct": _number(sc.get("dii_pct")),
                "dii_change_pp": _number(sc.get("dii_change")),
                "pledged_pct_of_promoter_holding": _number(sc.get("pledged_pct")),
                "pledged_change_pp": _number(sc.get("pledged_change")),
                "source": "Screener shareholding pattern",
            }
            tradeability = {
                "advt_cr": _number(sc.get("advt_cr")),
                "liquidity_band": sc.get("liquidity_band") or "unknown",
                "days_to_exit_1cr": _number(sc.get("days_to_exit_1cr")),
                "delivery_pct": _number(sc.get("deliv_pct")),
                "delivery_band": sc.get("delivery_band") or "unknown",
                "series": sc.get("series"),
                "delivery_source": "NSE sec_bhavdata_full",
            }
            snapshots.append(
                {
                    "ticker": ticker,
                    "name": stock.get("name") or ticker,
                    "sector": sector,
                    "as_of": as_of,
                    "ownership": ownership,
                    "tradeability": tradeability,
                    "mtf": {
                        "status": sc.get("mtf_status") or "unavailable",
                        "outstanding_cr": _number(sc.get("mtf_outstanding_cr")),
                        "value": _number(sc.get("mtf_outstanding_cr")),
                        "change_1m_pct": _number(sc.get("mtf_change_1m_pct")),
                        "change_1w_pct": _number(sc.get("mtf_change_1w_pct")),
                        "rank": sc.get("mtf_rank"),
                        "as_of": sc.get("mtf_as_of"),
                        "source": sc.get("mtf_source"),
                        "source_url": sc.get("mtf_source_url"),
                        "attribution": sc.get("mtf_attribution"),
                        "note": (
                            "NSE-disclosure-backed stock-level MTF outstanding"
                            if sc.get("mtf_status") == "available"
                            else "No matching stock-level MTF disclosure in the latest feed"
                        ),
                    },
                    "block_bulk_deals": deal_rows.get(ticker, [])[:10],
                }
            )

            reaction = _four_week_reaction(company)
            dimensions = {
                "business_impact": _business_impact(company),
                "market_reaction": (
                    _clamp(50 + reaction * 2.5) if reaction is not None else 0.0
                ),
                "market_opportunity": _market_opportunity(stock, company),
                "financial_strength": _financial_strength(stock),
            }
            # Tuple sort preserves the user's stated strict priority order.
            priorities.append(
                {
                    "ticker": ticker,
                    "name": stock.get("name") or ticker,
                    "sector": sector,
                    "as_of": as_of,
                    "rank": None,
                    "dimensions": dimensions,
                    "market_reaction_4w_pct": reaction,
                    "raw_fundamental_score": _number(
                        (stock.get("score") or {}).get("fundamental_score")
                    ),
                    "priority_order": [
                        "business_impact",
                        "market_reaction",
                        "market_opportunity",
                        "financial_strength",
                    ],
                }
            )

    priorities.sort(
        key=lambda row: tuple(
            row["dimensions"][key]
            for key in (
                "business_impact",
                "market_reaction",
                "market_opportunity",
                "financial_strength",
            )
        ),
        reverse=True,
    )
    for rank, row in enumerate(priorities, start=1):
        row["rank"] = rank

    return {
        "as_of": as_of,
        "mtf_attribution": (
            "MTF data via Margin Trading Facility "
            "(https://margintradingfacility.com), compiled from NSE disclosures"
        ),
        "method": "lexicographic_v1",
        "priority_order": [
            "business_impact",
            "market_reaction",
            "market_opportunity",
            "financial_strength",
        ],
        "snapshots": snapshots,
        "opportunity_ranking": priorities,
        "supply_chain_trees": build_supply_chain_trees(graph or {}, watchlist),
        "coverage": {
            "holdings": len(snapshots),
            "mtf_unavailable": sum(
                1 for row in snapshots if row["mtf"]["status"] != "available"
            ),
            "mtf_available": sum(
                1 for row in snapshots if row["mtf"]["status"] == "available"
            ),
        },
    }


def build_supply_chain_trees(
    graph: Dict[str, Any],
    watchlist: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build evidence-labelled tiers from curated directed graph edges.

    Direct supplier/customer links and sector-level inputs are kept separate:
    sector exposure is not presented as a confirmed company-specific purchase.
    """
    edges = (graph or {}).get("edges") or []
    direct = [e for e in edges if e.get("type") == "supplier_customer"]
    anchors = [e for e in edges if e.get("type") == "anchor_demand"]
    input_costs = [e for e in edges if e.get("type") == "input_cost"]
    companies = {}
    for stocks in (watchlist or {}).values():
        for stock in stocks or []:
            if isinstance(stock, dict) and stock.get("ticker"):
                companies[str(stock["name"]).lower()] = {
                    "ticker": str(stock["ticker"]).upper(),
                    "name": stock.get("name"),
                    "sector": stock.get("sector"),
                }

    roots = sorted(
        {str(e.get("dst")) for e in direct if e.get("dst")}
        | {str(e.get("src")) for e in anchors if e.get("src")},
        key=str.lower,
    )
    trees = []
    for root in roots:
        suppliers = [
            {
                "name": e.get("src"),
                "relationship": e.get("note") or "Curated supplier relationship",
                "evidence": e.get("evidence") or "curated",
                "tier": 1,
            }
            for e in direct
            if str(e.get("dst", "")).lower() == root.lower()
        ]
        customers = [
            {
                "name": e.get("dst"),
                "relationship": e.get("note") or "Curated customer relationship",
                "evidence": e.get("evidence") or "curated",
                "tier": 1,
            }
            for e in direct
            if str(e.get("src", "")).lower() == root.lower()
        ]
        upstream = []
        for supplier in suppliers:
            for edge in direct:
                if str(edge.get("dst", "")).lower() == str(supplier["name"]).lower():
                    upstream.append(
                        {
                            "name": edge.get("src"),
                            "supplies": supplier["name"],
                            "relationship": edge.get("note")
                            or "Curated upstream supplier relationship",
                            "evidence": edge.get("evidence") or "curated",
                            "tier": 2,
                        }
                    )

        sector_exposures = []
        component_nodes = {}
        for anchor in anchors:
            if str(anchor.get("src", "")).lower() != root.lower():
                continue
            sector = str(anchor.get("dst") or "")
            inputs = [
                {
                    "component": edge.get("src"),
                    "relationship": edge.get("note") or "Sector input-cost exposure",
                    "evidence": edge.get("evidence") or "curated",
                    "sector": sector,
                    "scope": "sector_level_not_company_specific",
                }
                for edge in input_costs
                if str(edge.get("dst", "")).lower() == sector.lower()
            ]
            dependencies = [
                {
                    "component": edge.get("src"),
                    "relationship": edge.get("note") or "Sector component dependency",
                    "evidence": edge.get("evidence") or "curated",
                    "sector": sector,
                    "scope": "sector_level_not_company_specific",
                }
                for edge in edges
                if edge.get("type") == "component_dependency"
                and str(edge.get("dst", "")).lower() == sector.lower()
            ]
            for node in inputs + dependencies:
                component_nodes.setdefault(str(node["component"]).lower(), node)
            sector_exposures.append(
                {
                    "sector": sector,
                    "anchor_relationship": anchor.get("note") or "",
                    "inputs": inputs,
                    "components": dependencies,
                    "relationship_scope": "sector_level_not_company_specific",
                }
            )
        component_layer = []
        for component in component_nodes.values():
            makers = [
                {
                    "name": edge.get("src"),
                    "relationship": edge.get("note")
                    or "Curated component manufacturer",
                    "evidence": edge.get("evidence") or "curated",
                    "tier": 3,
                }
                for edge in edges
                if edge.get("type") == "component_manufacturer"
                and str(edge.get("dst", "")).lower()
                == str(component["component"]).lower()
            ]
            component_layer.append(
                {
                    **component,
                    "tier": 2,
                    "manufacturers": makers,
                }
            )
        if not suppliers and not customers and not sector_exposures:
            continue
        trees.append(
            {
                "root": root,
                "root_ticker": companies.get(root.lower(), {}).get("ticker"),
                "tiers": [
                    {"tier": 0, "role": "anchor", "nodes": [{"name": root}]},
                    {
                        "tier": 1,
                        "role": "direct_relationships",
                        "suppliers": suppliers,
                        "customers": customers,
                    },
                    {"tier": 2, "role": "upstream_suppliers", "nodes": upstream},
                    {
                        "tier": 2,
                        "role": "components",
                        "nodes": sorted(
                            component_layer,
                            key=lambda node: str(node["component"]).lower(),
                        ),
                    },
                    {
                        "tier": 3,
                        "role": "component_manufacturers",
                        "nodes": [
                            maker
                            for node in component_layer
                            for maker in node["manufacturers"]
                        ],
                    },
                ],
                "sector_exposures": sector_exposures,
                "source_scope": "curated_entity_graph",
                "completeness": "partial",
                "limitations": (
                    "Only curated relationships are shown. Missing links do not "
                    "mean no commercial relationship; sector inputs are not "
                    "company-specific supplier claims."
                ),
            }
        )
    return trees
