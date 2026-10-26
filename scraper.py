import asyncio
import aiohttp
import feedparser
import datetime  # noqa: F401  (referenced via patch("scraper.datetime...") in tests)
from bs4 import BeautifulSoup
import html
import urllib.parse
import re
from logger import log
from config import SECTOR_QUERIES, GLOBAL_EVENT_QUERIES, PLI_SCHEMES
from providers.rss import fetch_query_feed_async
from providers.nse_announcements import fetch_filings as nse_fetch_filings
from providers import bse_announcements
from providers.bse_announcements import fetch_filings as bse_fetch_filings
from analysis.parsing import title_matches_company


async def fetch_all_feeds_async():
    """Fetches news from Google News RSS for all sectors asynchronously."""
    log.info("Initializing RSS Aggregation engine (Async)...")

    today_brief = {}
    tasks = []

    async with aiohttp.ClientSession() as session:
        for sector, queries in SECTOR_QUERIES.items():
            today_brief[sector] = []
            for query in queries:
                tasks.append(fetch_query_feed_async(session, sector, query))

        results = await asyncio.gather(*tasks)

    sector_results = {sector: [] for sector in SECTOR_QUERIES}
    for sec, news_list in results:
        sector_results[sec].extend(news_list)

    for sector in SECTOR_QUERIES:
        sector_news = []
        seen_titles = set()
        for cleaned in sector_results[sector]:
            title_lower = cleaned["title"].lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                sector_news.append(cleaned)

        # Newest first. This used to sort "Positive" sentiment first before
        # keeping four, so an upbeat-sounding story displaced a newer, more
        # negative one before anyone saw it — a selection bias applied by a
        # tone score that is not even a reading of policy direction.
        from analysis.event_evidence import article_date

        sector_news.sort(key=lambda x: article_date(x.get("date")) or "", reverse=True)
        today_brief[sector] = sector_news[:4]  # Store top 4 articles per sector
        log.info(
            f"Aggregated {len(today_brief[sector])} feed items for sector: {sector}"
        )

    return today_brief


_NAVIGATION_MARKS = ("menu", "nav", "header", "footer", "breadcrumb")


def _is_navigation(li):
    """A list item that is a page's menu rather than a release's content.

    A real page lists its menus in the same tags as a release lists its
    beneficiaries, and every one of them would otherwise be read as a
    company. A menu item is a link, or sits in a nav, header, footer or menu
    block; a list of beneficiaries in a release is plain text. Decided on
    structure alone, because PIB's markup could not be checked: the
    development sandbox's proxy refuses pib.gov.in.
    """
    link = li.find("a")
    if link is not None and link.get_text(strip=True) == li.get_text(strip=True):
        return True
    for parent in li.parents:
        if parent.name in ("nav", "header", "footer"):
            return True
        marks = " ".join(
            [str(parent.get("id") or "")] + list(parent.get("class") or [])
        ).lower()
        if any(m in marks for m in _NAVIGATION_MARKS):
            return True
    return False


# --- PLI beneficiaries in a release's text -----------------------------------
#
# A name is taken only with evidence that it is a company: a legal suffix
# ("Limited", "Pvt. Ltd.", "LLP"), PIB's own "Companies such as A, B and C", or
# a table column or list that is plainly a list of names. A capitalised phrase
# alone is not enough. PIB's menus, ministries and scheme names are
# capitalised too, and the parser that took every one of them, and any phrase
# ending in "Industries" or "Electronics", reported "Heavy Industries" and
# "Food Processing Industries" as companies. It also read "Dr. Reddy's
# Laboratories Limited" as "Laboratories Limited", because it allowed no full
# stop or apostrophe inside a name.

# One word of a name: capitalised, or a brand such as "ideaForge", with the
# apostrophe and ampersand of "Dr. Reddy's" and "M&M"; an abbreviation; or a
# word in brackets, as in "Dixon Technologies (India) Limited". Only an
# abbreviation ends in a stop, so a name never runs on into the next
# sentence: "... by Aurobindo. Kinvan Private Limited has ...".
_ABBREVIATION = (
    r"(?:(?:Dr|Mr|Mrs|Ms|Pvt|Co|Corp|Inc|Bros|St|Jr|Sr|Mfg|Intl|Ltd|LTD)\."
    r"|(?:[A-Z]\.)+)"
)
_NAME_WORD = (
    rf"(?:{_ABBREVIATION}|[A-Z][\w'’&-]*|[a-z]+[A-Z][\w'’&-]*" r"|\([A-Z][\w'’.&-]*\))"
)
_LEGAL_WORDS = r"(?:Limited|LIMITED|Ltd|LTD|LLP)"
_LEGAL_SUFFIX = (
    r"(?:(?:Private|PRIVATE|Pvt|PVT)(?:\.\s*|\s+)(?:Limited|LIMITED|Ltd|LTD)\.?"
    r"|(?:Limited|LIMITED|Ltd|LTD)\.?|LLP)"
)
# A name that ends in a legal suffix. Its words may not themselves be one, so
# "Lupin Limited and Cipla Limited" is two names.
_COMPANY_RE = re.compile(
    rf"(?<![\w'’.&-])(?!{_LEGAL_WORDS}\b){_NAME_WORD}"
    rf"(?:\s+(?:(?!{_LEGAL_WORDS}\b){_NAME_WORD}|&|of))*?"
    rf"\s+{_LEGAL_SUFFIX}(?!\w)"
)
_ENDS_LEGAL_RE = re.compile(rf"\s{_LEGAL_SUFFIX}$")
_LEGAL_WORD_RE = re.compile(r"(?i:private|pvt|limited|ltd|llp)")
# "Companies such as Lyfius Pharma, Kinvan Private Limited and ...": PIB names
# beneficiaries this way, often without a suffix ("GE Healthcare, Siemens").
_SUCH_AS_RE = re.compile(
    r"\b(?:companies|firms|manufacturers|players|beneficiaries|applicants)\s+"
    r"(?:such\s+as|like|including|namely)\s+",
    re.I,
)
_LISTED_NAME_RE = re.compile(rf"{_NAME_WORD}(?:\s+(?:{_NAME_WORD}|&|of))*")
_LIST_SEP_RE = re.compile(r"\s*,\s*(?:and\s+)?|\s+and\s+")
# What introduces a list of names that carry no suffix.
_LIST_CUE_RE = re.compile(
    r"\b(?:companies|applicants|beneficiaries|firms|manufacturers)\b", re.I
)
_NAME_HEADER_RE = re.compile(
    r"\b(?:name|applicant|company|companies|beneficiar\w*|firm|manufacturer)s?\b",
    re.I,
)
_MS_RE = re.compile(r"\bM/[sS]\b\.?\s*")
_NUMBERING_RE = re.compile(r"^(?:\(?\d{1,3}[.)]|\(?[ivx]{1,4}\)|[a-z]\))\s+")
_ABBREVIATION_RE = re.compile(r"\s*\([A-Z0-9&.\- ]{2,12}\)$")
# Words that begin a sentence rather than a name: "Notably Kinvan ..."
_LEAD_WORDS = {
    "the", "this", "these", "those", "its", "their", "notably", "also",
    "further", "furthermore", "moreover", "besides", "additionally",
    "similarly", "meanwhile", "thus", "here", "under", "through", "with", "by",
    "for", "from", "in", "at", "on", "of", "and", "as", "among", "amongst",
    "including", "while", "after", "companies", "company", "firms", "firm",
    "beneficiaries", "beneficiary", "applicants", "applicant", "messrs",
    "shri",
}  # fmt: skip
# A name with any of these words is the government's, not a company's.
_OFFICIAL_WORDS = {
    "ministry", "department", "scheme", "schemes", "pli", "government", "govt",
    "programme", "mission", "crore", "lakh", "incentive", "incentives",
    "minister", "secretary", "bureau", "cabinet", "parliament", "sabha",
}  # fmt: skip
# Read as a name by the shape of the words, and not one.
_NOT_NAMES = {
    "msme", "msmes", "startup", "startups", "psu", "psus", "cpse", "cpses",
    "oem", "oems", "india", "indian", "total", "grandtotal", "name", "others",
    "sno", "srno",
}  # fmt: skip
_BLOCK_TAGS = (
    "p", "div", "li", "td", "th", "tr", "table", "ul", "ol", "h1", "h2", "h3",
    "h4", "h5", "h6", "section", "article", "blockquote", "center",
)  # fmt: skip
_SCHEME_KEYS = sorted(
    ((key, label) for label, keys, _ in PLI_SCHEMES for key in keys),
    key=lambda pair: -len(pair[0]),
)
_SCHEME_RE = re.compile(
    r"\b(?P<key>"
    + "|".join(re.escape(key) for key, _ in _SCHEME_KEYS)
    + r")(?:s|es)?\b",
    re.I,
)
_SCHEME_LABEL = {key: label for key, label in _SCHEME_KEYS}
_SCHEME_SECTORS = {label: list(sectors) for label, _, sectors in PLI_SCHEMES}
# A scheme named as the scheme: "PLI Scheme for Bulk Drugs", "the textile
# PLI". Any other mention may be in passing ("... a resilient pharmaceutical
# supply chain"), or inside a company's name ("Lyfius Pharma").
_SCHEME_FOR_RE = re.compile(r"\b(?:PLI|incentive)\s+(?:scheme\s+)?for\s+", re.I)
_SCHEME_PLI_RE = re.compile(
    r"\b(?P<key>"
    + "|".join(re.escape(key) for key, _ in _SCHEME_KEYS)
    + r")(?:s|es)?\s+PLI\b",
    re.I,
)


