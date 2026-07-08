"""Exchange-disclosed events: fund-raising and bulk/block deals.

News headlines are a lossy echo of exchange disclosures — under SEBI LODR
Reg 30 every material event is filed with the exchanges first, completely
and with timestamps. This provider reads corporate-announcements and
bulk/block-deal feeds from BOTH exchanges:

  - Corporate announcements, classified for capital-raising events (QIP,
    rights issue, preferential allotment, warrants, buyback, FPO, NCDs).
  - Bulk and block deals — actual institutional buying/selling with
    counterparty names and quantities, not "sources say" articles.

BSE's API (api.bseindia.com) is unauthenticated JSON but its Akamai edge
blocks GitHub Actions' datacenter IPs outright — every production run so
far has degraded to zero events from it. NSE's API needs a cookie
handshake (a plain GET to the homepage first) but is, in practice, often
reachable from hosts BSE blocks — it runs alongside BSE rather than
replacing it, so whichever source actually gets through wins, and if both
are blocked the channel degrades to empty lists exactly as before. NSE's
announcement payload also carries the security's ISIN directly, so those
events are matched via entities.py's entity master (exact) before falling
back to the same conservative name-containment matching BSE events use.

Neither exchange's JSON shape is contractual, so parsing is defensive
throughout and every fetch degrades to an empty list — the briefing must
never be blocked by this channel.
"""

import asyncio
import datetime

from entities import build_entity_master, resolve_entity_by_isin
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

    Returns [{company, ticker, subject, category, date, keyword, source}] —
    ticker is None for non-watchlist companies (still useful: a rival
    raising capital is competitive intelligence).
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
                "source": "BSE",
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
                "source": "BSE",
            }
        )
    return deals


_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_NSE_HOME_URL = "https://www.nseindia.com/"
_NSE_ANNOUNCEMENTS_URL = (
    "https://www.nseindia.com/api/corporate-announcements?index=equities"
)
# Current-day bulk + block deals in one payload; NSE does not expose a
# lookback window on this endpoint the way BSE's announcements API does.
_NSE_LARGE_DEALS_URL = "https://www.nseindia.com/api/snapshot-capital-market-largedeal"


async def _bootstrap_nse_session(session):
    """NSE's API rejects requests with no cookies — a plain GET to the
    homepage first populates the shared aiohttp session's cookie jar for
    the API calls that follow. Returns False (never raises) on any
    failure, which the caller treats as "NSE unreachable this run"."""
    try:
        async with session.get(
            _NSE_HOME_URL, headers=_NSE_HEADERS, timeout=15
        ) as response:
            await response.read()
            if response.status != 200:
                log.warning(
                    f"NSE session bootstrap returned {response.status} for "
                    f"{_NSE_HOME_URL}"
                )
                return False
            return True
    except Exception as e:
        log.warning(f"NSE session bootstrap failed: {type(e).__name__}: {str(e)[:150]}")
        return False


async def _fetch_nse_json(session, url):
    """Mirrors _fetch_json's defensiveness for NSE: single attempt, short
    timeout, no redirect-following, truncated exception logging, None on
    any failure."""
    try:
        async with session.get(
            url, headers=_NSE_HEADERS, timeout=15, allow_redirects=False
        ) as response:
            if response.status != 200:
                log.warning(f"NSE API returned {response.status} for {url}")
                return None
            payload = await response.json(content_type=None)
            if not isinstance(payload, (dict, list)):
                preview = str(payload)[:120]
                log.warning(
                    f"NSE API returned unexpected JSON shape for {url}: "
                    f"{type(payload).__name__} {preview!r}"
                )
            return payload
    except Exception as e:
        log.warning(
            f"NSE API fetch failed for {url}: {type(e).__name__}: {str(e)[:150]}"
        )
        return None


