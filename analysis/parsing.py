import re
import urllib.parse
from logger import log

# Words that precede a PERSON's given name, never a company mention
# ("IBM CEO Arvind Krishna...", "Mr Arvind said...").
_PERSON_TITLES = {
    "mr",
    "mrs",
    "ms",
    "dr",
    "shri",
    "smt",
    "sri",
    "prof",
    "ceo",
    "cto",
    "cfo",
    "coo",
    "cmd",
    "md",
    "chairman",
    "chairperson",
    "founder",
    "president",
    "director",
    "minister",
    "justice",
    "governor",
}

# A capitalized word AFTER a company mention that keeps it a company mention.
# Generic corporate/market vocabulary — anything else capitalized following a
# mixed-case single-token match reads as a person's surname ("Arvind Krishna").
_CORP_CONTINUATIONS = {
    "ltd",
    "limited",
    "inc",
    "corp",
    "corporation",
    "india",
    "industries",
    "shares",
    "share",
    "stock",
    "stocks",
}

# Title-Case headlines capitalize verbs too ("Suzlon Wins 300MW Order"), so a
# capitalized headline verb after the match must not read as a surname.
_HEADLINE_VERBS = {
    "wins",
    "bags",
    "secures",
    "launches",
    "unveils",
    "announces",
    "reports",
    "posts",
    "zooms",
    "surges",
    "jumps",
    "falls",
    "gains",
    "rallies",
    "acquires",
    "partners",
    "expands",
    "confirms",
    "says",
    "plans",
    "eyes",
    "inks",
    "signs",
    "gets",
    "buys",
    "sells",
    "hits",
    "rises",
    "climbs",
    "slips",
    "drops",
    "soars",
    "delivers",
    "commissions",
    "starts",
    "begins",
    "opens",
}

_TOKEN_RE = re.compile(r"[A-Za-z0-9&.']+")


def _clean_token(token):
    return token.lower().rstrip(".").removesuffix("'s")


def title_matches_company(title, ticker, name):
    """Does this headline actually mention this company — not a person or a
    different company sharing a token with it?

    Replaces the bare substring matching that attributed "IBM CEO Arvind
    Krishna Confirms Quantum Computer..." to Arvind Ltd (and would let
    ticker LT match any headline containing "Ltd"). Rules:

    - Tokens must match whole-word, never substring.
    - The company name's core (before any parenthetical) matching as a
      consecutive multi-word phrase is accepted outright; a parenthetical
      alias ("(L&T)") is an additional candidate.
    - A single-token match (the ticker, or a one-word alias) is guarded:
      rejected when preceded by a person title (CEO/Mr/Shri/...), or when
      it appears mixed-case followed by a capitalized word that is not
      corporate vocabulary, part of this company's own name, or a headline
      verb — that shape is a person's given name + surname. An ALL-CAPS
      occurrence ("HAL", "ARVIND") always reads as a ticker, never a
      given name, so the surname guard doesn't apply to it.
    """
    tokens = _TOKEN_RE.findall(title or "")
    if not tokens:
        return False
    lowered = [_clean_token(t) for t in tokens]
    own_name_tokens = {_clean_token(t) for t in _TOKEN_RE.findall(name or "")}

    def _single_token_match(candidate):
        candidate = candidate.lower()
        for i, tok in enumerate(lowered):
            if tok != candidate:
                continue
            if i > 0 and lowered[i - 1] in _PERSON_TITLES:
                continue  # "CEO Arvind ..." — a person, not the company
            original = tokens[i]
            is_all_caps = original.isupper() and len(original) >= 2
            if not is_all_caps and i + 1 < len(tokens):
                nxt = tokens[i + 1]
                nxt_clean = _clean_token(nxt)
                if (
                    nxt[0].isupper()
                    and nxt_clean not in _CORP_CONTINUATIONS
                    and nxt_clean not in own_name_tokens
                    and nxt_clean not in _HEADLINE_VERBS
                ):
                    continue  # "Arvind Krishna" — given name + surname
            return True
        return False

    def _phrase_match(phrase_tokens):
        n = len(phrase_tokens)
        if n == 0:
            return False
        if n == 1:
            return _single_token_match(phrase_tokens[0])
        for i in range(len(lowered) - n + 1):
            if lowered[i : i + n] == phrase_tokens:
                return True
        return False

    # Company name core ("Larsen & Toubro" from "Larsen & Toubro (L&T)").
    name_core = (name or "").split("(")[0]
    if _phrase_match([_clean_token(t) for t in _TOKEN_RE.findall(name_core)]):
        return True

    # Parenthetical aliases: "(L&T)", "(PepsiCo)", "(CP PLUS)".
    for alias in re.findall(r"\(([^)]+)\)", name or ""):
        if _phrase_match([_clean_token(t) for t in _TOKEN_RE.findall(alias)]):
            return True

    return _single_token_match(ticker or "")