# How far into a line a scheme may be named and still be what the line is
# about: "a) PLI Scheme for ...", "The Government approved the PLI Scheme for".
_OPENS_LINE = 40


def _schemes_named(text):
    """``(position, scheme)`` for each PLI scheme ``text`` names, in order."""
    return [
        (m.start(), _SCHEME_LABEL[m.group("key").lower()])
        for m in _SCHEME_RE.finditer(text or "")
    ]


def _schemes_meant(text):
    """``(position, scheme)`` for each scheme ``text`` names as the scheme."""
    text = text or ""
    found = []
    for m in _SCHEME_FOR_RE.finditer(text):
        named = _SCHEME_RE.search(text, m.end(), m.end() + 80)
        if named:
            found.append((m.start(), _SCHEME_LABEL[named.group("key").lower()]))
    found += [
        (m.start(), _SCHEME_LABEL[m.group("key").lower()])
        for m in _SCHEME_PLI_RE.finditer(text)
    ]
    return sorted(found)


# Marks where one block of a page ends. Not a newline: the line breaks in the
# HTML's source are spaces to a reader, and fall inside names.
_BLOCK_END = "\x1e"


def _text_lines(soup):
    """The text a block at a time: a name never runs from one paragraph,
    cell or heading into the next, as it would in the page's text read
    whole."""
    copy = BeautifulSoup(str(soup), "lxml")
    for br in copy.find_all("br"):
        br.replace_with(_BLOCK_END)
    for tag in copy.find_all(_BLOCK_TAGS):
        tag.insert_before(_BLOCK_END)
        tag.append(_BLOCK_END)
    lines = (" ".join(part.split()) for part in copy.get_text().split(_BLOCK_END))
    return [line for line in lines if line]


def _clean_name(raw):
    name = _MS_RE.sub("", " ".join(str(raw or "").split()))
    name = _NUMBERING_RE.sub("", name)
    name = _ABBREVIATION_RE.sub("", name).strip(" ,;:-–")
    words = name.split()
    while words and words[0].lower().strip(".,") in _LEAD_WORDS:
        words.pop(0)
    while words and words[-1].lower() in ("of", "&", "and"):
        words.pop()
    name = " ".join(words)
    if name.endswith(".") and not re.search(r"\b(?:Ltd|Pvt|Co|Inc|Corp)\.$", name):
        name = name[:-1]
    return name


def _name_key(name):
    """A name without its case, punctuation, spaces and legal suffix, so
    "AurobindoPharma Limited" and "Aurobindo Pharma Ltd." are one company."""
    plain = str(name or "").lower().replace("’", "").replace("'", "")
    return "".join(
        word
        for word in re.findall(r"[a-z0-9]+", plain.replace("&", " and "))
        if word not in ("private", "pvt", "limited", "ltd", "llp", "the")
    )


def _is_company(name):
    words = name.split()
    if not words or not 2 <= len(name) <= 80 or len(words) > 10:
        return False
    if not (name[0].isupper() or re.match(r"[a-z]+[A-Z]", name)):
        return False
    if {w.lower().strip(".,()") for w in words} & _OFFICIAL_WORDS:
        return False
    if all(_LEGAL_WORD_RE.fullmatch(w.strip(".,")) for w in words):
        return False
    return _name_key(name) not in _NOT_NAMES


def _name_like(text):
    """Whether a cell or list item has the shape of a name: a few words,
    each capitalised or a joining word."""
    words = text.split()
    if not 1 <= len(words) <= 8 or re.search(r"[:;?!]", text):
        return False
    return all(re.fullmatch(_NAME_WORD, w) or w in ("&", "of", "and") for w in words)


def _table_names(table):
    """The cells of a table's name column, found by its heading. A table
    whose first rows name no such column is layout, not a list of
    beneficiaries: PIB sets its ministry's name in one."""
    rows = table.find_all("tr")
    column = None
    # The heading can follow a title row ("Annexure", "List of applicants").
    for at, row in enumerate(rows[:3]):
        heads = [c.get_text(" ", strip=True) for c in row.find_all(["th", "td"])]
        column = next(
            (
                i
                for i, h in enumerate(heads)
                if len(heads) > 1 and len(h) <= 40 and _NAME_HEADER_RE.search(h)
            ),
            None,
        )
        if column is not None:
            break
    if column is None:
        return []
    names = []
    for row in rows[at + 1 :]:
        cells = row.find_all(["td", "th"])
        if len(cells) > column:
            name = _clean_name(cells[column].get_text(" ", strip=True))
            if name and _name_like(name):
                names.append(name)
    return names


