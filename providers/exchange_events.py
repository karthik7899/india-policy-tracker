"""Exchange-disclosed events: fund-raising and bulk/block deals.

News headlines are a lossy echo of exchange disclosures — under SEBI LODR
Reg 30 every material event is filed with the exchanges first, completely
and with timestamps. This provider reads two BSE public API feeds directly:

  - Corporate announcements, classified for capital-raising events (QIP,
    rights issue, preferential allotment, warrants, buyback, FPO, NCDs).
  - Bulk and block deals — actual institutional buying/selling with
    counterparty names and quantities, not "sources say" articles.

Both endpoints are unauthenticated JSON but their shapes are not
contractual, so parsing is defensive throughout and every fetch degrades
to an empty list — the briefing must never be blocked by this channel.
"""

import datetime

from logger import log

_BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.bseindia.com/",
    "Accept": "application/json",
}

_ANNOUNCEMENTS_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
    "?pageno=1&strCat=-1&strPrevDate={frm}&strScrip=&strSearch=P"
    "&strToDate={to}&strType=C"
)

_BULK_DEALS_URL = "https://api.bseindia.com/BseIndiaAPI/api/BulkDeals/w?flag=0"
_BLOCK_DEALS_URL = "https://api.bseindia.com/BseIndiaAPI/api/BlockDeals/w?flag=0"

# Subject-line markers for capital-raising disclosures.
FUNDRAISING_KEYWORDS = (
    "qualified institution",
    "qip",
    "rights issue",
    "preferential allotment",
    "preferential issue",
    "raising of funds",
    "fund raising",
    "fund raise",
    "issue of warrants",
    "convertible warrants",
    "non-convertible debentures",
    "further public offer",
    "buyback",
    "buy-back",
    "institutional placement",
)


def _normalise(name):
    return "".join(ch for ch in str(name).lower() if ch.isalnum() or ch == " ")


def match_watchlist_company(company_name, watchlist):
    """Best-effort match of an exchange-disclosed company name to a holding.

    Conservative: the holding's full name must appear inside the disclosed
    name (or vice versa) after normalisation — token-overlap guessing causes
    false positives across India's many same-group companies (Tata Power vs
    Tata Motors), so substring containment of the whole name it is.
    Returns the matched stock's ticker, or None.
    """
    target = _normalise(company_name)
    if not target:
        return None
    for sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            hold = _normalise(stock.get("name", ""))
            if hold and (hold in target or target in hold):
                return stock.get("ticker")
    return None


def classify_fundraising(subject):
    """Returns the matched capital-raising keyword, or None."""
    text = str(subject or "").lower()
    for keyword in FUNDRAISING_KEYWORDS:
        if keyword in text:
            return keyword
    return None


def parse_announcements(payload, watchlist):
    """Extracts capital-raising events from a BSE announcements payload.

    Returns [{company, ticker, subject, category, date, keyword}] — ticker
    is None for non-watchlist companies (still useful: a rival raising
    capital is competitive intelligence).
    """
    events = []
    if not isinstance(payload, dict):
        return events
    rows = payload.get("Table") or []
    if not isinstance(rows, list):
        return events
    for row in rows:
        if not isinstance(row, dict):
            continue
        subject = row.get("NEWSSUB") or row.get("HEADLINE") or ""
        keyword = classify_fundraising(subject)
        if not keyword:
            continue
        company = row.get("SLONGNAME") or row.get("SNAME") or "Unknown"
        events.append(
            {
                "company": str(company).strip(),
                "ticker": match_watchlist_company(company, watchlist),
                "subject": str(subject).strip()[:200],
                "category": str(row.get("CATEGORYNAME") or "").strip(),
                "date": str(row.get("NEWS_DT") or "")[:10],
                "keyword": keyword,
            }
        )
    return events


