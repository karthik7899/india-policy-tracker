import os
import sys
import json
import datetime
import urllib.parse
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Ensure external dependencies are imported, handle graceful fallback if not installed yet
try:
    import feedparser
except ImportError:
    print("feedparser is required. Please install it using 'pip install feedparser'")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("requests is required. Please install it using 'pip install requests'")
    sys.exit(1)

# Curated Stock Watchlist Database
STOCK_WATCHLIST = {
    "clean_energy": [
        {"ticker": "TATAPOWER", "name": "Tata Power", "price": "432.50", "target": "520.00", "growth_pct": "20.2%", "catalyst": "Massive scaling in solar generation, microgrids, and leading India's EV charging network grid."},
        {"ticker": "SUZLON", "name": "Suzlon Energy", "price": "50.15", "target": "68.00", "growth_pct": "35.6%", "catalyst": "Turnaround story, completely debt-free, dominating wind turbine supply with a record order book."},
        {"ticker": "ADANIGREEN", "name": "Adani Green Energy", "price": "1845.00", "target": "2200.00", "growth_pct": "19.2%", "catalyst": "Developing the world's largest renewable energy park in Khavda, Gujarat (30 GW capacity target)."}
    ],
    "data_center_support": [
        {"ticker": "SCHNEIDER", "name": "Schneider Electric Infra", "price": "855.00", "target": "1120.00", "growth_pct": "31.0%", "catalyst": "Critical supplier of electrical distribution, smart grids, and high-efficiency cooling for data centers."},
        {"ticker": "STLTECH", "name": "Sterlite Technologies (STL)", "price": "142.10", "target": "195.00", "growth_pct": "37.2%", "catalyst": "Expanding optical fiber and cable capacities to meet hyper-scale data center interconnect demands."},
        {"ticker": "ANANTRAJ", "name": "Anant Raj Ltd", "price": "352.40", "target": "480.00", "growth_pct": "36.2%", "catalyst": "Real-estate developer transitioning commercial properties into major data center hubs in NCR."}
    ],
    "cybersecurity": [
        {"ticker": "TCS", "name": "Tata Consultancy Services", "price": "4015.00", "target": "4800.00", "growth_pct": "19.6%", "catalyst": "Expanding sovereign cloud and secure cyber command centers globally for enterprise clients."},
        {"ticker": "QUICKHEAL", "name": "Quick Heal Technologies", "price": "552.00", "target": "720.00", "growth_pct": "30.4%", "catalyst": "Surging enterprise adoption of their 'Seqrite' cybersecurity platform and government IT contracts."}
    ],
    "surveillance_security": [
        {"ticker": "CPPLUS", "name": "Aditya Infotech (CP PLUS)", "price": "712.50", "target": "920.00", "growth_pct": "29.1%", "catalyst": "CCTV market leader (35%+ share) newly listed, scaling domestic camera manufacturing under PLI."},
        {"ticker": "DIXON", "name": "Dixon Technologies", "price": "11240.00", "target": "14200.00", "growth_pct": "26.3%", "catalyst": "Primary EMS contract manufacturer producing CCTVs and DVRs for CP Plus and others under PLI."},
        {"ticker": "ADSL", "name": "Allied Digital Services", "price": "182.30", "target": "240.00", "growth_pct": "31.7%", "catalyst": "System integrator winning smart/safe city surveillance projects, managing master command centers."},
        {"ticker": "IDEAFORGE", "name": "IdeaForge Technology", "price": "702.15", "target": "950.00", "growth_pct": "35.3%", "catalyst": "Pioneer in tactical and mapping drone systems, primary supplier for Indian Army and police borders."}
    ],
    "manufacturing_electronics": [
        {"ticker": "DIXON", "name": "Dixon Technologies", "price": "11240.00", "target": "14200.00", "growth_pct": "26.3%", "catalyst": "Leader in electronic assembly (mobile, laptop, LED TV), heavily subsidized under manufacturing PLI."},
        {"ticker": "KAYNES", "name": "Kaynes Technology", "price": "3425.00", "target": "4400.00", "growth_pct": "28.5%", "catalyst": "High-end electronics and PCBA manufacturing, setting up a state-of-the-art semiconductor OSAT plant."},
        {"ticker": "CGPOWER", "name": "CG Power & Industrial", "price": "658.00", "target": "820.00", "growth_pct": "24.6%", "catalyst": "Partnering on a $1B semiconductor fab, strong order pipeline in railways and power grid equipment."}
    ],
    "fmcg": [
        {"ticker": "VBL", "name": "Varun Beverages (PepsiCo)", "price": "1510.00", "target": "1900.00", "growth_pct": "25.8%", "catalyst": "PepsiCo's dominant bottler, expanding into newer territories and scaling dairy/juice products."},
        {"ticker": "TATACONSUM", "name": "Tata Consumer Products", "price": "1122.00", "target": "1350.00", "growth_pct": "20.3%", "catalyst": "Premiumization strategy in foods & beverages, high-growth acquisitions (Capital Foods, Organic India)."},
        {"ticker": "ITC", "name": "ITC Ltd", "price": "431.10", "target": "510.00", "growth_pct": "18.3%", "catalyst": "Resilient cigarette margins funding rapid expansion of high-margin FMCG brands, direct rural boost play."}
    ],
    "sports_athleisure": [
        {"ticker": "METROBRAND", "name": "Metro Brands Ltd", "price": "1152.00", "target": "1480.00", "growth_pct": "28.5%", "catalyst": "Exclusive retail rights for Fila and Foot Locker in India, expanding athleisure footprint rapidly."},
        {"ticker": "CAMPUS", "name": "Campus Activewear", "price": "262.50", "target": "340.00", "growth_pct": "29.5%", "catalyst": "Dominant direct-to-consumer sports footwear brand in tier-2/3 cities, major beneficiary of fitness trends."},
        {"ticker": "PAGEIND", "name": "Page Industries", "price": "36450.00", "target": "44000.00", "growth_pct": "20.7%", "catalyst": "Jockey master franchise holder, expanding sports shorts, tees, and athleisure wear into rural hubs."}
    ],
    "big_cap_industries": [
        {"ticker": "LT", "name": "Larsen & Toubro (L&T)", "price": "3515.00", "target": "4200.00", "growth_pct": "19.5%", "catalyst": "Heavy infrastructure leader, direct beneficiary of the government's ₹11.11 Lakh Cr CAPEX budget."},
        {"ticker": "RELIANCE", "name": "Reliance Industries", "price": "2912.00", "target": "3500.00", "growth_pct": "20.2%", "catalyst": "Consolidating 5G market share, scaling retail stores, and commissioning green energy gigafactories."}
    ]
}

