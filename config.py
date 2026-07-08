# config.py
import os
import json
from logger import log

# Public GitHub Pages dashboard URL surfaced in the email digest. Overridable so
# forks can point the "View Live Dashboard" link at their own deployment.
DASHBOARD_URL = os.environ.get(
    "DASHBOARD_URL", "https://karthik7899.github.io/india-policy-tracker/"
)

# Minimal seed used ONLY as a fallback when watchlist.json is missing or
# corrupt. Deliberately restricted to fields that do not go stale
# (ticker, name, catalyst) — prices, ratings, and fundamentals are always
# fetched live by the pipeline. Do not add market data snapshots here.
STOCK_WATCHLIST = {
    "aerospace_defence": [
        {
            "ticker": "HAL",
            "name": "Hindustan Aeronautics",
            "catalyst": "State aerospace major, expanding local fighter jet assembly and benefiting from custom duty exemptions.",
        },
        {
            "ticker": "BEL",
            "name": "Bharat Electronics",
            "catalyst": "Defence electronics leader, securing major naval and surveillance command radar orders.",
        },
        {
            "ticker": "ASTRAMICRO",
            "name": "Astra Microwave",
            "catalyst": "High-end microwave sub-systems maker, critical supplier of radars and satellite payloads.",
        },
    ],
    "big_cap_industries": [
        {
            "ticker": "LT",
            "name": "Larsen & Toubro (L&T)",
            "catalyst": "Heavy infrastructure leader, direct beneficiary of the government's ₹11.11 Lakh Cr CAPEX budget.",
        },
        {
            "ticker": "RELIANCE",
            "name": "Reliance Industries",
            "catalyst": "Consolidating 5G market share, scaling retail stores, and commissioning green energy gigafactories.",
        },
    ],
    "clean_energy": [
        {
            "ticker": "TATAPOWER",
            "name": "Tata Power",
            "catalyst": "Massive scaling in solar generation, microgrids, and leading India's EV charging network grid.",
        },
        {
            "ticker": "SUZLON",
            "name": "Suzlon Energy",
            "catalyst": "Turnaround story, completely debt-free, dominating wind turbine supply with a record order book.",
        },
        {
            "ticker": "ADANIGREEN",
            "name": "Adani Green Energy",
            "catalyst": "Developing the world's largest renewable energy park in Khavda, Gujarat (30 GW capacity target).",
        },
    ],
    "cybersecurity": [
        {
            "ticker": "TCS",
            "name": "Tata Consultancy Services",
            "catalyst": "Expanding sovereign cloud and secure cyber command centers globally for enterprise clients.",
        },
        {
            "ticker": "QUICKHEAL",
            "name": "Quick Heal Technologies",
            "catalyst": "Surging enterprise adoption of their 'Seqrite' cybersecurity platform and government IT contracts.",
        },
    ],
    "data_center_support": [
        {
            "ticker": "SCHNEIDER",
            "name": "Schneider Electric Infra",
            "catalyst": "Critical supplier of electrical distribution, smart grids, and high-efficiency cooling for data centers.",
        },
        {
            "ticker": "STLTECH",
            "name": "Sterlite Technologies (STL)",
            "catalyst": "Expanding optical fiber and cable capacities to meet hyper-scale data center interconnect demands.",
        },
        {
            "ticker": "ANANTRAJ",
            "name": "Anant Raj Ltd",
            "catalyst": "Real-estate developer transitioning commercial properties into major data center hubs in NCR.",
        },
    ],
    "fmcg": [
        {
            "ticker": "VBL",
            "name": "Varun Beverages (PepsiCo)",
            "catalyst": "PepsiCo's dominant bottler, expanding into newer territories and scaling dairy/juice products.",
        },
        {
            "ticker": "TATACONSUM",
            "name": "Tata Consumer Products",
            "catalyst": "Premiumization strategy in foods & beverages, high-growth acquisitions (Capital Foods, Organic India).",
        },
        {
            "ticker": "ITC",
            "name": "ITC Ltd",
            "catalyst": "Resilient cigarette margins funding rapid expansion of high-margin FMCG brands, direct rural boost play.",
        },
    ],
    "industrial_manufacturing": [
        {
            "ticker": "SIEMENS",
            "name": "Siemens Ltd",
            "catalyst": "Diversified capital-goods major, expanding local factory automation and grid equipment manufacturing.",
        },
        {
            "ticker": "THERMAX",
            "name": "Thermax Ltd",
            "catalyst": "Industrial energy & environment engineering leader, scaling green hydrogen and boiler manufacturing capacity.",
        },
        {
            "ticker": "KIRLOSENG",
            "name": "Kirloskar Oil Engines",
            "catalyst": "Legacy engineering major pivoting to power generation and farm equipment manufacturing under 'Make in India'.",
        },
        {
            "ticker": "ELGIEQUIP",
            "name": "Elgi Equipments",
            "catalyst": "Global air compressor manufacturer, expanding export-oriented capacity from Indian plants.",
        },
    ],
    "logistics_heavy_capital": [
        {
            "ticker": "CONCOR",
            "name": "Container Corporation of India",
            "catalyst": "Dominant railway container carrier, major beneficiary of the ₹10,000 crore container manufacturing scheme.",
        },
        {
            "ticker": "BHEL",
            "name": "Bharat Heavy Electricals",
            "catalyst": "State-owned heavy power equipment giant, expanding local container manufacturing and green energy grids.",
        },
        {
            "ticker": "CUMMINSIND",
            "name": "Cummins India",
            "catalyst": "Leading heavy engine maker, supplying power backups and engines for logistics and railway expansion.",
        },
    ],
    "macro_indicators": [
        {
            "ticker": "MAKEINDIA",
            "name": "Mirae Asset Nifty India Manufacturing ETF",
            "catalyst": "Passive index fund tracking the Nifty India Manufacturing Index. Captures the Make in India and PLI momentum.",
        },
    ],
    "manufacturing_electronics": [
        {
            "ticker": "DIXON",
            "name": "Dixon Technologies",
            "catalyst": "Leader in electronic assembly (mobile, laptop, LED TV), heavily subsidized under manufacturing PLI.",
        },
        {
            "ticker": "KAYNES",
            "name": "Kaynes Technology",
            "catalyst": "High-end electronics and PCBA manufacturing, setting up a state-of-the-art semiconductor OSAT plant.",
        },
        {
            "ticker": "CGPOWER",
            "name": "CG Power & Industrial",
            "catalyst": "Partnering on a $1B semiconductor fab, strong order pipeline in railways and power grid equipment.",
        },
    ],
    "midcap_it": [
        {
            "ticker": "PERSISTENT",
            "name": "Persistent Systems",
            "catalyst": "High-growth digital engineering and enterprise AI services provider, consistently outpacing large-cap IT growth rates.",
        },
        {
            "ticker": "COFORGE",
            "name": "Coforge Ltd",
            "catalyst": "Mid-tier IT services firm with large deal wins in BFSI and travel verticals, expanding margins via GenAI offerings.",
        },
        {
            "ticker": "MPHASIS",
            "name": "Mphasis Ltd",
            "catalyst": "Direct-core BFS-focused IT services player, key beneficiary of enterprise cloud and cost-takeout deals.",
        },
        {
            "ticker": "LTTS",
            "name": "L&T Technology Services",
            "catalyst": "Engineering R&D services leader, scaling embedded software and semiconductor design-services wins.",
        },
    ],
    "semiconductors_equipment": [
        {
            "ticker": "ASMTEC",
            "name": "ASM Technologies",
            "catalyst": "Engineering design services for semiconductor equipment makers under India Semiconductor Mission (ISM) 2.0.",
        },
        {
            "ticker": "RIR",
            "name": "RIR Power Electronics",
            "catalyst": "Power semiconductor device supplier, building new SiC fab facility under semiconductor PLI.",
        },
        {
            "ticker": "SPELS",
            "name": "SPEL Semiconductor",
            "catalyst": "First semiconductor OSAT and assembly facility listed, expanding IC testing capabilities.",
        },
    ],
    "sports_athleisure": [
        {
            "ticker": "METROBRAND",
            "name": "Metro Brands Ltd",
            "catalyst": "Exclusive retail rights for Fila and Foot Locker in India, expanding athleisure footprint rapidly.",
        },
        {
            "ticker": "CAMPUS",
            "name": "Campus Activewear",
            "catalyst": "Dominant direct-to-consumer sports footwear brand in tier-2/3 cities, major beneficiary of fitness trends.",
        },
        {
            "ticker": "PAGEIND",
            "name": "Page Industries",
            "catalyst": "Jockey master franchise holder, expanding sports shorts, tees, and athleisure wear into rural hubs.",
        },
        {
            "ticker": "RELAXO",
            "name": "Relaxo Footwears Limited",
            "catalyst": "Auto-discovered via media radar. Catalyst: Relaxo Footwears Ltd (RELAXO) Share Price",
        },
    ],
    "surveillance_security": [
        {
            "ticker": "CPPLUS",
            "name": "Aditya Infotech (CP PLUS)",
            "catalyst": "CCTV market leader (35%+ share) newly listed, scaling domestic camera manufacturing under PLI.",
        },
        {
            "ticker": "ADSL",
            "name": "Allied Digital Services",
            "catalyst": "System integrator winning smart/safe city surveillance projects, managing master command centers.",
        },
        {
            "ticker": "IDEAFORGE",
            "name": "IdeaForge Technology",
            "catalyst": "Pioneer in tactical and mapping drone systems, primary supplier for Indian Army and police borders.",
        },
        {
            "ticker": "ZENTEC",
            "name": "Zen Technologies",
            "catalyst": "Anti-drone systems and combat training simulators, winning repeat Ministry of Defence counter-drone orders.",
        },
    ],
    "textiles_apparel": [
        {
            "ticker": "WELSPUNLIV",
            "name": "Welspun Living",
            "catalyst": "Major beneficiary of textile PLI, expanding home textiles capacity and global export market share.",
        },
        {
            "ticker": "GOKEX",
            "name": "Gokaldas Exports",
            "catalyst": "Top apparel manufacturer, setting up new fabrics processing mill under textile PLI approval.",
        },
        {
            "ticker": "ARVIND",
            "name": "Arvind Ltd",
            "catalyst": "Leading denim manufacturer, investing in technical textiles under recent government schemes.",
        },
    ],
}


