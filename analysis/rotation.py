import re
from concurrent.futures import ThreadPoolExecutor

from logger import log
from config import save_watchlist
from entities import build_entity_master, resolve_entity_by_isin
from providers.isin_master import load_isin_master, load_registered_names
from providers.yahoo import consensus_target, get_cached_ticker, has_analyst_consensus
from utils import thread_local_session, to_float
from .company_names import tidy_name
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


# Ceiling on watchlist changes (additions plus rotations) in a single run.
# The per-sector cap of five is not a brake on intake: with the fundamental
# screen feeding pre-resolved candidates, measured headroom across the
# watchlist was 16 additions in one pass — a 29% expansion of the portfolio
# in a morning, chosen by a screen with no production track record. Worse, it
# compounds, because each new holding anchors another industry peer table and
# so produces more candidates next run. Capping intake makes the screen ramp
# in over weeks, leaving every name reviewable, and costs nothing: deferred
# candidates are re-screened every run and simply arrive later.
MAX_INTAKE_PER_RUN = 3

# Candidates whose network lookups are issued together before the sequential
# decision pass runs over them.
#
# Batched rather than prefetching the whole queue, because the intake cap is
# the reason this loop is cheap: once it is reached, every remaining candidate
# is deferred without a single request. Prefetching everything would trade a
# latency win for a large increase in load on Screener, which already answers
# this pipeline with 429s. Wasted lookups are bounded to at most one batch.
PREFETCH_BATCH = 6


# The growth a candidate's latest quarter must show over the same quarter a
# year earlier. It replaced a 15% bar on the quarter before, which seasons
# decide: a hotel's April-June quarter, a footwear or textile maker's
# off-season. On 22 Oct 2026 that bar turned away 29 of the 31 candidates it
# saw, BDL among them at +130.8% on the year. The screen that hands most of
# them over (analysis/candidate_screen.py) measures growth on the year too.
MIN_SALES_YOY_PCT = 15.0

_QUARTER_RE = re.compile(r"^([A-Za-z]{3})[a-z]*\.?\s+(\d{4})$")


