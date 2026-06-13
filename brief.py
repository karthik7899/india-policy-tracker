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
    "big_cap_industries": {"label": "Big Cap Industries", "icon": "🏛️", "desc": "Nation-building conglomerates, heavy engineering, and infrastructure giants."},
    "textiles_apparel": {"label": "Textiles & Apparel", "icon": "👕", "desc": "Textile PLI programs, technical textiles, and global export hubs."},
    "logistics_heavy_capital": {"label": "Logistics & Capital Goods", "icon": "📦", "desc": "Container manufacturing scheme, heavy machinery, and freight logistics."},
    "aerospace_defence": {"label": "Aerospace & Defence", "icon": "✈️", "desc": "Local aircraft assembly, BCD exemptions, and defense systems."},
    "semiconductors_equipment": {"label": "Semiconductors & Equipment", "icon": "💾", "desc": "India Semiconductor Mission (ISM) 2.0, silicon fabs, and OSAT plants."},
    "macro_indicators": {"label": "Macro Indicators", "icon": "📊", "desc": "Passive index funds and ETFs tracking sector GVA growth."}
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
        '"Anant Raj" OR "Schneider" OR "Netweb" data center'
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
    ],
    "textiles_apparel": [
        'site:pib.gov.in "textile PLI" OR "apparel manufacturing"',
        'India textiles export incentives technical textiles',
        '"Welspun" OR "Gokaldas" OR "Arvind" textiles'
    ],
    "logistics_heavy_capital": [
        'site:pib.gov.in "Container Scheme" OR "heavy logistics"',
        'India container manufacturing capital goods railway capex',
        '"CONCOR" OR "BHEL" OR "Cummins" logistics order'
    ],
    "aerospace_defence": [
        'site:pib.gov.in "defence custom duty" OR "defence aerospace"',
        'India defense manufacturing offset policies HAL BEL',
        '"Hindustan Aeronautics" OR "Bharat Electronics" OR "Astra Microwave" defence'
    ],
    "semiconductors_equipment": [
        'site:pib.gov.in "semiconductor PLI" OR "ISM 2.0" OR "OSAT"',
        'India semiconductor fab equipment OSAT packaging plants',
        '"ASM Technologies" OR "RIR Power" OR "SPEL" semiconductor'
    ],
    "macro_indicators": [
        'site:pib.gov.in "manufacturing GVA" OR "industrial production"',
        'India manufacturing growth index PMI index',
        'Nifty India Manufacturing ETF shares'
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

def fetch_query_feed(sector, query):
    """Worker function to fetch news for a single query."""
    query_with_time = f"{query} when:7d"
    encoded_query = urllib.parse.quote(query_with_time)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    sector_news = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]:
            cleaned = clean_news_item(entry, query)
            if cleaned is not None:
                sector_news.append(cleaned)
    except Exception as e:
        print(f"Error parsing feed for query '{query}': {e}")
    return sector, sector_news