SECTOR_METADATA = {
    "aerospace_defence": {
        "desc": "Local aircraft assembly, BCD exemptions, " "and defense systems.",
        "icon": "✈️",
        "label": "Aerospace & Defence",
    },
    "big_cap_industries": {
        "desc": "Nation-building conglomerates, heavy "
        "engineering, and infrastructure giants.",
        "icon": "🏛️",
        "label": "Big Cap Industries",
    },
    "clean_energy": {
        "desc": "Solar, Wind, Green Hydrogen, and Grid " "Transmission initiatives.",
        "icon": "⚡",
        "label": "Clean Energy",
    },
    "cybersecurity": {
        "desc": "Data protection, software defense systems, "
        "and network security policies.",
        "icon": "🛡️",
        "label": "Cybersecurity",
    },
    "data_center_support": {
        "desc": "Power cooling, high-speed fiber "
        "cables, and server space "
        "infrastructure.",
        "icon": "🖥️",
        "label": "Data Center Support",
    },
    "fmcg": {
        "desc": "Rural disposable income, food processing, and "
        "consumer product growth.",
        "icon": "🛒",
        "label": "FMCG & Consumption",
    },
    "industrial_manufacturing": {
        "desc": "Capital goods, factory automation, and "
        "industrial engineering manufacturers.",
        "icon": "⚙️",
        "label": "Industrial Manufacturing",
    },
    "logistics_heavy_capital": {
        "desc": "Container manufacturing scheme, "
        "heavy machinery, and freight "
        "logistics.",
        "icon": "📦",
        "label": "Logistics & Capital Goods",
    },
    "macro_indicators": {
        "desc": "Passive index funds and ETFs tracking " "sector GVA growth.",
        "icon": "📊",
        "label": "Macro Indicators",
    },
    "manufacturing_electronics": {
        "desc": "PLI programs, semiconductor "
        "fabrications, and local contract "
        "assembly.",
        "icon": "🏭",
        "label": "Manufacturing & Electronics",
    },
    "midcap_it": {
        "desc": "Mid-tier IT services and engineering " "R&D outsourcing firms.",
        "icon": "💻",
        "label": "Midcap IT",
    },
    "semiconductors_equipment": {
        "desc": "India Semiconductor Mission (ISM) "
        "2.0, silicon fabs, and OSAT "
        "plants.",
        "icon": "💾",
        "label": "Semiconductors & Equipment",
    },
    "sports_athleisure": {
        "desc": "Active footwear, fitness apparel, and " "sports licensing brands.",
        "icon": "👟",
        "label": "Sports & Athleisure",
    },
    "surveillance_security": {
        "desc": "Smart City CCTVs, border security "
        "systems, and commercial surveillance "
        "cameras.",
        "icon": "📷",
        "label": "Surveillance & CCTV",
    },
    "textiles_apparel": {
        "desc": "Textile PLI programs, technical textiles, " "and global export hubs.",
        "icon": "👕",
        "label": "Textiles & Apparel",
    },
}

