import asyncio
import datetime
import sys
import aiohttp
from config import load_watchlist, save_watchlist, SECTOR_METADATA
from logger import log
from scraper import (
    fetch_all_feeds_async,
    fetch_global_event_feeds_async,
    scrape_pib_pli_approvals_async,
    fetch_advanced_rss_feeds_async,
    check_sebi_sid_filings_async,
    fetch_institutional_activity_async,
    fetch_exchange_filings_async,
)
from analysis.growth import update_live_stock_prices, apply_liquidity
from analysis.rotation import auto_curate_watchlist
from dashboard.builder import build_dashboard_views
from providers.screener import fetch_all_screener_fundamentals
from emails.mailer import build_briefing_email, send_email
from analysis import revisions as revisions_mod
from analysis import postmortem
from analysis.thesis import compute_thesis_health
from analysis.variant_perception import compute_variant_perception
from analysis.curve_stage import classify_sector_curve_stage
from analysis.market_share import (
    compute_industry_share,
    snapshot_prior_industry_shares,
)
from entities import find_duplicate_holdings
from providers.isin_master import (
    load_isin_master,
    refresh_isin_master_async,
    annotate_watchlist_isins,
)


def save_data_for_dashboard(brief_data, watchlist):
    """Write the run's two outputs.

    history.json keeps the full corpus for the next run's deduplication and
    for the four consumers that read the accumulated feeds; dashboard_data.json
    carries a trimmed display copy, because the browser downloads it whole on
    every page load. Splitting them means nothing done for the dashboard's
    sake can shrink what the pipeline computes on.
    """
    from dashboard.payload import build_display_payload
    from history.store import HistoryStore
    from utils import atomic_write_json

    HistoryStore().save(brief_data)

    output = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watchlist": watchlist,
        "sectors": SECTOR_METADATA,
        "briefing": build_display_payload(brief_data, watchlist),
    }
    atomic_write_json(output, "dashboard_data.json")

    log.info(
        "SUCCESS: Updated data saved to 'dashboard_data.json' for web dashboard display."
    )


