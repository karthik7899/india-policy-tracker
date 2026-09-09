"""Delivery percentage and exact turnover, from NSE's daily security file.

analysis/liquidity.py answers "can this position actually be exited?" from
Yahoo's close times volume. That is a reasonable proxy and it is all we had,
but it counts every share that changed hands — including intraday churn that
never settles and tells you nothing about whether real buyers exist.

NSE publishes the number that separates the two. ``sec_bhavdata_full``
carries DELIV_QTY and DELIV_PER alongside turnover for every security, per
session, keyed by SYMBOL — the same key the watchlist uses, so no ISIN join
is needed. A stock trading Rs 5 Cr a day at 20% delivery is a materially
different proposition from one trading Rs 5 Cr at 70%, and until now the
dashboard ranked them identically.

MEASURED (probe run 3, 14 Aug 2026): 376 KB, 3,308 rows, text/csv, no zip.
Columns: SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE,
LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS,
NO_OF_TRADES, DELIV_QTY, DELIV_PER. The archive host requires the browser UA
and Referer — a bare request times out, which was measured, not assumed.

SCOPE, deliberately: this reads ONE session, not a window. Averaging
delivery over twenty days would mean twenty requests of 376 KB for a
second-order refinement, and the single-session figure already answers the
question the ADVT band cannot. Treat it as a qualifier on turnover, not a
replacement for it.
"""

import csv
import datetime
import io

from logger import log
from utils import to_float

BASE_URL = "https://nsearchives.nseindia.com/products/content"

# The archive host filters on client identity: a bare request times out
# rather than being refused, which is a slower and more confusing failure
# than a 403. Same header set providers/isin_master.py has used for months.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
}

REQUEST_TIMEOUT_S = 20

# How many days back to walk looking for a published file. Covers a weekend
# plus a holiday or two; beyond that the data is too stale to qualify today's
# turnover and the absence is worth reporting instead of papering over.
MAX_LOOKBACK_DAYS = 5

# A lakh is 10^5 rupees; the dashboard speaks crore (10^7).
_LACS_PER_CRORE = 100.0

# Delivery bands. Below the first, most of the volume is intraday churn and
# the turnover figure flatters the stock's real tradeability.
CHURN_PCT = 25.0
HEALTHY_PCT = 50.0

# Series we read. EQ is the normal rolling segment. BE is trade-to-trade,
# where a stock sits under surveillance and intraday netting is not allowed.
#
# MEASURED 2026-09-09: STLTECH, DIACABS and MTARTECH were all missing from an
# EQ-only read and all three are in BE. Including them is right — they are
# holdings and their turnover is real — but their DELIVERY figure is not
# comparable. T2T MANDATES delivery, so ~100% there is a rule rather than
# evidence of accumulation, and banding it "delivery-led" would manufacture a
# bullish signal out of a trading restriction. Hence a band of its own.
READ_SERIES = ("EQ", "BE")
TRADE_TO_TRADE = "BE"


def url_for(day):
    """NSE names these files by DDMMYYYY, not the ISO order used elsewhere."""
    return f"{BASE_URL}/sec_bhavdata_full_{day.strftime('%d%m%Y')}.csv"


def parse_delivery_csv(text, series=READ_SERIES):
    """SYMBOL -> {deliv_pct, turnover_cr, trades}. Empty dict on any problem.

    Header names carry stray spaces in the wild — NSE's own files are
    inconsistent about it — so every key is normalised before lookup.

    ``series=None`` keeps every series and records which one each row came
    from. Only diagnostics use that: holdings missing from a normal read are
    either in a segment we do not take, or absent from NSE altogether, and
    that is answerable from the file rather than by guessing.

    Where a symbol appears in more than one series, EQ wins: it is the
    segment the position would normally be traded in.
    """
    out = {}
    if not text:
        return out
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            cleaned = {
                (k or "").strip().upper(): (v or "").strip() for k, v in row.items()
            }
            symbol = cleaned.get("SYMBOL", "").upper()
            # The same symbol appears under several series (EQ, BE, BZ) with
            # different liquidity, so rows are filtered rather than merged —
            # summing them would misstate both segments. READ_SERIES says
            # which ones we keep and why.
            row_series = cleaned.get("SERIES", "")
            if series is not None:
                allowed = (series,) if isinstance(series, str) else series
                if row_series not in allowed:
                    continue
            if not symbol:
                continue
            # EQ wins a symbol listed in several segments — it is where the
            # position would actually be traded.
            if out.get(symbol, {}).get("series") == "EQ" and row_series != "EQ":
                continue

            turnover_lacs = to_float(cleaned.get("TURNOVER_LACS"))
            # DELIV_PER is literally "-" for securities where delivery is not
            # reported. to_float gives None, which stays None: "not reported"
            # and "zero delivery" are different facts.
            deliv_pct = to_float(cleaned.get("DELIV_PER"))
            # Same rule as DELIV_PER above, and the reason this is not
            # ``int(x or 0) or None``: that idiom maps a reported zero onto
            # None, so a security that genuinely did not trade becomes
            # indistinguishable from one whose count NSE omitted. A suspended
            # or untraded scrip is exactly the case worth telling apart.
            trades = to_float(cleaned.get("NO_OF_TRADES"))

            out[symbol] = {
                "deliv_pct": round(deliv_pct, 2) if deliv_pct is not None else None,
                "turnover_cr": (
                    round(turnover_lacs / _LACS_PER_CRORE, 2)
                    if turnover_lacs is not None
                    else None
                ),
                "trades": int(trades) if trades is not None else None,
                "series": row_series,
            }
    except Exception as e:  # noqa: BLE001 - a malformed file is not a crash
        log.warning(f"Could not parse NSE delivery file: {e}")
    return out


