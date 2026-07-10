"""Historical Mutual-Fund backtesting baseline (Prompt 5 — leading/lagging indicators).

Ingests historical mutual-fund NAV data to establish a *backtesting baseline for
institutional accumulation* into the policy themes we track (manufacturing,
semiconductors, defence, logistics).

The NAV history of a thematic fund is used as a free, public proxy for how much
institutional capital has been compounding into that theme: a fund whose NAV is
accelerating (short-term momentum running ahead of its longer-term trend) signals
strengthening institutional accumulation, while a decelerating NAV signals the
opposite.

Data source
-----------
The same AMFI NAV history archived by the community ``captn3m0/historical-mf-data``
dataset is exposed as a free JSON API at ``api.mfapi.in`` (no key required). The
base URL is overridable via ``MF_DATA_BASE_URL`` so the ingestion can be pointed at
a local captn3m0 mirror instead. Every network call degrades gracefully — if the
source is unreachable the pipeline simply records an empty baseline and carries on.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from logger import log

# Overridable so the ingestion can target a captn3m0 mirror / self-hosted dataset.
MF_DATA_BASE_URL = os.environ.get("MF_DATA_BASE_URL", "https://api.mfapi.in")

# Map our tracked policy themes to the keywords that identify a matching scheme.
THEME_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "Manufacturing & PLI": ("manufacturing", "make in india"),
    "Semiconductors & Tech": ("semiconductor", "technology", "digital"),
    "Defence & Aerospace": ("defence", "defense", "aerospace"),
    "Logistics & Infra": ("logistics", "transport", "infrastructure"),
}

# Approx. number of NAV observations (trading days) in each lookback window.
_WINDOWS = {"1M": 21, "3M": 63, "1Y": 252}


def classify_theme(scheme_name: str) -> Optional[str]:
    """Return the policy theme a scheme name maps to, or ``None`` if it is off-theme."""
    name = (scheme_name or "").lower()
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            return theme
    return None


def _parse_nav_records(raw: List[Dict[str, Any]]) -> List[Tuple[str, float]]:
    """Normalize raw NAV rows into ``(iso_date, nav)`` tuples sorted oldest -> newest.

    Accepts the ``{"date": "DD-MM-YYYY", "nav": "123.45"}`` shape used by both the
    mfapi.in API and the captn3m0 CSV export. Malformed rows are skipped.
    """
    records: List[Tuple[str, float]] = []
    for row in raw or []:
        date_str = str(row.get("date", "")).strip()
        nav_str = str(row.get("nav", "")).strip()
        if not date_str or not nav_str:
            continue
        try:
            nav = float(nav_str)
        except ValueError:
            continue
        if nav <= 0:
            continue
        iso = _to_iso_date(date_str)
        if iso:
            records.append((iso, nav))

    records.sort(key=lambda r: r[0])
    return records


def _to_iso_date(date_str: str) -> Optional[str]:
    """Coerce a DD-MM-YYYY (or already-ISO) date string to ISO ``YYYY-MM-DD``."""
    for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _pct_change(records: List[Tuple[str, float]], lookback: int) -> Optional[float]:
    """Percentage NAV change over the last ``lookback`` observations."""
    if len(records) <= lookback:
        return None
    latest = records[-1][1]
    past = records[-1 - lookback][1]
    if past <= 0:
        return None
    return round((latest - past) / past * 100, 2)


def compute_accumulation_baseline(
    records: List[Tuple[str, float]],
) -> Optional[Dict[str, Any]]:
    """Summarize a fund's NAV history into an institutional-accumulation baseline.

    Returns trailing 1M/3M/1Y NAV returns plus an ``accumulation_trend`` label that
    compares short-term momentum against the longer-term trend:

    * **Accelerating** — recent (3M) pace is running ahead of the 1Y average pace.
    * **Decelerating** — recent pace has dropped below the 1Y average pace.
    * **Steady** — broadly in line.
    """
    if len(records) < 2:
        return None

    returns = {label: _pct_change(records, n) for label, n in _WINDOWS.items()}
    latest_nav = records[-1][1]

    trend = "Steady"
    r3m, r1y = returns.get("3M"), returns.get("1Y")
    if r3m is not None and r1y is not None:
        # Annualize the 3M pace and compare with the realized 1Y return.
        annualized_recent = r3m * 4
        if annualized_recent > r1y * 1.15:
            trend = "Accelerating"
        elif annualized_recent < r1y * 0.85:
            trend = "Decelerating"

    return {
        "latest_nav": round(latest_nav, 4),
        "as_of": records[-1][0],
        "observations": len(records),
        "return_1m": returns.get("1M"),
        "return_3m": returns.get("3M"),
        "return_1y": returns.get("1Y"),
        "accumulation_trend": trend,
    }


def _http_get_json(session: requests.Session, url: str) -> Optional[Any]:
    try:
        resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        log.error(f"MF data source returned {resp.status_code} for {url}")
    except (
        Exception
    ) as e:  # noqa: BLE001 - network/parse failures must not break the run
        log.error(f"Error fetching MF data from {url}: {e}")
    return None


# AMFI plan/option vocabulary — a token from this set marks where the share
# class begins and the underlying fund's name ends.
_PLAN_OPTION_TOKENS = {
    "direct",
    "regular",
    "growth",
    "idcw",
    "dividend",
    "payout",
    "reinvestment",
    "bonus",
    "quarterly",
    "monthly",
    "annual",
    "plan",
    "option",
}


def _base_fund_name(scheme_name: str) -> str:
    """Normalize a scheme name to its underlying fund for dedup purposes.

    AMFI lists the same fund once per share class, and the separator format
    is wildly inconsistent: "Fund - Direct Plan - Growth", "Fund-Growth",
    "Fund-Quarterly IDCW", "Fund Regular Plan - Payout of IDCW Option". A
    separator-based split (" - ") missed the no-space hyphen variants and
    let duplicates back into the baseline (run #76: the same BANK OF INDIA
    and Tata Infrastructure funds logged twice). Instead, hyphens are
    treated as spaces and the name is truncated at the first plan/option
    token."""
    tokens = (scheme_name or "").lower().replace("-", " ").split()
    base = []
    for token in tokens:
        if token.strip(".,()") in _PLAN_OPTION_TOKENS:
            break
        base.append(token)
    return " ".join(base).strip()


def discover_thematic_schemes(
    session: requests.Session, max_per_theme: int = 2
) -> Dict[str, List[Dict[str, Any]]]:
    """Find a handful of on-theme schemes from the dataset's full scheme list.

    A single fund is typically listed multiple times under separate scheme
    codes for its Direct/Regular and Growth/IDCW share classes — without
    dedup those all count separately against ``max_per_theme`` and the same
    fund name shows up more than once in the baseline.
    """
    schemes = _http_get_json(session, f"{MF_DATA_BASE_URL}/mf")
    discovered: Dict[str, List[Dict[str, Any]]] = {t: [] for t in THEME_KEYWORDS}
    if not isinstance(schemes, list):
        return discovered

    seen_names: Dict[str, set] = {t: set() for t in THEME_KEYWORDS}
    for entry in schemes:
        name = entry.get("schemeName", "")
        code = entry.get("schemeCode")
        theme = classify_theme(name)
        if not theme or not code or len(discovered[theme]) >= max_per_theme:
            continue
        base_name = _base_fund_name(name)
        if base_name in seen_names[theme]:
            continue
        seen_names[theme].add(base_name)
        discovered[theme].append({"code": code, "name": name})
    return discovered


def fetch_scheme_nav_history(
    session: requests.Session, code: Any
) -> List[Tuple[str, float]]:
    """Fetch and normalize a single scheme's historical NAV series."""
    payload = _http_get_json(session, f"{MF_DATA_BASE_URL}/mf/{code}")
    if isinstance(payload, dict):
        return _parse_nav_records(payload.get("data", []))
    return []


