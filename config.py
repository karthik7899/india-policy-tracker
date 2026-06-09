# config.py
import os
import json

# Curated Stock Watchlist Database (Default fallback)
STOCK_WATCHLIST = {
    "clean_energy": [
        {
            "ticker": "TATAPOWER",
            "name": "Tata Power",
            "price": "432.50",
            "target": "520.00",
            "growth_pct": "20.2%",
            "catalyst": "Massive scaling in solar generation, microgrids, and leading India's EV charging network grid.",
        },
        {
            "ticker": "SUZLON",
            "name": "Suzlon Energy",
            "price": "50.15",
            "target": "68.00",
            "growth_pct": "35.6%",
            "catalyst": "Turnaround story, completely debt-free, dominating wind turbine supply with a record order book.",
        },
        {
            "ticker": "ADANIGREEN",
            "name": "Adani Green Energy",
            "price": "1845.00",
            "target": "2200.00",
            "growth_pct": "19.2%",
            "catalyst": "Developing the world's largest renewable energy park in Khavda, Gujarat (30 GW capacity target).",
        },
    ],
    "data_center_support": [
        {
            "ticker": "SCHNEIDER",
            "name": "Schneider Electric Infra",
            "price": "855.00",
            "target": "1120.00",
            "growth_pct": "31.0%",
            "catalyst": "Critical supplier of electrical distribution, smart grids, and high-efficiency cooling for data centers.",
        },
        {
            "ticker": "STLTECH",
            "name": "Sterlite Technologies (STL)",
            "price": "142.10",
            "target": "195.00",
            "growth_pct": "37.2%",
            "catalyst": "Expanding optical fiber and cable capacities to meet hyper-scale data center interconnect demands.",
        },
        {
            "ticker": "ANANTRAJ",
            "name": "Anant Raj Ltd",
            "price": "352.40",
            "target": "480.00",
            "growth_pct": "36.2%",
            "catalyst": "Real-estate developer transitioning commercial properties into major data center hubs in NCR.",
        },
    ],
    "cybersecurity": [
        {
            "ticker": "TCS",
            "name": "Tata Consultancy Services",
            "price": "4015.00",
            "target": "4800.00",
            "growth_pct": "19.6%",
            "catalyst": "Expanding sovereign cloud and secure cyber command centers globally for enterprise clients.",
        },
        {
            "ticker": "QUICKHEAL",
            "name": "Quick Heal Technologies",
            "price": "552.00",
            "target": "720.00",
            "growth_pct": "30.4%",
            "catalyst": "Surging enterprise adoption of their 'Seqrite' cybersecurity platform and government IT contracts.",
        },
    ],
    "surveillance_security": [
        {
            "ticker": "CPPLUS",
            "name": "Aditya Infotech (CP PLUS)",
            "price": "712.50",
            "target": "920.00",
            "growth_pct": "29.1%",
            "catalyst": "CCTV market leader (35%+ share) newly listed, scaling domestic camera manufacturing under PLI.",
        },
        {
            "ticker": "DIXON",
            "name": "Dixon Technologies",
            "price": "11240.00",
            "target": "14200.00",
            "growth_pct": "26.3%",
            "catalyst": "Primary EMS contract manufacturer producing CCTVs and DVRs for CP Plus and others under PLI.",
        },
        {
            "ticker": "ADSL",
            "name": "Allied Digital Services",
            "price": "182.30",
            "target": "240.00",
            "growth_pct": "31.7%",
            "catalyst": "System integrator winning smart/safe city surveillance projects, managing master command centers.",
        },
        {
            "ticker": "IDEAFORGE",
            "name": "IdeaForge Technology",
            "price": "702.15",
            "target": "950.00",
            "growth_pct": "35.3%",
            "catalyst": "Pioneer in tactical and mapping drone systems, primary supplier for Indian Army and police borders.",
        },
    ],
    "manufacturing_electronics": [
        {
            "ticker": "DIXON",
            "name": "Dixon Technologies",
            "price": "11240.00",
            "target": "14200.00",
            "growth_pct": "26.3%",
            "catalyst": "Leader in electronic assembly (mobile, laptop, LED TV), heavily subsidized under manufacturing PLI.",
        },
        {
            "ticker": "KAYNES",
            "name": "Kaynes Technology",
            "price": "3425.00",
            "target": "4400.00",
            "growth_pct": "28.5%",
            "catalyst": "High-end electronics and PCBA manufacturing, setting up a state-of-the-art semiconductor OSAT plant.",
        },
        {
            "ticker": "CGPOWER",
            "name": "CG Power & Industrial",
            "price": "658.00",
            "target": "820.00",
            "growth_pct": "24.6%",
            "catalyst": "Partnering on a $1B semiconductor fab, strong order pipeline in railways and power grid equipment.",
        },
    ],
    "fmcg": [
        {
            "ticker": "VBL",
            "name": "Varun Beverages (PepsiCo)",
            "price": "1510.00",
            "target": "1900.00",
            "growth_pct": "25.8%",
            "catalyst": "PepsiCo's dominant bottler, expanding into newer territories and scaling dairy/juice products.",
        },
        {
            "ticker": "TATACONSUM",
            "name": "Tata Consumer Products",
            "price": "1122.00",
            "target": "1350.00",
            "growth_pct": "20.3%",
            "catalyst": "Premiumization strategy in foods & beverages, high-growth acquisitions (Capital Foods, Organic India).",
        },
        {
            "ticker": "ITC",
            "name": "ITC Ltd",
            "price": "431.10",
            "target": "510.00",
            "growth_pct": "18.3%",
            "catalyst": "Resilient cigarette margins funding rapid expansion of high-margin FMCG brands, direct rural boost play.",
        },
    ],
    "sports_athleisure": [
        {
            "ticker": "METROBRAND",
            "name": "Metro Brands Ltd",
            "price": "1152.00",
            "target": "1480.00",
            "growth_pct": "28.5%",
            "catalyst": "Exclusive retail rights for Fila and Foot Locker in India, expanding athleisure footprint rapidly.",
        },
        {
            "ticker": "CAMPUS",
            "name": "Campus Activewear",
            "price": "262.50",
            "target": "340.00",
            "growth_pct": "29.5%",
            "catalyst": "Dominant direct-to-consumer sports footwear brand in tier-2/3 cities, major beneficiary of fitness trends.",
        },
        {
            "ticker": "PAGEIND",
            "name": "Page Industries",
            "price": "36450.00",
            "target": "44000.00",
            "growth_pct": "20.7%",
            "catalyst": "Jockey master franchise holder, expanding sports shorts, tees, and athleisure wear into rural hubs.",
        },
    ],
    "big_cap_industries": [
        {
            "ticker": "LT",
            "name": "Larsen & Toubro (L&T)",
            "price": "3515.00",
            "target": "4200.00",
            "growth_pct": "19.5%",
            "catalyst": "Heavy infrastructure leader, direct beneficiary of the government's ₹11.11 Lakh Cr CAPEX budget.",
        },
        {
            "ticker": "RELIANCE",
            "name": "Reliance Industries",
            "price": "2912.00",
            "target": "3500.00",
            "growth_pct": "20.2%",
            "catalyst": "Consolidating 5G market share, scaling retail stores, and commissioning green energy gigafactories.",
        },
    ],
}