SECTOR_METADATA = {
    "clean_energy": {"label": "Clean Energy", "icon": "⚡", "desc": "Solar, Wind, Green Hydrogen, and Grid Transmission initiatives."},
    "data_center_support": {"label": "Data Center Support", "icon": "🖥️", "desc": "Power cooling, high-speed fiber cables, and server space infrastructure."},
    "cybersecurity": {"label": "Cybersecurity", "icon": "🛡️", "desc": "Data protection, software defense systems, and network security policies."},
    "surveillance_security": {"label": "Surveillance & CCTV", "icon": "📷", "desc": "Smart City CCTVs, border security systems, and commercial surveillance cameras."},
    "manufacturing_electronics": {"label": "Manufacturing & Electronics", "icon": "🏭", "desc": "PLI programs, semiconductor fabrications, and local contract assembly."},
    "fmcg": {"label": "FMCG & Consumption", "icon": "🛒", "desc": "Rural disposable income, food processing, and consumer product growth."},
    "sports_athleisure": {"label": "Sports & Athleisure", "icon": "👟", "desc": "Active footwear, fitness apparel, and sports licensing brands."},
    "big_cap_industries": {"label": "Big Cap Industries", "icon": "🏛️", "desc": "Nation-building conglomerates, heavy engineering, and infrastructure giants."}
}

