"""Company names: the name NSE registers, the stored names cut down from it,
and the shorter names headlines use.

Every attribution in this pipeline goes through one matcher
(analysis/parsing.title_matches_company), which accepts a name only as whole
words. A stored name with a cut word therefore matches nothing but the
ticker. That is what Screener's peer tables hand over, at about fifteen
characters: "NTPC Green Ene.", "Godrej Propert.", "Oracle Fin.Serv.". The
rotation admitted peers under those labels, so "NTPC Green Energy" headlines
never reached NTPC Green Energy, and the LLM reader could not resolve the
company it named. Other holdings carried "B P C L", "Anant Raj Ltd" or
"Inventurus Knowl", each of which matches no headline either.

NSE's equity list (providers/isin_master.py) carries each listing's
registered name. A stored name is repaired to it only when the stored name is
that name cut down: words truncated or abbreviated ("Ene.", "Devl."), reduced
to initials ("B P C L"), or with the legal suffix written in ("Anant Raj
Ltd"). A complete shorter name ("Kaynes Technology", "TVS Supply") or a
brand that is not the registered name at all (The Leela's registered company
is Schloss Bangalore) is how someone chose to write it, and is left alone.

Registered names can be longer than the news writes them ("Kalpataru
Projects International" is "Kalpataru Projects" in a headline), so
headline_names.json lists the shorter forms, by ticker, which the matcher
accepts beside the name. The displayed name stays the registered one.
"""

import functools
import json
import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADLINE_NAMES_PATH = os.path.join(ROOT, "headline_names.json")

_PARENS = re.compile(r"\s*\(([^)]*)\)")
_LEGAL_SUFFIX = re.compile(r"\s+(?:limited|ltd\.?)$", re.IGNORECASE)
_LEADING_THE = re.compile(r"^the\s+", re.IGNORECASE)


def _squash(text: str) -> str:
    return " ".join(str(text or "").split())


def clean_registered_name(raw: str) -> str:
    """NSE's name as headlines write it: "The Indian Hotels Company Limited"
    is "Indian Hotels Company", "Data Patterns (India) Limited" is "Data
    Patterns". A bracket would read as an alias to the matcher, and "(India)"
    as an alias matches every headline about India."""
    name = _PARENS.sub("", _squash(raw))
    name = _LEGAL_SUFFIX.sub("", name)
    return _LEADING_THE.sub("", name).strip()


def _words(name: str) -> List[str]:
    """Words for comparing two names: case dropped, split at spaces and at
    dots, so "Fin.Serv." is two words."""
    return [w for w in re.split(r"[\s.]+", name.lower()) if w]


def _abbreviates(short: str, word: str) -> bool:
    """Is ``short`` this word, or a cut-down form of it? A prefix ("Ene" for
    Energy, "B" for Bharat), or its first letter followed by more of its
    letters in order ("Devl" for Developers, "Ltd" for Limited)."""
    if word.startswith(short):
        return True
    rest = iter(word[1:])
    return short[0] == word[0] and all(ch in rest for ch in short[1:])


def repaired_name(stored: str, registered: Optional[str]) -> Optional[str]:
    """The registered name, if ``stored`` is it cut down; else None.

    Any bracketed alias on the stored name ("(CP PLUS)") is kept.
    """
    if not stored or not registered:
        return None
    aliases = "".join(f" ({a})" for a in _PARENS.findall(stored))
    core = _squash(_PARENS.sub("", stored))
    full = _words(_LEADING_THE.sub("", _PARENS.sub("", _squash(registered))))
    mine = _words(core)
    if not mine or len(mine) > len(full):
        return None
    if not all(_abbreviates(s, w) for s, w in zip(mine, full)):
        return None
    clean = clean_registered_name(registered)
    if not clean or core == clean:
        return None
    # Something was cut, or the legal suffix written out in full. Neither
    # is true of a complete shorter name, which someone chose.
    cut = any(s != w for s, w in zip(mine, full))
    if not cut and mine != full:
        return None
    return clean + aliases


