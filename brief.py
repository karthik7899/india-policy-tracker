import os
import sys
import re
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

# Curated Stock Watchlist Database (Default fallback)
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

# Try loading watchlist from file
watchlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
try:
    if os.path.exists(watchlist_path):
        with open(watchlist_path, "r", encoding="utf-8") as f:
            STOCK_WATCHLIST = json.load(f)
        print("Successfully loaded STOCK_WATCHLIST from watchlist.json")
    else:
        with open(watchlist_path, "w", encoding="utf-8") as f:
            json.dump(STOCK_WATCHLIST, f, indent=2, ensure_ascii=False)
        print("Created watchlist.json with default stock database")
except Exception as e:
    print(f"Error loading/writing watchlist.json: {e}")

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
        if sector == "emerging_players":
            continue
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
            
            potential_str = s['growth_pct']
            potential_color = "#34d399"  # green
            if potential_str.startswith("-"):
                potential_color = "#f87171"  # red
            elif potential_str == "0.0%" or potential_str == "+0.0%":
                potential_color = "#cbd5e1"
            
            # Rating badge with analyst count
            analyst_str = f" ({analyst_count})" if analyst_count else ""
            rating_badge = f"<span class='badge badge-neutral' style='font-size: 8px; margin-left: 6px; background-color: #1e293b; color: #60a5fa;'>{rating_text}{analyst_str}</span>" if rating_text != "N/A" else ""
            
            stock_rows += f"""
            <tr>
                <td class="stock-ticker">{s['ticker']}{rating_badge}</td>
                <td>{s['name']}{growth_badge}{earnings_badge}</td>
                <td>₹{s['price']}</td>
                <td>₹{s['target']}</td>
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
        if "emerging_players" in brief_data and sector in brief_data["emerging_players"]:
            players_str = ", ".join(brief_data["emerging_players"][sector])
            emerging_html = f"""
            <div style="margin-top: 15px; padding: 12px; background-color: rgba(245, 158, 11, 0.04); border-left: 3px solid var(--warning); border-radius: 4px; font-size: 11px; color: #94a3b8; line-height: 1.4;">
                <strong style="color: var(--warning); text-transform: uppercase; font-size: 10px; display: block; margin-bottom: 4px;">📡 Emerging Competitor Radar</strong>
                Spotted news mentions of <strong>{players_str}</strong>. Mapped as a potential new entrant or disruptive competitor in the {meta['label']} sector.
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
    """Updates STOCK_WATCHLIST with live prices and multi-source estimation metrics from Yahoo Finance.
    
    Fetches the following for each stock:
    - Live closing price (from historical data)
    - targetMedianPrice (more robust than mean - less affected by outlier analyst estimates)
    - targetMeanPrice (average analyst consensus)
    - targetHighPrice / targetLowPrice (range of analyst targets)
    - numberOfAnalystOpinions (analyst coverage depth - higher = more reliable)
    - recommendationKey (buy/hold/sell consensus label)
    - recommendationMean (1=Strong Buy to 5=Sell, numeric score)
    - revenueGrowth (YoY revenue growth rate)
    - earningsGrowth (YoY earnings/EPS growth rate)
    """
    print("Fetching live stock prices and multi-source estimation metrics from Yahoo Finance...")
    try:
        import yfinance as yf
    except ImportError:
        print("[WARNING] yfinance not installed. Skip live stock price update. Using static mock prices.")
        return

    for sector, stocks in STOCK_WATCHLIST.items():
        for stock in stocks:
            ticker = stock["ticker"]
            yahoo_ticker = f"{ticker}.NS"
            
            # Set default values for new keys
            stock["rating"] = "N/A"
            stock["revenue_growth"] = None
            stock["earnings_growth"] = None
            stock["analyst_count"] = None
            stock["target_median"] = None
            stock["target_high"] = None
            stock["target_low"] = None
            stock["rec_score"] = None
            
            try:
                ticker_obj = yf.Ticker(yahoo_ticker)
                
                # Fetch live price
                hist = ticker_obj.history(period="1d")
                if not hist.empty:
                    live_price = float(hist['Close'].iloc[-1])
                    stock["price"] = f"{live_price:.2f}"
                else:
                    live_price = float(stock["price"])
                    print(f"Warning: No close history for {yahoo_ticker}. Using static price.")
                
                # Fetch broker targets and financials from .info
                info = ticker_obj.info
                if info:
                    # --- TARGET PRICE ESTIMATION (multi-source cross-reference) ---
                    # Primary: Use MEDIAN target (more robust against outlier analysts)
                    # Fallback: Use MEAN target if median not available
                    median_target = info.get("targetMedianPrice")
                    mean_target = info.get("targetMeanPrice")
                    high_target = info.get("targetHighPrice")
                    low_target = info.get("targetLowPrice")
                    analyst_count = info.get("numberOfAnalystOpinions")
                    
                    # Store analyst coverage depth
                    if analyst_count and int(analyst_count) > 0:
                        stock["analyst_count"] = int(analyst_count)
                    
                    # Primary target: prefer median, fall back to mean
                    chosen_target = None
                    if median_target and float(median_target) > 0:
                        chosen_target = float(median_target)
                        stock["target_median"] = f"{chosen_target:.2f}"
                    if mean_target and float(mean_target) > 0:
                        if chosen_target is None:
                            chosen_target = float(mean_target)
                        # Always store mean as fallback reference
                        stock["target"] = f"{float(mean_target):.2f}"
                    if chosen_target:
                        stock["target"] = f"{chosen_target:.2f}"
                        
                    # Store target range for confidence assessment
                    if high_target and float(high_target) > 0:
                        stock["target_high"] = f"{float(high_target):.2f}"
                    if low_target and float(low_target) > 0:
                        stock["target_low"] = f"{float(low_target):.2f}"
                    
                    # --- ANALYST RECOMMENDATION ---
                    # recommendationKey: human readable (buy, hold, sell, strong_buy, etc.)
                    # recommendationMean: numeric 1.0 (Strong Buy) to 5.0 (Sell)
                    rating = info.get("recommendationKey")
                    if rating:
                        stock["rating"] = rating.replace("_", " ").title()
                    rec_mean = info.get("recommendationMean")
                    if rec_mean is not None:
                        stock["rec_score"] = round(float(rec_mean), 1)
                    
                    # --- GROWTH METRICS ---
                    # Revenue growth: YoY top-line growth
                    rev_growth = info.get("revenueGrowth")
                    if rev_growth is not None:
                        growth_pct = float(rev_growth) * 100
                        sign = "+" if growth_pct > 0 else ""
                        stock["revenue_growth"] = f"{sign}{growth_pct:.1f}%"
                        
                    # Earnings growth: YoY EPS/profit growth (complementary signal)
                    earn_growth = info.get("earningsGrowth")
                    if earn_growth is not None:
                        eg_pct = float(earn_growth) * 100
                        sign = "+" if eg_pct > 0 else ""
                        stock["earnings_growth"] = f"{sign}{eg_pct:.1f}%"
                
                # Recalculate potential growth based on live price and target price
                target_price = float(stock["target"])
                if live_price > 0:
                    growth_val = ((target_price - live_price) / live_price) * 100
                    sign = "+" if growth_val > 0 else ""
                    stock["growth_pct"] = f"{sign}{growth_val:.1f}%"
                    
                    # Build detailed log line
                    growth_info = f"Price = {live_price:.2f}, Target = {target_price:.2f} ({sign}{growth_val:.1f}%)"
                    rating_info = f" [Rating: {stock['rating']}]" if stock['rating'] != 'N/A' else ""
                    analyst_info = f" [Analysts: {stock['analyst_count']}]" if stock['analyst_count'] else ""
                    growth_alert = f" [Rev: {stock['revenue_growth']}]" if stock['revenue_growth'] else ""
                    earnings_alert = f" [EPS: {stock['earnings_growth']}]" if stock['earnings_growth'] else ""
                    print(f"Updated {ticker}: {growth_info}{rating_info}{analyst_info}{growth_alert}{earnings_alert}")
                    
            except Exception as e:
                print(f"Error updating price/metrics for {yahoo_ticker}: {e}. Using static price.")