def _list_names(soup):
    """Names from lists that are lists of names: mostly name-shaped, and
    either one of them carries a legal suffix or the text before the list
    says what it lists ("... the following applicants:")."""
    names = []
    for block in soup.find_all(["ul", "ol"]):
        items = [
            li for li in block.find_all("li", recursive=False) if not _is_navigation(li)
        ]
        texts = [_clean_name(li.get_text(" ", strip=True)) for li in items]
        shaped = [t for t in texts if t and _name_like(t)]
        if not shaped or len(shaped) * 2 < len(texts):
            continue
        before = block.find_previous_sibling()
        cue = before.get_text(" ", strip=True)[-300:] if before else ""
        if any(_ENDS_LEGAL_RE.search(t) for t in shaped) or _LIST_CUE_RE.search(cue):
            names += shaped
    return names


def _names_in_line(line):
    """``(position, name)`` for each company a line of text names."""
    found = [(m.start(), m.group(0)) for m in _COMPANY_RE.finditer(line)]
    for cue in _SUCH_AS_RE.finditer(line):
        at = cue.end()
        while True:
            item = _LISTED_NAME_RE.match(line, at)
            if not item:
                break
            found.append((item.start(), item.group(0)))
            sep = _LIST_SEP_RE.match(line, item.end())
            if not sep:
                break
            at = sep.end()
    return found


def _extract_pli_data_from_html(html, title, published_date="", title_only=False):
    """PLI beneficiaries a release names, each with the scheme it is under.

    The scheme is the title's when the title names one as the scheme ("PLI
    Scheme for Bulk Drugs for Resilient Pharmaceutical Supply Chain" is about
    bulk drugs), or names only one. A release about several ("... India's
    Pharmaceutical, Bulk Drugs and Medical Devices ...") gives each company
    the scheme of the section it is in, a line that opens by naming the scheme
    ("b) PLI Scheme for Pharmaceuticals"); failing that, the last scheme the
    text mentioned, a company's own name aside. A scheme named deep in a
    paragraph is a passing reference ("... APIs not covered under the Bulk
    Drugs PLI Scheme") and opens no section. ``title_only`` reads the scheme from the title alone, for
    a headline whose summary is other outlets' headlines. ``scheme_sectors``
    is the watchlist sectors that compete under that scheme, or None when no
    scheme could be told.
    """
    soup = BeautifulSoup(html or "", "lxml")
    lines = [_MS_RE.sub("", line) for line in _text_lines(soup)]
    text = " ".join(lines)
    in_title = [label for _, label in _schemes_named(title)]
    meant = [label for _, label in _schemes_meant(title)]
    whole = (meant or (in_title if len(set(in_title)) == 1 else [None]))[0]
    in_text = [label for _, label in _schemes_meant(text) + _schemes_named(text)]
    first = whole or (in_title or ([] if title_only else in_text) or [None])[0]
    scheme = (
        "PLI 2.0" if "2.0" in (title or "") or "2.0" in text[:500] else "PLI Scheme"
    )

    found = [(n, first) for t in soup.find_all("table") for n in _table_names(t)]
    found += [(n, first) for n in _list_names(soup)]
    meant_before = mentioned_before = None
    for line in lines:
        names = _names_in_line(line)
        spans = [(at, at + len(raw)) for at, raw in names]
        meant = [(pos, lab) for pos, lab in _schemes_meant(line) if pos <= _OPENS_LINE]
        mentioned = [
            (pos, label)
            for pos, label in _schemes_named(line)
            if not any(start <= pos < end for start, end in spans)
        ]
        for at, raw in names:
            label = first if title_only else whole
            for marks, carried in (
                (meant, meant_before),
                (mentioned, mentioned_before),
            ):
                if label is None and not title_only:
                    before = [lab for pos, lab in marks if pos < at]
                    label = before[-1] if before else carried
            found.append((_clean_name(raw), label or first))
        meant_before = meant[-1][1] if meant else meant_before
        mentioned_before = mentioned[-1][1] if mentioned else mentioned_before

    companies, seen = [], set()
    for name, label in found:
        key = _name_key(name)
        if not key or key in seen or not _is_company(name):
            continue
        seen.add(key)
        companies.append(
            {
                "name": name,
                "sector": label or "Manufacturing",
                "scheme": scheme,
                "date": published_date,
                "scheme_sectors": _SCHEME_SECTORS[label] if label else None,
            }
        )
    return companies


# Company names per search: few enough that one busy name (Apple, Google)
# does not take every result, enough to cover the graph in a few requests.
_COMPANY_BATCH = 8
# Results kept per company search; the vocabulary searches keep 5.
_COMPANY_RESULTS = 8
# What a company search looks for: its deals, and how its business is doing.
# Results and demand matter as much as deals — "Corning sales fall" is what
# reaches the Optiemus venture.
_COMPANY_TERMS = (
    "deal OR partnership OR investment OR order OR expansion OR supply OR "
    "sales OR revenue OR profit OR results OR guidance OR demand OR "
    "layoffs OR shutdown"
)


def watched_company_names(graph, holdings=(), extra=()):
    """Every company the graph ties to what we hold, plus ``extra``.

    The demand anchors, every holding's partners and rivals, and whoever else
    is being watched (new entrants the radar flagged). Holdings themselves
    are left out: their own news is searched for by sector.
    """
    held = {str(t).upper() for t in holdings}
    names = {str(n) for n in extra}
    for edge in (graph or {}).get("edges", []):
        if edge.get("type") == "anchor_demand":
            names.add(str(edge.get("src")))
        elif edge.get("type") in ("partner", "competitor"):
            names |= {
                str(end)
                for end in (edge.get("src"), edge.get("dst"))
                if str(end).upper() not in held
            }
    unique = {}
    for name in names:
        name = name.strip()
        if len(name) >= 3:
            unique.setdefault(name.lower(), name)
    return sorted(unique.values(), key=str.lower)


def company_queries(names, batch=_COMPANY_BATCH):
    """News searches covering ``names``, ``batch`` to a search.

    There used to be one search, of the first 12 anchors alphabetically:
    Nvidia, TSMC, Samsung, Micron, Microsoft and Qualcomm were never searched,
    and no holding's partner was searched at all.
    """
    return [
        "("
        + " OR ".join(f'"{n}"' for n in names[i : i + batch])
        + f") AND ({_COMPANY_TERMS})"
        for i in range(0, len(names), batch)
    ]


