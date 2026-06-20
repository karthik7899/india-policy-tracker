import asyncio
import datetime
import json
import aiohttp
from config import load_watchlist, save_watchlist, SECTOR_METADATA
from logger import log
from scraper import (
    fetch_all_feeds_async,
    scrape_pib_pli_approvals_async,
    fetch_advanced_rss_feeds_async,
    check_sebi_sid_filings_async,
    fetch_institutional_activity_async,
)
from metrics import (
    update_live_stock_prices,
    fetch_all_screener_fundamentals,
    auto_curate_watchlist,
    compile_valuation_and_institutional_data,
)
from mailer import build_html_email, send_email


def save_data_for_dashboard(brief_data, watchlist):
    """Saves the aggregated feed data to a JSON file for the static dashboard."""
    output = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watchlist": watchlist,
        "sectors": SECTOR_METADATA,
        "briefing": brief_data,
    }

    with open("dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    log.info(
        "SUCCESS: Updated data saved to 'dashboard_data.json' for web dashboard display."
    )


async def run_pipeline():
    watchlist = load_watchlist()

    # Gather news data async
    data = await fetch_all_feeds_async()

    # Auto-curate the watchlist (discovers emerging players and rotates stocks)
    emerging = await auto_curate_watchlist(data, watchlist)
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

        pli_competitors, (agreements, launches), sebi_filings, inst_activity = (
            await asyncio.gather(pli_task, adv_rss_task, sebi_task, inst_task)
        )

        data["emerging_competitors"] = pli_competitors
        data["corporate_agreements"] = agreements
        data["product_launches"] = launches
        data["sebi_filings"] = sebi_filings
        data["institutional_activity"] = inst_activity

    # Compile margin of safety and moat analytics
    compile_valuation_and_institutional_data(data, watchlist)

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