# RSS queries targeted at Indian policies and financial events
SECTOR_QUERIES = {
    "clean_energy": [
        'site:pib.gov.in "solar" OR "renewable" OR "green hydrogen"',
        'India clean energy policy ministry power',
        '"Adani Green" OR "Tata Power" OR "Suzlon" energy order'
    ],
    "data_center_support": [
        'site:pib.gov.in "data center" OR "digital infrastructure"',
        'India data center policy expansion investments',
        '"Anant Raj" OR "Schneider" data center power'
    ],
    "cybersecurity": [
        'site:pib.gov.in "cyber security" OR "cybersecurity" OR "CERT-In"',
        'India cyber security policy enterprise network protection',
        'TCS Quick Heal cyber contracts'
    ],
    "surveillance_security": [
        'site:pib.gov.in "CCTV" OR "safe city" OR "surveillance"',
        'India smart city CCTV cameras border defense drones',
        '"CP Plus" OR "Aditya Infotech" OR "Allied Digital" OR "IdeaForge" surveillance'
    ],
    "manufacturing_electronics": [
        'site:pib.gov.in "PLI" electronics OR "semiconductor" OR "OSAT"',
        'India electronics manufacturing PLI scheme semiconductor fab',
        'Dixon Kaynes semiconductor factory'
    ],
    "fmcg": [
        'site:pib.gov.in "agriculture" OR "rural development" OR "food processing"',
        'India FMCG consumption rural demand inflation',
        'Varun Beverages ITC results shares'
    ],
    "sports_athleisure": [
        'site:pib.gov.in "sports" OR "Khelo India" OR "footwear PLI"',
        'India sports brand athleisure market growth campus footwear',
        'Metro Brands Campus Activewear shares'
    ],
    "big_cap_industries": [
        'site:pib.gov.in "infrastructure" OR "capital expenditure" OR "Gati Shakti"',
        'India infra capex budget Larsen Toubro Reliance industries',
        'L&T order book Reliance green energy'
    ]
}

def clean_news_item(entry, query_term):
    """Formats and cleans an RSS entry. Returns None if the article is older than 7 days."""
    title = entry.get("title", "").split(" - ")[0]  # Remove source from title if appended
    source = entry.get("source", {}).get("title", "Finance Media")
    if " - " in entry.get("title", ""):
        parts = entry.get("title", "").split(" - ")
        if len(parts) > 1:
            source = parts[-1]
            
    link = entry.get("link", "")
    
    pub_date_raw = entry.get("published", "")
    pub_date = datetime.date.today().strftime("%d %b %Y")
    if pub_date_raw:
        try:
            # Parse standard RSS dates and filter out old ones
            parsed_t = entry.get("published_parsed")
            if parsed_t:
                article_date = datetime.date(*parsed_t[:3])
                # Filter out articles older than 7 days
                age_days = (datetime.date.today() - article_date).days
                if age_days > 7:
                    return None
                pub_date = article_date.strftime("%d %b %Y")
        except Exception:
            pass

    # Simple impact heuristic: does title have key high-growth words?
    summary = entry.get("summary", "")
    combined_text = (title + " " + summary).lower()
    impact = "Neutral"
    if any(w in combined_text for w in ["hike", "scheme approved", "approved", "subsidy", "record profit", "expansion", "secures order", "order of", "invests", "joint venture", "bullah", "launch", "semiconductor fab", "pli benefit"]):
        impact = "Positive"
    elif any(w in combined_text for w in ["delay", "investigation", "fine", "loss", "tariff hike negative", "penalty", "tax increase", "curb"]):
        impact = "Negative"

    return {
        "title": title,
        "source": source,
        "link": link,
        "date": pub_date,
        "impact": impact,
        "relevance": query_term
    }

def fetch_feed_data():
    """Fetches news and policy announcements from Google News RSS for all sectors."""
    print("Initializing RSS Aggregation engine...")
    today_brief = {}
    
    for sector, queries in SECTOR_QUERIES.items():
        print(f"Aggregating feed data for sector: {sector}...")
        sector_news = []
        seen_titles = set()
        
        for query in queries:
            # Append " when:7d" to ensure Google only returns recent articles
            query_with_time = f"{query} when:7d"
            encoded_query = urllib.parse.quote(query_with_time)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
            
            try:
                feed = feedparser.parse(rss_url)
                # Take top 3 articles per query to ensure high relevance
                for entry in feed.entries[:3]:
                    cleaned = clean_news_item(entry, query)
                    if cleaned is None:
                        continue
                    title_lower = cleaned["title"].lower()
                    if title_lower not in seen_titles:
                        seen_titles.add(title_lower)
                        sector_news.append(cleaned)
            except Exception as e:
                print(f"Error parsing feed for query '{query}': {e}")
                
        # Sort so Positive impacts are highlighted first
        sector_news.sort(key=lambda x: 1 if x["impact"] == "Positive" else (3 if x["impact"] == "Negative" else 2))
        today_brief[sector] = sector_news[:4] # Store top 4 articles per sector
        
    return today_brief

