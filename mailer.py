import os
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logger import log
from config import SECTOR_METADATA


def build_html_email(brief_data, watchlist):
    """Renders the HTML structure for the email notification."""
    today_str = datetime.date.today().strftime("%B %d, %Y")

    style = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0b0f19; color: #cbd5e1; margin: 0; padding: 20px; }
        .container { max-width: 650px; margin: 0 auto; background-color: #111827; border-radius: 12px; border: 1px solid #1f2937; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .header { background: linear-gradient(135deg, #1e3a8a, #0f172a); padding: 30px; text-align: center; border-bottom: 2px solid #3b82f6; }
        .header h1 { margin: 0; font-size: 24px; color: #ffffff; letter-spacing: 0.5px; }
        .header p { margin: 5px 0 0 0; font-size: 14px; color: #94a3b8; }
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

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {style}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🇮🇳 India Policy & Growth Sector Brief</h1>
                <p>Daily Intelligence Report | {today_str}</p>
            </div>
    """

    for sector, news_items in brief_data.items():
        if sector in (
            "emerging_players",
            "emerging_competitors",
            "corporate_agreements",
            "product_launches",
            "sebi_filings",
            "institutional_activity",
            "margin_of_safety",
            "buffett_valuation",
        ):
            continue
        if sector not in SECTOR_METADATA:
            continue
        meta = SECTOR_METADATA[sector]
        stocks = watchlist.get(sector, [])

        # Format news HTML
        news_html = ""
        if news_items:
            for item in news_items:
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
        else:
            news_html = "<p style='font-size: 13px; color: #4b5563; font-style: italic;'>No policy updates tracked in this cycle.</p>"

        # Format stocks HTML table
        stock_rows = ""
        for s in stocks:
            rating_text = s.get("rating", "N/A")
            growth_val = s.get("revenue_growth")
            earnings_val = s.get("earnings_growth")
            analyst_count = s.get("analyst_count")

            # Contextual revenue growth badge
            growth_badge = ""
            if growth_val:
                is_negative = growth_val.startswith("-")
                if is_negative:
                    growth_badge = f"<span style='margin-left: 6px; font-size: 9px; background-color: #7f1d1d; color: #f87171; padding: 2px 6px; border-radius: 4px; font-weight: bold; display: inline-block;'>📉 {growth_val} YoY</span>"
                else:
                    growth_badge = f"<span style='margin-left: 6px; font-size: 9px; background-color: #065f46; color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: bold; display: inline-block;'>🔥 {growth_val} YoY</span>"

            # Contextual earnings growth badge
            earnings_badge = ""
            if earnings_val:
                is_negative = earnings_val.startswith("-")
                if is_negative:
                    earnings_badge = f"<span style='margin-left: 4px; font-size: 8px; background-color: #2a1215; color: #f87171; padding: 2px 5px; border-radius: 3px; display: inline-block;'>EPS {earnings_val}</span>"
                else:
                    earnings_badge = f"<span style='margin-left: 4px; font-size: 8px; background-color: #1e1b4b; color: #a78bfa; padding: 2px 5px; border-radius: 3px; display: inline-block;'>EPS {earnings_val}</span>"

            potential_str = s.get("growth_pct")
            potential_color = "#cbd5e1"
            if potential_str:
                if potential_str.startswith("-"):
                    potential_color = "#f87171"  # red
                elif potential_str.startswith("+"):
                    potential_color = "#34d399"  # green
            else:
                potential_str = "—"

            target_val = s.get("target")
            target_str = f"₹{target_val}" if target_val else "—"

            # Rating badge with analyst count
            analyst_str = f" ({analyst_count})" if analyst_count else ""
            rating_badge = (
                f"<span class='badge badge-neutral' style='font-size: 8px; margin-left: 6px; background-color: #1e293b; color: #60a5fa;'>{rating_text}{analyst_str}</span>"
                if rating_text != "N/A"
                else ""
            )

            stock_rows += f"""
            <tr>
                <td class="stock-ticker">{s['ticker']}{rating_badge}</td>
                <td>{s['name']}{growth_badge}{earnings_badge}</td>
                <td>₹{s['price']}</td>
                <td>{target_str}</td>
                <td class="stock-growth" style="color: {potential_color} !important;">{potential_str}</td>
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
                    <strong style="color: #f59e0b; text-transform: uppercase; font-size: 10px; display: block; margin-bottom: 4px;">📡 Emerging Competitor Radar</strong>
                    Spotted news mentions of: {players_str}. Mapped as potential new entrants or disruptive competitors in the {meta['label']} sector.
                </div>
                """

        body_html += f"""
            <div class="section-card">
                <div class="sector-title">
                    <span class="sector-icon">{meta['icon']}</span>
                    <span>{meta['label']}</span>
                </div>
                <p style="font-size: 13px; color: #94a3b8; margin-top: -10px; margin-bottom: 15px;">{meta['desc']}</p>
                
                <h4 style="margin: 0 0 10px 0; font-size: 13px; text-transform: uppercase; color: #4b5563; letter-spacing: 0.5px;">Latest Bulletins & Policy Signals</h4>
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
                for a in agreements[:5]
            ]
        )
        agreements_html = f"""
        <div class="section-card">
            <h3 style="color: #60a5fa; margin-bottom: 10px; font-size: 16px;">🤝 Corporate Agreements & Partnerships</h3>
            <ul style="font-size: 13px; line-height: 1.6; padding-left: 20px; color: #cbd5e1;">{items}</ul>
        </div>
        """

    launches_html = ""
    launches = brief_data.get("product_launches", [])
    if launches:
        items = "".join(
            [
                f"<li><strong>{launch['source']}</strong>: {launch['title']}</li>"
                for launch in launches[:5]
            ]
        )
        launches_html = f"""
        <div class="section-card">
            <h3 style="color: #34d399; margin-bottom: 10px; font-size: 16px;">🚀 Product Launches & Innovations</h3>
            <ul style="font-size: 13px; line-height: 1.6; padding-left: 20px; color: #cbd5e1;">{items}</ul>
        </div>
        """

    # Append Institutional Activity & SEBI Filings
    inst_html = ""
    inst_activity = brief_data.get("institutional_activity", [])
    sebi_filings = brief_data.get("sebi_filings", [])

    if inst_activity or sebi_filings:
        inst_items = "".join(
            [
                f"<li><strong>{i['source']}</strong>: {i['headline']}</li>"
                for i in inst_activity[:4]
            ]
        )
        sebi_items = "".join(
            [
                f"<li><strong>{s['theme']}</strong>: {s['fund_name']} <span class='badge badge-neutral' style='font-size: 8px;'>SID Filed</span></li>"
                for s in sebi_filings[:4]
            ]
        )
        inst_html = f"""
        <div class="section-card">
            <h3 style="color: #a78bfa; margin-bottom: 10px; font-size: 16px;">🏛️ Institutional Capital & Fund Flow Tracker</h3>
            {f'<h4 style="margin: 5px 0; color: #94a3b8; font-size: 12px; text-transform: uppercase;">SEBI SID Filings (Leading Indicator):</h4><ul style="font-size: 13px; padding-left: 20px; color: #cbd5e1; margin-bottom: 10px;">{sebi_items}</ul>' if sebi_items else ''}
            {f'<h4 style="margin: 5px 0; color: #94a3b8; font-size: 12px; text-transform: uppercase;">Institutional Activity Feed (Lagging):</h4><ul style="font-size: 13px; padding-left: 20px; color: #cbd5e1;">{inst_items}</ul>' if inst_items else ''}
        </div>
        """

    # Append Graham Valuation & Buffett Moat
    valuation_html = ""
    mos = brief_data.get("margin_of_safety", [])
    buffett = brief_data.get("buffett_valuation", [])

    if mos or buffett:
        # Margin of safety items (Graham value screen)
        passed_mos = [m for m in mos if m["is_defensive_pass"] or m["is_bargain"]]
        mos_items = ""
        for m in passed_mos[:5]:
            screens = []
            if m["is_defensive_pass"]:
                screens.append("Defensive")
            if m["is_bargain"]:
                screens.append("Bargain (NCAV)")
            screens_str = " & ".join(screens)
            mos_items += f"<tr><td class='stock-ticker'>{m['ticker']}</td><td>{m['name']}</td><td>₹{m['price']}</td><td style='color: #34d399;'>{screens_str}</td></tr>"

        buffett_items = "".join(
            [
                f"<tr><td class='stock-ticker'>{b['ticker']}</td><td>{b['moat_status']}</td><td>₹{b['owner_earnings']} Cr</td><td style='color: "
                + ("#34d399" if b["passed_retained_test"] else "#f87171")
                + ";'>{'Pass' if b['passed_retained_test'] else 'Fail'}</td></tr>"
                for b in buffett[:5]
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
                            "price": s["price"],
                            "alerts": list(set(alerts)),
                        }
                    )

        caution_items = ""
        if caution_list:
            for c in caution_list[:8]:
                alerts_str = ", ".join(c["alerts"])
                caution_items += f"<tr><td class='stock-ticker'>{c['ticker']}</td><td>{c['name']}</td><td>₹{c['price']}</td><td style='color: #f87171; font-size: 11px;'>{alerts_str}</td></tr>"
        else:
            caution_items = "<tr><td colspan='4' style='text-align: center; color: #cbd5e1;'>All watchlist stocks passed core filters.</td></tr>"

        valuation_html = f"""
        <div class="section-card">
            <h3 style="color: #f59e0b; margin-bottom: 15px; font-size: 16px;">📊 Core Value Investing Matrix</h3>
            
            <h4 style="margin: 0 0 8px 0; color: #34d399; font-size: 12px; text-transform: uppercase;">🛡️ Graham Margin of Safety Pass List</h4>
            <table class="stock-table" style="margin-bottom: 15px;">
                <thead><tr><th>Ticker</th><th>Company</th><th>Price</th><th>Screen Passed</th></tr></thead>
                <tbody>{mos_items}</tbody>
            </table>
            
            <h4 style="margin: 15px 0 8px 0; color: #a78bfa; font-size: 12px; text-transform: uppercase;">🏰 Warren Buffett Allocation & Moat Screens</h4>
            <table class="stock-table" style="margin-bottom: 15px;">
                <thead><tr><th>Ticker</th><th>Moat</th><th>Owner Earnings</th><th>$1 Test</th></tr></thead>
                <tbody>{buffett_items}</tbody>
            </table>
            
            <h4 style="margin: 15px 0 8px 0; color: #f87171; font-size: 12px; text-transform: uppercase;">⚠️ Valuation Caution List & Warnings</h4>
            <table class="stock-table">
                <thead><tr><th>Ticker</th><th>Company</th><th>Price</th><th>Warnings / Failed Criteria</th></tr></thead>
                <tbody>{caution_items}</tbody>
            </table>
        </div>
        """

    body_html += agreements_html + launches_html + inst_html + valuation_html

    body_html += """
            <div class="footer">
                <p>This briefing is an automated policy analysis generated using PIB & public financial indicators.</p>
                <p>To view full interactive charts, visit the <a href="#" target="_blank">Policy Tracker Archive Dashboard</a>.</p>
                <p>&copy; 2026 Policy Tracker. India Growth Investing.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return body_html


def send_email(html_content):
    """Sends the briefing email using environment variable configurations."""
    receiver_email = os.environ.get("RECEIVER_EMAIL")
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not all([receiver_email, smtp_server, smtp_port, smtp_username, smtp_password]):
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
    msg["To"] = receiver_email

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
        server.sendmail(smtp_username, receiver_email, msg.as_string())
        server.quit()
        log.info(f"SUCCESS: Daily briefing email sent to {receiver_email}!")
        return True
    except Exception as e:
        log.error(f"FAILED: SMTP connection error: {e}")
        return False
