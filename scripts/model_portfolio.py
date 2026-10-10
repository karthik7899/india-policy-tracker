"""Write the model book into portfolios.json: the watchlist in equal weights.

    python scripts/model_portfolio.py                 # Rs 500 crore
    python scripts/model_portfolio.py --nav-cr 1000

Each holding gets the same share of the book, bought in whole shares at its
price in watchlist.json; what the rounding leaves over is cash. Every other
book in the file is kept as it is.

Run it once to set the model up. Running it again buys the book afresh at
the day's prices, which resets its profit and loss to nothing -- the book
is meant to be left alone so that drift, breaches and the orders that fix
them accumulate the way they would in a real one.
"""

import argparse
import datetime
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from utils import atomic_write_json, to_float  # noqa: E402

PATH = os.path.join(ROOT, "portfolios.json")
WATCHLIST = os.path.join(ROOT, "watchlist.json")
DASHBOARD = os.path.join(ROOT, "dashboard_data.json")

SCHEMA = {
    "id": "Short key; the dashboard links to a book by it.",
    "name": "What the page calls the book.",
    "kind": '"model" for an illustrative book, "actual" for real positions.',
    "benchmark": (
        'NIFTY50 or NIFTY500, or a Yahoo symbol such as "^CNXIT". One per book.'
    ),
    "inception": "Date the positions were bought (ISO). Optional.",
    "cash_cr": "Cash, in rupees crore.",
    "positions": (
        "[{ticker, quantity, avg_cost}]: NSE symbol, shares held, average "
        "price paid in rupees (optional; without it there is no P&L)."
    ),
    "targets": (
        '"equal_weight" (today\'s watchlist, evenly) or {TICKER: % of NAV}. A '
        "held name missing from the targets is sold."
    ),
    "target_cash_pct": "Cash to keep, % of NAV. Default 0.",
    "rebalance_band_pct": (
        "Drift, in percentage points of NAV, left untraded. Default 0.25."
    ),
    "limits": {
        "max_stock_pct": "Largest position, % of NAV.",
        "max_sector_pct": "Largest sector, % of NAV.",
        "max_group_pct": "Largest business group (business_groups.json), % of NAV.",
        "max_days_to_exit": (
            "Days to sell any position at 20% of its daily value traded."
        ),
        "max_ownership_pct": "Largest share of any one company, %.",
        "max_beta": "Beta to the benchmark. Optional.",
        "max_tracking_error_pct": "Tracking error, % a year. Optional.",
    },
    "exclusions": (
        '[TICKER or {ticker, reason}]: never held, e.g. {"ticker": "ITC", '
        '"reason": "tobacco"}.'
    ),
}


def holdings(watchlist):
    for sector, stocks in watchlist.items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for s in stocks:
            if isinstance(s, dict) and s.get("ticker"):
                yield str(s["ticker"]).upper(), to_float(s.get("price"))


def build(watchlist, nav_cr, inception):
    names = sorted(holdings(watchlist))
    priced = [(t, p) for t, p in names if p and p > 0]
    each = nav_cr * 1e7 / len(priced)
    positions, spent = [], 0.0
    for ticker, price in priced:
        qty = math.floor(each / price)
        if qty <= 0:
            continue
        positions.append({"ticker": ticker, "quantity": qty, "avg_cost": price})
        spent += qty * price
    return {
        "id": "model",
        "name": "Model book: the watchlist in equal weights",
        "kind": "model",
        "note": (
            f"Illustrative. ₹{nav_cr:g} crore bought in equal weights at the "
            f"prices of the {inception} run; nobody holds it. Replace it with "
            "real positions, bearing in mind this file is public."
        ),
        "inception": inception,
        "benchmark": "NIFTY50",
        "cash_cr": round((nav_cr * 1e7 - spent) / 1e7, 4),
        "targets": "equal_weight",
        "target_cash_pct": 0,
        "rebalance_band_pct": 0.25,
        "limits": {
            "max_stock_pct": 8,
            "max_sector_pct": 25,
            "max_group_pct": 15,
            "max_days_to_exit": 5,
            "max_ownership_pct": 1,
        },
        "exclusions": [],
        "positions": positions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--nav-cr", type=float, default=500.0)
    parser.add_argument(
        "--date",
        help="date the watchlist prices are from (default: the last run's)",
    )
    args = parser.parse_args(argv)

    with open(WATCHLIST, encoding="utf-8") as f:
        watchlist = json.load(f)
    inception = args.date
    if not inception:
        try:
            with open(DASHBOARD, encoding="utf-8") as f:
                inception = json.load(f)["last_updated"][:10]
        except (OSError, KeyError, ValueError):
            inception = datetime.date.today().isoformat()

    body = {"_about": "", "_schema": SCHEMA, "portfolios": []}
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as f:
            body = json.load(f)
    body["_about"] = (
        "Books the portfolio view measures (analysis/portfolio.py). This "
        "repository is public, and so is everything in this file. Field "
        "meanings are in _schema; scripts/model_portfolio.py writes the model."
    )
    body["_schema"] = SCHEMA
    model = build(watchlist, args.nav_cr, inception)
    books = [b for b in body.get("portfolios") or [] if b.get("id") != "model"]
    body["portfolios"] = [model] + books
    atomic_write_json(body, PATH)
    print(
        f"Model book: {len(model['positions'])} positions, Rs {args.nav_cr:g} "
        f"crore at the {inception} prices, Rs {model['cash_cr']:.4f} crore cash."
    )


if __name__ == "__main__":
    main()
