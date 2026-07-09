"""Early Warning System.

Synthesises signals already collected by the pipeline (Screener fundamentals,
Yahoo price/momentum, FII/DII/promoter holding shifts, valuation alerts and
policy events) into a single, severity-ranked feed of risk and opportunity
alerts. No new data sources are required — this is a consolidating layer on top
of data the daily briefing already produces.
"""

from typing import Any, Dict, List

from config import SECTOR_METADATA
from config_scoring import SCORING_CONFIG, EARLY_WARNING_CONFIG
from utils import to_float

# Lower rank sorts first.
_SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
_DIRECTION_RANK = {"risk": 0, "opportunity": 1}


# Canonical coercion shared across the codebase (was a private copy here).
_to_float = to_float


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
        if opm_expansion <= EARLY_WARNING_CONFIG.margin_compression_critical:
            margin_severity = "Critical"
        elif opm_expansion <= EARLY_WARNING_CONFIG.margin_compression_high:
            margin_severity = "High"
        else:
            margin_severity = "Medium"

        # A persistent multi-quarter slide is worse than a one-off dip of
        # the same size — escalate one level and show the trajectory.
        q_margins = [
            m
            for m in (
                _to_float(v) for v in (screener.get("quarterly_ebitda_margin") or [])
            )
            if m is not None
        ]
        persistent = (
            len(q_margins) >= 3 and q_margins[-1] < q_margins[-2] < q_margins[-3]
        )
        if persistent and margin_severity != "Critical":
            margin_severity = "High" if margin_severity == "Medium" else "Critical"

        if persistent:
            trail = " → ".join(f"{m:.1f}%" for m in q_margins[-3:])
            margin_signal = (
                f"Operating margin compressing for 3 straight quarters "
                f"({trail}); latest drop {abs(opm_expansion):.1f}pp."
            )
        else:
            margin_signal = (
                f"Operating margin contracted {abs(opm_expansion):.1f}pp QoQ."
            )

        emit(margin_severity, "risk", "Margin Compression", margin_signal)

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


# Statuses of a discovered emerging player that constitute a credible challenger.
_CHALLENGER_STATUSES = {"Pipeline", "Watchlisted"}

# A challenger must clear the high-growth bar to be treated as a real threat.
_CHALLENGER_GROWTH_BAR = 15.0


