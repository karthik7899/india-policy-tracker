import os
import datetime
import html as html_lib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logger import log
from config import SECTOR_METADATA, DASHBOARD_URL

_SEVERITY_BADGE = {
    "Critical": ("#7f1d1d", "#fca5a5"),
    "High": ("#7c2d12", "#fdba74"),
    "Medium": ("#374151", "#cbd5e1"),
    "Low": ("#1f2937", "#9ca3af"),
}


# Gmail clips messages over ~102 KB. The email renders at full richness
# first; if the result exceeds the budget (news-heavy day, growing research
# sections), it re-renders once with the compact caps — guaranteed delivery
# beats marginal extra rows.
_SIZE_BUDGET_BYTES = 95_000

_CAPS_NORMAL = {
    "stocks": 3,
    "news": 3,
    "warnings": 12,
    "lists": 5,
    "research": 6,
    "curve": 14,
    "emerging": 8,
    "caution": 8,
}
_CAPS_COMPACT = {
    "stocks": 2,
    "news": 1,
    "warnings": 8,
    "lists": 3,
    "research": 4,
    "curve": 10,
    "emerging": 5,
    "caution": 5,
}


def _build_early_warning_html(warnings, caps=_CAPS_NORMAL):
    """Renders the prioritized Early Warning card. Returns '' when there is nothing to flag."""
    if not warnings:
        return ""

    rows = ""
    for w in warnings[: caps["warnings"]]:
        bg, fg = _SEVERITY_BADGE.get(w.get("severity", "Low"), _SEVERITY_BADGE["Low"])
        is_risk = w.get("direction") == "risk"
        dir_icon = "▼" if is_risk else "▲"
        dir_color = "#f87171" if is_risk else "#34d399"
        sev_badge = (
            f"<span class='badge' style='background-color: {bg}; color: {fg};'>"
            f"{w.get('severity', '')}</span>"
        )
        rows += f"""
        <tr>
            <td class="ew-td">
                <span class="stock-ticker">{w.get('ticker', '')}</span>
                <span style="color: #94a3b8; font-size: 11px;"> · {w.get('sector', '')}</span>
            </td>
            <td class="ew-td">{sev_badge}</td>
            <td class="ew-td" style="color: {dir_color};">{dir_icon} {w.get('category', '')}</td>
            <td class="ew-td" style="font-size: 11px; color: #cbd5e1;">{w.get('signal', '')}</td>
        </tr>
        """

    risk_count = sum(1 for w in warnings if w.get("direction") == "risk")
    opp_count = len(warnings) - risk_count

    return f"""
    <div class="section-card">
        <h3 style="color: #f87171; margin-bottom: 6px; font-size: 16px;">Early Warning System</h3>
        <p style="font-size: 12px; color: #94a3b8; margin: 0 0 12px 0;">
            {risk_count} risk signal(s) and {opp_count} opportunity signal(s) detected across the watchlist,
            ranked by severity.
        </p>
        <table class="stock-table">
            <thead>
                <tr>
                    <th>Stock</th>
                    <th>Severity</th>
                    <th>Signal</th>
                    <th>Detail</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """


def _build_sector_valuation_html(rollup):
    """Renders the sector-relative valuation table. Returns '' when empty."""
    if not rollup:
        return ""

    rows = ""
    for r in rollup[:14]:
        rows += f"""
        <tr>
            <td>{r.get('label', '')}</td>
            <td style="color: #e2e8f0; font-weight: 600;">{r.get('median_pe', '—')}</td>
            <td style="color: #34d399; font-size: 11px;">{r.get('cheapest_ticker', '')} ({r.get('cheapest_pe', '')})</td>
            <td style="color: #f87171; font-size: 11px;">{r.get('most_expensive_ticker', '')} ({r.get('most_expensive_pe', '')})</td>
        </tr>
        """

    return f"""
    <div class="section-card">
        <h3 style="color: #38bdf8; margin-bottom: 6px; font-size: 16px;">Sector Valuation (Peer P/E)</h3>
        <p style="font-size: 12px; color: #94a3b8; margin: 0 0 12px 0;">
            Median price-to-earnings across each sector's watchlist peer group, cheapest sectors first.
            Use it to see which themes are richly vs cheaply priced relative to their peers.
        </p>
        <table class="stock-table">
            <thead>
                <tr><th>Sector</th><th>Median P/E</th><th>Cheapest</th><th>Priciest</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """


def _build_sector_growth_html(rollup):
    """Sector revenue-growth leaders (median YoY / CAGR). '' when empty."""
    if not rollup:
        return ""

    rows = ""
    for r in rollup[:10]:
        yoy = r.get("median_yoy_pct")
        cagr = r.get("median_cagr_pct")
        yoy_color = "#34d399" if (yoy or 0) >= 0 else "#f87171"
        yoy_sign = "+" if (yoy or 0) > 0 else ""
        cagr_sign = "+" if (cagr or 0) > 0 else ""
        fast_sign = "+" if (r.get("fastest_yoy_pct") or 0) > 0 else ""
        rows += f"""
        <tr>
            <td>{r.get('label', '')}</td>
            <td style="color: {yoy_color}; font-weight: 600;">{yoy_sign}{yoy}%</td>
            <td style="color: #e2e8f0;">{cagr_sign}{cagr}%</td>
            <td style="color: #94a3b8; font-size: 11px;">{r.get('fastest_ticker', '')} ({fast_sign}{r.get('fastest_yoy_pct', '')}%)</td>
        </tr>
        """

    return f"""
    <div class="section-card">
        <h3 style="color: #34d399; margin-bottom: 6px; font-size: 16px;">Sector Growth Leaders (Revenue)</h3>
        <p style="font-size: 12px; color: #94a3b8; margin: 0 0 12px 0;">
            Median revenue growth across each sector's holdings — YoY (same quarter last year)
            and annualized CAGR over the trailing quarters. Fastest-compounding themes first.
        </p>
        <table class="stock-table">
            <thead>
                <tr><th>Sector</th><th>Median YoY</th><th>Median CAGR</th><th>Fastest Grower</th></tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """


_THESIS_BADGE = {
    "Broken": ("#7f1d1d", "#fca5a5"),
    "Weakening": ("#7c2d12", "#fdba74"),
    "Intact": ("#065f46", "#34d399"),
}


def _build_research_engine_html(brief_data, caps=_CAPS_NORMAL):
    """Renders the research-engine card: thesis health, estimate-revision
    momentum, variant perception, sector curve stage, and the rotation
    engine's own track record. Each sub-section is independently optional —
    every input here is already computed by the pipeline, not fetched fresh,
    so this is purely a synthesis layer. Returns '' when nothing qualifies."""
    thesis_health = brief_data.get("thesis_health") or {}
    revisions = brief_data.get("estimate_revisions") or []
    variant = brief_data.get("variant_perception") or []
    curve_stage = brief_data.get("curve_stage") or {}
    hit_rate = brief_data.get("rotation_hit_rate") or {}
    recent_outcomes = brief_data.get("rotation_recent_outcomes") or []

    if not any([thesis_health, revisions, variant, curve_stage, recent_outcomes]):
        return ""

    sections = ""

    # --- Thesis health -----------------------------------------------
    flagged = [r for r in thesis_health.values() if r.get("status") != "Intact"]
    if thesis_health:
        flagged.sort(key=lambda r: 0 if r["status"] == "Broken" else 1)
        intact_count = len(thesis_health) - len(flagged)
        rows = ""
        for r in flagged[: caps["research"]]:
            bg, fg = _THESIS_BADGE.get(r["status"], _THESIS_BADGE["Weakening"])
            reason = (r.get("reasons") or [""])[0]
            rows += f"""
            <tr>
                <td class="ew-td"><span class="stock-ticker">{r.get('ticker', '')}</span></td>
                <td class="ew-td"><span class="badge" style="background-color: {bg}; color: {fg};">{r['status']}</span></td>
                <td class="ew-td" style="font-size: 11px; color: #cbd5e1;">{reason}</td>
            </tr>
            """
        thesis_block = f"""
        <h4 style="margin: 0 0 6px 0; color: #e2e8f0; font-size: 13px; text-transform: uppercase;">Thesis Health</h4>
        <p style="font-size: 11px; color: #94a3b8; margin: 0 0 10px 0;">
            {intact_count} intact &middot; {len(flagged)} flagged. A thesis moves from Intact only when
            this cycle's evidence contradicts the original catalyst — not on price noise alone.
        </p>
        """
        if rows:
            thesis_block += f"""
            <table class="stock-table" style="margin-bottom: 15px;">
                <thead><tr><th>Stock</th><th>Status</th><th>Why</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            """
        sections += thesis_block

    # --- Estimate revision momentum -----------------------------------
    if revisions:
        rows = ""
        for r in revisions[: caps["research"]]:
            up = r["direction"] == "up"
            color = "#34d399" if up else "#f87171"
            arrow = "▲" if up else "▼"
            rows += f"""
            <tr>
                <td class="ew-td"><span class="stock-ticker">{r.get('ticker', '')}</span></td>
                <td class="ew-td num" style="color: {color}; font-weight: 700;">{arrow} {r['target_change_pct']:+.1f}%</td>
                <td class="ew-td" style="font-size: 11px; color: #94a3b8;">{r.get('sector', '')}</td>
            </tr>
            """
        sections += f"""
        <h4 style="margin: 15px 0 6px 0; color: #e2e8f0; font-size: 13px; text-transform: uppercase;">Estimate Revision Momentum</h4>
        <p style="font-size: 11px; color: #94a3b8; margin: 0 0 10px 0;">
            Target-price moves since the last run &mdash; the closest free proxy to analyst revision momentum.
        </p>
        <table class="stock-table" style="margin-bottom: 15px;">
            <thead><tr><th>Stock</th><th>Target &Delta;</th><th>Sector</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

    # --- Variant perception ---------------------------------------------
    if variant:
        rows = ""
        for r in variant[: caps["research"]]:
            bullish = r["direction"] == "more_bullish"
            color = "#34d399" if bullish else "#f87171"
            rows += f"""
            <tr>
                <td class="ew-td"><span class="stock-ticker">{r.get('ticker', '')}</span></td>
                <td class="ew-td num">₹{r['our_estimate']:.0f}</td>
                <td class="ew-td num">₹{r['consensus_target']:.0f}</td>
                <td class="ew-td num" style="color: {color}; font-weight: 700;">{r['divergence_pct']:+.0f}%</td>
            </tr>
            """
        sections += f"""
        <h4 style="margin: 15px 0 6px 0; color: #e2e8f0; font-size: 13px; text-transform: uppercase;">Variant Perception</h4>
        <p style="font-size: 11px; color: #94a3b8; margin: 0 0 10px 0;">
            Where this pipeline's own Graham estimate diverges most from analyst consensus &mdash;
            the actual bet being made, not just the highest headline upside.
        </p>
        <table class="stock-table" style="margin-bottom: 15px;">
            <thead><tr><th>Stock</th><th>Our Estimate</th><th>Consensus</th><th>Divergence</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

    # --- Sector curve stage ----------------------------------------------
    if curve_stage:
        rows = ""
        for sector, info in list(curve_stage.items())[: caps["curve"]]:
            rows += f"""
            <tr>
                <td class="ew-td">{sector.replace('_', ' ').title()}</td>
                <td class="ew-td">{info['stage']}</td>
                <td class="ew-td num">{info['median_qoq_growth_pct']:+.1f}%</td>
            </tr>
            """
        sections += f"""
        <h4 style="margin: 15px 0 6px 0; color: #e2e8f0; font-size: 13px; text-transform: uppercase;">Sector Curve Stage</h4>
        <table class="stock-table" style="margin-bottom: 15px;">
            <thead><tr><th>Sector</th><th>Stage</th><th>Median QoQ Growth</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """

    # --- Rotation engine track record -------------------------------------
    if hit_rate.get("total_scored") or recent_outcomes:
        win_rate = hit_rate.get("win_rate_pct")
        summary = (
            f"{hit_rate['wins']}/{hit_rate['total_scored']} decisions "
            f"({win_rate}%) played out within 45+ days of being made."
            if hit_rate.get("total_scored")
            else "No rotation decisions have reached the 45-day scoring window yet."
        )
        rows = ""
        for e in recent_outcomes[: caps["lists"]]:
            win = e.get("outcome") == "Thesis Playing Out"
            color = "#34d399" if win else "#f87171"
            rows += f"""
            <tr>
                <td class="ew-td"><span class="stock-ticker">{e.get('ticker', '')}</span></td>
                <td class="ew-td" style="color: {color}; font-weight: 700;">{e.get('outcome', '')}</td>
                <td class="ew-td num">{e.get('realized_return_pct', 0):+.1f}%</td>
            </tr>
            """
        sections += f"""
        <h4 style="margin: 15px 0 6px 0; color: #e2e8f0; font-size: 13px; text-transform: uppercase;">Rotation Engine Track Record</h4>
        <p style="font-size: 11px; color: #94a3b8; margin: 0 0 10px 0;">{summary}</p>
        """
        if rows:
            sections += f"""
            <table class="stock-table">
                <thead><tr><th>Stock</th><th>Outcome</th><th>Realized Return</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
            """

    if not sections:
        return ""

    return f"""
    <div class="section-card">
        <h3 style="color: #a78bfa; margin-bottom: 4px; font-size: 16px;">Research Engine</h3>
        <p style="font-size: 12px; color: #94a3b8; margin: 0 0 14px 0;">
            Synthesis of this cycle's own signals &mdash; no new data, just sharper questions asked of it.
        </p>
        {sections}
    </div>
    """


