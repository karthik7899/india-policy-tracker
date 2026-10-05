"""Does a company belong in the sector it is filed under?

The rotation engine gave a candidate the sector of whatever surfaced it:
the news feed whose headline named it, or the holding whose Screener peer
table listed it. Neither says what the company does, and the watchlist
showed it — Godrej Properties under Data Center Support (a real-estate peer
of Anant Raj, which is there for its data-centre pivot), Adani Power, a
thermal generator, under Clean Energy, Oracle Financial Services and
Capillary (banking and loyalty software) under Cybersecurity, a power-cable
maker and a rooftop-solar maker under Semiconductors. A misfiled holding
gets the wrong sector index, the wrong policy tags and the wrong peers.

The company's own Yahoo profile is the check: its industry ("Real Estate -
Development", "Utilities - Independent Power Producers") and a few keyword
groups read from its business summary. Each sector lists the industries
that belong to it; a few thesis-defined sectors also need words the
industry cannot carry (a security product, renewable generation, data
centres). The rotation probe already loads that profile, so the check costs
no request.

Used two ways:

  place()            for a rotation candidate: keep its sector if it fits,
                     move it to the one sector it does fit, or refuse it
  audit_watchlist()  for current holdings: report misfits and a suggested
                     sector each run. Nothing is moved — a holding's sector
                     is the owner's call, and some are there for a thesis
                     the industry label cannot see.

A company whose industry is unknown is never refused for it: the check
says "unverified" and the earlier behaviour stands, so a Yahoo gap cannot
stop the rotation engine.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# Keyword groups read from a business summary. Kept small and literal: they
# tell sectors apart where industry labels do not, and say nothing else.
KEYWORDS = {
    "security": r"cyber|information security|endpoint|firewall|threat|antivirus|"
    r"identity (?:and|&) access|security (?:software|solutions|products|services)",
    "renewable": r"renewable|solar|wind|hydro|green energy|green hydrogen",
    "thermal": r"thermal power|coal[- ]fired|coal based|coal-based",
    "data_centre": r"data cent(?:er|re)",
    "semiconductor": r"semiconductor|wafer|chip|osat|integrated circuit",
    "defence": r"defen[cs]e|military|missile|radar|naval",
    "surveillance": r"surveillance|cctv|video security|drone|unmanned|safe city|"
    r"command and control",
    "footwear": r"footwear|shoe",
}
_KEYWORD_RES = {k: re.compile(v, re.IGNORECASE) for k, v in KEYWORDS.items()}

# Yahoo industry names, lower-case. A sector's company fits when its industry
# is listed here, or (``also_if``) its summary carries one of the groups —
# and, where given, it carries a ``require`` group and no ``exclude`` group.
SECTOR_FIT: Dict[str, Dict[str, Any]] = {
    "aerospace_defence": {
        "industries": ["aerospace & defense"],
        "also_if": ["defence"],
    },
    "banking_financials": {
        "industries": [
            "banks - regional",
            "banks - diversified",
            "credit services",
            "capital markets",
            "asset management",
            "financial conglomerates",
            "mortgage finance",
            "insurance - life",
            "insurance - diversified",
            "insurance - property & casualty",
            "financial data & stock exchanges",
        ],
    },
    "big_cap_industries": {
        "industries": [
            "oil & gas refining & marketing",
            "oil & gas integrated",
            "oil & gas e&p",
            "engineering & construction",
            "conglomerates",
            "infrastructure operations",
            "building materials",
            "steel",
            "utilities - independent power producers",
            "utilities - regulated electric",
            "utilities - diversified",
            "telecom services",
        ],
    },
    "clean_energy": {
        "industries": [
            "utilities - renewable",
            "solar",
            "utilities - independent power producers",
            "utilities - regulated electric",
            "utilities - diversified",
            "specialty industrial machinery",
            "electrical equipment & parts",
        ],
        "require": ["renewable"],
        "exclude": ["thermal"],
    },
    "cybersecurity": {
        "industries": [
            "software - infrastructure",
            "software - application",
            "information technology services",
        ],
        "require": ["security"],
    },
    "data_center_support": {
        "industries": [
            "electrical equipment & parts",
            "communication equipment",
            "computer hardware",
            "information technology services",
        ],
        "also_if": ["data_centre"],
    },
    "fmcg": {
        "industries": [
            "beverages - non-alcoholic",
            "beverages - brewers",
            "beverages - wineries & distilleries",
            "packaged foods",
            "confectioners",
            "tobacco",
            "household & personal products",
            "farm products",
            "food distribution",
        ],
    },
    "healthcare_hospitals": {
        "industries": [
            "medical care facilities",
            "diagnostics & research",
            "health information services",
        ],
    },
    "hospitality_travel": {
        "industries": [
            "lodging",
            "resorts & casinos",
            "travel services",
            "airlines",
            "restaurants",
            "leisure",
        ],
    },
    "industrial_manufacturing": {
        "industries": [
            "specialty industrial machinery",
            "farm & heavy construction machinery",
            "tools & accessories",
            "metal fabrication",
            "electrical equipment & parts",
            "diversified industrials",
            "pollution & treatment controls",
            "industrial distribution",
        ],
    },
    "logistics_heavy_capital": {
        "industries": [
            "integrated freight & logistics",
            "railroads",
            "trucking",
            "marine shipping",
            "airports & air services",
            "infrastructure operations",
            "specialty industrial machinery",
            "farm & heavy construction machinery",
        ],
    },
    "manufacturing_electronics": {
        "industries": [
            "electronic components",
            "consumer electronics",
            "electrical equipment & parts",
            "computer hardware",
            "communication equipment",
            "scientific & technical instruments",
            "metal fabrication",
        ],
    },
    "midcap_it": {
        "industries": [
            "information technology services",
            "software - application",
            "software - infrastructure",
            "health information services",
        ],
    },
    "semiconductors_equipment": {
        "industries": [
            "semiconductors",
            "semiconductor equipment & materials",
            "electronic components",
            "scientific & technical instruments",
        ],
        "also_if": ["semiconductor"],
    },
    "sports_athleisure": {
        "industries": [
            "footwear & accessories",
            "apparel manufacturing",
            "apparel retail",
            "leisure",
        ],
        "also_if": ["footwear"],
    },
    "surveillance_security": {
        "industries": [
            "security & protection services",
            "communication equipment",
            "electronic components",
            "consumer electronics",
            "aerospace & defense",
            "scientific & technical instruments",
        ],
        "also_if": ["surveillance"],
    },
    "textiles_apparel": {
        "industries": [
            "textile manufacturing",
            "apparel manufacturing",
            "apparel retail",
        ],
    },
}


def keywords(summary: Any) -> List[str]:
    """The keyword groups a business summary carries."""
    text = str(summary or "")
    return sorted(k for k, rx in _KEYWORD_RES.items() if rx.search(text))


def fits(sector: str, industry: Any, groups) -> Optional[bool]:
    """True/False, or None when the company's industry is unknown or the
    sector has no rule (macro indicators)."""
    rule = SECTOR_FIT.get(sector)
    ind = str(industry or "").strip().lower()
    if rule is None or not ind:
        return None
    groups = set(groups or ())
    listed = ind in rule["industries"] or bool(groups & set(rule.get("also_if", ())))
    if not listed:
        return False
    if rule.get("require") and not groups & set(rule["require"]):
        return False
    if groups & set(rule.get("exclude", ())):
        return False
    return True


def fitting_sectors(industry: Any, groups, among=None) -> List[str]:
    """Every sector the company fits, in SECTOR_FIT order."""
    return [
        s
        for s in SECTOR_FIT
        if (among is None or s in among) and fits(s, industry, groups)
    ]


def place(sector: str, industry: Any, groups, among=None) -> Tuple[Optional[str], str]:
    """Where a rotation candidate belongs: ``(sector or None, reason)``.

    Kept where it was found if it fits there (or its industry is unknown);
    moved when it fits exactly one other sector; refused when it fits none,
    or several and not the one it came from — guessing between sectors is
    how this went wrong in the first place.
    """
    verdict = fits(sector, industry, groups)
    if verdict is None:
        return sector, "industry unknown; sector unverified"
    if verdict:
        return sector, f"{industry} fits {sector}"
    others = [s for s in fitting_sectors(industry, groups, among) if s != sector]
    if len(others) == 1:
        return others[0], f"{industry} fits {others[0]}, not {sector}"
    if others:
        return None, f"{industry} fits {', '.join(others)}, not {sector}"
    return None, f"{industry} fits none of our sectors"


def audit_watchlist(watchlist: Dict[str, Any]) -> Dict[str, Any]:
    """Holdings whose recorded industry does not fit their sector.

    Reads ``yahoo_industry`` and ``business_keywords``, which
    providers/yahoo.py records on each holding. Returns ``{checked,
    misfits: [{ticker, name, sector, industry, suggested}], unverified:
    [tickers]}``. Reports only; moves nothing.
    """
    checked, misfits, unverified = 0, [], []
    for sector, stocks in (watchlist or {}).items():
        if sector not in SECTOR_FIT or not isinstance(stocks, list):
            continue
        for s in stocks:
            if not isinstance(s, dict) or not s.get("ticker"):
                continue
            industry = s.get("yahoo_industry")
            groups = s.get("business_keywords") or []
            verdict = fits(sector, industry, groups)
            if verdict is None:
                unverified.append(s["ticker"])
                continue
            checked += 1
            if not verdict:
                misfits.append(
                    {
                        "ticker": s["ticker"],
                        "name": s.get("name") or s["ticker"],
                        "sector": sector,
                        "industry": industry,
                        "suggested": fitting_sectors(industry, groups),
                    }
                )
    return {"checked": checked, "misfits": misfits, "unverified": unverified}