SECTOR_METADATA = {
    "clean_energy": {
        "label": "Clean Energy",
        "icon": "⚡",
        "desc": "Solar, Wind, Green Hydrogen, and Grid Transmission initiatives.",
    },
    "data_center_support": {
        "label": "Data Center Support",
        "icon": "🖥️",
        "desc": "Power cooling, high-speed fiber cables, and server space infrastructure.",
    },
    "cybersecurity": {
        "label": "Cybersecurity",
        "icon": "🛡️",
        "desc": "Data protection, software defense systems, and network security policies.",
    },
    "surveillance_security": {
        "label": "Surveillance & CCTV",
        "icon": "📷",
        "desc": "Smart City CCTVs, border security systems, and commercial surveillance cameras.",
    },
    "manufacturing_electronics": {
        "label": "Manufacturing & Electronics",
        "icon": "🏭",
        "desc": "PLI programs, semiconductor fabrications, and local contract assembly.",
    },
    "fmcg": {
        "label": "FMCG & Consumption",
        "icon": "🛒",
        "desc": "Rural disposable income, food processing, and consumer product growth.",
    },
    "sports_athleisure": {
        "label": "Sports & Athleisure",
        "icon": "👟",
        "desc": "Active footwear, fitness apparel, and sports licensing brands.",
    },
    "big_cap_industries": {
        "label": "Big Cap Industries",
        "icon": "🏛️",
        "desc": "Nation-building conglomerates, heavy engineering, and infrastructure giants.",
    },
}

# RSS queries targeted at Indian policies and financial events
SECTOR_QUERIES = {
    "clean_energy": [
        'site:pib.gov.in "solar" OR "renewable" OR "green hydrogen"',
        "India clean energy policy ministry power",
        '"Adani Green" OR "Tata Power" OR "Suzlon" energy order',
    ],
    "data_center_support": [
        'site:pib.gov.in "data center" OR "digital infrastructure"',
        "India data center policy expansion investments",
        '"Anant Raj" OR "Schneider" OR "Netweb" data center',
    ],
    "cybersecurity": [
        'site:pib.gov.in "cyber security" OR "cybersecurity" OR "CERT-In"',
        "India cyber security policy enterprise network protection",
        "TCS Quick Heal cyber contracts",
    ],
    "surveillance_security": [
        'site:pib.gov.in "CCTV" OR "safe city" OR "surveillance"',
        "India smart city CCTV cameras border defense drones",
        '"CP Plus" OR "Aditya Infotech" OR "Allied Digital" OR "IdeaForge" surveillance',
    ],
    "manufacturing_electronics": [
        'site:pib.gov.in "PLI" electronics OR "semiconductor" OR "OSAT"',
        "India electronics manufacturing PLI scheme semiconductor fab",
        "Dixon Kaynes semiconductor factory",
    ],
    "fmcg": [
        'site:pib.gov.in "agriculture" OR "rural development" OR "food processing"',
        "India FMCG consumption rural demand inflation",
        "Varun Beverages ITC results shares",
    ],
    "sports_athleisure": [
        'site:pib.gov.in "sports" OR "Khelo India" OR "footwear PLI"',
        "India sports brand athleisure market growth campus footwear",
        "Metro Brands Campus Activewear shares",
    ],
    "big_cap_industries": [
        'site:pib.gov.in "infrastructure" OR "capital expenditure" OR "Gati Shakti"',
        "India infra capex budget Larsen Toubro Reliance industries",
        "L&T order book Reliance green energy",
    ],
}


def load_watchlist():
    """Load watchlist from JSON file or return default if not exists."""
    watchlist_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "watchlist.json"
    )
    try:
        if os.path.exists(watchlist_path):
            with open(watchlist_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return STOCK_WATCHLIST


def save_watchlist(watchlist):
    """Saves watchlist back to watchlist.json."""
    watchlist_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "watchlist.json"
    )
    try:
        with open(watchlist_path, "w", encoding="utf-8") as f:
            json.dump(watchlist, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