async def resolve_ticker_from_name_async(company_name, session):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(company_name)}&quotesCount=5"
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            if response.status == 200:
                data = await response.json()
                quotes = data.get("quotes", [])
                for q in quotes:
                    symbol = q.get("symbol", "")
                    if symbol.endswith(".NS"):
                        return (
                            symbol.split(".")[0],
                            q.get("longname") or q.get("shortname") or company_name,
                        )
                for q in quotes:
                    symbol = q.get("symbol", "")
                    if symbol.endswith(".BO"):
                        return (
                            symbol.split(".")[0],
                            q.get("longname") or q.get("shortname") or company_name,
                        )
    except Exception as e:
        log.error(f"Error resolving ticker for {company_name}: {e}")
    return None, None


def resolve_ticker_from_name(company_name, session=None):
    import requests

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(company_name)}&quotesCount=5"
    try:
        if session:
            r = session.get(url, headers=headers, timeout=10)
        else:
            r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            quotes = data.get("quotes", [])
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".NS"):
                    return (
                        symbol.split(".")[0],
                        q.get("longname") or q.get("shortname") or company_name,
                    )
            for q in quotes:
                symbol = q.get("symbol", "")
                if symbol.endswith(".BO"):
                    return (
                        symbol.split(".")[0],
                        q.get("longname") or q.get("shortname") or company_name,
                    )
    except Exception as e:
        log.error(f"Error resolving ticker for {company_name}: {e}")
    return None, None


def extract_row_values(soup, section_id, row_label_pattern):
    """Extracts the numeric cells of a labelled row from a Screener section.

    The label must be matched against the cell's TEXT, not its ``.string``:
    BeautifulSoup's ``string=`` matcher only fires when a tag contains a
    single bare text node, and Screener wraps expandable row labels (Sales,
    Net Profit, Borrowings, Promoters, ...) in a nested <button>, making
    ``.string`` None. That single quirk silently blanked every sales/debt/
    shareholding-derived metric in production while plain-label rows
    (OPM %, EPS) kept working — so this walks first-column cells and
    matches on ``get_text()`` instead.
    """
    sec = soup.find("section", id=section_id)
    if not sec:
        return []
    pattern = re.compile(row_label_pattern)
    for tr in sec.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        label_text = tds[0].get_text(" ", strip=True)
        if not pattern.search(label_text):
            continue
        vals = [
            td.get_text(strip=True).replace(",", "").replace("%", "")
            for td in tds[1:]
            if td.get_text(strip=True)
        ]
        numeric_vals = []
        for v in vals:
            try:
                numeric_vals.append(float(v))
            except ValueError:
                pass
        return numeric_vals
    return []


def calculate_trend(values, periods=4):
    if not values:
        return [0] * periods
    return values[-periods:]


def calculate_growth(val1, val2):
    if not val1 or val1 == 0:
        return 0.0
    return round(((val2 - val1) / abs(val1)) * 100, 2)
