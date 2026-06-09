import asyncio
import datetime
import json
from config import load_watchlist, save_watchlist, SECTOR_METADATA
from logger import log
from scraper import fetch_all_feeds_async
from metrics import (
    update_live_stock_prices,
    fetch_all_screener_fundamentals,
    auto_curate_watchlist,
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
    emerging = auto_curate_watchlist(data, watchlist)
    data["emerging_players"] = emerging

    # Fetch live Yahoo Finance prices
    update_live_stock_prices(watchlist)

    # Fetch Screener.in fundamentals async
    await fetch_all_screener_fundamentals(watchlist)

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