def classify_delivery(deliv_pct, series=None):
    """Plain label for a delivery percentage; 'unknown' when not reported.

    Trade-to-trade gets its own band rather than a number on the same scale.
    Delivery is compulsory in that segment, so a high figure says the stock is
    under surveillance, not that anyone is accumulating it — the opposite of
    what "delivery-led" would imply to a reader.

    Coerced rather than trusted: these values travel through screener dicts
    that carry strings, and a comparison against one raises TypeError deep in
    a render rather than here.
    """
    if series == TRADE_TO_TRADE:
        return "trade-to-trade"
    deliv_pct = to_float(deliv_pct)
    if deliv_pct is None:
        return "unknown"
    if deliv_pct < CHURN_PCT:
        return "churn"
    if deliv_pct < HEALTHY_PCT:
        return "mixed"
    return "delivery-led"


def delivery_note(assessment):
    """One sentence when delivery undercuts the turnover figure, else None.

    Only fires on the churn band: saying "70% delivery" about a healthy stock
    is noise, whereas "Rs 8 Cr traded but 12% delivered" changes what the
    turnover means.
    """
    assessment = assessment or {}
    if assessment.get("series") == TRADE_TO_TRADE:
        # Compulsory delivery cannot be churn, and saying so would be noise.
        return None
    pct = to_float(assessment.get("deliv_pct"))
    turnover = to_float(assessment.get("turnover_cr"))
    if pct is None or pct >= CHURN_PCT:
        return None
    traded = f"Rs {turnover:.2f} Cr traded" if turnover else "Turnover"
    return (
        f"{traded} but only {pct:.0f}% delivered — most of that volume is "
        "intraday churn, so the liquidity band flatters this name."
    )


async def fetch_delivery_async(session, day=None, lookback=MAX_LOOKBACK_DAYS):
    """Latest published session's delivery data. Never raises; {} on failure.

    Walks back day by day because the file for a weekend or holiday simply
    does not exist, and because today's is not published until after the
    close. Returns the first day that yields rows, so the caller gets real
    data rather than an empty dict on any non-trading day.
    """
    day = day or datetime.date.today()
    for offset in range(lookback + 1):
        candidate = day - datetime.timedelta(days=offset)
        url = url_for(candidate)
        try:
            async with session.get(
                url, headers=HEADERS, timeout=REQUEST_TIMEOUT_S
            ) as response:
                if response.status != 200:
                    continue
                text = await response.text()
        except Exception as e:  # noqa: BLE001 - an enrichment must not end a run
            log.info(
                f"NSE delivery fetch failed for {candidate} "
                f"({type(e).__name__}: {str(e)[:80]})."
            )
            continue

        rows = parse_delivery_csv(text)
        if rows:
            log.info(
                f"NSE delivery: {len(rows)} securities "
                f"({sum(1 for r in rows.values() if r.get('series') == 'BE')} "
                f"trade-to-trade) for {candidate.isoformat()}."
            )
            return rows

    log.info(
        f"NSE delivery unavailable for the last {lookback + 1} days; "
        "liquidity keeps its volume-derived turnover only."
    )
    return {}


def apply_delivery(watchlist, delivery):
    """Stamp delivery onto each holding's screener dict. Returns the count.

    Must run AFTER the Screener rebuild, for the same reason turnover does:
    that fetch replaces the dict wholesale, so anything written earlier is
    erased. This repo has already shipped that bug twice — once for turnover,
    once for the 52-week range — and both times the symptom was a feature
    that reported nothing while looking like it worked.

    NOTE: every key written below — deliv_pct, delivery_band, series and
    turnover_cr_last — must also be declared on models/core.CompanyFinancials,
    or coercion silently drops it and the scorer reads None no matter what is
    attached here. The names must match exactly; turnover_cr_last is not
    turnover_cr.
    """
    applied = 0
    for _sector, stocks in (watchlist or {}).items():
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            row = (delivery or {}).get(str(stock.get("ticker") or "").upper())
            if not row:
                continue
            screener = stock.get("screener")
            if not isinstance(screener, dict):
                screener = {}
                stock["screener"] = screener
            screener["deliv_pct"] = row.get("deliv_pct")
            screener["delivery_band"] = classify_delivery(
                row.get("deliv_pct"), row.get("series")
            )
            screener["series"] = row.get("series")
            # Named apart from advt_cr, which is a multi-session average. One
            # session's turnover is a different measurement and conflating
            # them would make the dashboard's own numbers disagree.
            screener["turnover_cr_last"] = row.get("turnover_cr")
            applied += 1
    return applied