SECTOR_QUERIES = {
    "aerospace_defence": [
        'site:pib.gov.in "defence custom duty" OR ' '"defence aerospace"',
        "India defense manufacturing offset policies HAL " "BEL",
        '"Hindustan Aeronautics" OR "Bharat Electronics" '
        'OR "Astra Microwave" defence',
    ],
    "big_cap_industries": [
        'site:pib.gov.in "infrastructure" OR "capital ' 'expenditure" OR "Gati Shakti"',
        "India infra capex budget Larsen Toubro Reliance " "industries",
        "L&T order book Reliance green energy",
    ],
    "clean_energy": [
        'site:pib.gov.in "solar" OR "renewable" OR "green ' 'hydrogen"',
        "India clean energy policy ministry power",
        '"Adani Green" OR "Tata Power" OR "Suzlon" energy ' "order",
    ],
    "cybersecurity": [
        'site:pib.gov.in "cyber security" OR "cybersecurity" ' 'OR "CERT-In"',
        "India cyber security policy enterprise network " "protection",
        "TCS Quick Heal cyber contracts",
    ],
    "data_center_support": [
        'site:pib.gov.in "data center" OR "digital ' 'infrastructure"',
        "India data center policy expansion investments",
        '"Anant Raj" OR "Schneider" OR "Netweb" data ' "center",
    ],
    "fmcg": [
        'site:pib.gov.in "agriculture" OR "rural development" OR "food ' 'processing"',
        "India FMCG consumption rural demand inflation",
        "Varun Beverages ITC results shares",
    ],
    "industrial_manufacturing": [
        'site:pib.gov.in "capital goods" OR "industrial '
        'manufacturing" OR "factory automation"',
        "India industrial manufacturing capital goods engineering order book",
        '"Siemens" OR "Thermax" OR "Kirloskar" OR "Elgi ' 'Equipments" manufacturing',
    ],
    "logistics_heavy_capital": [
        'site:pib.gov.in "Container Scheme" OR ' '"heavy logistics"',
        "India container manufacturing capital " "goods railway capex",
        '"CONCOR" OR "BHEL" OR "Cummins" logistics ' "order",
    ],
    "macro_indicators": [
        'site:pib.gov.in "manufacturing GVA" OR ' '"industrial production"',
        "India manufacturing growth index PMI index",
        "Nifty India Manufacturing ETF shares",
    ],
    "manufacturing_electronics": [
        'site:pib.gov.in "PLI" electronics OR ' '"semiconductor" OR "OSAT"',
        "India electronics manufacturing PLI " "scheme semiconductor fab",
        "Dixon Kaynes semiconductor factory",
    ],
    "midcap_it": [
        'site:pib.gov.in "IT services" OR "digital ' 'engineering" OR "GCC"',
        "India midcap IT services growth deal wins GenAI",
        '"Persistent Systems" OR "Coforge" OR "Mphasis" OR ' '"LTTS" IT services',
    ],
    "semiconductors_equipment": [
        'site:pib.gov.in "semiconductor PLI" OR ' '"ISM 2.0" OR "OSAT"',
        "India semiconductor fab equipment OSAT " "packaging plants",
        '"ASM Technologies" OR "RIR Power" OR ' '"SPEL Semiconductor"',
    ],
    "sports_athleisure": [
        'site:pib.gov.in "sports" OR "Khelo India" OR ' '"footwear PLI"',
        "India sports brand athleisure market growth " "campus footwear",
        "Metro Brands Campus Activewear shares",
    ],
    "surveillance_security": [
        'site:pib.gov.in "CCTV" OR "safe city" OR ' '"surveillance"',
        "India smart city CCTV cameras border defense " "drones",
        '"CP Plus" OR "Aditya Infotech" OR "Allied '
        'Digital" OR "IdeaForge" surveillance',
    ],
    "textiles_apparel": [
        'site:pib.gov.in "textile PLI" OR "apparel ' 'manufacturing"',
        "India textiles export incentives technical " "textiles",
        '"Welspun" OR "Gokaldas" OR "Arvind" textiles',
    ],
}