def fetch_screener_fundamentals():
    """Enriches STOCK_WATCHLIST with actual filed financial data from Screener.in.
    
    This provides a 'ground truth' data layer from BSE/NSE company filings,
    complementing Yahoo Finance's analyst estimates. Data includes:
    - PE Ratio, ROCE, ROE (valuation & efficiency metrics)
    - Market Cap, Book Value
    - Latest quarterly Sales, Net Profit, EPS (actual reported numbers)
    - Promoter/FII/DII holding percentages
    
    Source: Screener.in (aggregates BSE/NSE filed data)
    """
    import time
    print("Fetching actual filed fundamentals from Screener.in (BSE/NSE filings)...")
    
    for sector, stocks in STOCK_WATCHLIST.items():
        for stock in stocks:
            ticker = stock["ticker"]
            
            # Initialize screener fields
            stock["screener"] = {}
            
            try:
                # Try consolidated first (better for companies with subsidiaries)
                url = f"https://www.screener.in/company/{ticker}/consolidated/"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                
                r = requests.get(url, headers=headers, timeout=15)
                r.encoding = 'utf-8'  # Force UTF-8 (Screener.in uses ₹ symbols)
                if r.status_code != 200:
                    # Fallback to standalone
                    url = f"https://www.screener.in/company/{ticker}/"
                    r = requests.get(url, headers=headers, timeout=15)
                    r.encoding = 'utf-8'
                    if r.status_code != 200:
                        print(f"  {ticker}: Screener.in returned HTTP {r.status_code}. Skipping.")
                        continue
                
                html = r.text
                sc = {}
                
                # --- EXTRACT TOP-LEVEL RATIOS ---
                # Pattern: <span class="name">Label</span> ... <span class="number">VALUE</span>
                def extract_ratio(label):
                    pattern = rf'{label}\s*</span>.*?<span class="number">\s*([\d,\.]+)\s*</span>'
                    match = re.search(pattern, html, re.DOTALL)
                    if match:
                        return match.group(1).replace(",", "")
                    return None
                
                sc["market_cap"] = extract_ratio("Market Cap")      # in Cr.
                sc["pe_ratio"] = extract_ratio("Stock P/E")
                sc["industry_pe"] = extract_ratio("Industry PE")
                sc["book_value"] = extract_ratio("Book Value")
                sc["roce"] = extract_ratio("ROCE")                  # %
                sc["roe"] = extract_ratio("ROE")                    # %
                sc["dividend_yield"] = extract_ratio("Dividend Yield")
                
                # --- EXTRACT QUARTERLY RESULTS (actual filed numbers) ---
                qs_match = re.search(r'id="quarters"(.*?)(?:</section>)', html, re.DOTALL)
                if qs_match:
                    qs = qs_match.group(1)
                    
                    # Get latest quarter name
                    q_headers = re.findall(r'data-date-key="[^"]*">\s*(\w+ \d{4})', qs)
                    if q_headers:
                        sc["latest_quarter"] = q_headers[-1]
                    
                    # Extract row values from quarterly table
                    def extract_row_last(label):
                        row_match = re.search(rf'{label}.*?</tr>', qs, re.DOTALL)
                        if row_match:
                            vals = re.findall(r'<td[^>]*>\s*([\d,\.\-]+)\s*</td>', row_match.group(0))
                            if vals:
                                return vals[-1].replace(",", "")
                        return None
                    
                    sc["q_sales"] = extract_row_last("Sales")
                    sc["q_net_profit"] = extract_row_last("Net Profit")
                    sc["q_opm"] = extract_row_last("OPM")
                    sc["q_eps"] = extract_row_last("EPS in Rs")
                
                # --- EXTRACT SHAREHOLDING PATTERN ---
                sh_match = re.search(r'id="shareholding"(.*?)(?:</section>|id=")', html, re.DOTALL)
                if sh_match:
                    sh = sh_match.group(1)
                    def extract_holding(label):
                        match = re.search(rf'{label}.*?<td[^>]*>\s*([\d\.]+)\s*%', sh, re.DOTALL)
                        return match.group(1) if match else None
                    sc["promoter_pct"] = extract_holding("Promoters")
                    sc["fii_pct"] = extract_holding("FIIs")
                    sc["dii_pct"] = extract_holding("DIIs")
                
                # Remove None values and store
                sc = {k: v for k, v in sc.items() if v is not None}
                stock["screener"] = sc
                
                # Build log line
                log_parts = []
                if sc.get("pe_ratio"):
                    ind_pe = f" vs Ind:{sc['industry_pe']}" if sc.get("industry_pe") else ""
                    log_parts.append(f"PE={sc['pe_ratio']}{ind_pe}")
                if sc.get("roce"):
                    log_parts.append(f"ROCE={sc['roce']}%")
                if sc.get("roe"):
                    log_parts.append(f"ROE={sc['roe']}%")
                if sc.get("q_sales"):
                    log_parts.append(f"Q.Sales=Rs.{sc['q_sales']}Cr")
                if sc.get("promoter_pct"):
                    log_parts.append(f"Promoter={sc['promoter_pct']}%")
                    
                print(f"  {ticker}: {' | '.join(log_parts)}")
                
                # Rate limit: be polite to Screener.in (free service)
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  {ticker}: Screener.in error: {str(e).encode('ascii', 'replace').decode()}. Skipping.")