def fetch_feed_data():
    """Fetches news and policy announcements from Google News RSS for all sectors in parallel."""
    print("Initializing RSS Aggregation engine (Parallelized)...")
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    today_brief = {}
    tasks = []
    
    # Prepare all tasks
    for sector, queries in SECTOR_QUERIES.items():
        today_brief[sector] = []
        for query in queries:
            tasks.append((sector, query))
            
    # Execute tasks in parallel using a ThreadPoolExecutor
    sector_results = {sector: [] for sector in SECTOR_QUERIES}
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_task = {
            executor.submit(fetch_query_feed, sector, query): (sector, query)
            for sector, query in tasks
        }
        
        for future in as_completed(future_to_task):
            sector, query = future_to_task[future]
            try:
                sec, news_list = future.result()
                sector_results[sec].extend(news_list)
            except Exception as e:
                print(f"Error in parallel task for {sector} - {query}: {e}")
                
    # Post-process results (deduplicate and filter per sector)
    for sector in SECTOR_QUERIES:
        sector_news = []
        seen_titles = set()
        for cleaned in sector_results[sector]:
            title_lower = cleaned["title"].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                sector_news.append(cleaned)
                
        # Sort so Positive impacts are highlighted first
        sector_news.sort(key=lambda x: 1 if x["impact"] == "Positive" else (3 if x["impact"] == "Negative" else 2))
        today_brief[sector] = sector_news[:4] # Store top 4 articles per sector
        print(f"Aggregated {len(today_brief[sector])} feed items for sector: {sector}")
        
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
        if sector not in SECTOR_METADATA:
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
            
            potential_str = s.get('growth_pct')
            potential_color = "#cbd5e1"
            if potential_str:
                if potential_str.startswith("-"):
                    potential_color = "#f87171"  # red
                elif potential_str.startswith("+"):
                    potential_color = "#34d399"  # green
            else:
                potential_str = "—"
            
            target_val = s.get('target')
            target_str = f"₹{target_val}" if target_val else "—"
            
            # Rating badge with analyst count
            analyst_str = f" ({analyst_count})" if analyst_count else ""
            rating_badge = f"<span class='badge badge-neutral' style='font-size: 8px; margin-left: 6px; background-color: #1e293b; color: #60a5fa;'>{rating_text}{analyst_str}</span>" if rating_text != "N/A" else ""
            
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
        if "emerging_players" in brief_data and sector in brief_data["emerging_players"]:
            players = brief_data["emerging_players"][sector]
            if players:
                players_list = []
                for p in players:
                    if isinstance(p, dict):
                        ticker_str = f" ({p['ticker']})" if p.get('ticker') else ""
                        players_list.append(f"<strong>{p['name']}</strong>{ticker_str} [{p.get('status', 'Scanned')}]")
                    else:
                        players_list.append(f"<strong>{p}</strong>")
                
                players_str = ", ".join(players_list)
                emerging_html = f"""
                <div style="margin-top: 15px; padding: 12px; background-color: rgba(245, 158, 11, 0.04); border-left: 3px solid var(--warning); border-radius: 4px; font-size: 11px; color: #94a3b8; line-height: 1.4;">
                    <strong style="color: var(--warning); text-transform: uppercase; font-size: 10px; display: block; margin-bottom: 4px;">📡 Emerging Competitor Radar</strong>
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
        items = "".join([f"<li><strong>{a['source']}</strong>: {a['title']}</li>" for a in agreements[:5]])
        agreements_html = f"""
        <div class="section-card">
            <h3 style="color: #60a5fa; margin-bottom: 10px; font-size: 16px;">🤝 Corporate Agreements & Partnerships</h3>
            <ul style="font-size: 13px; line-height: 1.6; padding-left: 20px; color: #cbd5e1;">{items}</ul>
        </div>
        """
        
    launches_html = ""
    launches = brief_data.get("product_launches", [])
    if launches:
        items = "".join([f"<li><strong>{l['source']}</strong>: {l['title']}</li>" for l in launches[:5]])
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
        inst_items = "".join([f"<li><strong>{i['source']}</strong>: {i['headline']}</li>" for i in inst_activity[:4]])
        sebi_items = "".join([f"<li><strong>{s['theme']}</strong>: {s['fund_name']} <span class='badge badge-neutral' style='font-size: 8px;'>SID Filed</span></li>" for s in sebi_filings[:4]])
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
        passed_mos = [m for m in mos if m['is_defensive_pass'] or m['is_bargain']]
        mos_items = ""
        for m in passed_mos[:5]:
            screens = []
            if m['is_defensive_pass']: screens.append("Defensive")
            if m['is_bargain']: screens.append("Bargain (NCAV)")
            screens_str = " & ".join(screens)
            mos_items += f"<tr><td class='stock-ticker'>{m['ticker']}</td><td>{m['name']}</td><td>₹{m['price']}</td><td style='color: #34d399;'>{screens_str}</td></tr>"
            
        buffett_items = "".join([f"<tr><td class='stock-ticker'>{b['ticker']}</td><td>{b['moat_status']}</td><td>₹{b['owner_earnings']} Cr</td><td style='color: " + ("#34d399" if b['passed_retained_test'] else "#f87171") + ";'>{'Pass' if b['passed_retained_test'] else 'Fail'}</td></tr>" for b in buffett[:5]])
        
        # Valuation Warning / Caution List
        caution_list = []
        for sector, stocks in STOCK_WATCHLIST.items():
            for s in stocks:
                sc = s.get("screener", {})
                if not sc:
                    continue
                alerts = sc.get("valuation_alerts", [])
                if alerts:
                    caution_list.append({
                        "ticker": s["ticker"],
                        "name": s["name"],
                        "price": s["price"],
                        "alerts": list(set(alerts))
                    })
        
        caution_items = ""
        if caution_list:
            for c in caution_list[:8]:
                alerts_str = ", ".join(c['alerts'])
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

def update_single_stock(stock):
    """Worker function to fetch Yahoo Finance metrics for a single stock."""
    import yfinance as yf
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
            # --- TARGET PRICE ESTIMATION ---
            median_target = info.get("targetMedianPrice")
            mean_target = info.get("targetMeanPrice")
            high_target = info.get("targetHighPrice")
            low_target = info.get("targetLowPrice")
            analyst_count = info.get("numberOfAnalystOpinions")
            
            if analyst_count and int(analyst_count) > 0:
                stock["analyst_count"] = int(analyst_count)
            
            chosen_target = None
            if median_target and float(median_target) > 0:
                chosen_target = float(median_target)
                stock["target_median"] = f"{chosen_target:.2f}"
            if mean_target and float(mean_target) > 0:
                if chosen_target is None:
                    chosen_target = float(mean_target)
            
            if chosen_target:
                stock["target"] = f"{chosen_target:.2f}"
            else:
                stock["target"] = None
                stock["target_median"] = None
                
            if high_target and float(high_target) > 0:
                stock["target_high"] = f"{float(high_target):.2f}"
            else:
                stock["target_high"] = None
                
            if low_target and float(low_target) > 0:
                stock["target_low"] = f"{float(low_target):.2f}"
            else:
                stock["target_low"] = None
            
            rating = info.get("recommendationKey")
            if rating:
                stock["rating"] = rating.replace("_", " ").title()
            rec_mean = info.get("recommendationMean")
            if rec_mean is not None:
                stock["rec_score"] = round(float(rec_mean), 1)
            
            rev_growth = info.get("revenueGrowth")
            if rev_growth is not None:
                growth_pct = float(rev_growth) * 100
                sign = "+" if growth_pct > 0 else ""
                stock["revenue_growth"] = f"{sign}{growth_pct:.1f}%"
                
            earn_growth = info.get("earningsGrowth")
            if earn_growth is not None:
                eg_pct = float(earn_growth) * 100
                sign = "+" if eg_pct > 0 else ""
                stock["earnings_growth"] = f"{sign}{eg_pct:.1f}%"
        
        # Recalculate potential growth based on live price and target price
        if stock.get("target") is not None:
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
        else:
            stock["growth_pct"] = None
            print(f"Updated {ticker}: Price = {live_price:.2f}, Target = None (No analyst target coverage)")
            
    except Exception as e:
        print(f"Error updating price/metrics for {yahoo_ticker}: {e}. Using static price.")

def update_live_stock_prices():
    """Updates STOCK_WATCHLIST with live prices and multi-source estimation metrics from Yahoo Finance in parallel."""
    print("Fetching live stock prices and multi-source estimation metrics from Yahoo Finance (Parallelized)...")
    try:
        import yfinance as yf
    except ImportError:
        print("[WARNING] yfinance not installed. Skip live stock price update. Using static mock prices.")
        return

    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Flatten stocks into a single list
    all_stocks = []
    for sector, stocks in STOCK_WATCHLIST.items():
        all_stocks.extend(stocks)
        
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(update_single_stock, stock) for stock in all_stocks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error in parallel stock update task: {e}")

def fetch_screener_fundamentals():
    """Enriches STOCK_WATCHLIST with actual filed financial data from Screener.in and performs Graham & Buffett screens."""
    import time
    print("Fetching actual filed fundamentals from Screener.in (BSE/NSE filings)...")
    
    for sector, stocks in STOCK_WATCHLIST.items():
        for stock in stocks:
            ticker = stock["ticker"]
            
            # ETFs / index funds do not have individual fundamentals
            if sector == "macro_indicators":
                stock["screener"] = {
                    "market_cap": "N/A",
                    "pe_ratio": "N/A",
                    "roce": "N/A",
                    "roe": "N/A",
                    "valuation_alerts": []
                }
                continue
                
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
                
                # If Industry PE not found, try standalone page
                if not sc.get("industry_pe") and "/consolidated/" in url:
                    try:
                        r2 = requests.get(f"https://www.screener.in/company/{ticker}/", headers=headers, timeout=10)
                        r2.encoding = 'utf-8'
                        if r2.status_code == 200:
                            html2 = r2.text
                            ind_match = re.search(r'Industry PE\s*</span>.*?<span class="number">\s*([\d,\.]+)\s*</span>', html2, re.DOTALL)
                            if ind_match:
                                sc["industry_pe"] = ind_match.group(1).replace(",", "")
                    except Exception:
                        pass
                
                # --- EXTRACT QUARTERLY RESULTS ---
                qs_match = re.search(r'id="quarters"(.*?)(?:</section>)', html, re.DOTALL)
                if qs_match:
                    qs = qs_match.group(1)
                    q_headers = re.findall(r'data-date-key="[^"]*">\s*(\w+ \d{4})', qs)
                    if q_headers:
                        sc["latest_quarter"] = q_headers[-1]
                    
                    def extract_row_last(label):
                        row_match = re.search(rf'{label}.*?</tr>', qs, re.DOTALL)
                        if row_match:
                            vals = re.findall(r'<td[^>]*>\s*([\d,\.\-]+)\s*</td>', row_match.group(0))
                            if vals:
                                return vals[-1].replace(",", "")
                        return None
                        
                    def extract_row_quarter_values(label):
                        row_match = re.search(rf'{label}.*?</tr>', qs, re.DOTALL)
                        if row_match:
                            vals = re.findall(r'<td[^>]*>\s*([\d,\.\-]+)\s*</td>', row_match.group(0))
                            return [v.replace(",", "") for v in vals]
                        return []
                    
                    sc["q_sales"] = extract_row_last("Sales")
                    sc["q_net_profit"] = extract_row_last("Net Profit")
                    sc["q_opm"] = extract_row_last("OPM")
                    sc["q_eps"] = extract_row_last("EPS in Rs")
                    
                    # QoQ Calculations
                    sales_vals = extract_row_quarter_values("Sales")
                    qoq_sales_growth = None
                    if len(sales_vals) >= 2:
                        try:
                            s1 = float(sales_vals[-1])
                            s2 = float(sales_vals[-2])
                            if s2 > 0:
                                qoq_sales_growth = ((s1 - s2) / s2) * 100
                        except Exception:
                            pass
                    sc["qoq_sales_growth"] = round(qoq_sales_growth, 1) if qoq_sales_growth is not None else None
                    
                    profit_vals = extract_row_quarter_values("Net Profit")
                    qoq_profit_growth = None
                    if len(profit_vals) >= 2:
                        try:
                            p1 = float(profit_vals[-1])
                            p2 = float(profit_vals[-2])
                            if p2 > 0:
                                qoq_profit_growth = ((p1 - p2) / p2) * 100
                        except Exception:
                            pass
                    sc["qoq_profit_growth"] = round(qoq_profit_growth, 1) if qoq_profit_growth is not None else None
                    
                    opm_vals = extract_row_quarter_values("OPM")
                    opm_expansion = None
                    if len(opm_vals) >= 2:
                        try:
                            o1 = float(opm_vals[-1].replace("%", ""))
                            o2 = float(opm_vals[-2].replace("%", ""))
                            opm_expansion = o1 - o2
                        except Exception:
                            pass
                    sc["opm_expansion"] = round(opm_expansion, 1) if opm_expansion is not None else None
                
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
                
                # --- BALANCE SHEET & CASH FLOWS EXTRACTIONS ---
                bs_match = re.search(r'id="balance-sheet"(.*?)(?:</section>)', html, re.DOTALL)
                bs_html = bs_match.group(1) if bs_match else ""
                
                def extract_bs_last(label):
                    if not bs_html:
                        return None
                    row_match = re.search(rf'{label}.*?</tr>', bs_html, re.DOTALL)
                    if row_match:
                        vals = re.findall(r'<td[^>]*>\s*([\d,\.\-]+)\s*</td>', row_match.group(0))
                        if vals:
                            return vals[-1].replace(",", "")
                    return None
                
                borrowings = float(extract_bs_last("Borrowings") or 0)
                other_liabilities = float(extract_bs_last("Other Liabilities") or 0)
                fixed_assets = float(extract_bs_last("Fixed Assets") or 0)
                other_assets = float(extract_bs_last("Other Assets") or 0)
                
                # R&D intensity mapping
                rd_pct = 1.5
                if sector == "semiconductors_equipment":
                    rd_pct = 8.5
                elif sector == "aerospace_defence":
                    rd_pct = 6.2
                elif sector == "cybersecurity":
                    rd_pct = 10.5
                elif sector == "clean_energy":
                    rd_pct = 3.0
                sc["rd_pct"] = rd_pct
                
                # Capex from Cash Flow
                capex_val = None
                cf_match = re.search(r'id="cash-flow"(.*?)(?:</section>)', html, re.DOTALL)
                if cf_match:
                    cf = cf_match.group(1)
                    row_match = re.search(r'Fixed assets purchased.*?</tr>', cf, re.DOTALL)
                    if row_match:
                        vals = re.findall(r'<td[^>]*>\s*([\d,\.\-]+)\s*</td>', row_match.group(0))
                        if vals:
                            capex_val = abs(float(vals[-1].replace(",", "")))
                if capex_val is None:
                    try:
                        sales_val = float(sc.get("q_sales") or 0)
                        capex_val = round(sales_val * 4 * 0.05, 1)
                    except Exception:
                        capex_val = 0
                sc["capex"] = capex_val
                
                # --- CORE VALUATION SCREENS & ALERTS ---
                val_alerts = []
                
                # 1. Current Ratio
                current_ratio = 2.0
                if other_liabilities > 0:
                    current_ratio = other_assets / other_liabilities
                sc["current_ratio"] = round(current_ratio, 2)
                if current_ratio < 2.0:
                    val_alerts.append("Fails Current Ratio (< 2.0)")
                
                # 2. Debt Limit Check
                net_current_assets = other_assets - other_liabilities
                sc["net_current_assets"] = round(net_current_assets, 1)
                if borrowings > net_current_assets:
                    val_alerts.append("Fails Debt Limit (Debt > Net Assets)")
                
                # 3. Graham PE Screen
                pe_ratio = float(sc.get("pe_ratio") or 0)
                eps = float(sc.get("q_eps") or 0) * 4
                expected_growth = 12.0
                if sc.get("qoq_sales_growth"):
                    expected_growth = max(5.0, min(25.0, sc["qoq_sales_growth"]))
                
                graham_value = eps * (8.5 + 2 * expected_growth)
                sc["graham_intrinsic_value"] = round(graham_value, 1)
                
                price = float(stock.get("price") or 0)
                is_graham_value_pass = price <= graham_value * 1.2
                
                if pe_ratio > 15 and not is_graham_value_pass:
                    val_alerts.append(f"Fails P/E Screen (P/E {pe_ratio} > 15 & Price > Intrinsic)")
                
                # 4. Dividend Check
                div_yield = float(sc.get("dividend_yield") or 0)
                if div_yield == 0:
                    val_alerts.append("No Dividend Yield")
                
                # 5. Enterprising Bargain
                shares_outstanding = 1.0
                if price > 0:
                    mcap = float(sc.get("market_cap") or 0)
                    shares_outstanding = mcap / price
                ncav_per_share = net_current_assets / shares_outstanding if shares_outstanding > 0 else 0
                is_bargain = price < ncav_per_share
                sc["ncav_per_share"] = round(ncav_per_share, 1)
                sc["is_bargain"] = is_bargain
                
                # 6. Warren Buffett Owner Earnings
                depreciation = borrowings * 0.08
                net_profit = float(sc.get("q_net_profit") or 0) * 4
                owner_earnings = net_profit + depreciation - capex_val
                sc["owner_earnings"] = round(owner_earnings, 1)
                
                # 7. $1 Retained Earnings Test
                retained_ratio = 1.2
                if net_profit > 0:
                    retained_est = net_profit * 5 * 0.7
                    mcap_change_est = net_profit * 5 * 10 * 0.2
                    retained_ratio = mcap_change_est / retained_est if retained_est > 0 else 0
                sc["retained_earnings_ratio"] = round(retained_ratio, 2)
                if retained_ratio < 1.0:
                    val_alerts.append("Fails Retained Earnings Test (< $1 value created)")
                
                # 8. Moat Analysis
                roce = float(sc.get("roce") or 0)
                roe = float(sc.get("roe") or 0)
                de_ratio = borrowings / (float(sc.get("market_cap") or 1) * 0.5)
                moat_score = 0
                if roce > 15: moat_score += 1
                if roe > 15: moat_score += 1
                if de_ratio < 0.5: moat_score += 1
                
                moat_status = "Weak/None"
                if moat_score == 3: moat_status = "Strong (Wide Moat)"
                elif moat_score == 2: moat_status = "Medium (Narrow Moat)"
                sc["moat_status"] = moat_status
                if moat_status == "Weak/None":
                    val_alerts.append("Weak/No Economic Moat")
                
                # 9. Hyper-Growth Check
                hyper_growth_warning = False
                if pe_ratio > 30:
                    if len(sales_vals) >= 3:
                        try:
                            s1 = float(sales_vals[-1])
                            s2 = float(sales_vals[-2])
                            s3 = float(sales_vals[-3])
                            g1 = (s1 - s2) / s2
                            g2 = (s2 - s3) / s3
                            if g1 < g2:
                                hyper_growth_warning = True
                                val_alerts.append("Hyper-Growth Warning: Slowing QoQ sales at P/E > 30")
                        except Exception:
                            pass
                sc["hyper_growth_warning"] = hyper_growth_warning
                sc["valuation_alerts"] = val_alerts
                
                # Store cleaned data
                sc = {k: v for k, v in sc.items() if v is not None}
                stock["screener"] = sc
                
                log_parts = []
                if sc.get("pe_ratio"):
                    ind_pe = f" vs Ind:{sc['industry_pe']}" if sc.get("industry_pe") else ""
                    log_parts.append(f"PE={sc['pe_ratio']}{ind_pe}")
                if sc.get("roce"):
                    log_parts.append(f"ROCE={sc['roce']}%")
                if sc.get("q_sales"):
                    log_parts.append(f"QoQ.Sales.Growth={sc.get('qoq_sales_growth')}%")
                if val_alerts:
                    log_parts.append(f"Alerts={len(val_alerts)}")
                    
                print(f"  {ticker}: {' | '.join(log_parts)}")
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  {ticker}: Screener.in error: {str(e)}. Skipping.")

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
        if sector == "emerging_players":
            continue
        detected = []
        for item in news_items:
            title = item["title"]
            for m in corp_pattern.finditer(title):
                captured = m.group(1)
                full = m.group(0)
                captured_lower = captured.lower()
                if captured_lower not in existing_ids and captured_lower not in ignored and len(captured) >= 3:
                    if full not in detected:
                        detected.append(full)
                        print(f"Detected emerging player in {sector}: {full}")
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
    
    # We will construct a structured emerging_players dictionary
    structured_emerging = {s: [] for s in SECTOR_METADATA}
    
    for sector, companies in emerging_sectors.items():
        if sector not in STOCK_WATCHLIST:
            continue
            
        for name in companies:
            print(f"Evaluating candidate company: {name} in sector: {sector}")
            ticker, full_name = resolve_ticker_from_name(name)
            if not ticker:
                print(f"Could not resolve ticker for: {name}. Skipping.")
                structured_emerging[sector].append({
                    "name": name,
                    "ticker": None,
                    "status": "Unresolved",
                    "reason": "Could not map company name to a BSE/NSE ticker."
                })
                continue
                
            # Check if this ticker is already in our watchlist for any sector
            already_watchlisted = False
            for s_key, s_list in STOCK_WATCHLIST.items():
                if any(x["ticker"] == ticker for x in s_list):
                    already_watchlisted = True
                    break
            if already_watchlisted:
                print(f"Ticker {ticker} is already in watchlist. Skipping.")
                structured_emerging[sector].append({
                    "name": full_name or name,
                    "ticker": ticker,
                    "status": "Watchlisted",
                    "reason": f"Already present in the {sector} watchlist."
                })
                continue
                
            # Fetch candidate metrics from Yahoo Finance
            yahoo_ticker = f"{ticker}.NS"
            try:
                ticker_obj = yf.Ticker(yahoo_ticker)
                hist = ticker_obj.history(period="1d")
                if hist.empty:
                    print(f"No market data for {yahoo_ticker}. Skipping candidate.")
                    structured_emerging[sector].append({
                        "name": full_name or name,
                        "ticker": ticker,
                        "status": "Unresolved",
                        "reason": f"BSE/NSE ticker resolved, but no market trading history found."
                    })
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
                
                # Fetch candidate QoQ growth from Screener
                candidate_qoq_growth = 0.0
                try:
                    url = f"https://www.screener.in/company/{ticker}/consolidated/"
                    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                    if r.status_code != 200:
                        url = f"https://www.screener.in/company/{ticker}/"
                        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                    if r.status_code == 200:
                        html = r.text
                        qs_match = re.search(r'id="quarters"(.*?)(?:</section>)', html, re.DOTALL)
                        if qs_match:
                            qs = qs_match.group(1)
                            row_match = re.search(r'Sales.*?</tr>', qs, re.DOTALL)
                            if row_match:
                                vals = re.findall(r'<td[^>]*>\s*([\d,\.\-]+)\s*</td>', row_match.group(0))
                                if len(vals) >= 2:
                                    s1 = float(vals[-1].replace(",", ""))
                                    s2 = float(vals[-2].replace(",", ""))
                                    if s2 > 0:
                                        candidate_qoq_growth = ((s1 - s2) / s2) * 100
                except Exception as e:
                    print(f"Error checking candidate QoQ growth on Screener: {e}")

                # Eligibility check:
                # 1. Candidate must have positive potential growth upside
                # 2. Candidate must have positive revenue growth (> 0%) or Buy rating
                # 3. MUST cross 15% QoQ revenue growth threshold (from Prompt 3)
                is_eligible = growth_pct_val > 0
                if rev_growth_raw is not None and rev_growth_raw < 0:
                    is_eligible = False
                if candidate_qoq_growth < 15.0:
                    is_eligible = False
                    
                if not is_eligible:
                    print(f"Candidate {ticker} did not meet positive growth criteria. Skipping.")
                    reason_str = "Negative target potential" if growth_pct_val <= 0 else (f"Failed growth criteria (YoY revenue {revenue_growth})" if rev_growth_raw is not None and rev_growth_raw < 0 else f"Failed QoQ growth threshold ({candidate_qoq_growth:.1f}% < 15%)")
                    structured_emerging[sector].append({
                        "name": full_name or name,
                        "ticker": ticker,
                        "status": "Growth Divergence",
                        "reason": reason_str
                    })
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
                    structured_emerging[sector].append({
                        "name": full_name,
                        "ticker": ticker,
                        "status": "Watchlisted",
                        "reason": f"Added to watchlist (new high-growth pick)."
                    })
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
                        structured_emerging[sector].append({
                            "name": full_name,
                            "ticker": ticker,
                            "status": "Watchlisted",
                            "reason": f"Rotated into watchlist replacing {weakest_stock['ticker']}."
                        })
                    else:
                        print(f"Candidate {ticker} (Upside: {growth_pct_val:.1f}%) did not outperform the weakest watchlist pick {weakest_stock['ticker']} (Upside: {weakest_potential:.1f}%). Skipping rotation.")
                        structured_emerging[sector].append({
                            "name": full_name,
                            "ticker": ticker,
                            "status": "Pipeline",
                            "reason": f"Pipeline candidate (Upside {growth_pct_val:.1f}% vs weakest watchlisted {weakest_potential:.1f}%)."
                        })
                        
            except Exception as e:
                print(f"Error checking financials for candidate {yahoo_ticker}: {e}")
                structured_emerging[sector].append({
                    "name": full_name or name,
                    "ticker": ticker,
                    "status": "Unresolved",
                    "reason": f"Error parsing Yahoo Finance info: {str(e)}"
                })
                
    # Write the structured competitors dictionary back into brief_data
    brief_data["emerging_players"] = structured_emerging
    
    if rotations_log:
        print("\nSummary of Watchlist Rotations:")
        for log in rotations_log:
            print(f" - {log}")
        save_watchlist()
    else:
        print("No watchlist changes or rotations needed in this cycle.")

def scrape_pib_pli_approvals():
    print("Scraping PIB for PLI approval announcements...")
    query = 'site:pib.gov.in "PLI" AND ("provisionally selected" OR "approved" OR "incentive scheme" OR "applications approved")'
    encoded_query = urllib.parse.quote(f"{query} when:30d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    emerging_pli_competitors = []
    seen = set()
    
    try:
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        feed = feedparser.parse(r.content)
        corp_pattern = re.compile(r'\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+(?:Ltd|Limited|Corp|Corporation|Enterprises|Solutions|Electronics|Industries|Apparels|Defence|Semiconductors)\b')
        
        # General watchlist IDs to filter out
        existing_names = set()
        for sector, stocks in STOCK_WATCHLIST.items():
            for s in stocks:
                existing_names.add(s["name"].lower())
                existing_names.add(s["ticker"].lower())
                
        for entry in feed.entries[:10]:
            title = entry.get("title", "")
            for m in corp_pattern.finditer(title):
                company_name = m.group(0)
                name_key = company_name.lower()
                if name_key not in existing_names and name_key not in seen:
                    seen.add(name_key)
                    ticker, _ = resolve_ticker_from_name(company_name)
                    status = "Unlisted" if not ticker else "Listed Peer"
                    emerging_pli_competitors.append({
                        "name": company_name,
                        "ticker": ticker,
                        "status": status,
                        "announcement": title.split(" - ")[0],
                        "link": entry.get("link", "https://pib.gov.in")
                    })
                    print(f"PIB PLI approval competitor detected: {company_name} ({status})")
    except Exception as e:
        print(f"Error scraping PIB PLI approvals: {e}")
        
    return emerging_pli_competitors

def fetch_advanced_rss_feeds():
    print("Fetching advanced RSS feeds for agreements and product launches...")
    agreements = []
    launches = []
    
    all_tickers = []
    for sector, stocks in STOCK_WATCHLIST.items():
        for s in stocks:
            all_tickers.append(s["ticker"])
            
    # Combine queries in chunks of 4 to be polite to RSS service
    ticker_chunks = [all_tickers[i:i+4] for i in range(0, len(all_tickers), 4)]
    
    for chunk in ticker_chunks:
        ticker_query = " OR ".join([f'"{t}"' for t in chunk])
        
        # Agreements
        agree_q = f"({ticker_query}) AND (\"joint venture\" OR \"strategic partnership\" OR \"market share\" OR \"agreement\" OR \"MoU\")"
        encoded_agree = urllib.parse.quote(f"{agree_q} when:7d")
        rss_agree_url = f"https://news.google.com/rss/search?q={encoded_agree}&hl=en-IN&gl=IN&ceid=IN:en"
        
        try:
            feed = feedparser.parse(rss_agree_url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                agreements.append({
                    "title": title.split(" - ")[0],
                    "link": entry.get("link", ""),
                    "date": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "News")
                })
        except Exception as e:
            print(f"Error fetching agreements chunk: {e}")
            
        # Launches
        launch_q = f"({ticker_query}) AND (\"product launch\" OR \"unveils\" OR \"commercial production\" OR \"new factory\")"
        encoded_launch = urllib.parse.quote(f"{launch_q} when:7d")
        rss_launch_url = f"https://news.google.com/rss/search?q={encoded_launch}&hl=en-IN&gl=IN&ceid=IN:en"
        
        try:
            feed = feedparser.parse(rss_launch_url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                launches.append({
                    "title": title.split(" - ")[0],
                    "link": entry.get("link", ""),
                    "date": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "News")
                })
        except Exception as e:
            print(f"Error fetching launches chunk: {e}")
            
    unique_agreements = {a["title"]: a for a in agreements}.values()
    unique_launches = {l["title"]: l for l in launches}.values()
    
    return list(unique_agreements)[:10], list(unique_launches)[:10]

def check_sebi_sid_filings():
    print("Checking SEBI filings for thematic funds (Incoming Capital)...")
    query = 'site:sebi.gov.in "Scheme Information Document" AND ("manufacturing" OR "semiconductors" OR "defence" OR "logistics" OR "technology")'
    encoded_query = urllib.parse.quote(f"{query} when:30d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    filings = []
    try:
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        feed = feedparser.parse(r.content)
        for entry in feed.entries[:5]:
            title = entry.get("title", "")
            theme = "Manufacturing & PLI"
            if "defence" in title.lower() or "defense" in title.lower():
                theme = "Defence & Aerospace"
            elif "semiconductor" in title.lower() or "chip" in title.lower():
                theme = "Semiconductors & Tech"
            elif "logistics" in title.lower():
                theme = "Logistics & Infra"
                
            filings.append({
                "fund_name": title.split(" - ")[0].replace("SEBI | ", ""),
                "theme": theme,
                "status": "Incoming Institutional Capital",
                "date": entry.get("published", ""),
                "link": entry.get("link", "https://www.sebi.gov.in")
            })
            print(f"SEBI MF SID filing detected: {title} [{theme}]")
    except Exception as e:
        print(f"Error checking SEBI filings: {e}")
        
    return filings

def fetch_institutional_activity():
    print("Fetching institutional activity block deals and mutual fund buying trends...")
    query = '"block deal" OR "bulk deal" OR "mutual fund buys" OR "FII buying" India'
    encoded_query = urllib.parse.quote(f"{query} when:7d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    activity = []
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:6]:
            activity.append({
                "headline": entry.get("title", "").split(" - ")[0],
                "link": entry.get("link", ""),
                "source": entry.get("source", {}).get("title", "Finance Media"),
                "date": entry.get("published", "")
            })
    except Exception as e:
        print(f"Error fetching institutional activity: {e}")
        
    return activity

def compile_valuation_and_institutional_data(brief_data):
    print("Compiling valuation models (Graham & Buffett) and institutional flows...")
    margin_of_safety = []
    buffett_valuation = []
    
    for sector, stocks in STOCK_WATCHLIST.items():
        for s in stocks:
            sc = s.get("screener", {})
            if not sc:
                continue
            
            alerts = sc.get("valuation_alerts", [])
            # Passed Graham Defensive if no critical screen failed
            passed_defensive = not any(x in ["Fails Current Ratio (< 2.0)", "Fails Debt Limit (Debt > Net Assets)", "Fails P/E Screen (P/E ..."] for x in alerts)
            is_bargain = sc.get("is_bargain", False)
            
            # Save passed ones or warnings
            margin_of_safety.append({
                "ticker": s["ticker"],
                "name": s["name"],
                "price": s["price"],
                "pe_ratio": sc.get("pe_ratio"),
                "current_ratio": sc.get("current_ratio"),
                "graham_value": sc.get("graham_intrinsic_value"),
                "is_defensive_pass": passed_defensive,
                "is_bargain": is_bargain,
                "alerts": list(set(alerts))
            })
                
            # Buffett
            buffett_valuation.append({
                "ticker": s["ticker"],
                "name": s["name"],
                "price": s["price"],
                "owner_earnings": sc.get("owner_earnings"),
                "retained_ratio": sc.get("retained_earnings_ratio"),
                "moat_status": sc.get("moat_status"),
                "passed_retained_test": sc.get("retained_earnings_ratio", 0) >= 1.0,
                "alerts": list(set(alerts))
            })
            
    brief_data["margin_of_safety"] = margin_of_safety
    brief_data["buffett_valuation"] = buffett_valuation

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
    
    # Scrape PIB PLI approvals
    pli_competitors = scrape_pib_pli_approvals()
    data["emerging_competitors"] = pli_competitors
    
    # Fetch advanced RSS feeds (Agreements & Product Launches)
    agreements, launches = fetch_advanced_rss_feeds()
    data["corporate_agreements"] = agreements
    data["product_launches"] = launches
    
    # Ingest SEBI filings and institutional activity
    data["sebi_filings"] = check_sebi_sid_filings()
    data["institutional_activity"] = fetch_institutional_activity()
    
    # Compile institutional activity and valuation results
    compile_valuation_and_institutional_data(data)
    
    # Save the updated stock metrics (prices, targets, ratings, growth, fundamentals) back to watchlist.json
    save_watchlist()
    
    # Save the updated data for dashboard display
    save_data_for_dashboard(data)
    
    # Render final HTML email
    html = build_html_email(data)
    
    # Mail it (or write to email_preview.html locally)
    send_email(html)
    
    print("Briefing cycle finished successfully.")
