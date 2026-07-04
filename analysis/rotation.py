import re
from logger import log
import requests
from config import save_watchlist
from providers.yahoo import get_cached_ticker
from .parsing import resolve_ticker_from_name


def detect_emerging_players(brief_data, watchlist):
    """Scans aggregated news titles for corporate names not currently in the watchlist."""
    log.info("Scanning headlines for emerging players...")
    emerging_players = {}

    existing_ids = set()
    for sector, stocks in watchlist.items():
        for s in stocks:
            existing_ids.add(s["ticker"].lower())
            existing_ids.add(s["name"].lower())
            for part in s["name"].split():
                if len(part) > 3:
                    existing_ids.add(part.lower())

    ignored = {
        "india",
        "delhi",
        "mumbai",
        "pib",
        "union",
        "minister",
        "cabinet",
        "government",
        "ministry",
        "national",
        "state",
        "budget",
        "digital",
        "system",
        "centre",
        "center",
        "sebi",
        "rbi",
        "nse",
        "bse",
        "parliament",
        "supreme",
        "court",
        "railways",
        # Honorifics — headlines about officials ("Shri Amit Shah launches…")
        # must not reach ticker resolution as company candidates.
        "shri",
        "smt",
        "sri",
        "dr",
        "pm",
        "cm",
    }
    corp_pattern = re.compile(
        r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+(?:Ltd|Limited|Corp|Corporation|Technologies|Enterprises|Solutions|Infrastructure)\b"
    )
    # Headlines rarely spell out corporate suffixes ("Dixon wins order", not
    # "Dixon Technologies Ltd wins order"), so also catch capitalized names
    # followed by a competitive verb. Precision is preserved downstream: every
    # candidate still has to survive ticker resolution and the growth gate.
    corp_verb_pattern = re.compile(
        r"\b([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+){0,2})\s+"
        r"(?:[Ww]ins|[Bb]ags|[Ss]ecures|[Ll]aunches|[Uu]nveils|[Aa]cquires|"
        r"[Pp]artners|[Cc]ommissions|[Ee]xpands)\b"
    )

    for sector, news_items in brief_data.items():
        if sector == "emerging_players":
            continue
        detected = []
        for item in news_items:
            title = item["title"]
            candidates = [
                (m.group(1), m.group(0)) for m in corp_pattern.finditer(title)
            ]
            # The verb itself is not part of the company name.
            candidates += [
                (m.group(1), m.group(1)) for m in corp_verb_pattern.finditer(title)
            ]
            for captured, full in candidates:
                captured_lower = captured.lower()
                tokens = captured_lower.split()
                if (
                    captured_lower not in existing_ids
                    and len(captured) >= 3
                    and all(tok not in ignored for tok in tokens)
                ):
                    if full not in detected:
                        detected.append(full)
                        log.info(f"Detected emerging player in {sector}: {full}")
        if detected:
            emerging_players[sector] = detected

    return emerging_players


def _get_potential(stock):
    try:
        return float(stock["growth_pct"].replace("%", ""))
    except Exception:
        return 0.0