def _market_share_shifts(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flag holdings whose share of tracked peer-group revenue is shifting.

    Reads the annotations written by ``analysis.market_share`` — an actual
    revenue-share measurement, so unlike growth-rate comparisons it is
    weighted by base size and needs no news coverage to fire.
    """
    alerts: List[Dict[str, Any]] = []
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        sector_label = SECTOR_METADATA.get(sector, {}).get("label", sector)
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            sc = stock.get("screener")
            if not isinstance(sc, dict):
                continue

            # Prefer the industry-wide share (full Screener peer table, all
            # listed rivals) over the narrow watchlist peer-group estimate.
            industry_change = _to_float(sc.get("industry_share_change_pp"))
            industry_share = _to_float(sc.get("industry_share_pct"))
            if industry_change is not None and industry_share is not None:
                change = industry_change
                share = industry_share
                lookback = 1
                peers = sc.get("industry_peer_count", 0)
                group_label = f"{peers}-company industry group"
            elif "peer_share_pct" in sc:
                change = _to_float(sc.get("peer_share_change_pp"))
                share = _to_float(sc.get("peer_share_pct"))
                lookback = sc.get("peer_share_lookback", 1)
                peers = sc.get("peer_group_size", 0)
                group_label = f"{peers}-stock peer group"
            else:
                continue
            if change is None or share is None:
                continue
            prev = share - change

            if change <= EARLY_WARNING_CONFIG.share_loss_pp:
                severity = (
                    "High"
                    if change <= EARLY_WARNING_CONFIG.share_loss_critical_pp
                    else "Medium"
                )
                alerts.append(
                    {
                        "ticker": stock.get("ticker"),
                        "name": stock.get("name"),
                        "sector": sector_label,
                        "severity": severity,
                        "direction": "risk",
                        "category": "Market Share",
                        "signal": (
                            f"Losing revenue share of its {group_label}: "
                            f"{prev:.1f}% → {share:.1f}% over {lookback} period(s)."
                        ),
                    }
                )
            elif change >= EARLY_WARNING_CONFIG.share_gain_pp:
                alerts.append(
                    {
                        "ticker": stock.get("ticker"),
                        "name": stock.get("name"),
                        "sector": sector_label,
                        "severity": "Medium",
                        "direction": "opportunity",
                        "category": "Market Share",
                        "signal": (
                            f"Gaining revenue share of its {group_label}: "
                            f"{prev:.1f}% → {share:.1f}% over {lookback} period(s)."
                        ),
                    }
                )
    return alerts


def _growth_laggards(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fallback share-erosion proxy for stocks without peer-share data.

    When a sector's peer group is too thin to compute revenue share, compare
    each holding's QoQ sales growth against the sector median; trailing it by
    ``growth_laggard_gap`` points suggests the holding is ceding ground.
    """
    alerts: List[Dict[str, Any]] = []
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        sector_label = SECTOR_METADATA.get(sector, {}).get("label", sector)

        rows = []
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            sc = stock.get("screener")
            if not isinstance(sc, dict):
                continue
            growth = _to_float(sc.get("qoq_sales_growth"))
            if growth is not None:
                rows.append((stock, sc, growth))

        if len(rows) < 3:
            continue

        growths = sorted(g for _, _, g in rows)
        mid = len(growths) // 2
        median = (
            growths[mid] if len(growths) % 2 else (growths[mid - 1] + growths[mid]) / 2
        )

        for stock, sc, growth in rows:
            if "peer_share_pct" in sc:
                continue  # the direct share signal already covers this stock
            if growth <= median - EARLY_WARNING_CONFIG.growth_laggard_gap:
                alerts.append(
                    {
                        "ticker": stock.get("ticker"),
                        "name": stock.get("name"),
                        "sector": sector_label,
                        "severity": "Medium",
                        "direction": "risk",
                        "category": "Growth Laggard",
                        "signal": (
                            f"QoQ sales growth of {growth:+.1f}% trails the "
                            f"{sector_label} median of {median:+.1f}% — "
                            f"likely ceding ground to sector peers."
                        ),
                    }
                )
    return alerts


def _competitive_threats(
    data: Dict[str, Any], watchlist: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Flag incumbents being out-grown by a high-growth challenger in their sector.

    Challengers come from two radars: the news-driven emerging-player scan
    (``data["emerging_players"]``) and Screener's structured industry peer
    tables (``data["peer_competitors"]``), which need no news coverage.
    The strongest challenger in a sector is compared against the QoQ growth
    of the holdings we already own.
    """
    alerts: List[Dict[str, Any]] = []
    emerging = data.get("emerging_players", {})
    if not isinstance(emerging, dict):
        emerging = {}
    peer_radar = data.get("peer_competitors", {})
    if not isinstance(peer_radar, dict):
        peer_radar = {}

    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue

        challengers = []
        for c in emerging.get(sector, []) or []:
            if not isinstance(c, dict):
                continue
            if c.get("status") not in _CHALLENGER_STATUSES:
                continue
            growth = _to_float(c.get("qoq_growth"))
            if growth is not None and growth >= _CHALLENGER_GROWTH_BAR:
                challengers.append(
                    (c.get("name") or c.get("ticker") or "A new entrant", growth)
                )

        for c in peer_radar.get(sector, []) or []:
            if not isinstance(c, dict):
                continue
            growth = _to_float(c.get("sales_var_pct"))
            if growth is not None and growth >= _CHALLENGER_GROWTH_BAR:
                challengers.append(
                    (c.get("name") or c.get("ticker") or "A listed peer", growth)
                )

        if not challengers:
            continue

        # Compare the single strongest challenger against each lagging holding.
        challenger_name, challenger_growth = max(challengers, key=lambda x: x[1])
        sector_label = SECTOR_METADATA.get(sector, {}).get("label", sector)

        held_tickers = {
            str(c[0]).upper() for c in challengers
        }  # challenger names (avoid self-flagging)

        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            ticker = str(stock.get("ticker", "")).strip()
            name = str(stock.get("name", "")).strip()
            if name.upper() in held_tickers or ticker.upper() in held_tickers:
                continue
            sc = stock.get("screener")
            incumbent_growth = _to_float(
                sc.get("qoq_sales_growth") if isinstance(sc, dict) else None
            )
            if incumbent_growth is None:
                # Data gap must not mute the radar entirely — a fast-growing
                # challenger is still worth pointing to, at lower confidence.
                alerts.append(
                    {
                        "ticker": ticker,
                        "name": name,
                        "sector": sector_label,
                        "severity": "Low",
                        "direction": "risk",
                        "category": "Competitive Threat",
                        "signal": (
                            f"{challenger_name} is growing at +{challenger_growth:.1f}% "
                            f"QoQ in this sector (own growth data unavailable)."
                        ),
                    }
                )
                continue
            if (
                incumbent_growth < _CHALLENGER_GROWTH_BAR
                and incumbent_growth < challenger_growth
            ):
                alerts.append(
                    {
                        "ticker": ticker,
                        "name": name,
                        "sector": sector_label,
                        "severity": "Medium",
                        "direction": "risk",
                        "category": "Competitive Threat",
                        "signal": (
                            f"{challenger_name} is growing faster "
                            f"(QoQ +{challenger_growth:.1f}% vs +{incumbent_growth:.1f}%) "
                            f"and could pressure market share."
                        ),
                    }
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

    # Sector-level competitive-threat pass (news radar + Screener peer radar).
    warnings.extend(_competitive_threats(data, watchlist))

    from analysis.competitive_intel import new_entrant_signals

    warnings.extend(new_entrant_signals(data, watchlist))

    # Direct market-share measurement, with a growth-laggard fallback for
    # stocks the share computation couldn't cover.
    warnings.extend(_market_share_shifts(watchlist))
    warnings.extend(_growth_laggards(watchlist))

    # Exchange-disclosed events: capital raises and bulk/block deals.

    warnings.sort(
        key=lambda a: (
            _DIRECTION_RANK.get(a["direction"], 9),
            _SEVERITY_RANK.get(a["severity"], 9),
            a["ticker"],
        )
    )
    return warnings
