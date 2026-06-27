"""Early Warning System.

Synthesises signals already collected by the pipeline (Screener fundamentals,
Yahoo price/momentum, FII/DII/promoter holding shifts, valuation alerts and
policy events) into a single, severity-ranked feed of risk and opportunity
alerts. No new data sources are required — this is a consolidating layer on top
of data the daily briefing already produces.
"""

from typing import Any, Dict, List, Optional

from config import SECTOR_METADATA
from config_scoring import SCORING_CONFIG, EARLY_WARNING_CONFIG

# Lower rank sorts first.
_SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
_DIRECTION_RANK = {"risk": 0, "opportunity": 1}


def _to_float(value: Any) -> Optional[float]:
    """Best-effort numeric coercion tolerant of ``None``, strings and ``%``/``+`` signs."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace("+", "").replace(",", "")
        if not cleaned or cleaned in {"-", "—", "N/A", "NA"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _build_policy_map(data: Dict[str, Any]) -> Dict[str, List[str]]:
    """Map an upper-cased company name/ticker to the policy catalysts touching it.

    Mirrors the mapping built in ``dashboard/builder.py`` so the two views stay
    consistent.
    """
    policy_map: Dict[str, List[str]] = {}

    def _add(name: str, label: str) -> None:
        if not name:
            return
        policy_map.setdefault(name.upper(), []).append(label)

    for ev in data.get("emerging_competitors", []):
        _add(
            ev.get("name", ev.get("company", "")),
            f"PLI / scheme: {ev.get('scheme') or ev.get('announcement') or 'approval'}",
        )
    for ev in data.get("corporate_agreements", []):
        _add(ev.get("company", ""), f"Agreement: {ev.get('title', '')}")
    for ev in data.get("product_launches", []):
        _add(
            ev.get("company", ""),
            f"Launch: {ev.get('product') or ev.get('title', '')}",
        )
    for ev in data.get("corporate_filings", []):
        _add(ev.get("company", ""), f"Filing: {ev.get('filing', '')}")
    for ev in data.get("sebi_filings", []):
        _add(ev.get("company", ""), f"SEBI: {ev.get('title', '')}")

    return policy_map


def _evaluate_stock(
    stock: Dict[str, Any],
    sector_label: str,
    policy_map: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    """Apply every rule to a single stock and return the alerts it raised."""
    ticker = str(stock.get("ticker", "")).strip()
    name = str(stock.get("name", "")).strip()
    alerts: List[Dict[str, Any]] = []

    def emit(severity: str, direction: str, category: str, signal: str) -> None:
        alerts.append(
            {
                "ticker": ticker,
                "name": name,
                "sector": sector_label,
                "severity": severity,
                "direction": direction,
                "category": category,
                "signal": signal,
            }
        )

    screener = stock.get("screener")
    if not isinstance(screener, dict):
        screener = {}

    promoter_change = _to_float(screener.get("promoter_change"))
    fii_change = _to_float(screener.get("fii_change"))
    dii_change = _to_float(screener.get("dii_change"))
    qoq_sales = _to_float(screener.get("qoq_sales_growth"))
    current_ratio = _to_float(screener.get("current_ratio"))
    debt_to_equity = _to_float(screener.get("debt_to_equity"))
    opm_expansion = _to_float(screener.get("opm_expansion"))
    valuation_alerts = screener.get("valuation_alerts") or []

    percent_change = _to_float(stock.get("percent_change"))
    volume_surge = _to_float(stock.get("volume_surge")) or _to_float(
        stock.get("relative_volume")
    )
    price_to_ma = _to_float(stock.get("price_to_ma"))

    # --- Risk rules -------------------------------------------------------
    if promoter_change is not None and promoter_change < 0:
        if promoter_change <= EARLY_WARNING_CONFIG.promoter_exit_critical:
            emit(
                "Critical",
                "risk",
                "Promoter Exit",
                f"Promoters cut their stake by {abs(promoter_change):.2f}% this quarter.",
            )
        elif promoter_change <= EARLY_WARNING_CONFIG.promoter_exit_high:
            emit(
                "High",
                "risk",
                "Promoter Selling",
                f"Promoter holding declined {abs(promoter_change):.2f}%.",
            )

    if fii_change is not None and fii_change < 0:
        if fii_change <= EARLY_WARNING_CONFIG.fii_outflow_critical:
            emit(
                "Critical",
                "risk",
                "FII Outflow",
                f"Heavy foreign institutional selling ({fii_change:.2f}%).",
            )
        elif fii_change <= EARLY_WARNING_CONFIG.fii_outflow_high:
            emit(
                "High",
                "risk",
                "FII Selling",
                f"Foreign institutions reduced holdings ({fii_change:.2f}%).",
            )

    if qoq_sales is not None and qoq_sales < 0:
        emit(
            "High",
            "risk",
            "Revenue Contraction",
            f"Quarter-on-quarter sales fell {abs(qoq_sales):.1f}%.",
        )

    if current_ratio is not None and current_ratio < 1.0:
        emit(
            "High",
            "risk",
            "Liquidity Stress",
            f"Current ratio of {current_ratio:.2f} is below 1.0 (short-term obligations risk).",
        )

    if debt_to_equity is not None:
        if debt_to_equity > EARLY_WARNING_CONFIG.leverage_critical:
            emit(
                "High",
                "risk",
                "High Leverage",
                f"Debt-to-equity of {debt_to_equity:.2f} exceeds 1.0.",
            )
        elif debt_to_equity > SCORING_CONFIG.max_debt_to_equity:
            emit(
                "Medium",
                "risk",
                "Elevated Leverage",
                f"Debt-to-equity of {debt_to_equity:.2f} is above the "
                f"{SCORING_CONFIG.max_debt_to_equity} comfort threshold.",
            )

    if (
        opm_expansion is not None
        and opm_expansion <= EARLY_WARNING_CONFIG.margin_compression
    ):
        emit(
            "Medium",
            "risk",
            "Margin Compression",
            f"Operating margin contracted {abs(opm_expansion):.1f}%.",
        )

    if valuation_alerts:
        deduped = list(dict.fromkeys(str(a) for a in valuation_alerts if a))
        if deduped:
            emit(
                "Medium",
                "risk",
                "Valuation Stretch",
                "Valuation flags: " + "; ".join(deduped),
            )

    if (
        percent_change is not None
        and percent_change <= EARLY_WARNING_CONFIG.intraday_drop_high
    ):
        severity = (
            "Critical"
            if percent_change <= EARLY_WARNING_CONFIG.intraday_drop_critical
            else "High"
        )
        emit(
            severity,
            "risk",
            "Price Breakdown",
            f"Price dropped {abs(percent_change):.1f}% in the latest session.",
        )

    if price_to_ma is not None and 0 < price_to_ma < 1.0:
        emit(
            "Low",
            "risk",
            "Below Trend",
            f"Trading {(1 - price_to_ma) * 100:.0f}% below its moving average.",
        )

    # --- Opportunity rules -----------------------------------------------
    if (
        fii_change is not None
        and dii_change is not None
        and fii_change > 0
        and dii_change > 0
    ):
        emit(
            "High",
            "opportunity",
            "Institutional Accumulation",
            f"Both FIIs (+{fii_change:.2f}%) and DIIs (+{dii_change:.2f}%) are accumulating.",
        )
    elif (fii_change is not None and fii_change > 0) or (
        dii_change is not None and dii_change > 0
    ):
        who = "FIIs" if (fii_change or 0) > 0 else "DIIs"
        delta = fii_change if (fii_change or 0) > 0 else dii_change
        emit(
            "Medium",
            "opportunity",
            "Institutional Buying",
            f"{who} added to positions (+{delta:.2f}%).",
        )

    catalysts = policy_map.get(name.upper(), []) + policy_map.get(ticker.upper(), [])
    if catalysts:
        emit(
            "Medium",
            "opportunity",
            "Policy Catalyst",
            "Active policy tailwind — " + "; ".join(dict.fromkeys(catalysts)),
        )

    if (
        volume_surge is not None
        and volume_surge >= EARLY_WARNING_CONFIG.volume_surge_breakout
        and percent_change is not None
        and percent_change > 0
    ):
        emit(
            "Medium",
            "opportunity",
            "Momentum Breakout",
            f"Up {percent_change:.1f}% on {volume_surge:.1f}x relative volume.",
        )

    return alerts


def generate_early_warnings(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Produce a severity-ranked list of early-warning alerts across the watchlist.

    Risks are surfaced before opportunities; within each group alerts are ordered
    Critical -> Low. The ``macro_indicators`` pseudo-sector is skipped, matching
    ``dashboard/builder.py``.
    """
    policy_map = _build_policy_map(data)
    warnings: List[Dict[str, Any]] = []

    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        sector_label = SECTOR_METADATA.get(sector, {}).get("label", sector)
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            warnings.extend(_evaluate_stock(stock, sector_label, policy_map))

    warnings.sort(
        key=lambda a: (
            _DIRECTION_RANK.get(a["direction"], 9),
            _SEVERITY_RANK.get(a["severity"], 9),
            a["ticker"],
        )
    )
    return warnings