def _resolve_ticker(company, isin, watchlist, entity_master):
    """ISIN match first (exact — NSE payloads carry it directly), falling
    back to the same conservative name-containment matching BSE events
    use when ISIN isn't present or hasn't been indexed yet."""
    entity = resolve_entity_by_isin(isin, entity_master) if isin else None
    if entity:
        return entity.get("ticker")
    return match_watchlist_company(company, watchlist)


def parse_nse_announcements(payload, watchlist, entity_master=None):
    """Extracts capital-raising events from NSE's corporate-announcements
    payload. Field names are best-effort — NSE's shape isn't contractual
    and couldn't be verified from a network-restricted dev sandbox, so a
    row's worth of keys is logged if nothing parses, to make a follow-up
    field-name fix a one-line change instead of another guessing round.
    """
    events = []
    entity_master = entity_master or {}
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("data")
    else:
        rows = None
    if not isinstance(rows, list):
        return events
    for row in rows:
        if not isinstance(row, dict):
            continue
        subject = row.get("desc") or row.get("subject") or row.get("attchmntText") or ""
        keyword = classify_fundraising(subject)
        if not keyword:
            continue
        company = (
            row.get("sm_name") or row.get("company") or row.get("symbol") or "Unknown"
        )
        isin = row.get("sm_isin") or row.get("isin")
        events.append(
            {
                "company": str(company).strip(),
                "ticker": _resolve_ticker(company, isin, watchlist, entity_master),
                "subject": str(subject).strip()[:200],
                "category": str(row.get("desc") or "").strip()[:60],
                "date": str(row.get("an_dt") or row.get("sort_date") or "")[:10],
                "keyword": keyword,
                "source": "NSE",
            }
        )
    if rows and not events:
        sample = sorted(rows[0].keys()) if isinstance(rows[0], dict) else []
        log.info(
            f"NSE announcements: {len(rows)} rows, 0 fundraising matches. "
            f"Sample row keys: {sample}"
        )
    return events


def parse_nse_deals(payload, watchlist, entity_master=None):
    """Extracts bulk/block deal rows touching watchlist companies from
    NSE's large-deals snapshot. Field names are best-effort for the same
    reason as parse_nse_announcements."""
    deals = []
    entity_master = entity_master or {}
    if not isinstance(payload, dict):
        return deals
    for deal_type, key in (("bulk", "BULK_DEALS_DATA"), ("block", "BLOCK_DEALS_DATA")):
        rows = payload.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            company = (
                row.get("BD_SCRIP_NAME")
                or row.get("symbol")
                or row.get("BD_SYMBOL")
                or ""
            )
            isin = row.get("BD_ISIN") or row.get("isin")
            ticker = _resolve_ticker(company, isin, watchlist, entity_master)
            if not ticker:
                continue  # deals feed is market-wide; keep only our companies
            side_raw = str(row.get("BD_BUY_SELL") or row.get("buySell") or "").strip()
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
                        row.get("BD_CLIENT_NAME") or row.get("clientName") or ""
                    ).strip()[:80],
                    "side": side,
                    "quantity": row.get("BD_QTY_TRD") or row.get("quantityTraded"),
                    "price": row.get("BD_TP_WATP") or row.get("tradePrice"),
                    "date": str(row.get("BD_DT_DATE") or row.get("date") or "")[:10],
                    "deal_type": deal_type,
                    "source": "NSE",
                }
            )
    return deals