async def fetch_global_event_feeds_async(session, holdings=(), watched=()):
    """Global market-event headlines: supply-chain shocks, big tie-ups, and
    the news of companies tied to our holdings, whose second-order impact
    lands on them.

    Queries are entity-free vocabulary from config plus company searches
    assembled at runtime from the entity graph (watched_company_names) — so
    which companies get watched is data, never code. Enhancement channel:
    fail-safe, capped, and never blocks the briefing.
    """
    from analysis.entity_graph import load_entity_graph
    from utils import fetch_text_async

    queries = [(q, 5) for q in GLOBAL_EVENT_QUERIES]
    names = watched_company_names(load_entity_graph(), holdings, watched)
    queries += [(q, _COMPANY_RESULTS) for q in company_queries(names)]

    items = []
    seen = set()

    async def _fetch_query(query):
        try:
            encoded = urllib.parse.quote(f"{query} when:3d")
            url = (
                f"https://news.google.com/rss/search?q={encoded}"
                f"&hl=en-IN&gl=IN&ceid=IN:en"
            )
            status, xml_data = await fetch_text_async(session, url, timeout=15)
            if status == 200:
                return feedparser.parse(xml_data)
        except Exception as e:
            log.error(f"Global event feed query failed: {e}")
        return None

    # ⚡ Bolt Optimization: Batch fetch global event feed queries concurrently to prevent event-loop blocking from sequential IO.
    feeds = await asyncio.gather(*(_fetch_query(q) for q, _ in queries))

    for feed, (_, keep) in zip(feeds, queries):
        if not feed:
            continue
        for entry in feed.entries[:keep]:
            title = entry.get("title", "").split(" - ")[0].strip()
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            items.append(
                {
                    "title": title,
                    "link": entry.get("link", ""),
                    "date": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "News"),
                }
            )

    log.info(
        f"Global event feed: {len(items)} headlines collected "
        f"({len(names)} companies searched in {len(queries) - len(GLOBAL_EVENT_QUERIES)} "
        f"batch(es))."
    )
    return items


# Headlines kept per state per run. The query is broad on purpose (any policy
# word, any of our sector words), so the reader, not the query, decides what
# is policy.
STATE_ITEMS_PER_QUERY = 6
# Google News ignores "when:7d" for these queries: the first live run got 54
# headlines, 39 of them older than the 45-day retention, so stale stories took
# the slots meant for new ones. Age is checked here, before the slots fill.
STATE_MAX_AGE_DAYS = 14


async def fetch_state_policy_async(session, today=None):
    """State-government headlines, a few simple Google News searches per state.

    Each item carries ``feed_state``: the state whose search found it. That is
    where the search looked, not whose policy it is — the article can mention
    a state the headline does not — so jurisdiction is read from the headline
    itself (analysis/policy_impact.state_of). Items from a state's industrial
    policy searches (config.STATE_INDUSTRY_QUERIES) also carry
    ``feed_kind: "industry"``. Fail-safe like every feed: a search that fails
    contributes nothing and the run continues.
    """
    from analysis.event_evidence import article_date
    from config import STATE_INDUSTRY_QUERIES, STATE_POLICY_QUERIES
    from utils import fetch_text_async

    today = today or datetime.date.today()
    cutoff = (today - datetime.timedelta(days=STATE_MAX_AGE_DAYS)).isoformat()

    async def _fetch(state, kind, query):
        try:
            url = (
                "https://news.google.com/rss/search?q="
                f"{urllib.parse.quote(query + ' when:7d')}&hl=en-IN&gl=IN&ceid=IN:en"
            )
            status, xml_data = await fetch_text_async(session, url, timeout=15)
            if status == 200:
                return state, kind, feedparser.parse(xml_data)
            log.info(f"State policy feed ({state}, {query}): HTTP {status}.")
        except Exception as e:
            log.error(f"State policy feed ({state}, {query}) failed: {e}")
        return state, kind, None

    searches = [
        (state, kind, query)
        for kind, table in (
            ("general", STATE_POLICY_QUERIES),
            ("industry", STATE_INDUSTRY_QUERIES),
        )
        for state, queries in table.items()
        for query in queries
    ]
    results = await asyncio.gather(*(_fetch(*s) for s in searches))
    # One pool per state and kind, so a state's searches share its slots and
    # its industrial-policy searches have their own.
    pools: dict = {}
    for state, kind, feed in results:
        if feed:
            pools.setdefault((state, kind), []).extend(feed.entries)
    items, seen, per_state, stale, industry = [], set(), {}, 0, 0
    for (state, kind), entries in pools.items():
        fresh = []
        for entry in entries:
            date = article_date(entry.get("published")) or ""
            if date >= cutoff:
                fresh.append((date, entry))
            else:
                stale += 1
        fresh.sort(key=lambda d: d[0], reverse=True)
        taken = 0
        for _, entry in fresh:
            if taken >= STATE_ITEMS_PER_QUERY:
                break
            title = entry.get("title", "").split(" - ")[0].strip()
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            taken += 1
            per_state[state] = per_state.get(state, 0) + 1
            if kind == "industry":
                industry += 1
            items.append(
                {
                    "title": title,
                    "link": entry.get("link", ""),
                    "date": entry.get("published", ""),
                    "source": entry.get("source", {}).get("title", "News"),
                    "feed_state": state,
                    **({"feed_kind": "industry"} if kind == "industry" else {}),
                }
            )
    states = dict.fromkeys([*STATE_POLICY_QUERIES, *STATE_INDUSTRY_QUERIES])
    log.info(
        f"State policy feed: {len(items)} headline(s), {industry} from "
        "industrial-policy searches — "
        + ", ".join(f"{s} {per_state.get(s, 0)}" for s in states)
        + f"; {stale} older than {STATE_MAX_AGE_DAYS} days skipped."
    )
    return items


# Releases read from PIB per run, and the months of PIB's list of releases
# asked for: this one and the last, so a run on the 1st still sees 30 days. A
# month's list is about a megabyte and a release about 130 KB, and PIB is a
# government site: each is asked for in turn, never in parallel.
MAX_PLI_RELEASES = 8
PIB_MONTHS = 2
# Release fetches that may fail before PIB is left alone for the run.
_PIB_FAILURES = 2
# Names looked up on Yahoo at once.
_RESOLVE_AT_ONCE = 5
# A release about an incentive scheme: PLI, and the newer schemes run the
# same way ("Electronics Component Manufacturing Scheme").
_PLI_TITLE_RE = re.compile(
    r"\bpli\b|production[\s-]+linked\s+incentive|\bmanufacturing\s+scheme\b", re.I
)
# What a title says when the release may name a scheme's beneficiaries.
_SCHEME_NEWS_RE = re.compile(
    r"\b(?:schemes?|incentives?|approv\w*|selected|beneficiar\w*)\b", re.I
)


def pli_search_url():
    """The Google News search that says which PLI releases PIB has posted."""
    query = (
        'site:pib.gov.in "PLI" AND ("provisionally selected" OR "approved" OR '
        '"incentive scheme" OR "applications approved")'
    )
    return (
        "https://news.google.com/rss/search?q="
        f"{urllib.parse.quote(f'{query} when:30d')}&hl=en-IN&gl=IN&ceid=IN:en"
    )