def _normalize_watchlist(watchlist):
    """Canonicalize every stock record's typed fields on load (see
    models/stock.py). Well-formed records round-trip unchanged; drifted
    ones ("1,840.00", a float where a string belongs) are repaired here,
    at the boundary, instead of surprising a parser mid-pipeline. A record
    that can't be normalized is kept raw — normalization must never be the
    reason the watchlist fails to load."""
    from models.stock import normalize_stock_record

    if not isinstance(watchlist, dict):
        return watchlist
    for sector, stocks in watchlist.items():
        if not isinstance(stocks, list):
            continue
        for i, stock in enumerate(stocks):
            if not isinstance(stock, dict):
                continue
            try:
                stocks[i] = normalize_stock_record(stock)
            except Exception as e:
                log.warning(
                    f"Could not normalize stock record in {sector} "
                    f"(kept raw): {type(e).__name__}: {str(e)[:120]}"
                )
    return watchlist


def load_watchlist():
    watchlist_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "watchlist.json"
    )
    try:
        with open(watchlist_path, "r", encoding="utf-8") as f:
            return _normalize_watchlist(json.load(f))
    except FileNotFoundError:
        log.error(
            "watchlist.json not found — falling back to the minimal seed "
            "watchlist (tickers only, no market data). The briefing will "
            "rebuild prices and fundamentals from live sources this run."
        )
        return STOCK_WATCHLIST
    except json.JSONDecodeError:
        log.error(
            "watchlist.json is corrupt — falling back to the minimal seed "
            "watchlist (tickers only, no market data). The briefing will "
            "rebuild prices and fundamentals from live sources this run."
        )
        return STOCK_WATCHLIST
    except Exception as e:
        log.error(f"Unexpected error loading watchlist.json: {e}")
        return STOCK_WATCHLIST


def save_watchlist(watchlist):
    watchlist_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "watchlist.json"
    )
    try:
        from utils import atomic_write_json

        atomic_write_json(watchlist, watchlist_path)
        return True
    except OSError:
        return False
