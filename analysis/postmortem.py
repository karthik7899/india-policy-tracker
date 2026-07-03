"""Rotation decision post-mortems.

``analysis/rotation.py`` adds and rotates stocks every run but never learns
whether those calls were any good — the same blind spot every automated
strategy has until someone forces a scorecard. This module is that
scorecard: every add/rotate decision is logged with the price and target at
decision time; once enough time has passed, the decision is re-priced
against the stock's current watchlist price and marked as playing out or
not. The ledger is a small JSON file committed alongside
``dashboard_data.json``/``watchlist.json`` so the history survives runs.
"""

import datetime
import os

from logger import log
from utils import atomic_write_json

LEDGER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "rotation_ledger.json"
)

# Give a decision this many days to play out before scoring it — too soon and
# daily price noise dominates any real thesis signal.
MIN_AGE_DAYS = 45

_PLAYING_OUT = "Thesis Playing Out"
_UNDERPERFORMING = "Underperforming"
_UNTRACKED = "Left Watchlist (unscored)"


def load_ledger(path=LEDGER_PATH):
    import json

    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        log.error(f"Failed to load rotation ledger from {path}: {e}")
        return []


def save_ledger(ledger, path=LEDGER_PATH):
    try:
        atomic_write_json(ledger, path)
        return True
    except OSError as e:
        log.error(f"Failed to save rotation ledger to {path}: {e}")
        return False


def log_decision(ledger, action, sector, stock, today=None):
    """Appends a new decision entry. ``action`` is 'added' or 'rotated_in'.

    ``stock`` is the candidate dict as constructed in rotation.py, expected
    to carry ticker/name/price/target. Silently skips if price/target are
    missing or unparseable — nothing useful to score later.
    """
    try:
        price = float(stock.get("price"))
        target = float(stock.get("target"))
    except (TypeError, ValueError):
        return ledger

    date_str = (today or datetime.date.today()).isoformat()
    ledger.append(
        {
            "date": date_str,
            "action": action,
            "sector": sector,
            "ticker": stock.get("ticker"),
            "name": stock.get("name"),
            "price_at_decision": price,
            "target_at_decision": target,
            "scored": False,
            "outcome": None,
            "realized_return_pct": None,
        }
    )
    return ledger


def _current_price(watchlist, ticker):
    for stocks in (watchlist or {}).values():
        for stock in stocks or []:
            if isinstance(stock, dict) and stock.get("ticker") == ticker:
                try:
                    return float(stock.get("price"))
                except (TypeError, ValueError):
                    return None
    return None


def score_pending_decisions(ledger, watchlist, min_age_days=MIN_AGE_DAYS, today=None):
    """Scores ledger entries old enough to judge. Mutates and returns the ledger."""
    today = today or datetime.date.today()
    scored_count = 0

    for entry in ledger:
        if entry.get("scored"):
            continue
        try:
            decided = datetime.date.fromisoformat(entry["date"])
        except (KeyError, ValueError):
            continue
        age_days = (today - decided).days
        if age_days < min_age_days:
            continue

        current_price = _current_price(watchlist, entry["ticker"])
        if current_price is None:
            entry["scored"] = True
            entry["outcome"] = _UNTRACKED
            scored_count += 1
            continue

        price_at = entry["price_at_decision"]
        target_at = entry["target_at_decision"]
        realized_pct = (
            round((current_price - price_at) / price_at * 100, 1) if price_at else None
        )
        anticipated_pct = (
            round((target_at - price_at) / price_at * 100, 1) if price_at else None
        )

        entry["scored"] = True
        entry["realized_return_pct"] = realized_pct
        if (
            realized_pct is not None
            and anticipated_pct is not None
            and anticipated_pct > 0
            and realized_pct >= 0.5 * anticipated_pct
        ):
            entry["outcome"] = _PLAYING_OUT
        else:
            entry["outcome"] = _UNDERPERFORMING
        scored_count += 1

    if scored_count:
        log.info(f"Rotation post-mortem: scored {scored_count} decisions.")
    return ledger


def compute_hit_rate(ledger):
    """Returns {total_scored, wins, win_rate_pct} over decisions with a realized outcome."""
    judged = [e for e in ledger if e.get("outcome") in (_PLAYING_OUT, _UNDERPERFORMING)]
    wins = sum(1 for e in judged if e["outcome"] == _PLAYING_OUT)
    total = len(judged)
    return {
        "total_scored": total,
        "wins": wins,
        "win_rate_pct": round(wins / total * 100, 1) if total else None,
    }


def recent_outcomes(ledger, limit=5):
    """Most recently scored decisions, newest first — for the briefing."""
    judged = [e for e in ledger if e.get("outcome") in (_PLAYING_OUT, _UNDERPERFORMING)]
    judged.sort(key=lambda e: e["date"], reverse=True)
    return judged[:limit]