def build_institutional_baseline(
    session: Optional[requests.Session] = None, max_per_theme: int = 2
) -> List[Dict[str, Any]]:
    """Ingest historical NAV data and return per-fund accumulation baselines.

    Fully defensive: any failure (no network, bad data) yields an empty list so the
    daily briefing pipeline is never interrupted.
    """
    log.info("Building institutional accumulation baseline from historical MF data...")
    owns_session = session is None
    session = session or requests.Session()
    baseline: List[Dict[str, Any]] = []

    try:
        discovered = discover_thematic_schemes(session, max_per_theme=max_per_theme)
        for theme, schemes in discovered.items():
            for scheme in schemes:
                records = fetch_scheme_nav_history(session, scheme["code"])
                metrics = compute_accumulation_baseline(records)
                if not metrics:
                    continue
                entry = {"theme": theme, "fund_name": scheme["name"], **metrics}
                baseline.append(entry)
                log.info(
                    f"MF baseline [{theme}] {scheme['name']}: "
                    f"1Y {metrics['return_1y']}% ({metrics['accumulation_trend']})"
                )
    except Exception as e:  # noqa: BLE001
        log.error(f"Error building institutional baseline: {e}")
    finally:
        if owns_session:
            session.close()

    # Strongest accumulation first.
    baseline.sort(key=lambda b: (b.get("return_1y") or -999), reverse=True)
    return baseline