def detect_emerging_players(brief_data):
    """Scans aggregated news titles for corporate names not currently in the watchlist."""
    print("Scanning headlines for emerging players...")
    import re
    emerging_players = {}
    
    # Get set of all existing watchlist names and tickers to exclude them
    existing_ids = set()
    for sector, stocks in STOCK_WATCHLIST.items():
        for s in stocks:
            existing_ids.add(s["ticker"].lower())
            existing_ids.add(s["name"].lower())
            for part in s["name"].split():
                if len(part) > 3:
                    existing_ids.add(part.lower())
                    
    # General stopwords to ignore
    ignored = {"india", "delhi", "mumbai", "pib", "union", "minister", "cabinet", "government", "ministry", "national", "state", "monsoon", "ebola", "science", "budget", "digital", "system"}

    # Pattern: Capitalized words followed by corporate identifiers
    corp_pattern = re.compile(r'\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+(?:Ltd|Limited|Corp|Corporation|Technologies|Enterprises|Solutions|Infrastructure)\b')

    for sector, news_items in brief_data.items():
        detected = []
        for item in news_items:
            title = item["title"]
            matches = corp_pattern.findall(title)
            for match in matches:
                match_lower = match.lower()
                if match_lower not in existing_ids and match_lower not in ignored and len(match) > 3:
                    if match not in detected:
                        detected.append(match)
                        print(f"Detected emerging player in {sector}: {match}")
        if detected:
            emerging_players[sector] = detected
            
    return emerging_players