def tidy_name(name: str, registered: Optional[str] = None) -> str:
    """The name to store: repaired to the registered name where it is that
    name cut down; else as given, without a legal suffix, which no headline
    needs ("Faze Three Limited" matches only where "Limited" is written)."""
    repaired = repaired_name(name, registered)
    if repaired:
        return repaired
    aliases = "".join(f" ({a})" for a in _PARENS.findall(name or ""))
    core = _squash(_PARENS.sub("", name or ""))
    return (_LEGAL_SUFFIX.sub("", core) or core) + aliases


def _holdings(watchlist) -> Iterable[Dict[str, Any]]:
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for stock in stocks:
            if isinstance(stock, dict) and stock.get("ticker"):
                yield stock


def repair_holding_names(
    watchlist, names: Dict[str, str]
) -> List[Tuple[str, str, str]]:
    """Repair every holding's stored name; returns (ticker, old, new) per
    change, for the log."""
    changed = []
    for stock in _holdings(watchlist):
        ticker = str(stock["ticker"]).upper()
        old = stock.get("name") or ""
        new = tidy_name(old, names.get(ticker)) if old else ""
        if new and new != old:
            stock["name"] = new
            changed.append((ticker, old, new))
    return changed


def name_rows(rows_by_key, names: Dict[str, str]) -> int:
    """The same repair for competitor rows ({key: [{ticker, name}, ...]}),
    as Screener's peer tables return them. Returns the count renamed."""
    renamed = 0
    for rows in (rows_by_key or {}).values():
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or not row.get("name"):
                continue
            new = tidy_name(row["name"], names.get(str(row.get("ticker", "")).upper()))
            if new != row["name"]:
                row["name"] = new
                renamed += 1
    return renamed


def looks_shortened(name: str) -> bool:
    """For a name NSE's list cannot check: a word cut with a dot ("Hold."),
    a run of initials ("B P C L") or a legal suffix. Initials with dots
    ("S.P.") and "Dr." are how names are written."""
    core = _squash(_PARENS.sub("", name or ""))
    if _LEGAL_SUFFIX.search(core):
        return True
    words = core.split()
    if sum(1 for w in words if len(w) == 1 and w.isalpha()) >= 3:
        return True
    for word in words:
        if not word.endswith("."):
            continue
        parts = [p for p in word.split(".") if p]
        if word.lower() in ("dr.", "st.") or all(len(p) == 1 for p in parts):
            continue
        return True
    return False


@functools.lru_cache(maxsize=4)
def _headline_names(path: str) -> Dict[str, Tuple[str, ...]]:
    try:
        with open(path, encoding="utf-8") as handle:
            body = json.load(handle)
    except (OSError, ValueError):
        return {}
    return {
        str(ticker).upper(): tuple(str(n) for n in forms if n)
        for ticker, forms in (body.get("names") or {}).items()
        if isinstance(forms, list)
    }


def headline_names(ticker: str) -> Tuple[str, ...]:
    """The shorter names headlines use for this ticker (headline_names.json)."""
    return _headline_names(HEADLINE_NAMES_PATH).get(str(ticker or "").upper(), ())


def found_only_by_ticker(
    watchlist, coverage: Dict[str, List[Dict[str, Any]]], minimum: int = 3
) -> List[Tuple[str, str, int]]:
    """Holdings whose counted news never names them except by ticker:
    (ticker, name, items). The name is then not how headlines write the
    company, and any headline without the ticker is lost. This is how the
    cut-down names were found."""
    from analysis.parsing import title_matches_company

    flagged = []
    for stock in _holdings(watchlist):
        ticker = str(stock["ticker"]).upper()
        name = stock.get("name") or ""
        heads = [
            i.get("headline") or ""
            for i in (coverage or {}).get(ticker) or []
            if i.get("status") == "counted"
        ]
        if len(heads) < minimum:
            continue
        forms = (name, *headline_names(ticker))
        if not any(
            title_matches_company(h, "", form) for h in heads for form in forms if form
        ):
            flagged.append((ticker, name, len(heads)))
    return flagged