def auto_curate_watchlist(brief_data, watchlist):
    """Discovers emerging competitors and rotates underperforming stocks.

    Returns (structured_emerging, decisions): the emerging-player radar dict,
    and a list of {action, sector, stock} for every add/rotate this run —
    the raw material for the rotation post-mortem ledger in
    analysis/postmortem.py.
    """
    log.info("Starting automated watchlist curation and rotation cycle...")
    from config import SECTOR_METADATA

    emerging_sectors = detect_emerging_players(brief_data, watchlist)
    rotations_log = []
    decisions = []

    # We will construct a structured emerging_players dictionary
    structured_emerging = {s: [] for s in SECTOR_METADATA}

    # ⚡ Bolt Optimization: Pre-flatten watchlist to avoid O(n^2) loop
    watchlisted_tickers = {
        s["ticker"] for s_list in watchlist.values() for s in s_list if s.get("ticker")
    }

    with requests.Session() as session:
        for sector, companies in emerging_sectors.items():
            if sector not in watchlist:
                continue

            for name in companies:
                log.info(f"Evaluating candidate company: {name} in {sector}")
                ticker, full_name = resolve_ticker_from_name(name, session=session)
                if not ticker:
                    log.info(f"Could not resolve ticker for: {name}. Skipping.")
                    structured_emerging[sector].append(
                        {
                            "name": name,
                            "ticker": None,
                            "status": "Unresolved",
                            "reason": "Could not map company name to a BSE/NSE ticker.",
                        }
                    )
                    continue

                already_watchlisted = ticker in watchlisted_tickers
                if already_watchlisted:
                    log.info(f"Ticker {ticker} is already in watchlist. Skipping.")
                    structured_emerging[sector].append(
                        {
                            "name": full_name or name,
                            "ticker": ticker,
                            "status": "Watchlisted",
                            "reason": f"Already present in the {sector} watchlist.",
                        }
                    )
                    continue

                yahoo_ticker = f"{ticker}.NS"
                try:
                    # The pooled session is only for Screener/resolution calls;
                    # yfinance manages its own session (see providers/yahoo.py).
                    ticker_obj = get_cached_ticker(yahoo_ticker)
                    hist = ticker_obj.history(period="1d", timeout=10)
                    if hist.empty:
                        log.info(
                            f"No market data for {yahoo_ticker}. Skipping candidate."
                        )
                        structured_emerging[sector].append(
                            {
                                "name": full_name or name,
                                "ticker": ticker,
                                "status": "Unresolved",
                                "reason": "BSE/NSE ticker resolved, but no market trading history found.",
                            }
                        )
                        continue

                    live_price = float(hist["Close"].iloc[-1])
                    info = ticker_obj.info or {}

                    consensus_target = info.get("targetMeanPrice")
                    if consensus_target and float(consensus_target) > 0:
                        target_price = float(consensus_target)
                    else:
                        target_price = live_price * 1.25

                    growth_pct_val = ((target_price - live_price) / live_price) * 100
                    rating = (
                        info.get("recommendationKey", "N/A").replace("_", " ").title()
                    )

                    rev_growth_raw = info.get("revenueGrowth")
                    revenue_growth = (
                        f"{float(rev_growth_raw) * 100:.1f}%"
                        if rev_growth_raw is not None
                        else None
                    )

                    # Fetch candidate QoQ growth from Screener (using pooled session)
                    candidate_qoq_growth = 0.0
                    try:
                        url = f"https://www.screener.in/company/{ticker}/consolidated/"
                        r = session.get(
                            url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
                        )
                        if r.status_code != 200:
                            url = f"https://www.screener.in/company/{ticker}/"
                            r = session.get(
                                url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
                            )
                        if r.status_code == 200:
                            html = r.text
                            qs_match = re.search(
                                r'id="quarters"(.*?)(?:</section>)', html, re.DOTALL
                            )
                            if qs_match:
                                qs = qs_match.group(1)
                                row_match = re.search(r"Sales.*?</tr>", qs, re.DOTALL)
                                if row_match:
                                    vals = re.findall(
                                        r"<td[^>]*>\s*([\d,\.\-]+)\s*</td>",
                                        row_match.group(0),
                                    )
                                    if len(vals) >= 2:
                                        s1 = float(vals[-1].replace(",", ""))
                                        s2 = float(vals[-2].replace(",", ""))
                                        if s2 > 0:
                                            candidate_qoq_growth = (
                                                (s1 - s2) / s2
                                            ) * 100
                    except Exception as e:
                        log.error(
                            f"Error checking candidate QoQ growth on Screener: {e}"
                        )

                    # Eligibility check:
                    is_eligible = growth_pct_val > 0
                    if rev_growth_raw is not None and rev_growth_raw < 0:
                        is_eligible = False
                    if candidate_qoq_growth < 15.0:
                        is_eligible = False

                    if not is_eligible:
                        log.info(
                            f"Candidate {ticker} did not meet positive growth criteria. Skipping."
                        )
                        reason_str = (
                            "Negative target potential"
                            if growth_pct_val <= 0
                            else (
                                f"Failed growth criteria (YoY revenue {revenue_growth})"
                                if rev_growth_raw is not None and rev_growth_raw < 0
                                else f"Failed QoQ growth threshold ({candidate_qoq_growth:.1f}% < 15%)"
                            )
                        )
                        structured_emerging[sector].append(
                            {
                                "name": full_name or name,
                                "ticker": ticker,
                                "status": "Growth Divergence",
                                "reason": reason_str,
                            }
                        )
                        continue

                    related_headline = f"Policy tailwinds in the {sector} segment."
                    for item in brief_data.get(sector, []):
                        if name.lower() in item["title"].lower():
                            related_headline = item["title"]
                            break

                    candidate_stock = {
                        "ticker": ticker,
                        "name": full_name,
                        "price": f"{live_price:.2f}",
                        "target": f"{target_price:.2f}",
                        "growth_pct": f"{growth_pct_val:.1f}%",
                        "catalyst": f"Auto-discovered via media radar. Catalyst: {related_headline}",
                        "rating": rating,
                        "revenue_growth": revenue_growth,
                    }

                    current_watchlist = watchlist[sector]
                    if len(current_watchlist) < 5:
                        current_watchlist.append(candidate_stock)
                        watchlisted_tickers.add(ticker)
                        log.info(
                            f"ADDED: {ticker} to {sector} (Space available: {len(current_watchlist)}/5)"
                        )
                        rotations_log.append(
                            f"Added {full_name} ({ticker}) to {sector}"
                        )
                        decisions.append(
                            {
                                "action": "added",
                                "sector": sector,
                                "stock": dict(candidate_stock),
                            }
                        )
                        structured_emerging[sector].append(
                            {
                                "name": full_name,
                                "ticker": ticker,
                                "status": "Watchlisted",
                                "reason": "Added to watchlist (new high-growth pick).",
                                "qoq_growth": round(candidate_qoq_growth, 1),
                            }
                        )
                    else:

                        def get_potential(stock):
                            try:
                                return float(stock["growth_pct"].replace("%", ""))
                            except Exception:
                                return 0.0

                        sorted_watchlist = sorted(current_watchlist, key=get_potential)
                        weakest_stock = sorted_watchlist[0]
                        weakest_potential = get_potential(weakest_stock)

                        if growth_pct_val > weakest_potential:
                            watchlist[sector] = [
                                x
                                for x in current_watchlist
                                if x["ticker"] != weakest_stock["ticker"]
                            ]
                            watchlist[sector].append(candidate_stock)
                            watchlisted_tickers.discard(weakest_stock["ticker"])
                            watchlisted_tickers.add(ticker)
                            log.info(
                                f"ROTATED: Replaced {weakest_stock['ticker']} with {ticker}"
                            )
                            rotations_log.append(
                                f"Rotated {weakest_stock['name']} out for {full_name} in {sector}"
                            )
                            decisions.append(
                                {
                                    "action": "rotated_in",
                                    "sector": sector,
                                    "stock": dict(candidate_stock),
                                }
                            )
                            structured_emerging[sector].append(
                                {
                                    "name": full_name,
                                    "ticker": ticker,
                                    "status": "Watchlisted",
                                    "reason": f"Rotated into watchlist replacing {weakest_stock['ticker']}.",
                                    "qoq_growth": round(candidate_qoq_growth, 1),
                                }
                            )
                        else:
                            log.info(
                                f"Candidate {ticker} (Upside: {growth_pct_val:.1f}%) did not outperform the weakest watchlist pick {weakest_stock['ticker']} (Upside: {weakest_potential:.1f}%). Skipping rotation."
                            )
                            structured_emerging[sector].append(
                                {
                                    "name": full_name,
                                    "ticker": ticker,
                                    "status": "Pipeline",
                                    "reason": f"Pipeline candidate (Upside {growth_pct_val:.1f}% vs weakest watchlisted {weakest_potential:.1f}%).",
                                    "qoq_growth": round(candidate_qoq_growth, 1),
                                }
                            )

                except Exception as e:
                    log.error(f"Error checking financials for {yahoo_ticker}: {e}")
                    structured_emerging[sector].append(
                        {
                            "name": name,
                            "ticker": ticker,
                            "status": "Unresolved",
                            "reason": f"Error parsing Yahoo Finance info: {str(e)}",
                        }
                    )

    if rotations_log:
        save_watchlist(watchlist)

    return structured_emerging, decisions