def save_watchlist():
    """Saves STOCK_WATCHLIST back to watchlist.json."""
    watchlist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watchlist.json")
    try:
        with open(watchlist_path, "w", encoding="utf-8") as f:
            json.dump(STOCK_WATCHLIST, f, indent=2, ensure_ascii=False)
        print("Saved updated watchlist to watchlist.json")
    except Exception as e:
        print(f"Error saving watchlist: {e}")

def resolve_ticker_from_name(company_name):
    """Queries Yahoo Finance Search API to find the NSE/BSE ticker for a company name."""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(company_name)}&quotesCount=5"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            quotes = data.get("quotes", [])
            # Search for NSE first
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".NS"):
                    return symbol.split(".")[0], q.get("longname") or q.get("shortname") or company_name
            # Fallback to BSE
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".BO"):
                    return symbol.split(".")[0], q.get("longname") or q.get("shortname") or company_name
    except Exception as e:
        print(f"Error resolving ticker for {company_name}: {e}")
    return None, None

def auto_curate_watchlist(brief_data):
    """Discovers emerging competitors, fetches their metrics, and auto-rotates underperforming watchlist stocks."""
    print("Starting automated watchlist curation and rotation cycle...")
    try:
        import yfinance as yf
    except ImportError:
        print("[WARNING] yfinance not installed. Cannot fetch metrics for auto-curation.")
        return
        
    emerging_sectors = detect_emerging_players(brief_data)
    
    # Track which players were actually added or rotated
    rotations_log = []
    
    for sector, companies in emerging_sectors.items():
        if sector not in STOCK_WATCHLIST:
            continue
            
        for name in companies:
            print(f"Evaluating candidate company: {name} in sector: {sector}")
            ticker, full_name = resolve_ticker_from_name(name)
            if not ticker:
                print(f"Could not resolve ticker for: {name}. Skipping.")
                continue
                
            # Check if this ticker is already in our watchlist for any sector
            already_watchlisted = False
            for s_key, s_list in STOCK_WATCHLIST.items():
                if any(x["ticker"] == ticker for x in s_list):
                    already_watchlisted = True
                    break
            if already_watchlisted:
                print(f"Ticker {ticker} is already in watchlist. Skipping.")
                continue
                
            # Fetch candidate metrics from Yahoo Finance
            yahoo_ticker = f"{ticker}.NS"
            try:
                ticker_obj = yf.Ticker(yahoo_ticker)
                hist = ticker_obj.history(period="1d")
                if hist.empty:
                    print(f"No market data for {yahoo_ticker}. Skipping candidate.")
                    continue
                    
                live_price = float(hist['Close'].iloc[-1])
                info = ticker_obj.info or {}
                
                # Check target price and compute potential
                consensus_target = info.get("targetMeanPrice")
                if consensus_target and float(consensus_target) > 0:
                    target_price = float(consensus_target)
                else:
                    target_price = live_price * 1.25 # Default 25% upside estimate if analysts haven't coverage
                    
                growth_pct_val = ((target_price - live_price) / live_price) * 100
                rating = info.get("recommendationKey", "N/A").replace("_", " ").title()
                
                rev_growth_raw = info.get("revenueGrowth")
                revenue_growth = f"{float(rev_growth_raw) * 100:.1f}%" if rev_growth_raw is not None else None
                
                # Eligibility check:
                # 1. Candidate must have positive potential growth upside
                # 2. Candidate must have positive revenue growth (> 0%) or Buy rating
                is_eligible = growth_pct_val > 0
                if rev_growth_raw is not None and rev_growth_raw < 0:
                    is_eligible = False
                    
                if not is_eligible:
                    print(f"Candidate {ticker} did not meet positive growth criteria. Skipping.")
                    continue
                    
                # We have a valid, eligible high-growth candidate!
                # Now find the first news headline related to this candidate to use as a catalyst
                related_headline = f"Policy tailwinds in the {sector} segment."
                for item in brief_data.get(sector, []):
                    if name.lower() in item["title"].lower():
                        related_headline = item["title"]
                        break
                        
                candidate_stock = {
                    "ticker": ticker,
                    "name": full_name,
                    "price": f"{live_price:.2f}",
                    "target": f"{target_price:.2f}",
                    "growth_pct": f"{growth_pct_val:.1f}%",
                    "catalyst": f"Auto-discovered via media radar. Catalyst: {related_headline}",
                    "rating": rating,
                    "revenue_growth": revenue_growth
                }
                
                # Check watchlist size
                current_watchlist = STOCK_WATCHLIST[sector]
                if len(current_watchlist) < 5:
                    # Directly append since there is space
                    current_watchlist.append(candidate_stock)
                    print(f"ADDED: {ticker} to {sector} watchlist (Space available: {len(current_watchlist)}/5)")
                    rotations_log.append(f"Added {full_name} ({ticker}) to {sector}")
                else:
                    # Watchlist is full (5 items). Perform rotation logic.
                    # Find the stock with the lowest potential growth (upside pct)
                    def get_potential(stock):
                        try:
                            return float(stock["growth_pct"].replace("%", ""))
                        except Exception:
                            return 0.0
                            
                    sorted_watchlist = sorted(current_watchlist, key=get_potential)
                    weakest_stock = sorted_watchlist[0]
                    weakest_potential = get_potential(weakest_stock)
                    
                    # If candidate has higher growth potential than the weakest stock, rotate!
                    if growth_pct_val > weakest_potential:
                        # Remove weakest stock
                        STOCK_WATCHLIST[sector] = [x for x in current_watchlist if x["ticker"] != weakest_stock["ticker"]]
                        STOCK_WATCHLIST[sector].append(candidate_stock)
                        print(f"ROTATED: Replaced underperformer {weakest_stock['ticker']} (Upside: {weakest_stock['growth_pct']}) with high-growth candidate {ticker} (Upside: {candidate_stock['growth_pct']}) in {sector}!")
                        rotations_log.append(f"Rotated {weakest_stock['name']} ({weakest_stock['ticker']}) out for {full_name} ({ticker}) in {sector}")
                    else:
                        print(f"Candidate {ticker} (Upside: {growth_pct_val:.1f}%) did not outperform the weakest watchlist pick {weakest_stock['ticker']} (Upside: {weakest_potential:.1f}%). Skipping rotation.")
                        
            except Exception as e:
                print(f"Error checking financials for candidate {yahoo_ticker}: {e}")
                
    if rotations_log:
        print("\nSummary of Watchlist Rotations:")
        for log in rotations_log:
            print(f" - {log}")
        save_watchlist()
    else:
        print("No watchlist changes or rotations needed in this cycle.")

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
    # Gather news data
    data = fetch_feed_data()
    
    # Scan news headlines for emerging competitor signals
    emerging = detect_emerging_players(data)
    data["emerging_players"] = emerging
    
    # Auto-curate the watchlist using the newly scanned emerging players (adding/rotating stocks)
    auto_curate_watchlist(data)
    
    # Fetch live Yahoo Finance prices, broker targets, and growth metrics for the final curated watchlist
    update_live_stock_prices()
    
    # Enrich with actual filed fundamentals from Screener.in (PE, ROCE, ROE, quarterly results)
    fetch_screener_fundamentals()
    
    # Save the updated stock metrics (prices, targets, ratings, growth, fundamentals) back to watchlist.json
    save_watchlist()
    
    # Save the updated data for dashboard display
    save_data_for_dashboard(data)
    
    # Render final HTML email
    html = build_html_email(data)
    
    # Mail it (or write to email_preview.html locally)
    send_email(html)
    
    print("Briefing cycle finished successfully.")