async def run_pipeline():
    # NOTE: this pipeline intentionally mixes two concurrency models:
    # asyncio/aiohttp for the scrapers and Screener, and
    # ThreadPoolExecutor/requests for yfinance (which is sync-only).
    # Don't refactor one into the other — yfinance can't be awaited, and the
    # scrapers gain nothing from threads.
    watchlist = load_watchlist()

    # Stamp each holding's ISIN from the committed symbol→ISIN master so
    # identity-keyed features (rotation's duplicate guard, the duplicate-
    # holding check below) work from the first line of the run, offline.
    isin_master = load_isin_master()
    annotate_watchlist_isins(watchlist, isin_master)

    # Snapshot targets/coverage before anything mutates the watchlist, so
    # estimate-revision momentum can diff "before this run" vs "after".
    prior_estimates = revisions_mod.snapshot_prior_estimates(watchlist)
    prior_industry_shares = snapshot_prior_industry_shares(watchlist)

    # Gather news data async
    data = await fetch_all_feeds_async()

    # Rotation runs before the Screener fetch (so anything it adds gets
    # fundamentals the same run), which means this run's peer tables do not
    # exist yet. The previous run's are already committed in
    # dashboard_data.json and are screened on quarterly fundamentals, so a
    # day of staleness costs nothing.
    from history.store import HistoryStore
    from analysis.candidate_screen import (
        candidates_for_rotation,
        screen_sector_candidates,
    )

    prior = HistoryStore().data.get("briefing", {})
    prior_screened = screen_sector_candidates(
        prior.get("peer_competitors") or {},
        known_symbols=set(isin_master),
    )

    # Auto-curate the watchlist (discovers emerging players and rotates stocks)
    emerging, rotation_decisions = auto_curate_watchlist(
        data, watchlist, screened_candidates=candidates_for_rotation(prior_screened)
    )
    data["emerging_players"] = emerging

    rotation_ledger = postmortem.load_ledger()
    for decision in rotation_decisions:
        postmortem.log_decision(
            rotation_ledger, decision["action"], decision["sector"], decision["stock"]
        )

    # Fetch live Yahoo Finance prices
    data["freshness"] = {"live_prices": update_live_stock_prices(watchlist)}

    # Fetch Screener.in fundamentals async; also returns Screener's industry
    # peer tables — a competitor-discovery channel independent of headlines.
    peer_competitors, industry_tables = await fetch_all_screener_fundamentals(watchlist)
    data["peer_competitors"] = peer_competitors or {}
    data["candidate_screen"] = screen_sector_candidates(
        peer_competitors or {}, known_symbols=set(isin_master)
    )

    # The Screener fetch rebuilds each stock's screener dict from scratch,
    # dropping the ISIN stamped above — re-annotate so identity survives
    # into the duplicate check and the committed watchlist.
    isin_covered = annotate_watchlist_isins(watchlist, isin_master)
    log.info(f"ISIN coverage: {isin_covered} holdings keyed by ISIN.")

    # Turnover is re-applied here for the same reason ISIN is: it was computed
    # during the price fetch above, and the Screener fetch has just replaced
    # the dict it lives in.
    liquidity_applied = apply_liquidity(watchlist)
    log.info(f"Liquidity: turnover attached to {liquidity_applied} holding(s).")

    # True industry market share: each holding's slice of its FULL Screener
    # industry peer group's quarterly sales, not just the watchlist subset.
    data["industry_share"] = compute_industry_share(
        watchlist, industry_tables, prior_industry_shares
    )

    # Safety net: ISIN identifies each holding uniquely, so the same company
    # silently ending up tracked under two sectors — as DIXON was, until this
    # check existed — surfaces as a log warning the same run it happens
    # instead of persisting unnoticed.
    duplicate_holdings = find_duplicate_holdings(watchlist)
    for dup in duplicate_holdings:
        holdings_desc = ", ".join(
            f"{h['ticker']} ({h['sector']})" for h in dup["holdings"]
        )
        log.warning(f"Duplicate holding detected (ISIN {dup['isin']}): {holdings_desc}")

    # Estimate each holding's share of tracked peer-group revenue and its trend
    from analysis.market_share import compute_peer_market_share

    data["market_share"] = compute_peer_market_share(watchlist)

    # Gather additional policy and institutional feeds asynchronously
    async with aiohttp.ClientSession() as session:
        log.info("Starting concurrent policy and institutional feeds scraping...")
        pli_task = scrape_pib_pli_approvals_async(session, watchlist)
        adv_rss_task = fetch_advanced_rss_feeds_async(session, watchlist)
        sebi_task = check_sebi_sid_filings_async(session)
        inst_task = fetch_institutional_activity_async(session, watchlist)
        filings_task = fetch_exchange_filings_async(session, watchlist)
        isin_refresh_task = refresh_isin_master_async(session, isin_master)
        global_events_task = fetch_global_event_feeds_async(session)

        (
            pli_competitors,
            (agreements, launches),
            sebi_filings,
            inst_activity,
            corp_filings,
            _isin_added,
            global_market_news,
        ) = await asyncio.gather(
            pli_task,
            adv_rss_task,
            sebi_task,
            inst_task,
            filings_task,
            isin_refresh_task,
            global_events_task,
        )

        from history.store import HistoryStore

        store = HistoryStore()

        merged_competitors = store.deduplicate_and_merge(
            "emerging_competitors", pli_competitors, ["name", "scheme"]
        )
        merged_agreements = store.deduplicate_and_merge(
            "corporate_agreements", agreements, ["company", "title"]
        )
        merged_launches = store.deduplicate_and_merge(
            "product_launches", launches, ["company", "product"]
        )
        merged_filings = store.deduplicate_and_merge(
            "corporate_filings", corp_filings, ["company", "filing"]
        )
        merged_sebi = store.deduplicate_and_merge(
            "sebi_filings", sebi_filings, ["company", "link"]
        )
        merged_inst = store.deduplicate_and_merge(
            "institutional_activity", inst_activity, ["company", "title"]
        )

        data["emerging_competitors"] = merged_competitors
        data["corporate_agreements"] = merged_agreements
        data["product_launches"] = merged_launches
        data["sebi_filings"] = merged_sebi
        data["institutional_activity"] = merged_inst
        data["corporate_filings"] = merged_filings
        data["global_market_news"] = global_market_news[:30]

        # Market-event engine: classify WHAT happened across every collected
        # headline, keep a rolling window via the committed history, and let
        # the entity graph grow itself from tie-up headlines.
        from analysis.entity_graph import load_entity_graph, harvest_partner_edges
        from analysis.event_engine import (
            classify_headlines,
            compute_supply_stress,
            refresh_merged_events,
        )

        graph = load_entity_graph()
        events = classify_headlines(data, watchlist)
        # Re-attribute the merged list with the current rules, so a fix to the
        # matcher reaches events carried over from earlier runs instead of
        # only applying to today's.
        data["market_events"] = refresh_merged_events(
            store.deduplicate_and_merge(
                "market_events", events, ["headline", "event_type"]
            )[:120],
            watchlist,
        )
        data["supply_stress"] = compute_supply_stress(data["market_events"], graph)
        harvest_partner_edges(data["corporate_agreements"], watchlist, graph)

        # The price-based counterpart of supply_stress above. That one counts
        # supply-side headlines, so a quarter where copper quietly rose 18%
        # with nobody writing about it produced no signal at all.
        from analysis.input_cost import compute_input_cost_shock

        data["input_cost_shock"] = compute_input_cost_shock()

    # Revenue growth first: it annotates each holding's TTM figure, which the
    # scoring model below reads. Running it afterwards left the scorer with no
    # growth input at all, silently.
    from analysis.sector_growth import build_sector_growth

    data["sector_growth"] = build_sector_growth(watchlist)

    # Compile margin of safety and moat analytics
    build_dashboard_views(data, watchlist)

    # Estimate-revision momentum: this run's targets/coverage vs the prior run
    data["estimate_revisions"] = revisions_mod.compute_revision_momentum(
        watchlist, prior_estimates
    )

    # Variant perception: where our independent Graham estimate diverges most
    # sharply from analyst consensus.
    data["variant_perception"] = compute_variant_perception(watchlist)

    # Sector S-curve stage, from trailing quarterly sales trends already fetched.
    data["curve_stage"] = classify_sector_curve_stage(watchlist)

    # Score any rotation decisions old enough to judge, and persist the ledger
    # so the hit-rate accumulates across runs.
    postmortem.score_pending_decisions(rotation_ledger, watchlist)
    data["rotation_hit_rate"] = postmortem.compute_hit_rate(rotation_ledger)
    data["rotation_recent_outcomes"] = postmortem.recent_outcomes(rotation_ledger)
    data["watchlist_changes"] = postmortem.recent_changes(rotation_ledger)
    postmortem.save_ledger(rotation_ledger)

    # Sector-relative valuation: annotate stocks with peer-group P/E context
    from analysis.sector_valuation import build_sector_valuation

    data["sector_valuation"] = build_sector_valuation(watchlist)

    # Establish the historical-MF institutional accumulation baseline (backtesting)
    from analysis.backtesting import build_institutional_baseline

    data["institutional_baseline"] = build_institutional_baseline()

    # Synthesize a prioritized early-warning feed from the collected signals
    from analysis.early_warning import generate_early_warnings
    from analysis.competitive_intel import detect_new_entrants

    # Connect fetched headlines to the incumbents they threaten (e.g. Amber
    # Enterprises moving on mobile manufacturing = a Dixon problem) before
    # the early-warning engine runs.
    data["new_entrants"] = detect_new_entrants(data, watchlist)

    # Tag each warning against the previous run so the dashboard can lead
    # with what is new rather than re-presenting yesterday's standing
    # conditions.
    from dashboard.payload import annotate_warning_status

    data["early_warnings"] = annotate_warning_status(
        generate_early_warnings(data, watchlist),
        prior.get("early_warnings") or [],
    )

    # Attribute collected headlines to the holdings they actually name, so
    # picking a company shows that company's coverage rather than its
    # sector's.
    from analysis.stock_topics import build_stock_topics

    data["stock_topics"] = build_stock_topics(data, watchlist)

    # The same attribution kept as a full audit — merged and excluded items
    # included — written per ticker so the browser pays for it only when a
    # reader opens a drawer. The counts ride in the payload; the detail does
    # not, which is what keeps dashboard_data.json a display copy.
    from analysis.coverage import build_coverage, coverage_counts
    from history.store import write_coverage_sidecars

    coverage = build_coverage(data, watchlist)
    data["coverage_count"] = coverage_counts(coverage)
    write_coverage_sidecars(coverage)

    # Thesis health: does the accumulated evidence this cycle still support
    # each holding's catalyst, or has a kill criterion tripped?
    data["thesis_health"] = compute_thesis_health(
        watchlist, data["early_warnings"], data["estimate_revisions"]
    )

    # Save watchlist changes
    save_watchlist(watchlist)

    # Save dashboard JSON
    save_data_for_dashboard(data, watchlist)

    # Build and send email. Subject, body and plain-text part all come from
    # one summary, so the inbox line cannot disagree with the briefing.
    message = build_briefing_email(data, watchlist)
    log.info(f"Briefing subject: {message['subject']}")
    send_email(message["html"], message["subject"], message["text"])

    # Deliberately after the send: a degraded briefing is still worth reading,
    # and it carries the evidence needed to diagnose the degradation. This only
    # decides whether the job reports success.
    from health import log_run_health

    healthy = log_run_health(data, watchlist)

    log.info("Briefing cycle finished successfully.")
    return healthy


if __name__ == "__main__":
    if not asyncio.run(run_pipeline()):
        sys.exit(1)