def _headline_text(title, summary):
    """The headline and summary as plain text.

    Google News summaries are HTML, and for a story several outlets carried
    they hold a list of the related headlines, each of which the parser
    would read as a company. Without the markup only the parser's
    company-suffix match ("... Ltd", "... Limited") can find a name.
    """
    # ⚡ Bolt Optimization: Use regex and html.unescape for massive speedups (~50x-100x)
    # when merely stripping tags from strings like RSS summaries, avoiding BeautifulSoup's DOM parsing overhead.
    plain = html.unescape(re.sub(r"<[^>]+>", " ", summary)) if summary else ""
    # Consolidate multiple spaces that replacing tags might have introduced
    plain = re.sub(r"\s+", " ", plain).strip()
    return f"{title} {plain}".strip()


def _stories(entries):
    """One story per headline, newest first, with each day Google dated it.

    Google carries some PIB stories twice, weeks apart, under one title.
    """
    from providers import pib

    stories = {}
    for entry in entries:
        title = pib.strip_site(entry.get("title", ""))
        key = " ".join(pib.title_words(title))
        if not key:
            continue
        story = stories.setdefault(
            key,
            {
                "title": title,
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "published": entry.get("published", ""),
                "days": set(),
            },
        )
        day = pib.ist_day(entry.get("published"))
        if day:
            story["days"].add(day)
    return sorted(
        stories.values(),
        key=lambda s: max(s["days"], default=datetime.date.min),
        reverse=True,
    )


def _relevance(title):
    """2 for a release about an incentive scheme, 1 for one that may name a
    scheme's beneficiaries, 0 for the rest: Google's search also finds PIB
    pages that mention PLI in passing ("India's GDP Performance")."""
    if _PLI_TITLE_RE.search(title):
        return 2
    return int(bool(_SCHEME_RE.search(title) or _SCHEME_NEWS_RE.search(title)))


async def _locate_on_pib(stories, index, today):
    """The releases to read, from PIB's lists of this month's and last
    month's releases: each story's own, found by its title whatever day
    Google gave it, and every release PIB titles as an incentive scheme's.

    Returns them most relevant and then newest first (PRIDs rise with time);
    the stories not on the lists, whose names can come only from their
    headlines; and how many the lists had that are about no scheme, which are
    not read.
    """
    from providers import pib

    listed = {}
    for first in pib.months_to(today, PIB_MONTHS):
        releases = await index.releases_in(first)
        if releases is None:
            break
        for title, prid, link in releases:
            listed.setdefault(prid, (title, link, pib.title_words(title)))
    chosen, unfound = {}, []
    for story in stories:
        want = pib.title_words(story["title"])
        match = None
        if len(want) >= 3:
            match = next(
                (
                    p
                    for p, (_, _, words) in listed.items()
                    if pib.same_words(want, words)
                ),
                None,
            )
        if match is None:
            unfound.append(story)
            continue
        title, link, _ = listed[match]
        chosen.setdefault(match, {"prid": match, "title": title, "link": link})
        chosen[match].setdefault("story", story)
    for prid, (title, link, _) in listed.items():
        if prid not in chosen and _PLI_TITLE_RE.search(title):
            chosen[prid] = {"prid": prid, "title": title, "link": link}
    ranked = sorted(
        chosen.values(),
        key=lambda r: (_relevance(r["title"]), int(r["prid"])),
        reverse=True,
    )
    # "12 Years of Make in India" mentions PLI, and its few names are filed
    # under whichever scheme the page last mentioned.
    general = [r for r in ranked if not _relevance(r["title"])]
    unfound += [r["story"] for r in general if "story" in r]
    return [r for r in ranked if _relevance(r["title"])], unfound, len(general)


def _held(watchlist, registered):
    """The keys of every name and ticker we hold, and the NSE symbols."""
    keys, tickers = set(), set()
    for stocks in watchlist.values():
        for stock in stocks if isinstance(stocks, list) else []:
            if not isinstance(stock, dict):
                continue
            ticker = str(stock.get("ticker") or "").upper()
            for name in (stock.get("name"), ticker, registered.get(ticker)):
                if name:
                    keys.add(_name_key(name))
            if ticker:
                tickers.add(ticker)
    keys.discard("")
    return keys, tickers


def _is_held(key, held_keys):
    """Whether a name's key is a holding's: the same, or a holding's name
    with more after it, as "Dixon Technologies (India)" is "Dixon
    Technologies". Short keys must match whole."""
    return key in held_keys or any(len(k) >= 6 and key.startswith(k) for k in held_keys)


