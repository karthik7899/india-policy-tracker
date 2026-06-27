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
    watchlist = load_watchlist()

    # Gather news data async
    data = await fetch_all_feeds_async()

    # Auto-curate the watchlist (discovers emerging players and rotates stocks)
    emerging = auto_curate_watchlist(data, watchlist)
    data["emerging_players"] = emerging

    # Fetch live Yahoo Finance prices
    update_live_stock_prices(watchlist)

    # Fetch Screener.in fundamentals async
    await fetch_all_screener_fundamentals(watchlist)

    # Gather additional policy and institutional feeds asynchronously
    async with aiohttp.ClientSession() as session:
        log.info("Starting concurrent policy and institutional feeds scraping...")
        pli_task = scrape_pib_pli_approvals_async(session, watchlist)
        adv_rss_task = fetch_advanced_rss_feeds_async(session, watchlist)
        sebi_task = check_sebi_sid_filings_async(session)
        inst_task = fetch_institutional_activity_async(session, watchlist)
        filings_task = fetch_exchange_filings_async(session, watchlist)

        (
            pli_competitors,
            (agreements, launches),
            sebi_filings,
            inst_activity,
            corp_filings,
        ) = await asyncio.gather(
            pli_task, adv_rss_task, sebi_task, inst_task, filings_task
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

    # Compile margin of safety and moat analytics
    build_dashboard_views(data, watchlist)

    # Establish the historical-MF institutional accumulation baseline (backtesting)
    from analysis.backtesting import build_institutional_baseline

    data["institutional_baseline"] = build_institutional_baseline()

    # Synthesize a prioritized early-warning feed from the collected signals
    from analysis.early_warning import generate_early_warnings

    data["early_warnings"] = generate_early_warnings(data, watchlist)

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