def build_html_email(brief_data):
    """Renders the HTML structure for the email notification."""
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    # CSS variables embedded in email style
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
        meta = SECTOR_METADATA[sector]
        stocks = STOCK_WATCHLIST[sector]
        
        # Format news HTML
        news_html = ""
        if news_items:
            for item in news_items:
                badge_class = "badge-positive" if item["impact"] == "Positive" else ("badge-negative" if item["impact"] == "Negative" else "badge-neutral")
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
            stock_rows += f"""
            <tr>
                <td class="stock-ticker">{s['ticker']}</td>
                <td>{s['name']}</td>
                <td>₹{s['price']}</td>
                <td>₹{s['target']}</td>
                <td class="stock-growth">+{s['growth_pct']}</td>
            </tr>
            <tr>
                <td colspan="5" class="stock-catalyst">
                    <strong>Catalyst:</strong> {s['catalyst']}
                </td>
            </tr>
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
            </div>
        """

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
        print("\n[WARNING] Email credentials not fully configured in environment variables.")
        print("Required: RECEIVER_EMAIL, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD")
        print("Skipping email delivery. Writing email preview output locally to 'email_preview.html' instead.")
        with open("email_preview.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("Email preview written to: 'email_preview.html'. Open it to check layout.")
        return False

    print(f"Connecting to SMTP server {smtp_server}:{smtp_port}...")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🇮🇳 Daily India Policy Briefing: {datetime.date.today().strftime('%d %b %Y')}"
    msg["From"] = smtp_username
    msg["To"] = receiver_email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        # Determine port connection method (SSL or STARTTLS)
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, receiver_email, msg.as_string())
        server.quit()
        print(f"SUCCESS: Daily briefing email sent successfully to {receiver_email}!")
        return True
    except Exception as e:
        print(f"FAILED: SMTP connection error: {e}")
        return False

def update_live_stock_prices():
    """Updates STOCK_WATCHLIST with live prices from Yahoo Finance and recalculates growth potentials."""
    print("Fetching live stock prices from Yahoo Finance...")
    try:
        import yfinance as yf
    except ImportError:
        print("[WARNING] yfinance not installed. Skip live stock price update. Using static mock prices.")
        return

    for sector, stocks in STOCK_WATCHLIST.items():
        for stock in stocks:
            ticker = stock["ticker"]
            yahoo_ticker = f"{ticker}.NS"
            try:
                ticker_obj = yf.Ticker(yahoo_ticker)
                hist = ticker_obj.history(period="1d")
                if not hist.empty:
                    live_price = float(hist['Close'].iloc[-1])
                    stock["price"] = f"{live_price:.2f}"
                    
                    # Recalculate potential growth based on live price and target price
                    target_price = float(stock["target"])
                    if live_price > 0:
                        growth_val = ((target_price - live_price) / live_price) * 100
                        stock["growth_pct"] = f"{growth_val:.1f}%"
                        print(f"Updated {ticker}: Price = {live_price:.2f}, Target = {target_price:.2f} ({growth_val:.1f}%)")
                else:
                    print(f"Warning: No data returned for {yahoo_ticker}. Using static price.")
            except Exception as e:
                print(f"Error updating price for {yahoo_ticker}: {e}. Using static price.")

def save_data_for_dashboard(brief_data):
    """Saves the aggregated feed data to a JSON file for the static dashboard."""
    output = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watchlist": STOCK_WATCHLIST,
        "sectors": SECTOR_METADATA,
        "briefing": brief_data
    }
    
    with open("dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        
    print("SUCCESS: Updated data saved to 'dashboard_data.json' for web dashboard display.")

if __name__ == "__main__":
    # Update stock watchlist with live Yahoo Finance prices
    update_live_stock_prices()
    
    # Gather data
    data = fetch_feed_data()
    
    # Save for dashboard
    save_data_for_dashboard(data)
    
    # Render HTML
    html = build_html_email(data)
    
    # Mail it
    send_email(html)
    
    print("Briefing cycle finished successfully.")