def _dedupe_events(events):
    """Drops exact repeats when both BSE and NSE happen to report the same
    disclosure (keyed on ticker/company + keyword + date, ignoring source)."""
    seen = set()
    deduped = []
    for event in events:
        key = (
            event.get("ticker") or event.get("company"),
            event.get("keyword"),
            event.get("date"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(event)
    return deduped


def _dedupe_deals(deals):
    seen = set()
    deduped = []
    for deal in deals:
        key = (
            deal.get("ticker"),
            deal.get("deal_type"),
            deal.get("date"),
            deal.get("client"),
            deal.get("quantity"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(deal)
    return deduped


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


async def _fetch_bse_fundraising(session, watchlist, lookback_days):
    try:
        today = datetime.date.today()
        frm = (today - datetime.timedelta(days=lookback_days)).strftime("%Y%m%d")
        url = _ANNOUNCEMENTS_URL.format(frm=frm, to=today.strftime("%Y%m%d"))
        payload = await _fetch_json(session, url)
        return parse_announcements(payload, watchlist)
    except Exception as e:
        log.warning(f"BSE fundraising radar failed safely: {e!r}")
        return []


async def _fetch_nse_fundraising(session, watchlist, entity_master):
    try:
        if not await _bootstrap_nse_session(session):
            return []
        payload = await _fetch_nse_json(session, _NSE_ANNOUNCEMENTS_URL)
        return parse_nse_announcements(payload, watchlist, entity_master)
    except Exception as e:
        log.warning(f"NSE fundraising radar failed safely: {e!r}")
        return []


async def fetch_fundraising_events_async(session, watchlist, lookback_days=3):
    """Capital-raising disclosures from BSE + NSE announcements over the
    lookback window (BSE) / current listing (NSE), merged and deduplicated.

    Wrapped whole: this channel is enhancement data, and run #65 proved that
    letting even a parsing surprise propagate kills the entire briefing via
    asyncio.gather. Nothing here may ever raise.
    """
    try:
        log.info("Fetching BSE + NSE capital-raising disclosures (Async)...")
        entity_master = build_entity_master(watchlist)
        bse_events, nse_events = await asyncio.gather(
            _fetch_bse_fundraising(session, watchlist, lookback_days),
            _fetch_nse_fundraising(session, watchlist, entity_master),
        )
        events = _dedupe_events(bse_events + nse_events)
        if events:
            log.info(
                f"Fundraising radar: {len(events)} capital-raising events "
                f"(BSE={len(bse_events)}, NSE={len(nse_events)})."
            )
        else:
            log.info(
                "Fundraising radar: no qualifying disclosures from either exchange."
            )
        return events
    except Exception as e:
        log.warning(f"Fundraising radar failed safely: {e!r}")
        return []


async def _fetch_bse_deals(session, watchlist):
    try:
        bulk_payload = await _fetch_json(session, _BULK_DEALS_URL)
        block_payload = await _fetch_json(session, _BLOCK_DEALS_URL)
        return parse_deals(bulk_payload, watchlist, "bulk") + parse_deals(
            block_payload, watchlist, "block"
        )
    except Exception as e:
        log.warning(f"BSE deals radar failed safely: {e!r}")
        return []


async def _fetch_nse_deals(session, watchlist, entity_master):
    try:
        if not await _bootstrap_nse_session(session):
            return []
        payload = await _fetch_nse_json(session, _NSE_LARGE_DEALS_URL)
        return parse_nse_deals(payload, watchlist, entity_master)
    except Exception as e:
        log.warning(f"NSE deals radar failed safely: {e!r}")
        return []


async def fetch_institutional_deals_async(session, watchlist):
    """Bulk + block deals from BSE and NSE touching watchlist companies,
    merged and deduplicated.

    Wrapped whole for the same reason as the fundraising fetch: enhancement
    data must never be able to take the briefing down.
    """
    try:
        log.info("Fetching BSE + NSE bulk/block deals (Async)...")
        entity_master = build_entity_master(watchlist)
        bse_deals, nse_deals = await asyncio.gather(
            _fetch_bse_deals(session, watchlist),
            _fetch_nse_deals(session, watchlist, entity_master),
        )
        deals = _dedupe_deals(bse_deals + nse_deals)
        if deals:
            log.info(
                f"Deals radar: {len(deals)} bulk/block deals on watchlist names "
                f"(BSE={len(bse_deals)}, NSE={len(nse_deals)})."
            )
        else:
            log.info(
                "Deals radar: no deals touching watchlist names from either exchange."
            )
        return deals
    except Exception as e:
        log.warning(f"Deals radar failed safely: {e!r}")
        return []
