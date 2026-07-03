import asyncio
import datetime
import aiohttp
from config import load_watchlist, save_watchlist, SECTOR_METADATA
from logger import log
from scraper import (
    fetch_all_feeds_async,
    scrape_pib_pli_approvals_async,
    fetch_advanced_rss_feeds_async,
    check_sebi_sid_filings_async,
    fetch_institutional_activity_async,
    fetch_exchange_filings_async,
)
from analysis.growth import update_live_stock_prices
from analysis.rotation import auto_curate_watchlist
from dashboard.builder import build_dashboard_views
from providers.screener import fetch_all_screener_fundamentals
from emails.mailer import build_html_email, send_email
from analysis import revisions as revisions_mod
from analysis import postmortem
from analysis.thesis import compute_thesis_health
from analysis.variant_perception import compute_variant_perception
from analysis.curve_stage import classify_sector_curve_stage
from analysis.market_share import (
    compute_industry_share,
    snapshot_prior_industry_shares,
)
from providers.exchange_events import (
    fetch_fundraising_events_async,
    fetch_institutional_deals_async,
)


def save_data_for_dashboard(brief_data, watchlist):
    """Saves the aggregated feed data to a JSON file for the static dashboard."""
    output = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watchlist": watchlist,
        "sectors": SECTOR_METADATA,
        "briefing": brief_data,
    }

    from utils import atomic_write_json

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

    # Snapshot targets/coverage before anything mutates the watchlist, so
    # estimate-revision momentum can diff "before this run" vs "after".
    prior_estimates = revisions_mod.snapshot_prior_estimates(watchlist)
    prior_industry_shares = snapshot_prior_industry_shares(watchlist)

    # Gather news data async
    data = await fetch_all_feeds_async()

    # Auto-curate the watchlist (discovers emerging players and rotates stocks)
    emerging, rotation_decisions = auto_curate_watchlist(data, watchlist)
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
    peer_competitors, industry_peers = await fetch_all_screener_fundamentals(watchlist)
    data["peer_competitors"] = peer_competitors or {}

    # True industry market share: each holding's slice of its FULL Screener
    # industry peer group's quarterly sales, not just the watchlist subset.
    data["industry_share"] = compute_industry_share(
        watchlist, industry_peers, prior_industry_shares
    )

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
        fundraising_task = fetch_fundraising_events_async(session, watchlist)
        deals_task = fetch_institutional_deals_async(session, watchlist)

        (
            pli_competitors,
            (agreements, launches),
            sebi_filings,
            inst_activity,
            corp_filings,
            fundraising_events,
            institutional_deals,
        ) = await asyncio.gather(
            pli_task,
            adv_rss_task,
            sebi_task,
            inst_task,
            filings_task,
            fundraising_task,
            deals_task,
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
        merged_fundraising = store.deduplicate_and_merge(
            "fundraising_events", fundraising_events, ["company", "subject"]
        )
        merged_deals = store.deduplicate_and_merge(
            "institutional_deals",
            institutional_deals,
            ["ticker", "client", "date", "side"],
        )

        data["emerging_competitors"] = merged_competitors
        data["corporate_agreements"] = merged_agreements
        data["product_launches"] = merged_launches
        data["sebi_filings"] = merged_sebi
        data["institutional_activity"] = merged_inst
        data["corporate_filings"] = merged_filings
        data["fundraising_events"] = merged_fundraising[:40]
        data["institutional_deals"] = merged_deals[:40]

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
    postmortem.save_ledger(rotation_ledger)

    # Sector-relative valuation: annotate stocks with peer-group P/E context
    from analysis.sector_valuation import build_sector_valuation

    data["sector_valuation"] = build_sector_valuation(watchlist)

    # Establish the historical-MF institutional accumulation baseline (backtesting)
    from analysis.backtesting import build_institutional_baseline

    data["institutional_baseline"] = build_institutional_baseline()

    # Synthesize a prioritized early-warning feed from the collected signals
    from analysis.early_warning import generate_early_warnings

    data["early_warnings"] = generate_early_warnings(data, watchlist)

    # Thesis health: does the accumulated evidence this cycle still support
    # each holding's catalyst, or has a kill criterion tripped?
    data["thesis_health"] = compute_thesis_health(
        watchlist, data["early_warnings"], data["estimate_revisions"]
    )

    # Save watchlist changes
    save_watchlist(watchlist)

    # Save dashboard JSON
    save_data_for_dashboard(data, watchlist)

    # Build and send email
    html = build_html_email(data, watchlist)
    send_email(html)

    log.info("Briefing cycle finished successfully.")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
