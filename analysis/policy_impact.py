"""Which way policy news cuts, sector by sector.

The tracker's news carried an ``impact`` label from VADER, a general-purpose
sentiment scorer. Sentiment is not direction: of 72 sector items in one run
53 read "Positive" and none "Negative", including "FMCG firms to hold prices
through festive season despite rising commodity costs" — a margin headwind —
and "Top 6 Semiconductor Stocks In India To Invest In", which is not policy
at all. For a policy tracker that label was the least informative field it
had.

The LLM reader (analysis/llm_reader.py) now reads, for every headline,
whether a government or regulator acted, how, how far along the measure is,
and which of our sectors it helps or hurts — each effect quoting the
headline for what is affected. This module turns those readings into:

  policy_impacts        one row per policy headline, with its sector effects
  sector_policy_balance tailwinds and headwinds per sector over a window
  annotate_sector_news  the per-sector feed items, labelled with their
                        direction for THAT sector
  state_of              whose measure it is, when a state government's

The PIB queries see only the Centre. State governments set land prices,
power tariffs and capital subsidies, and run their own EV, electronics,
data-centre and textile policies: they decide where a plant is built. A
state-policy feed (scraper.fetch_state_policy_async) brings those headlines
in, the same reader reads them, and state_of() labels whose policy it is.

All of it is the LLM's reading, labelled as such wherever it is shown. It is
never fed into scores or warnings: like every other LLM-only output here, it
informs the reader and is scored against eval/policy_labels.json before
anyone should lean on it.
"""

import datetime
import re
from typing import Any, Dict, List, Optional

from analysis.event_evidence import article_date

# How much a measure counts toward a sector's balance by how far along it is.
# A proposal is a signal, not yet a change to anyone's economics.
STATUS_WEIGHT = {"in_force": 1.0, "approved": 1.0, "proposed": 0.5}
BALANCE_WINDOW_DAYS = 30

# State-feed headlines kept across runs: as long as the balance looks back,
# with room for a story dated a little before it was collected.
STATE_RETENTION_DAYS = 45
STATE_FEED_CAP = 80

# Every state and its forms in headlines. Abbreviations are matched
# case-sensitively ("UP government", never "up"), full names in any case.
_STATES = {
    "Andhra Pradesh": (r"andhra pradesh", r"andhra", r"(?-i:AP)"),
    "Arunachal Pradesh": (r"arunachal pradesh", r"arunachal"),
    "Assam": (r"assam",),
    "Bihar": (r"bihar",),
    "Chhattisgarh": (r"chhattisgarh",),
    "Goa": (r"goa",),
    "Gujarat": (r"gujarat",),
    "Haryana": (r"haryana",),
    "Himachal Pradesh": (r"himachal pradesh", r"himachal", r"(?-i:HP)"),
    "Jharkhand": (r"jharkhand",),
    "Karnataka": (r"karnataka",),
    "Kerala": (r"kerala",),
    "Madhya Pradesh": (r"madhya pradesh", r"(?-i:MP)"),
    "Maharashtra": (r"maharashtra", r"(?-i:Maha)"),
    "Odisha": (r"odisha", r"orissa"),
    "Punjab": (r"punjab",),
    "Rajasthan": (r"rajasthan",),
    "Tamil Nadu": (r"tamil\s+nadu", r"(?-i:TN)"),
    "Telangana": (r"telangana",),
    "Uttar Pradesh": (r"uttar pradesh", r"(?-i:UP)"),
    "Uttarakhand": (r"uttarakhand",),
    "West Bengal": (r"west bengal", r"(?-i:WB)"),
}
# Words that make a state the actor rather than a location.
_STATE_ACTOR = (
    r"(?:govt|government|cabinet|cm|chief\s+minister|minister|assembly|"
    r"budget|policy|scheme|subsidy|incentives?|tariff|approves|announces|"
    r"unveils|notifies|clears|signs|mou|inks)"
)
_STATE_RES = {
    state: re.compile(
        r"\b(?:"
        + "|".join(forms)
        + r")(?:'s|’s)?\s+(?:[\w-]+\s+){0,2}?"
        + _STATE_ACTOR
        + r"\b",
        re.IGNORECASE,
    )
    for state, forms in _STATES.items()
}
# The Centre acting in or for a state is still the Centre's measure.
_CENTRAL_RE = re.compile(
    # "Centre" as the government, not a data, call or distribution centre,
    # nor a "centre of excellence".
    r"\b(?:(?<!data\s)(?<!call\s)(?<!care\s)(?<!distribution\s)"
    r"(?<!experience\s)(?<!fulfilment\s)(?<!development\s)(?<!service\s)"
    r"centre(?!\s+(?:of|for)\b)|central\s+govt|central\s+government|"
    r"union\s+(?:cabinet|budget|government|minister)|modi\s+govt|goi)\b",
    re.IGNORECASE,
)