def _screener_quarterly_sales(session, ticker):
    """``[(quarter, sales), ...]`` from the candidate's Screener page, oldest
    first; None when no page showed figures.

    Read as providers/screener.py reads a holding: the consolidated
    accounts, then the standalone ones when the consolidated page is not
    there or shows no figures, and a lender's "Revenue" line as its sales.
    This used a regex of its own that knew neither, and answered 0.0 for
    anything it could not read: on 22 Oct 2026 ten candidates, three banks
    among them, were turned away at a "growth" of exactly 0.0%.

    Errors are swallowed, as before: a page that cannot be read leaves the
    candidate unmeasured, never the run failed.
    """
    from bs4 import BeautifulSoup
    from providers.screener import ACCOUNTS, SALES_ROW, company_url
    from .parsing import extract_row_by_column

    for accounts in ACCOUNTS:
        try:
            r = session.get(
                company_url(ticker, accounts),
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
        except Exception as e:  # noqa: BLE001 - one candidate, not the run
            log.warning(f"{ticker}: Screener {accounts} page not read: {e!r}")
            return None
        if r.status_code == 404:
            continue
        if r.status_code != 200:
            # After a 429 or a 403 the other view would meet the same answer.
            log.info(f"{ticker}: Screener {accounts} page: HTTP {r.status_code}.")
            return None
        quarters = extract_row_by_column(
            BeautifulSoup(r.text, "lxml"), "quarters", SALES_ROW
        )
        if quarters:
            return quarters
    return None


def _quarter_key(label):
    match = _QUARTER_RE.match(str(label or "").strip())
    return (match.group(1).lower(), int(match.group(2))) if match else None


def _sales_yoy(quarters):
    """The latest quarter's sales against the same quarter a year earlier, in
    percent; None when that quarter is not on the page or was not positive.
    Matched by column header, so a blank column cannot pair the wrong two."""
    if not quarters:
        return None
    latest = _quarter_key(quarters[-1][0])
    if latest is None:
        return None
    month, year = latest
    base = next(
        (
            value
            for label, value in quarters
            if _quarter_key(label) == (month, year - 1)
        ),
        None,
    )
    if base is None or base <= 0:
        return None
    return round((quarters[-1][1] - base) / base * 100, 1)


def _sales_qoq(quarters):
    """Sales growth on the quarter before, as the competitive-threat warning
    compares challengers (analysis/early_warning.py); None without two
    quarters or a positive base."""
    if not quarters or len(quarters) < 2 or quarters[-2][1] <= 0:
        return None
    return round((quarters[-1][1] - quarters[-2][1]) / quarters[-2][1] * 100, 1)


def _probe_candidate(name, preresolved, isin_master, watchlisted=()):
    """Every network call for one candidate, and nothing that decides anything.

    Split out so these can run concurrently. What stays OUT of here is the
    point: the intake cap, the watchlist-membership check and the ISIN
    duplicate check all depend on decisions made about EARLIER candidates in
    the same run, so evaluating them concurrently would change which
    candidates get admitted. This returns facts; the caller still decides in
    order.
    """
    # Own session per thread: requests.Session is not thread-safe, and these
    # run in a pool. See utils.thread_local_session.
    session = thread_local_session()

    probe = {"ticker": None, "full_name": name, "error": None}

    if preresolved:
        ticker, full_name = preresolved, name
    else:
        ticker, full_name = resolve_ticker_from_name(name, session=session)
    if not ticker:
        probe["error"] = "unresolved"
        return probe

    probe["ticker"] = ticker
    probe["full_name"] = full_name or name
    probe["isin"] = isin_master.get(ticker)

    # Stop before the market-data call for something already held. The
    # sequential version checked this between resolving and pricing, and a
    # test pins that an existing holding costs zero quote requests — batching
    # the two calls together quietly broke it. ``watchlisted`` is a snapshot:
    # it only changes in the decision pass, which runs after this one, and the
    # caller re-probes if a rotation frees the ticker in between.
    if ticker in watchlisted:
        probe["error"] = "watchlisted"
        return probe

    try:
        # The pooled session is only for Screener/resolution calls; yfinance
        # manages its own session (see providers/yahoo.py).
        ticker_obj = get_cached_ticker(f"{ticker}.NS")
        hist = ticker_obj.history(period="1d", timeout=10)
        if hist.empty:
            probe["error"] = "no_market_data"
            return probe

        live_price = float(hist["Close"].iloc[-1])
        info = ticker_obj.info or {}

        # The analysts' target, read as a holding's is, or none. A candidate
        # no analyst covers used to be given price x 1.25: a made-up 25% that
        # passed the potential check by construction and outbid every holding
        # below it. 31 of the ledger's first 64 decisions came in that way.
        target_price = consensus_target(info)

        rev_growth_raw = info.get("revenueGrowth")
        from analysis.sector_fit import keywords

        probe.update(
            {
                # What the company does, for the sector-fit check in the
                # decision pass (analysis/sector_fit.py).
                "industry": info.get("industry"),
                "keywords": keywords(info.get("longBusinessSummary")),
                "live_price": live_price,
                "target_price": target_price,
                "growth_pct_val": (
                    (target_price - live_price) / live_price * 100
                    if target_price
                    else None
                ),
                "rating": info.get("recommendationKey", "N/A")
                .replace("_", " ")
                .title(),
                "rev_growth_raw": rev_growth_raw,
                "revenue_growth": (
                    f"{float(rev_growth_raw) * 100:.1f}%"
                    if rev_growth_raw is not None
                    else None
                ),
            }
        )
    except Exception as e:  # noqa: BLE001 - reported per candidate, not raised
        probe["error"] = "fetch_failed"
        probe["exception"] = str(e)
        return probe

    quarters = _screener_quarterly_sales(session, ticker)
    probe["sales_yoy"] = _sales_yoy(quarters)
    probe["qoq_growth"] = _sales_qoq(quarters)
    return probe


def _get_potential(stock):
    # to_float handles every historical growth_pct format ("+23.0%", 23.0,
    # None) — the old string-only parse silently returned 0.0 the moment
    # the field held a number instead of a string, ranking every stock
    # equally weakest.
    value = to_float(stock.get("growth_pct"))
    return 0.0 if value is None else value


# A holding no analyst covers has no upside to compare: its growth_pct is the
# pipeline's own Graham estimate, clamped at -50%, which made it every
# sector's weakest pick. Optiemus and Birla Cable replaced each other 23
# times in a month that way. Such a holding goes only on a huge upset: its
# thesis Broken (analysis/thesis.py) on this many runs in a row.
HUGE_UPSET_RUNS = 5


def _broken_runs(stock):
    return int(to_float(stock.get("thesis_broken_runs")) or 0)


def _replaceable(holdings, candidate_upside):
    """``(holding, why)``: the holding a candidate may replace, or None and
    why not. Upside is compared only between analysts' targets."""
    upset = [
        s
        for s in holdings
        if not has_analyst_consensus(s) and _broken_runs(s) >= HUGE_UPSET_RUNS
    ]
    if upset:
        worst = max(upset, key=_broken_runs)
        return worst, f"its thesis has been Broken for {_broken_runs(worst)} runs"
    if candidate_upside is None:
        return None, "no analyst target, so no upside to set against a holding's"
    covered = [s for s in holdings if has_analyst_consensus(s)]
    if not covered:
        return None, "no holding here has an analyst target to compare with"
    weakest = min(covered, key=_get_potential)
    potential = _get_potential(weakest)
    if candidate_upside > potential:
        return weakest, f"upside {candidate_upside:.1f}% against {potential:.1f}%"
    return None, (
        f"upside {candidate_upside:.1f}% did not beat the weakest covered pick "
        f"{weakest['ticker']} ({potential:.1f}%)"
    )


def auto_curate_watchlist(brief_data, watchlist, screened_candidates=None):
    """Discovers emerging competitors and rotates underperforming stocks.

    Candidates come from two places: names extracted from sector headlines,
    and — via ``screened_candidates`` — listed peers that cleared the
    fundamental gates in analysis/candidate_screen.py. The second source
    exists because the first depends on a company being written about and
    then correctly name-resolved, which is why a competitor as visible as
    Syrma sat in the peer radar for months without ever being evaluated.

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
    # ISIN-keyed index of current holdings — catches a candidate that is
    # actually an existing holding resurfacing under a different symbol or
    # name spelling, which the ticker-string check below can't see.
    entity_master = build_entity_master(watchlist)
    isin_master = load_isin_master()
    registered_names = load_registered_names()

    # We will construct a structured emerging_players dictionary
    structured_emerging = {s: [] for s in SECTOR_METADATA}

    watchlisted_tickers = {x["ticker"] for s_list in watchlist.values() for x in s_list}

    # Headline-derived names arrive unresolved; screened peers arrive with a
    # ticker Screener already gave us. Both are evaluated by the same gates
    # below — the only difference is that the screened ones skip a name
    # lookup that discards most headline candidates.
    #
    # One flat queue rather than a per-sector loop, because the intake cap
    # below makes evaluation order matter: iterating sectors would hand every
    # slot to whichever sector sorts first and starve the rest. Headline names
    # go first (they are few and event-driven), then screened peers strongest
    # first, so the cap spends its slots on the best candidates available
    # anywhere.
    queue = [
        (sector, name, None)
        for sector, names in emerging_sectors.items()
        for name in names
        if sector in watchlist
    ]
    seen_names = {(s, n.lower()) for s, n, _ in queue}
    screened_queue = []
    for sector, rows in (screened_candidates or {}).items():
        if sector not in watchlist:
            continue
        for row in rows or []:
            name = row.get("name") or ""
            if (sector, name.lower()) in seen_names:
                continue
            screened_queue.append(
                (
                    sector,
                    name,
                    row.get("ticker"),
                    to_float(row.get("growth_pct")) or 0.0,
                )
            )
    screened_queue.sort(key=lambda c: c[3], reverse=True)
    queue.extend((s, n, t) for s, n, t, _ in screened_queue)

    intake = 0
    # One probe per company per run, shared by every sector it comes up in.
    # Hitachi Energy sat in two sectors' peer tables on 23 Oct 2026 and was
    # probed twice at once: Yahoo gave one probe no analyst target and the
    # other a 39.8% upside, so the same company was judged on two readings.
    probed = {}

    def probe_key(candidate):
        return (candidate[2] or "").upper() or candidate[1].strip().lower()

    # Batched: probe a handful of candidates concurrently, then decide over
    # them in queue order. The decision pass is deliberately sequential —
    # the intake cap, watchlisted_tickers and the per-sector slot count all
    # change as candidates are admitted, so deciding concurrently would
    # change WHICH candidates get in, which is a behaviour change dressed
    # as a speed-up.
    for offset in range(0, len(queue), PREFETCH_BATCH):
        chunk = queue[offset : offset + PREFETCH_BATCH]

        if intake >= MAX_INTAKE_PER_RUN:
            # Cap already reached: defer the rest without a single request,
            # exactly as the sequential version did.
            probes = [None] * len(chunk)
        else:
            # Snapshot taken before the pool starts, so every probe in a
            # batch sees the same membership.
            snapshot = frozenset(watchlisted_tickers)
            fresh = {}
            for candidate in chunk:
                if probe_key(candidate) not in probed:
                    fresh.setdefault(probe_key(candidate), candidate)
            if fresh:
                with ThreadPoolExecutor(
                    max_workers=min(PREFETCH_BATCH, len(fresh))
                ) as pool:
                    results = list(
                        pool.map(
                            lambda c: _probe_candidate(
                                c[1], c[2], isin_master, snapshot
                            ),
                            fresh.values(),
                        )
                    )
                for key, result in zip(fresh, results):
                    probed[key] = result
                    # A headline name resolves to the ticker a screened
                    # peer arrives with: one probe serves both.
                    if result.get("ticker"):
                        probed.setdefault(str(result["ticker"]).upper(), result)
            probes = [probed[probe_key(c)] for c in chunk]

        for (sector, name, preresolved), probe in zip(chunk, probes):
            if intake >= MAX_INTAKE_PER_RUN:
                structured_emerging.setdefault(sector, []).append(
                    {
                        "name": name,
                        "ticker": preresolved,
                        "status": "Deferred",
                        "reason": (
                            f"Run intake cap reached ({MAX_INTAKE_PER_RUN} "
                            "watchlist changes); will be reconsidered next run."
                        ),
                    }
                )
                continue

            log.info(f"Evaluating candidate company: {name} in {sector}")
            ticker = probe["ticker"]
            # The name it would be held under. A screened peer arrives with
            # Screener's cut-down label ("NTPC Green Ene."), which matched no
            # headline; NSE's registered name replaces it
            # (analysis/company_names.py).
            full_name = tidy_name(
                probe["full_name"] or name, registered_names.get(ticker)
            )

            if probe["error"] == "unresolved":
                log.info(f"Could not resolve ticker for: {name}. Skipping.")
                structured_emerging.setdefault(sector, []).append(
                    {
                        "name": name,
                        "ticker": None,
                        "status": "Unresolved",
                        "reason": "Could not map company name to a BSE/NSE ticker.",
                    }
                )
                continue

            if probe["error"] == "watchlisted" and ticker not in watchlisted_tickers:
                # Rotated out earlier in this same batch, so it is a live
                # candidate again and was never priced. Rare; probe now.
                probe = _probe_candidate(name, ticker, isin_master, watchlisted_tickers)

            if ticker in watchlisted_tickers:
                log.info(f"Ticker {ticker} is already in watchlist. Skipping.")
                structured_emerging.setdefault(sector, []).append(
                    {
                        "name": full_name or name,
                        "ticker": ticker,
                        "status": "Watchlisted",
                        "reason": f"Already present in the {sector} watchlist.",
                    }
                )
                continue

            if probe["error"] == "no_market_data":
                log.info(f"No market data for {ticker}.NS. Skipping candidate.")
                structured_emerging.setdefault(sector, []).append(
                    {
                        "name": full_name or name,
                        "ticker": ticker,
                        "status": "Unresolved",
                        "reason": "BSE/NSE ticker resolved, but no market trading history found.",
                    }
                )
                continue

            if probe["error"] == "fetch_failed":
                log.error(
                    f"Error checking financials for {ticker}.NS: "
                    f"{probe.get('exception')}"
                )
                structured_emerging.setdefault(sector, []).append(
                    {
                        "name": name,
                        "ticker": ticker,
                        "status": "Unresolved",
                        "reason": f"Error parsing Yahoo Finance info: {probe.get('exception')}",
                    }
                )
                continue

            try:
                live_price = probe["live_price"]
                target_price = probe["target_price"]
                growth_pct_val = probe["growth_pct_val"]
                rating = probe["rating"]
                rev_growth_raw = probe["rev_growth_raw"]
                revenue_growth = probe["revenue_growth"]
                candidate_qoq_growth = probe.get("qoq_growth")
                sales_yoy = probe.get("sales_yoy")
                candidate_isin = probe["isin"]

                existing_entity = resolve_entity_by_isin(candidate_isin, entity_master)
                if existing_entity and existing_entity["ticker"] != ticker:
                    log.info(
                        f"Candidate {ticker} shares ISIN {candidate_isin} with "
                        f"existing holding {existing_entity['ticker']} "
                        f"({existing_entity['sector']}). Skipping as duplicate."
                    )
                    structured_emerging.setdefault(sector, []).append(
                        {
                            "name": full_name or name,
                            "ticker": ticker,
                            "status": "Watchlisted",
                            "reason": (
                                f"Already tracked as {existing_entity['ticker']} "
                                f"in {existing_entity['sector']} "
                                f"(same ISIN {candidate_isin})."
                            ),
                        }
                    )
                    continue

                # Eligibility check. Target potential is judged only where
                # analysts set a target; without one, the growth tests decide.
                status = None
                if growth_pct_val is not None and growth_pct_val <= 0:
                    status, reason_str = (
                        "Growth Divergence",
                        "Negative target potential",
                    )
                elif rev_growth_raw is not None and rev_growth_raw < 0:
                    status = "Growth Divergence"
                    reason_str = (
                        f"Failed growth criteria (YoY revenue {revenue_growth})"
                    )
                elif sales_yoy is None:
                    # Not a failure to grow: no figures were read, so there is
                    # nothing to admit it on, and saying 0.0% would be a guess.
                    status = "Unresolved"
                    reason_str = (
                        "Quarterly sales not read from Screener, so growth is "
                        "not measured"
                    )
                elif sales_yoy < MIN_SALES_YOY_PCT:
                    status = "Growth Divergence"
                    reason_str = (
                        f"Quarterly sales {sales_yoy:+.1f}% on the same quarter "
                        f"last year, under the {MIN_SALES_YOY_PCT:.0f}% bar"
                    )

                if status:
                    log.info(f"Candidate {ticker} not eligible: {reason_str}.")
                    structured_emerging.setdefault(sector, []).append(
                        {
                            "name": full_name or name,
                            "ticker": ticker,
                            "status": status,
                            "reason": reason_str,
                        }
                    )
                    continue

                # Sector fit: the candidate inherited the sector of the feed
                # or peer table that surfaced it, which says nothing about
                # what it does — Godrej Properties reached Data Center
                # Support as a real-estate peer of Anant Raj. Keep it where
                # it fits, move it to the one sector it does fit, or refuse.
                from analysis.sector_fit import place

                found_in = sector
                placed, fit_reason = place(
                    sector, probe.get("industry"), probe.get("keywords"), watchlist
                )
                if placed is None:
                    log.info(f"Candidate {ticker} refused: {fit_reason}.")
                    structured_emerging.setdefault(found_in, []).append(
                        {
                            "name": full_name or name,
                            "ticker": ticker,
                            "status": "Sector Mismatch",
                            "reason": f"Not added: {fit_reason}.",
                        }
                    )
                    continue
                if placed != found_in:
                    log.info(
                        f"Candidate {ticker} found via {found_in} placed in "
                        f"{placed}: {fit_reason}."
                    )
                    sector = placed

                related_headline = f"Policy tailwinds in the {sector} segment."
                name_lower = name.lower()
                for item in brief_data.get(sector, []):
                    if name_lower in item["title"].lower():
                        related_headline = item["title"]
                        break

                candidate_stock = {
                    "ticker": ticker,
                    "name": full_name,
                    "price": f"{live_price:.2f}",
                    # Only the analysts' target. Without one the holding
                    # takes the pipeline's own estimate later in the run
                    # (dashboard/builder.py), marked as such.
                    **(
                        {
                            "target": f"{target_price:.2f}",
                            "growth_pct": f"{growth_pct_val:.1f}%",
                        }
                        if target_price
                        else {}
                    ),
                    "catalyst": f"Auto-discovered via media radar. Catalyst: {related_headline}",
                    "rating": rating,
                    "revenue_growth": revenue_growth,
                    **(
                        {"yahoo_industry": probe["industry"]}
                        if probe.get("industry")
                        else {}
                    ),
                    **(
                        {"business_keywords": probe["keywords"]}
                        if probe.get("keywords")
                        else {}
                    ),
                }

                current_watchlist = watchlist[sector]
                if len(current_watchlist) < 5:
                    current_watchlist.append(candidate_stock)
                    watchlisted_tickers.add(ticker)
                    intake += 1
                    log.info(
                        f"ADDED: {ticker} to {sector} (Space available: {len(current_watchlist)}/5)"
                    )
                    rotations_log.append(f"Added {full_name} ({ticker}) to {sector}")
                    decisions.append(
                        {
                            "action": "added",
                            "sector": sector,
                            "stock": dict(candidate_stock),
                        }
                    )
                    structured_emerging.setdefault(sector, []).append(
                        {
                            "name": full_name,
                            "ticker": ticker,
                            "status": "Watchlisted",
                            "reason": "Added to watchlist (new high-growth pick).",
                            "qoq_growth": candidate_qoq_growth,
                            "sales_yoy": sales_yoy,
                        }
                    )
                else:
                    weakest_stock, why = _replaceable(current_watchlist, growth_pct_val)

                    if weakest_stock is not None:
                        watchlist[sector] = [
                            x
                            for x in current_watchlist
                            if x["ticker"] != weakest_stock["ticker"]
                        ]
                        watchlist[sector].append(candidate_stock)
                        watchlisted_tickers.remove(weakest_stock["ticker"])
                        watchlisted_tickers.add(ticker)
                        intake += 1
                        log.info(
                            f"ROTATED: Replaced {weakest_stock['ticker']} with "
                            f"{ticker}: {why}."
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
                        structured_emerging.setdefault(sector, []).append(
                            {
                                "name": full_name,
                                "ticker": ticker,
                                "status": "Watchlisted",
                                "reason": f"Rotated into watchlist replacing {weakest_stock['ticker']}.",
                                "qoq_growth": candidate_qoq_growth,
                                "sales_yoy": sales_yoy,
                            }
                        )
                    else:
                        log.info(
                            f"Candidate {ticker} not rotated in: {why}. Skipping rotation."
                        )
                        structured_emerging.setdefault(sector, []).append(
                            {
                                "name": full_name,
                                "ticker": ticker,
                                "status": "Pipeline",
                                "reason": f"Pipeline candidate: {why}.",
                                "qoq_growth": candidate_qoq_growth,
                                "sales_yoy": sales_yoy,
                            }
                        )

            except Exception as e:
                log.error(f"Error checking financials for {ticker}.NS: {e}")
                structured_emerging.setdefault(sector, []).append(
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