async def scrape_pib_pli_approvals_async(
    session, watchlist, registered=None, today=None
):
    """PLI beneficiaries named in PIB releases from the last 30 days.

    Google News says which releases there were, but every link it gives
    leads to its own page, not to pib.gov.in, and this returned nothing on
    every run from at least mid-September 2026. Each story is now found by
    its title on PIB's own list of this month's and last month's releases,
    and read from PIB: the release's text only, not the site's menus and
    sidebars. Every release on those lists that PIB titles as an incentive
    scheme's is read too. A story the lists do not have is read from its
    headline, which names a company only now and then.

    A beneficiary is reported only under a scheme some holding works in
    (config.PLI_SCHEMES), and not when it is a holding: a holding's own
    approval is not a competitor. ``registered`` is NSE's registered names by
    symbol, which settle most tickers without asking Yahoo.
    """
    from analysis.event_evidence import article_date
    from providers import pib
    from utils import fetch_text_async

    if registered is None:
        from providers.isin_master import load_registered_names

        registered = load_registered_names()
    log.info("Scraping PIB for PLI approval announcements (Async)...")
    search_note = ""
    entries = []
    try:
        status, xml_data = await fetch_text_async(session, pli_search_url(), timeout=15)
        if status != 200:
            search_note = f"search returned HTTP {status}"
        else:
            entries = feedparser.parse(xml_data).entries
    except Exception as e:
        log.error(f"Error scraping PIB PLI approvals: {e}")
        search_note = f"search failed ({type(e).__name__})"
    stories = _stories(entries)

    index = pib.MonthIndex(session)
    ranked, unread, general = await _locate_on_pib(
        stories, index, today or pib.today_in_india()
    )
    to_read = ranked[:MAX_PLI_RELEASES]
    unread += [r["story"] for r in ranked[MAX_PLI_RELEASES:] if "story" in r]

    found, from_releases, failed, no_text = [], 0, 0, 0
    for item in to_read:
        story = item.get("story")
        if failed >= _PIB_FAILURES:
            unread += [story] if story else []
            continue
        try:
            status, page = await fetch_text_async(
                session, pib.release_url(item["prid"]), timeout=20
            )
        except Exception as ex:
            status, page = None, ""
            log.warning(
                f"PLI release {item['prid']} fetch failed: {type(ex).__name__}: {ex}"
            )
        if status != 200:
            failed += 1
            if status is not None:
                log.warning(f"PLI release {item['prid']}: HTTP {status}.")
            unread += [story] if story else []
            continue
        release = pib.read_release(page)
        if release is None:
            no_text += 1
            unread += [story] if story else []
            continue
        title = release["title"] or item["title"]
        names = _extract_pli_data_from_html(release["html"], title, release["date"])
        from_releases += 1
        for comp in names:
            comp.update(announcement=title, link=item["link"], found_in="release page")
        found += names

    for story in unread:
        names = _extract_pli_data_from_html(
            _headline_text(story["title"], story["summary"]),
            story["title"],
            article_date(story["published"]) or "",
            title_only=True,
        )
        for comp in names:
            comp.update(
                announcement=story["title"], link=story["link"], found_in="headline"
            )
        found += names

    # Only under a scheme a holding works in, once each, and not a holding.
    held_keys, held_tickers = _held(watchlist, registered)
    by_key = {}
    for symbol, name in registered.items():
        by_key.setdefault(_name_key(name), set()).add(symbol)
    sectors_held = set(watchlist)
    off_scheme, no_scheme, seen, candidates = {}, 0, set(), []
    for comp in found:
        scheme_sectors = comp.pop("scheme_sectors", None)
        if scheme_sectors is None:
            # Under no scheme it names, nothing says the company competes
            # with a holding: PIB's appeal to bank employees came up in the
            # PLI search, and a headline can name a company and no scheme.
            no_scheme += 1
            continue
        mine = [s for s in scheme_sectors if s in sectors_held]
        if not mine:
            off_scheme[comp["sector"]] = off_scheme.get(comp["sector"], 0) + 1
            continue
        comp["watch_sectors"] = mine
        key = _name_key(comp["name"])
        if key in seen or _is_held(key, held_keys):
            continue
        seen.add(key)
        symbols = by_key.get(key, set())
        comp["ticker"] = next(iter(symbols)) if len(symbols) == 1 else None
        if comp["ticker"] in held_tickers:
            continue
        candidates.append(comp)

    from analysis.parsing import resolve_ticker_from_name_async

    gate = asyncio.Semaphore(_RESOLVE_AT_ONCE)

    async def _resolve(comp):
        if comp["ticker"]:
            return comp["ticker"]
        async with gate:
            ticker, _ = await resolve_ticker_from_name_async(comp["name"], session)
        return ticker

    tickers = await asyncio.gather(*(_resolve(c) for c in candidates))
    deduped = []
    for comp, ticker in zip(candidates, tickers):
        if ticker and str(ticker).upper() in held_tickers:
            continue
        comp["ticker"] = ticker
        comp["status"] = "Listed Peer" if ticker else "Unlisted"
        deduped.append(comp)
        log.info(
            f"PIB PLI approval competitor detected: {comp['name']} ({comp['status']})"
        )

    # One line that says where an empty result came from.
    located = sum(1 for r in ranked if "story" in r) + general
    listed_pli = len(ranked) + general - located
    by_source = {
        source: sum(1 for c in found if c["found_in"] == source)
        for source in ("release page", "headline")
    }
    log.info(
        "PLI approvals: "
        + (
            search_note
            or f"{len(entries)} search result(s) in the last 30 days, "
            f"{len(stories)} release(s)"
        )
        + f"; {located} found on PIB's lists of releases ({index.read} month(s) read)"
        + (f", {general} of them about no scheme and not read" if general else "")
        + (f", {listed_pli} more it titles as a scheme's" if listed_pli else "")
        + (f"; {index.failed}" if index.failed else "")
        + f"; {from_releases} release(s) read from PIB"
        + (f", {no_text} without a release's text" if no_text else "")
        + (f"; {failed} fetch(es) failed" if failed else "")
        + f"; {by_source['release page']} name(s) from releases, "
        f"{by_source['headline']} from headlines"
        + (
            "; left out under schemes no holding works in: "
            + ", ".join(f"{s} {n}" for s, n in sorted(off_scheme.items()))
            if off_scheme
            else ""
        )
        + (
            f"; {no_scheme} name(s) left out where no scheme is named"
            if no_scheme
            else ""
        )
        + f"; {len(deduped)} new candidate(s) after removing duplicates and "
        "holdings."
    )
    return deduped


async def fetch_advanced_rss_feeds_async(session, watchlist):
    log.info(
        "Fetching advanced RSS feeds for agreements and product launches (Async)..."
    )
    agreements = []
    launches = []

    all_tickers = []
    for sector, stocks in watchlist.items():
        for s in stocks:
            all_tickers.append(s["ticker"])

    # Combine queries in chunks of 4 to be polite to RSS service
    ticker_chunks = [all_tickers[i : i + 4] for i in range(0, len(all_tickers), 4)]

    # Pre-flatten watchlist once; matching itself is word-boundary + person-
    # name-guarded (see analysis.parsing.title_matches_company) — bare
    # substring checks mis-attributed "IBM CEO Arvind Krishna ..." to Arvind
    # Ltd and let ticker LT match any headline containing "Ltd".
    flat_watchlist = [
        (s["ticker"], s["name"], sector_name)
        for sector_name, stocks in watchlist.items()
        for s in stocks
    ]

    async def process_chunk(chunk):
        ticker_query = " OR ".join([f'"{t}"' for t in chunk])

        # Agreements
        agree_q = f'({ticker_query}) AND ("joint venture" OR "strategic partnership" OR "agreement" OR "collaboration" OR "MoU" OR "acquisition" OR "stake purchase")'
        encoded_agree = urllib.parse.quote(f"{agree_q} when:7d")
        rss_agree_url = f"https://news.google.com/rss/search?q={encoded_agree}&hl=en-IN&gl=IN&ceid=IN:en"

        from utils import fetch_text_async

        try:
            status, xml_data = await fetch_text_async(
                session, rss_agree_url, timeout=15
            )
            if status == 200:
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:3]:
                    title = entry.get("title", "")

                    # Attribute to a holding, exactly as launches and filings
                    # already do. Without this the record carried no company
                    # field at all, so dashboard/builder.py keyed all forty
                    # agreements under "" and none of them ever reached the
                    # holding they were about — a third of the policy-event
                    # corpus scoring nothing, silently.
                    matched_company = "Unknown"
                    matched_industry = "Corporate"
                    for ticker_sym, s_name, sector_name in flat_watchlist:
                        if title_matches_company(title, ticker_sym, s_name):
                            matched_company = s_name
                            matched_industry = sector_name
                            break

                    agreements.append(
                        {
                            "company": matched_company,
                            "industry": matched_industry,
                            "title": title.split(" - ")[0],
                            "link": entry.get("link", ""),
                            "date": entry.get("published", ""),
                            "source": entry.get("source", {}).get("title", "News"),
                        }
                    )
        except Exception as e:
            log.error(f"Error fetching agreements chunk: {e}")

        # Launches
        launch_q = f'({ticker_query}) AND ("product launch" OR "unveils" OR "commercial production" OR "production starts" OR "new facility" OR "new plant" OR "pilot production")'
        encoded_launch = urllib.parse.quote(f"{launch_q} when:7d")
        rss_launch_url = f"https://news.google.com/rss/search?q={encoded_launch}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with session.get(rss_launch_url, timeout=15) as resp:
                if resp.status == 200:
                    xml_data = await resp.text()
                    feed = feedparser.parse(xml_data)
                    for entry in feed.entries[:3]:
                        title = entry.get("title", "")

                        matched_company = "Unknown"
                        matched_industry = "Manufacturing"
                        for ticker_sym, s_name, sector_name in flat_watchlist:
                            if title_matches_company(title, ticker_sym, s_name):
                                matched_company = s_name
                                matched_industry = sector_name
                                break

                        launches.append(
                            {
                                "company": matched_company,
                                "product": title.split(" - ")[0],
                                "industry": matched_industry,
                                "date": entry.get("published", ""),
                                "source": entry.get("source", {}).get("title", "News"),
                                "link": entry.get("link", ""),
                            }
                        )
        except Exception as e:
            log.error(f"Error fetching launches chunk: {e}")

    await asyncio.gather(*[process_chunk(chunk) for chunk in ticker_chunks])

    unique_agreements = {a["title"]: a for a in agreements}.values()
    unique_launches = {launch["product"]: launch for launch in launches}.values()

    return list(unique_agreements)[:10], list(unique_launches)[:10]