def parse_deals(payload, watchlist, deal_type):
    """Extracts bulk/block deal rows touching watchlist companies.

    BSE deal rows name the scrip, the client, buy/sell side and quantity;
    field names vary between the two feeds so lookups are permissive.
    """
    deals = []
    if not isinstance(payload, dict):
        return deals
    rows = payload.get("Table") or []
    if not isinstance(rows, list):
        return deals
    for row in rows:
        if not isinstance(row, dict):
            continue
        company = row.get("SNAME") or row.get("Scripname") or row.get("SLONGNAME") or ""
        ticker = match_watchlist_company(company, watchlist)
        if not ticker:
            continue  # deals feed is market-wide; keep only our companies
        side_raw = str(
            row.get("BUYSELL") or row.get("Dealtype") or row.get("BD_TP") or ""
        ).strip()
        side = (
            "buy"
            if side_raw.lower().startswith(("b", "p"))
            else "sell" if side_raw.lower().startswith("s") else side_raw or "n/a"
        )
        deals.append(
            {
                "company": str(company).strip(),
                "ticker": ticker,
                "client": str(
                    row.get("CLIENTNAME") or row.get("Clientname") or ""
                ).strip()[:80],
                "side": side,
                "quantity": row.get("QTY") or row.get("Quantity"),
                "price": row.get("RATE") or row.get("TradePrice"),
                "date": str(row.get("DT") or row.get("Dealdate") or "")[:10],
                "deal_type": deal_type,
            }
        )
    return deals


async def _fetch_json(session, url):
    """Single attempt, short timeout, None on any failure — this channel is
    enhancement data and must never slow or block the briefing.

    Redirects are NOT followed: BSE's Akamai edge answers datacenter IPs
    (like GitHub Actions runners) with a 302 to an error page, and following
    that produced a TooManyRedirects exception whose repr dumped the entire
    redirect chain into the log. A 302 is treated as a plain non-200 miss,
    and any exception message is truncated so this channel can never spam
    the briefing log again.
    """
    try:
        async with session.get(
            url, headers=_BSE_HEADERS, timeout=15, allow_redirects=False
        ) as response:
            if response.status != 200:
                location = response.headers.get("Location", "")
                hint = " (edge/bot block)" if "error" in location.lower() else ""
                log.warning(f"BSE API returned {response.status}{hint} for {url}")
                return None
            payload = await response.json(content_type=None)
            if not isinstance(payload, dict):
                preview = str(payload)[:120]
                log.warning(
                    f"BSE API returned non-dict JSON for {url}: "
                    f"{type(payload).__name__} {preview!r}"
                )
            return payload
    except Exception as e:
        log.warning(
            f"BSE API fetch failed for {url}: {type(e).__name__}: {str(e)[:150]}"
        )
        return None


async def fetch_fundraising_events_async(session, watchlist, lookback_days=3):
    """Capital-raising disclosures from BSE announcements over the lookback window.

    Wrapped whole: this channel is enhancement data, and run #65 proved that
    letting even a parsing surprise propagate kills the entire briefing via
    asyncio.gather. Nothing here may ever raise.
    """
    try:
        log.info("Fetching BSE capital-raising disclosures (Async)...")
        today = datetime.date.today()
        frm = (today - datetime.timedelta(days=lookback_days)).strftime("%Y%m%d")
        url = _ANNOUNCEMENTS_URL.format(frm=frm, to=today.strftime("%Y%m%d"))
        payload = await _fetch_json(session, url)
        events = parse_announcements(payload, watchlist)
        if events:
            log.info(f"BSE fundraising radar: {len(events)} capital-raising events.")
        else:
            log.info("BSE fundraising radar: no qualifying disclosures.")
        return events
    except Exception as e:
        log.warning(f"BSE fundraising radar failed safely: {e!r}")
        return []


async def fetch_institutional_deals_async(session, watchlist):
    """Bulk + block deals from BSE touching watchlist companies.

    Wrapped whole for the same reason as the fundraising fetch: enhancement
    data must never be able to take the briefing down.
    """
    try:
        log.info("Fetching BSE bulk/block deals (Async)...")
        bulk_payload = await _fetch_json(session, _BULK_DEALS_URL)
        block_payload = await _fetch_json(session, _BLOCK_DEALS_URL)
        deals = parse_deals(bulk_payload, watchlist, "bulk") + parse_deals(
            block_payload, watchlist, "block"
        )
        if deals:
            log.info(
                f"BSE deals radar: {len(deals)} bulk/block deals on watchlist names."
            )
        else:
            log.info("BSE deals radar: no deals touching watchlist names.")
        return deals
    except Exception as e:
        log.warning(f"BSE deals radar failed safely: {e!r}")
        return []