def state_of(headline: str) -> Optional[str]:
    """The state whose measure a headline reports, or None.

    Read from the headline, never from the query that found it. A state is
    the actor only when its name sits right before a government word —
    "Gujarat government", "Tamil Nadu's EV policy", "UP cabinet approves" —
    so a plant "in Khavda, Gujarat" or "AP Government and Suzlon break
    ground" is judged on its words, not on the place name. A headline that
    names the Centre is the Centre's, and one naming two states' actions is
    not attributed to either.
    """
    text = str(headline or "")
    if _CENTRAL_RE.search(text):
        return None
    found = [state for state, rx in _STATE_RES.items() if rx.search(text)]
    return found[0] if len(found) == 1 else None


def prune_state_policy(
    items: List[Dict[str, Any]], today: str = ""
) -> List[Dict[str, Any]]:
    """State-feed items within the retention window, newest first, capped."""
    today = today or datetime.date.today().isoformat()
    cutoff = (
        datetime.date.fromisoformat(today)
        - datetime.timedelta(days=STATE_RETENTION_DAYS)
    ).isoformat()
    kept = [
        i
        for i in items or []
        if isinstance(i, dict) and (article_date(i.get("date")) or "") >= cutoff
    ]
    kept.sort(key=lambda i: article_date(i.get("date")) or "", reverse=True)
    return kept[:STATE_FEED_CAP]


def policy_impacts(
    readings: Dict[str, Dict[str, Any]],
    sources: Optional[Dict[str, Dict[str, str]]] = None,
    today: str = "",
) -> List[Dict[str, Any]]:
    """Policy headlines with at least one sector effect, newest first."""
    today = today or datetime.date.today().isoformat()
    out = []
    for headline, reading in (readings or {}).items():
        if not isinstance(reading, dict):
            continue
        if reading.get("policy_measure") in (None, "none"):
            continue
        effects = reading.get("sector_effects") or []
        if not effects:
            continue
        citation = (sources or {}).get(headline.lower()) or {}
        state = state_of(headline)
        out.append(
            {
                "headline": headline[:200],
                "measure": reading["policy_measure"],
                "status": reading.get("policy_status") or "proposed",
                "effects": effects,
                **({"state": state} if state else {}),
                "date": article_date(citation.get("date")) or today,
                **({"link": citation["link"]} if citation.get("link") else {}),
                **({"source": citation["source"]} if citation.get("source") else {}),
                "reader": "llm",
            }
        )
    out.sort(key=lambda r: (r["date"], r["headline"]), reverse=True)
    return out


def sector_policy_balance(
    impacts: List[Dict[str, Any]],
    today: str = "",
    window_days: int = BALANCE_WINDOW_DAYS,
) -> Dict[str, Dict[str, Any]]:
    """``{sector: {tailwind, headwind, mixed, net, items}}`` over the window.

    Counts are weighted by status (a proposal counts half) and ``net`` is
    tailwind minus headwind. ``items`` keeps the headlines behind the count,
    so the number can always be traced to what was read.
    """
    today = today or datetime.date.today().isoformat()
    cutoff = (
        datetime.date.fromisoformat(today) - datetime.timedelta(days=window_days)
    ).isoformat()
    balance: Dict[str, Dict[str, Any]] = {}
    for impact in impacts or []:
        if str(impact.get("date", "")) < cutoff:
            continue
        weight = STATUS_WEIGHT.get(impact.get("status"), 0.5)
        for effect in impact.get("effects") or []:
            row = balance.setdefault(
                effect["sector"],
                {"tailwind": 0.0, "headwind": 0.0, "mixed": 0.0, "items": []},
            )
            row[effect["direction"]] += weight
            row["items"].append(
                {
                    "headline": impact["headline"],
                    "direction": effect["direction"],
                    "status": impact.get("status"),
                    "date": impact.get("date"),
                    **({"link": impact["link"]} if impact.get("link") else {}),
                }
            )
    for row in balance.values():
        row["net"] = round(row["tailwind"] - row["headwind"], 2)
        for key in ("tailwind", "headwind", "mixed"):
            row[key] = round(row[key], 2)
    return balance


def annotate_sector_news(
    data: Dict[str, Any], readings: Dict[str, Dict[str, Any]], sectors
) -> int:
    """Label each sector feed item with its policy reading for that sector.

    ``item["policy"]`` is ``{measure, status, direction}`` where direction is
    the reading for the sector the item is filed under — None when the item
    is policy news that does not touch this sector directly, which is itself
    worth knowing. Items the LLM has not read, or that are not policy, get no
    ``policy`` key at all. Returns how many items were labelled.
    """
    labelled = 0
    for sector in sectors or []:
        for item in data.get(sector) or []:
            if not isinstance(item, dict):
                continue
            item.pop("policy", None)
            reading = (readings or {}).get(str(item.get("title") or "").strip())
            if not reading or reading.get("policy_measure") in (None, "none"):
                continue
            direction = next(
                (
                    e["direction"]
                    for e in reading.get("sector_effects") or []
                    if e.get("sector") == sector
                ),
                None,
            )
            item["policy"] = {
                "measure": reading["policy_measure"],
                "status": reading.get("policy_status") or "proposed",
                "direction": direction,
            }
            labelled += 1
    return labelled