def holding_names(watchlist):
    """Display names of everything we hold.

    Both exchange providers set ``company`` to the watchlist name when they
    match a holding, so an exact hit here means the filing is about a stock
    in the book. That is the only holdings signal that survives the merge —
    each provider sorts its own output holdings-first, but that ordering is
    invisible once the lists are concatenated.
    """
    return {
        s.get("name")
        for stocks in (watchlist or {}).values()
        for s in (stocks or [])
        if isinstance(s, dict) and s.get("name")
    }


def _interleave(*sources):
    """Round-robin across sources, preserving each one's internal order.

    Concatenation is what starved BSE: NSE alone returns hundreds of records,
    so `nse + bse` followed by a ten-row cap meant BSE never reached the
    section at all. Measured in production on 2026-09-09 — 40 filings, every
    one from NSE, on a pipeline where the BSE provider was working fine.
    """
    from itertools import zip_longest

    out = []
    for group in zip_longest(*sources):
        out.extend(item for item in group if item is not None)
    return out


async def fetch_exchange_filings_async(session, watchlist, cap=10, held_out=None):
    """Corporate filings from both exchanges and the press.

    The exchange APIs give the filing itself — exact identifier, the
    company's own subject line, the attached PDF. The news search below is
    what we had before them and is kept as the fallback, because either
    exchange can refuse a cloud IP on any given day: a block must degrade the
    section, not empty it.

    Ordering decides the whole result, because a full trading day produces
    hundreds of filings for a section that shows ten. Two rules, in order:

      1. Holdings before everything else. A filing about a stock we own is
         worth more than one about a company we have never heard of, whoever
         published it.
      2. Within each tier, round-robin across sources rather than
         concatenating. Concatenation lets whichever source answers first
         consume every slot — which is exactly what happened to BSE.
    """
    log.info(
        "Fetching NSE/BSE corporate filings (Async)..."
        if bse_announcements.BSE_ENABLED
        else "Fetching NSE corporate filings (Async); BSE is switched off..."
    )

    async def no_filings():
        return []

    # to_thread because both providers are sync requests (they need cookie-jar
    # persistence across the handshake) and this coroutine must not block the
    # event loop while they sleep out their rate-limit pauses. Gathered so the
    # two exchanges' pauses overlap instead of adding up.
    nse_filings, bse_filings, news_filings = await asyncio.gather(
        asyncio.to_thread(nse_fetch_filings, watchlist),
        (
            asyncio.to_thread(bse_fetch_filings, watchlist)
            if bse_announcements.BSE_ENABLED
            else no_filings()
        ),
        _fetch_filing_news_async(session, watchlist),
    )

    held = holding_names(watchlist)

    def split(filings):
        ours = [f for f in filings if f.get("company") in held]
        theirs = [f for f in filings if f.get("company") not in held]
        return ours, theirs

    nse_held, nse_rest = split(nse_filings)
    bse_held, bse_rest = split(bse_filings)
    news_held, news_rest = split(news_filings)

    # Every exchange filing by a holding, uncapped, for event confirmation
    # (analysis/event_evidence.confirm_with_filings). The section below keeps
    # ten; the check needs all of them — the one that confirms an order win is
    # rarely among the day's first ten. Exchange filings only: the news path
    # is somebody's account of a filing, which is what gets checked.
    if held_out is not None:
        ticker_of = {
            s.get("name"): str(s.get("ticker", "")).upper()
            for key, stocks in (watchlist or {}).items()
            if key != "macro_indicators"
            for s in stocks or []
            if isinstance(s, dict) and s.get("ticker")
        }
        from analysis.event_evidence import article_date

        for f in nse_held + bse_held:
            ticker = ticker_of.get(f.get("company"))
            if not ticker:
                continue
            held_out.append(
                {
                    "ticker": ticker,
                    "date": article_date(f.get("date")) or "",
                    "text": str(f.get("filing") or "")[:240],
                    "source": f.get("source"),
                    "link": f.get("link") or "",
                }
            )

    # Exchanges lead each tier: they carry the filing itself, where the news
    # path carries somebody's account of it and identifies the company by a
    # fuzzy title match.
    ordered = (
        _interleave(nse_held, bse_held)
        + news_held
        + _interleave(nse_rest, bse_rest)
        + news_rest
    )

    # Keyed on (company, filing), not filing alone. Two companies file the
    # same subject constantly — NSE stamps a coarse category on many records
    # — so a text-only key silently collapses a whole day into one row. This
    # matches the key main.py already dedupes the merged history on.
    #
    # setdefault, not a dict comprehension: the comprehension idiom used
    # elsewhere in this file keeps the LAST record for a duplicate key, which
    # here would hand every reported filing back to the weaker news version.
    unique = {}
    for filing in ordered:
        unique.setdefault((filing["company"], filing["filing"]), filing)
    result = list(unique.values())[:cap]

    kept = {}
    for f in result:
        kept[f.get("source", "?")] = kept.get(f.get("source", "?"), 0) + 1
    log.info(
        f"Corporate filings: {len(nse_filings)} from NSE, "
        + (
            f"{len(bse_filings)} from BSE, "
            if bse_announcements.BSE_ENABLED
            else "BSE off, "
        )
        + f"{len(news_filings)} from news; kept {len(result)} — {kept}. "
        f"{len(nse_held) + len(bse_held) + len(news_held)} concerned holdings."
    )
    return result