def _escape_deep(value):
    """Recursively HTML-escapes every string in a nested structure.

    Feed titles, company names and filing text arrive from external sources
    and routinely contain '&', '<' or quotes; unescaped they corrupt the
    email markup mid-document. Escaping once at the boundary keeps every
    f-string below safe without peppering the template with escape calls."""
    if isinstance(value, str):
        return html_lib.escape(value, quote=True)
    if isinstance(value, dict):
        return {k: _escape_deep(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_escape_deep(v) for v in value]
    return value


def _render_email(brief_data, watchlist, caps):
    """Renders the HTML document at the row caps given."""
    brief_data = _escape_deep(brief_data or {})
    watchlist = _escape_deep(watchlist or {})
    today_str = datetime.date.today().strftime("%B %d, %Y")

    style = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b0f19; color: #cbd5e1; margin: 0; padding: 20px; }
        .preheader { display: none !important; visibility: hidden; opacity: 0; color: transparent; height: 0; width: 0; overflow: hidden; mso-hide: all; }
        .container { max-width: 650px; margin: 0 auto; background-color: #111827; border-radius: 12px; border: 1px solid #1f2937; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .header { background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 32px 30px; text-align: center; border-bottom: 2px solid #3b82f6; }
        .header h1 { margin: 0; font-size: 24px; color: #ffffff; letter-spacing: 0.5px; }
        .header p { margin: 6px 0 0 0; font-size: 14px; color: #94a3b8; }
        .cta-button { display: inline-block; margin-top: 18px; padding: 11px 26px; background: linear-gradient(135deg, #3b82f6, #2563eb); color: #ffffff !important; font-size: 13px; font-weight: 600; text-decoration: none; border-radius: 8px; letter-spacing: 0.3px; box-shadow: 0 2px 8px rgba(37,99,235,0.4); }
        .summary-strip { display: table; width: 100%; border-collapse: collapse; background-color: #0f172a; border-bottom: 1px solid #1f2937; }
        .stat { display: table-cell; padding: 16px 10px; text-align: center; border-right: 1px solid #1f2937; vertical-align: middle; }
        .stat:last-child { border-right: none; }
        .stat-num { font-size: 22px; font-weight: 700; line-height: 1; }
        .stat-label { font-size: 10px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 6px; }
        .method-badge { display: inline-block; margin-left: 6px; padding: 1px 6px; font-size: 8px; font-weight: 600; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.3px; vertical-align: middle; }
        .method-analyst { background-color: #0c2a4d; color: #60a5fa; }
        .method-fundamental { background-color: #2a230c; color: #fbbf24; }
        .section-card { padding: 25px; border-bottom: 1px solid #1f2937; }
        .section-card:last-child { border-bottom: none; }
        .sector-title { display: flex; align-items: center; font-size: 18px; color: #3b82f6; font-weight: bold; margin-bottom: 15px; }
        .sector-icon { margin-right: 8px; font-size: 20px; }
        .news-item { margin-bottom: 15px; padding-bottom: 12px; border-bottom: 1px dashed #374151; }
        .news-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
        .news-title { font-size: 14px; font-weight: 600; color: #e2e8f0; text-decoration: none; }
        .news-title:hover { color: #60a5fa; }
        .meta-line { font-size: 11px; color: #6b7280; margin-top: 4px; }
        .badge { display: inline-block; padding: 2px 6px; font-size: 10px; font-weight: bold; border-radius: 4px; text-transform: uppercase; }
        .badge-positive { background-color: #065f46; color: #34d399; }
        .badge-neutral { background-color: #374151; color: #9ca3af; }
        .badge-negative { background-color: #7f1d1d; color: #f87171; }
        .badge-success-alert { background-color: #065f46; color: #34d399; font-size: 9px; padding: 2px 6px; border-radius: 4px; display: inline-block; }
        .kpi { margin-left: 6px; font-size: 9px; padding: 2px 6px; border-radius: 4px; font-weight: bold; display: inline-block; }
        .kpi-pos { background-color: #065f46; color: #34d399; }
        .kpi-neg { background-color: #7f1d1d; color: #f87171; }
        .kpi-eps-pos { margin-left: 4px; font-size: 8px; padding: 2px 5px; background-color: #1e1b4b; color: #a78bfa; }
        .kpi-eps-neg { margin-left: 4px; font-size: 8px; padding: 2px 5px; background-color: #2a1215; color: #f87171; }
        .ew-td { padding: 8px; font-size: 12px; border-bottom: 1px solid #1f2937; }
        .stock-table { width: 100%; border-collapse: collapse; margin-top: 15px; background-color: #0f172a; border-radius: 8px; overflow: hidden; border: 1px solid #1f2937; }
        .stock-table th { background-color: #1e293b; color: #94a3b8; font-size: 11px; padding: 8px; text-align: left; text-transform: uppercase; border-bottom: 1px solid #1f2937; }
        .stock-table td { padding: 8px; font-size: 12px; border-bottom: 1px solid #1f2937; color: #cbd5e1; }
        .stock-ticker { font-weight: bold; color: #60a5fa; }
        .stock-growth { font-weight: bold; color: #34d399; }
        .stock-catalyst { font-size: 11px; color: #94a3b8; padding: 6px 8px 8px 8px !important; background-color: #0b0f19; }
        .footer { padding: 20px; background-color: #0f172a; text-align: center; font-size: 11px; color: #4b5563; border-top: 1px solid #1f2937; }
        .footer a { color: #3b82f6; text-decoration: none; }
    </style>
    """

    # Headline counts for the summary strip / preview text.
    warnings = brief_data.get("early_warnings", [])
    risk_count = sum(1 for w in warnings if w.get("direction") == "risk")
    opp_count = len(warnings) - risk_count
    sectors_tracked = sum(
        1 for s in (watchlist or {}) if s in SECTOR_METADATA and s != "macro_indicators"
    )

    preheader = (
        f"{risk_count} risk &amp; {opp_count} opportunity signals across "
        f"{sectors_tracked} sectors — {today_str}"
    )

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
    </head>
    <body>
        <span class="preheader">{preheader}</span>
        <div class="container">
            <div class="header">
                <h1>🇮🇳 India Policy &amp; Growth Sector Brief</h1>
                <p>Daily Intelligence Report | {today_str}</p>
                <a href="{DASHBOARD_URL}" class="cta-button" target="_blank">View Live Dashboard</a>
            </div>
            <div class="summary-strip">
                <div class="stat">
                    <div class="stat-num" style="color: #f87171;">{risk_count}</div>
                    <div class="stat-label">Risk Signals</div>
                </div>
                <div class="stat">
                    <div class="stat-num" style="color: #34d399;">{opp_count}</div>
                    <div class="stat-label">Opportunities</div>
                </div>
                <div class="stat">
                    <div class="stat-num" style="color: #60a5fa;">{sectors_tracked}</div>
                    <div class="stat-label">Sectors Tracked</div>
                </div>
            </div>
    """

    # Data-freshness banner: warn prominently when the live price refresh
    # largely failed, so stale numbers are never silently presented as current.
    freshness = brief_data.get("freshness", {}).get("live_prices")
    if freshness and freshness.get("total"):
        updated, total = freshness["updated"], freshness["total"]
        if updated < total * 0.8:
            body_html += f"""
            <div style="padding: 10px 25px; background-color: #2a230c; color: #fbbf24; font-size: 12px; border-bottom: 1px solid #1f2937;">
                ⚠ Live price refresh degraded: only {updated}/{total} stocks updated this run.
                Prices for the remainder are from a previous briefing.
            </div>
    """

    # Early Warning System — the first actionable thing the reader should see
    body_html += _build_early_warning_html(warnings, caps)

    # Research Engine: thesis health, revision momentum, variant perception,
    # curve stage, rotation track record — all synthesized from data already
    # computed above, no new fetches.
    body_html += _build_research_engine_html(brief_data, caps)

    for sector, news_items in brief_data.items():
        if sector in (
            "emerging_players",
            "emerging_competitors",
            "corporate_agreements",
            "product_launches",
            "corporate_filings",
            "sebi_filings",
            "institutional_activity",
            "margin_of_safety",
            "buffett_valuation",
        ):
            continue
        if sector not in SECTOR_METADATA:
            continue
        meta = _escape_deep(SECTOR_METADATA[sector])
        stocks = watchlist.get(sector, [])

        # Format news HTML. The email carries the top items per sector to
        # stay under Gmail's ~102 KB clip limit; the dashboard has them all.
        news_html = ""
        if news_items:
            for item in news_items[: caps["news"]]:
                badge_class = (
                    "badge-positive"
                    if item["impact"] == "Positive"
                    else (
                        "badge-negative"
                        if item["impact"] == "Negative"
                        else "badge-neutral"
                    )
                )
                news_html += f"""
                <div class="news-item">
                    <a href="{item['link']}" class="news-title" target="_blank">{item['title']}</a>
                    <div class="meta-line">
                        <span class="badge {badge_class}">{item['impact']} Impact</span> |
                        <span>{item['source']}</span> | <span>{item['date']}</span>
                    </div>
                </div>
                """
            overflow = len(news_items) - caps["news"]
            if overflow > 0:
                news_html += (
                    f"<p style='font-size: 11px; color: #6b7280; margin: 6px 0 0 0;'>"
                    f"+ {overflow} more on the "
                    f"<a href='{DASHBOARD_URL}' style='color: #60a5fa;' target='_blank'>live dashboard</a>."
                    f"</p>"
                )
        else:
            news_html = "<p style='font-size: 13px; color: #4b5563; font-style: italic;'>No policy updates tracked in this cycle.</p>"

        # Format stocks HTML table — capped per sector: the email is the
        # digest, the dashboard is the detail (47 full cards alone were
        # ~36 KB, pushing even the compact render against Gmail's clip).
        stock_rows = ""
        shown_stocks = stocks[: caps.get("stocks", len(stocks))]
        for s in shown_stocks:
            rating_text = s.get("rating", "N/A")
            growth_val = s.get("revenue_growth")
            earnings_val = s.get("earnings_growth")
            analyst_count = s.get("analyst_count")

            # Contextual revenue growth badge
            growth_badge = ""
            if growth_val:
                is_negative = growth_val.startswith("-")
                if is_negative:
                    growth_badge = f"<span class='kpi kpi-neg'>{growth_val} YoY</span>"
                else:
                    growth_badge = f"<span class='kpi kpi-pos'>{growth_val} YoY</span>"

            # Contextual earnings growth badge
            earnings_badge = ""
            if earnings_val:
                is_negative = earnings_val.startswith("-")
                if is_negative:
                    earnings_badge = (
                        f"<span class='kpi kpi-eps-neg'>EPS {earnings_val}</span>"
                    )
                else:
                    earnings_badge = (
                        f"<span class='kpi kpi-eps-pos'>EPS {earnings_val}</span>"
                    )

            potential_str = s.get("growth_pct")
            potential_color = "#cbd5e1"
            if potential_str:
                if potential_str.startswith("-"):
                    potential_color = "#f87171"  # red
                elif potential_str.startswith("+"):
                    potential_color = "#34d399"  # green
            else:
                potential_str = "—"

            # Disclose how the upside was derived (analyst consensus vs model).
            method = s.get("estimate_method")
            method_badge = ""
            if method == "Analyst Consensus":
                method_badge = "<div><span class='method-badge method-analyst'>Analyst</span></div>"
            elif method == "Fundamental Estimate":
                method_badge = "<div><span class='method-badge method-fundamental'>Model Est.</span></div>"

            target_val = s.get("target")
            target_str = f"₹{target_val}" if target_val else "—"

            # Rating badge with analyst count
            analyst_str = f" ({analyst_count})" if analyst_count else ""
            rating_badge = (
                f"<span class='badge badge-neutral' style='font-size: 8px; margin-left: 6px; background-color: #1e293b; color: #60a5fa;'>{rating_text}{analyst_str}</span>"
                if rating_text != "N/A"
                else ""
            )

            price_val = s.get("price")
            price_str = f"₹{price_val}" if price_val else "—"

            stock_rows += f"""
            <tr>
                <td class="stock-ticker">{s['ticker']}{rating_badge}</td>
                <td>{s['name']}{growth_badge}{earnings_badge}</td>
                <td>{price_str}</td>
                <td>{target_str}</td>
                <td class="stock-growth" style="color: {potential_color} !important;">{potential_str}{method_badge}</td>
            </tr>
            <tr>
                <td colspan="5" class="stock-catalyst">
                    <strong>Catalyst:</strong> {s['catalyst']}
                </td>
            </tr>
            """

        # Format emerging players HTML (from dynamic scanner)
        emerging_html = ""
        if (
            "emerging_players" in brief_data
            and sector in brief_data["emerging_players"]
        ):
            players = brief_data["emerging_players"][sector]
            if players:
                players_list = []
                for p in players:
                    if isinstance(p, dict):
                        ticker_str = f" ({p['ticker']})" if p.get("ticker") else ""
                        players_list.append(
                            f"<strong>{p['name']}</strong>{ticker_str} [{p.get('status', 'Scanned')}]"
                        )
                    else:
                        players_list.append(f"<strong>{p}</strong>")

                players_str = ", ".join(players_list)
                emerging_html = f"""
                <div style="margin-top: 15px; padding: 12px; background-color: rgba(245, 158, 11, 0.04); border-left: 3px solid #f59e0b; border-radius: 4px; font-size: 11px; color: #94a3b8; line-height: 1.4;">
                    <strong style="color: #f59e0b; text-transform: uppercase; font-size: 10px; display: block; margin-bottom: 4px;">Emerging Competitor Radar</strong>
                    Spotted news mentions of: {players_str}. Mapped as potential new entrants or disruptive competitors in the {meta['label']} sector.
                </div>
                """

        hidden_stocks = len(stocks) - len(shown_stocks)
        if hidden_stocks > 0:
            stock_rows += (
                f"<tr><td colspan='5' style='font-size: 11px; color: #6b7280;'>"
                f"+ {hidden_stocks} more holding(s) on the "
                f"<a href='{DASHBOARD_URL}' style='color: #60a5fa;' target='_blank'>live dashboard</a>."
                f"</td></tr>"
            )

        body_html += f"""
            <div class="section-card">
                <div class="sector-title">
                    <span class="sector-icon">{meta['icon']}</span>
                    <span>{meta['label']}</span>
                </div>
                <p style="font-size: 13px; color: #94a3b8; margin-top: -10px; margin-bottom: 15px;">{meta['desc']}</p>
                
                <h4 style="margin: 0 0 10px 0; font-size: 13px; text-transform: uppercase; color: #4b5563; letter-spacing: 0.5px;">Latest Bulletins &amp; Policy Signals</h4>
                {news_html}
                
                <h4 style="margin: 15px 0 10px 0; font-size: 13px; text-transform: uppercase; color: #4b5563; letter-spacing: 0.5px;">High-Growth Catalyst Watchlist</h4>
                <table class="stock-table">
                    <thead>
                        <tr>
                            <th>Ticker</th>
                            <th>Company</th>
                            <th>CMP</th>
                            <th>Target</th>
                            <th>Potential</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stock_rows}
                    </tbody>
                </table>
                {emerging_html}
            </div>
        """

    # Append Corporate Agreements & Product Launches
    agreements_html = ""
    agreements = brief_data.get("corporate_agreements", [])
    if agreements:
        items = "".join(
            [
                f"<li><strong>{a['source']}</strong>: {a['title']}</li>"
                for a in agreements[: caps["lists"]]
            ]
        )
        agreements_html = f"""
        <div class="section-card">
            <h3 style="color: #60a5fa; margin-bottom: 10px; font-size: 16px;">Corporate Agreements &amp; Partnerships</h3>
            <ul style="font-size: 13px; line-height: 1.6; padding-left: 20px; color: #cbd5e1;">{items}</ul>
        </div>
        """

    launches_html = ""
    launches = brief_data.get("product_launches", [])
    if launches:
        items = "".join(
            [
                f"<li><strong>{launch.get('company', 'Unknown')}</strong> ({launch.get('industry', 'Manufacturing')}): {launch.get('product', launch.get('title', ''))} <em style='font-size: 11px; color: #94a3b8;'>[{launch.get('source', 'News')}]</em></li>"
                for launch in launches[: caps["lists"]]
            ]
        )
        launches_html = f"""
        <div class="section-card">
            <h3 style="color: #34d399; margin-bottom: 10px; font-size: 16px;">Product Launches &amp; Innovations</h3>
            <ul style="font-size: 13px; line-height: 1.6; padding-left: 20px; color: #cbd5e1;">{items}</ul>
        </div>
        """

    filings_html = ""
    filings = brief_data.get("corporate_filings", [])
    if filings:
        items = "".join(
            [
                f"<li><strong>{f.get('company', 'Unknown')}</strong> ({f.get('industry', 'Corporate')}): {f.get('filing', '')} <em style='font-size: 11px; color: #94a3b8;'>[{f.get('source', 'Exchange')}]</em></li>"
                for f in filings[: caps["lists"]]
            ]
        )
        filings_html = f"""
        <div class="section-card">
            <h3 style="color: #6366f1; margin-bottom: 10px; font-size: 16px;">Corporate Exchange Filings</h3>
            <ul style="font-size: 13px; line-height: 1.6; padding-left: 20px; color: #cbd5e1;">{items}</ul>
        </div>
        """

    # Global Emerging Competitors from PLI
    emerging_competitors = brief_data.get("emerging_competitors", [])
    emerging_html_global = ""
    if emerging_competitors:
        grouped = {}
        for c in emerging_competitors:
            name = c.get("name", "Unknown")
            if name not in grouped:
                grouped[name] = {
                    "ticker": c.get("ticker", ""),
                    "status": c.get("status", ""),
                    "schemes": [],
                }
            if c.get("announcement"):
                grouped[name]["schemes"].append(c.get("announcement"))

        emerging_items = ""
        for name, data in list(grouped.items())[: caps["emerging"]]:
            ticker_str = f" ({data['ticker']})" if data["ticker"] else ""
            status_html = f"<span class='badge badge-success-alert' style='font-size: 8px;'>{data['status']}</span>"
            schemes_html = "".join([f"<li>{s}</li>" for s in data["schemes"][:3]])
            emerging_items += f"<li><strong>{name}</strong>{ticker_str} {status_html}<ul style='padding-left: 20px; font-size: 11px; color: #94a3b8;'>{schemes_html}</ul></li>"
        if len(grouped) > caps["emerging"]:
            emerging_items += (
                f"<li style='color: #6b7280; font-size: 11px;'>"
                f"+ {len(grouped) - caps['emerging']} more on the dashboard.</li>"
            )

        emerging_html_global = f"""
        <div class="section-card">
            <h3 style="color: #60a5fa; margin-bottom: 10px; font-size: 16px;">Emerging Competitors (PLI Approvals)</h3>
            <ul style="font-size: 13px; padding-left: 20px; color: #cbd5e1;">{emerging_items}</ul>
        </div>
        """

    # Append Institutional Activity & SEBI Filings
    inst_html = ""
    inst_activity = brief_data.get("institutional_activity", [])
    sebi_filings = brief_data.get("sebi_filings", [])
    inst_baseline = brief_data.get("institutional_baseline", [])

    baseline_items = ""
    for b in inst_baseline[: caps["lists"]]:
        trend = b.get("accumulation_trend", "Steady")
        trend_color = (
            "#34d399"
            if trend == "Accelerating"
            else ("#f87171" if trend == "Decelerating" else "#94a3b8")
        )
        r1y = b.get("return_1y")
        r1y_str = f"{'+' if (r1y or 0) > 0 else ''}{r1y}%" if r1y is not None else "—"
        baseline_items += (
            f"<li><strong>{b.get('theme', 'Theme')}</strong>: {b.get('fund_name', 'Scheme')} "
            f"<span style='color: {trend_color}; font-size: 11px;'>(1Y {r1y_str} · {trend})</span></li>"
        )

    if inst_activity or sebi_filings or baseline_items:
        inst_items = "".join(
            [
                f"<li><strong>{i['source']}</strong>: {i['headline']}</li>"
                for i in inst_activity[: min(4, caps["lists"])]
            ]
        )
        sebi_items = "".join(
            [
                f"<li><strong>{s['theme']}</strong>: {s['fund_name']} <span class='badge badge-neutral' style='font-size: 8px;'>SID Filed</span></li>"
                for s in sebi_filings[: min(4, caps["lists"])]
            ]
        )
        inst_html = f"""
        <div class="section-card">
            <h3 style="color: #a78bfa; margin-bottom: 10px; font-size: 16px;"> Institutional Capital &amp; Fund Flow Tracker</h3>
            {f'<h4 style="margin: 5px 0; color: #94a3b8; font-size: 12px; text-transform: uppercase;">SEBI SID Filings (Leading Indicator):</h4><ul style="font-size: 13px; padding-left: 20px; color: #cbd5e1; margin-bottom: 10px;">{sebi_items}</ul>' if sebi_items else ''}
            {f'<h4 style="margin: 5px 0; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Institutional Activity Feed (Lagging):</h4><ul style="font-size: 13px; padding-left: 20px; color: #cbd5e1;">{inst_items}</ul>' if inst_items else ''}
            {f'<h4 style="margin: 5px 0; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Accumulation Baseline (Historical MF NAV):</h4><ul style="font-size: 13px; padding-left: 20px; color: #cbd5e1;">{baseline_items}</ul>' if baseline_items else ''}
        </div>
        """

    # Append Graham Valuation & Buffett Moat
    valuation_html = ""
    mos = brief_data.get("margin_of_safety", [])
    buffett = brief_data.get("buffett_valuation", [])

    if mos or buffett:
        # Margin of safety items (Graham value screen)
        passed_mos = [
            m for m in mos if m.get("is_defensive_pass") or m.get("is_bargain")
        ]
        mos_items = ""
        for m in passed_mos[: caps["lists"]]:
            screens = []
            if m.get("is_defensive_pass"):
                screens.append("Defensive")
            if m.get("is_bargain"):
                screens.append("Bargain (NCAV)")
            screens_str = " & ".join(screens)
            mos_items += f"<tr><td class='stock-ticker'>{m['ticker']}</td><td>{m['name']}</td><td>₹{m['price']}</td><td style='color: #34d399;'>{screens_str}</td></tr>"

        buffett_items = "".join(
            [
                f"<tr><td class='stock-ticker'>{b['ticker']}</td><td>{b.get('moat_status', 'Unknown')}</td><td>₹{b.get('owner_earnings', 0)} Cr</td><td style='color: "
                f"{'#34d399' if b.get('passed_retained_test') else '#f87171'};'>{'Pass' if b.get('passed_retained_test') else 'Fail'}</td></tr>"
                for b in buffett[: caps["lists"]]
            ]
        )

        # Valuation Warning / Caution List
        caution_list = []
        for sector, stocks in watchlist.items():
            for s in stocks:
                sc = s.get("screener", {})
                if not sc:
                    continue
                alerts = sc.get("valuation_alerts", [])
                if alerts:
                    caution_list.append(
                        {
                            "ticker": s["ticker"],
                            "name": s["name"],
                            "price": s.get("price", "N/A"),
                            "alerts": list(set(alerts)),
                        }
                    )

        caution_items = ""
        if caution_list:
            for c in caution_list[: caps["caution"]]:
                alerts_str = ", ".join(c["alerts"])
                caution_items += f"<tr><td class='stock-ticker'>{c['ticker']}</td><td>{c['name']}</td><td>₹{c['price']}</td><td style='color: #f87171; font-size: 11px;'>{alerts_str}</td></tr>"
        else:
            caution_items = "<tr><td colspan='4' style='text-align: center; color: #cbd5e1;'>All watchlist stocks passed core filters.</td></tr>"

        scoring_list = []
        for sector, stocks in watchlist.items():
            for s in stocks:
                if "score" in s and s["score"]:
                    scoring_list.append(
                        {
                            "ticker": s["ticker"],
                            "score": s["score"]["overall_score"],
                            "confidence": s["score"]["confidence"],
                            "recommendations": "<br>".join(
                                s["score"]["recommendations"] or []
                            ),
                            "reasons": "<br>".join(s["score"]["reasons"] or ["None"]),
                            "risks": "<br>".join(s["score"]["risks"] or ["None"]),
                        }
                    )

        scoring_list = sorted(scoring_list, key=lambda x: x["score"], reverse=True)
        scoring_items = "".join(
            [
                f"<tr><td class='stock-ticker'>{c['ticker']}</td><td>{c['score']} ({c['confidence']})</td><td style='color: #34d399; font-size: 11px;'>{c['reasons']}</td><td style='color: #f87171; font-size: 11px;'>{c['risks']}</td></tr>"
                for c in scoring_list[: caps["lists"]]
            ]
        )

        valuation_html = f"""
        <div class="section-card">
            <h3 style="color: #f59e0b; margin-bottom: 15px; font-size: 16px;">Core Value Investing Matrix</h3>
            
            <h4 style="margin: 0 0 8px 0; color: #34d399; font-size: 12px; text-transform: uppercase;">Top Ranked AI Scores</h4>
            <table class="stock-table" style="margin-bottom: 15px;">
                <thead><tr><th>Ticker</th><th>Score</th><th>Tailwinds / Reasons</th><th>Identified Risks</th></tr></thead>
                <tbody>{scoring_items}</tbody>
            </table>
            
            <h4 style="margin: 0 0 8px 0; color: #34d399; font-size: 12px; text-transform: uppercase;">Graham Margin of Safety Pass List</h4>
            <table class="stock-table" style="margin-bottom: 15px;">
                <thead><tr><th>Ticker</th><th>Company</th><th>Price</th><th>Screen Passed</th></tr></thead>
                <tbody>{mos_items}</tbody>
            </table>
            
            <h4 style="margin: 15px 0 8px 0; color: #a78bfa; font-size: 12px; text-transform: uppercase;">Warren Buffett Allocation &amp; Moat Screens</h4>
            <table class="stock-table" style="margin-bottom: 15px;">
                <thead><tr><th>Ticker</th><th>Moat</th><th>Owner Earnings</th><th>$1 Test</th></tr></thead>
                <tbody>{buffett_items}</tbody>
            </table>
            
            <h4 style="margin: 15px 0 8px 0; color: #f87171; font-size: 12px; text-transform: uppercase;">⚠ Valuation Caution List &amp; Warnings</h4>
            <table class="stock-table">
                <thead><tr><th>Ticker</th><th>Company</th><th>Price</th><th>Warnings / Failed Criteria</th></tr></thead>
                <tbody>{caution_items}</tbody>
            </table>
        </div>
        """

    sector_valuation_html = _build_sector_valuation_html(
        brief_data.get("sector_valuation", [])
    )
    sector_growth_html = _build_sector_growth_html(brief_data.get("sector_growth", []))

    body_html += (
        sector_valuation_html
        + sector_growth_html
        + agreements_html
        + launches_html
        + filings_html
        + emerging_html_global
        + inst_html
        + valuation_html
    )

    body_html += f"""
            <div class="footer">
                <p>This briefing is an automated policy analysis generated using PIB &amp; public financial indicators.</p>
                {f'<p>Data freshness: live prices refreshed for {freshness["updated"]}/{freshness["total"]} stocks.</p>' if freshness and freshness.get("total") else ''}
                <p>To view full interactive charts, visit the <a href="{DASHBOARD_URL}" target="_blank">Policy Tracker Archive Dashboard</a>.</p>
                <p>&copy; 2026 Policy Tracker. India Growth Investing.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Gmail clips messages over ~102 KB; indentation alone was ~20% of the
    # document. Whitespace is insignificant in HTML, so compact it.
    return "\n".join(line.strip() for line in body_html.split("\n") if line.strip())


def build_html_email(brief_data, watchlist):
    """Renders the briefing email, guaranteed under Gmail's clip limit.

    Renders at full richness first; if the document exceeds the size budget,
    re-renders once with compact row caps rather than risk the client
    truncating the message mid-table.
    """
    html = _render_email(brief_data, watchlist, _CAPS_NORMAL)
    size = len(html.encode("utf-8"))
    if size > _SIZE_BUDGET_BYTES:
        log.warning(
            f"Briefing email is {size} bytes (> {_SIZE_BUDGET_BYTES}); "
            f"re-rendering with compact caps."
        )
        html = _render_email(brief_data, watchlist, _CAPS_COMPACT)
    return html


def send_email(html_content):
    """Sends the briefing email using environment variable configurations."""
    raw_emails = os.environ.get("RECEIVER_EMAIL", "")
    receiver_emails = [
        email.strip() for email in raw_emails.split(",") if email.strip()
    ]
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not all([receiver_emails, smtp_server, smtp_port, smtp_username, smtp_password]):
        log.warning(
            "Email credentials not fully configured. Skipping sending. Writing preview to 'email_preview.html'."
        )
        with open("email_preview.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        return False

    log.info(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = (
        f"🇮🇳 Daily India Policy Briefing: {datetime.date.today().strftime('%d %b %Y')}"
    )
    msg["From"] = smtp_username
    msg["To"] = ", ".join(receiver_emails)

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()

        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, receiver_emails, msg.as_string())
        server.quit()
        log.info(f"SUCCESS: Daily briefing email sent to {', '.join(receiver_emails)}!")
        return True
    except (smtplib.SMTPException, OSError) as e:
        log.error(f"FAILED: SMTP connection error: {e}")
        return False