async def _fetch_filing_news_async(session, watchlist):
    """Filings as reported by the press. The original implementation, now the
    fallback: it recovers the company by fuzzy title match, so it is strictly
    weaker identification than NSE's symbol, but it survives an IP block."""
    filings = []

    all_tickers = []
    for sector, stocks in watchlist.items():
        for s in stocks:
            all_tickers.append(s["ticker"])

    ticker_chunks = [all_tickers[i : i + 4] for i in range(0, len(all_tickers), 4)]

    flat_watchlist = [
        (s["ticker"], s["name"], sector_name)
        for sector_name, stocks in watchlist.items()
        for s in stocks
    ]

    async def process_chunk(chunk):
        ticker_query = " OR ".join([f'"{t}"' for t in chunk])
        filing_q = f'({ticker_query}) AND ("NSE" OR "BSE" OR "Exchange Filing" OR "Regulatory Filing") AND ("Agreement" OR "MoU" OR "Acquisition" OR "Expansion" OR "Capacity" OR "Capex" OR "Joint Venture" OR "Technology Transfer")'
        encoded_filing = urllib.parse.quote(f"{filing_q} when:3d")
        rss_url = f"https://news.google.com/rss/search?q={encoded_filing}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with session.get(rss_url, timeout=15) as resp:
                if resp.status == 200:
                    xml_data = await resp.text()
                    feed = feedparser.parse(xml_data)
                    for entry in feed.entries[:3]:
                        title = entry.get("title", "")

                        matched_company = "Unknown"
                        matched_industry = "Corporate"
                        for ticker_sym, s_name, sector_name in flat_watchlist:
                            if title_matches_company(title, ticker_sym, s_name):
                                matched_company = s_name
                                matched_industry = sector_name
                                break

                        filings.append(
                            {
                                "company": matched_company,
                                "filing": title.split(" - ")[0],
                                "industry": matched_industry,
                                "date": entry.get("published", ""),
                                "source": entry.get("source", {}).get(
                                    "title", "Exchange"
                                ),
                                "link": entry.get("link", ""),
                            }
                        )
        except Exception as e:
            log.error(f"Error fetching filings chunk: {e}")

    await asyncio.gather(*[process_chunk(chunk) for chunk in ticker_chunks])

    # Deduped here as well as in the caller: this half can repeat a headline
    # across chunks, and the cap keeps a chatty news day from crowding out
    # the exchange records it gets merged with.
    unique_filings = {f["filing"]: f for f in filings}.values()
    return list(unique_filings)[:10]


async def check_sebi_sid_filings_async(session):
    log.info("Checking SEBI filings for thematic funds (Incoming Capital) (Async)...")
    query = 'site:sebi.gov.in "Scheme Information Document" AND ("manufacturing" OR "semiconductors" OR "defence" OR "logistics" OR "technology")'
    encoded_query = urllib.parse.quote(f"{query} when:30d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    filings = []
    try:
        async with session.get(rss_url, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:5]:
                    title = entry.get("title", "")
                    theme = "Manufacturing & PLI"
                    if "defence" in title.lower() or "defense" in title.lower():
                        theme = "Defence & Aerospace"
                    elif "semiconductor" in title.lower() or "chip" in title.lower():
                        theme = "Semiconductors & Tech"
                    elif "logistics" in title.lower():
                        theme = "Logistics & Infra"

                    filings.append(
                        {
                            "fund_name": title.split(" - ")[0].replace("SEBI | ", ""),
                            "theme": theme,
                            "status": "Incoming Institutional Capital",
                            "date": entry.get("published", ""),
                            "link": entry.get("link", "https://www.sebi.gov.in"),
                        }
                    )
                    log.info(f"SEBI MF SID filing detected: {title} [{theme}]")
    except Exception as e:
        log.error(f"Error checking SEBI filings: {e}")

    return filings


def _parse_block_deal_headline(headline, flat_watchlist, headline_lower):
    buyer = "Institutional Investor"
    action = "Buy"
    company = "Listed Company"
    details = "Block Deal"

    if any(
        w in headline_lower
        for w in [
            "sells",
            "dumped",
            "exits",
            "offloads",
            "reduces stake",
        ]
    ):
        action = "Sell"
    elif any(
        w in headline_lower
        for w in [
            "buys",
            "acquires",
            "purchases",
            "picks up",
            "increases stake",
        ]
    ):
        action = "Buy"

    buyer_match = re.search(
        r"^([A-Z0-9][A-Za-z0-9\s\.\&]+?)\s+(?:buys|acquires|sells|purchases|picks up|offloads|exits|increases|decreases|shares|block|bulk|mutual)",
        headline,
    )
    if buyer_match:
        buyer = buyer_match.group(1).strip()

    details_match = re.search(
        r"(\d+(?:\.\d+)?%\s*stake|\d+\s*(?:lakh|million|crore)?\s*shares|worth\s*(?:Rs\s*)?\d+\s*(?:cr|crore|crores)?)",
        headline,
        re.IGNORECASE,
    )
    if details_match:
        details = details_match.group(1).strip()

    company_match = re.search(
        r"(?:in|of|shares of|stake in|shares in)\s+([A-Z][A-Za-z0-9\s\&]+?)(?:\s+via|\s+worth|\s+for|\s+at|\s+through|\s+block|\s+bulk|$)",
        headline,
    )
    if company_match:
        company = company_match.group(1).strip()

    # Match against watchlist stocks (word-boundary + person-name guard)
    matched_company = None
    matched_ticker = None
    for ticker_sym, s_name, _sector in flat_watchlist:
        if title_matches_company(headline, ticker_sym, s_name):
            matched_company = s_name
            matched_ticker = ticker_sym
            break

    if matched_company:
        company = f"{matched_company} ({matched_ticker})"

    return buyer, action, company, details


async def fetch_institutional_activity_async(session, watchlist):
    log.info(
        "Fetching institutional activity block deals and mutual fund buying trends (Async)..."
    )
    query = '"block deal" OR "bulk deal" OR "mutual fund buys" OR "FII buying" India'
    encoded_query = urllib.parse.quote(f"{query} when:7d")
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

    flat_watchlist = [
        (s["ticker"], s["name"], None) for stocks in watchlist.values() for s in stocks
    ]

    activity = []
    try:
        async with session.get(rss_url, timeout=15) as response:
            if response.status == 200:
                xml_data = await response.text()
                feed = feedparser.parse(xml_data)
                for entry in feed.entries[:8]:  # Get top 8 entries
                    headline = entry.get("title", "").split(" - ")[0].strip()
                    headline_lower = headline.lower()

                    buyer, action, company, details = _parse_block_deal_headline(
                        headline, flat_watchlist, headline_lower
                    )

                    activity.append(
                        {
                            "headline": headline,
                            "link": entry.get("link", ""),
                            "source": entry.get("source", {}).get(
                                "title", "Finance Media"
                            ),
                            "date": entry.get("published", ""),
                            "buyer": buyer,
                            "action": action,
                            "company": company,
                            "details": details,
                        }
                    )
    except Exception as e:
        log.error(f"Error fetching institutional activity: {e}")

    return activity
