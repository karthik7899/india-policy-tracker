"""A book of positions: what it is worth, what it is exposed to, how fast it
could be sold, and how it moves against its benchmark.

Everything else in this pipeline tracks names. An institution manages money,
and the questions it asks first are about the money: how much is in each
name, sector and business group; how much of it could be sold in a week;
what a market fall would cost; which positions breach the mandate; and what
to trade to get back to target. This answers those from the positions in
portfolios.json and the prices the run has already fetched.

Inputs, and where each comes from:

  * Positions, cash, targets, limits and exclusions: portfolios.json. The
    committed file holds a MODEL book -- the watchlist bought in equal
    weights at the prices of the 9 Oct 2026 run -- so the page has something
    real to compute on. A real book replaces it; the repository is public,
    so anything put there is public too.
  * Prices: the run's live prices; weekly closes from the same one-year
    weekly download as the 52-week range (analysis/growth.py), plus one
    batched download for the benchmark and for any position the watchlist no
    longer holds.
  * Traded value and market value: each holding's screener block (advt_cr is
    the last month's average daily value traded; market_cap is in crore).
  * Business groups: business_groups.json, which lists only memberships that
    are certain. A holding in no group is its own.

What it does not claim:

  * Returns over past windows are a BACKCAST: today's weights held through
    each window. They say how the current book would have behaved, not how
    the book did; nothing here records past positions. And they flatter it:
    the watchlist holds these names partly because they rose, so the first
    live run's year read +27.5% against the Nifty's -10.9% (10 Oct 2026).
    analysis/track_record.py measures picks from the day they were made,
    which is the fair test, and says so for the same reason.
  * No allocation/selection (Brinson) attribution. That needs the
    benchmark's constituent weights, which no source this pipeline reads
    provides. Contribution by stock and sector is given instead.
  * Risk comes from at most 52 weekly returns. That is short: a beta or a
    volatility from one year moves a lot the next, and the page says so.
  * Days to exit come from a month of traded value at a fifth of each
    session (analysis/liquidity.PARTICIPATION_RATE). There is no order-book
    depth behind them.
"""

import datetime
import json
import math
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from analysis.liquidity import PARTICIPATION_RATE
from logger import log
from utils import to_float

PORTFOLIOS_PATH = "portfolios.json"
GROUPS_PATH = "business_groups.json"

_RUPEES_PER_CRORE = 1e7
WEEKS_PER_YEAR = 52
# Fewer weekly returns than this and a holding gets no beta or volatility:
# under half a year, one quarter's results dominate the figure.
MIN_WEEKS = 26
# A week the backcast skips: less than this share of the invested book had
# prices at both ends of it.
MIN_COVER = 0.5

BENCHMARKS = {
    "NIFTY50": ("Nifty 50", "^NSEI"),
    "NIFTY500": ("Nifty 500", "^CRSLDX"),
}
DEFAULT_BENCHMARK = "NIFTY50"

# Backcast windows, in weeks. The last is "the year", shortened to what the
# weekly download returned when that is a week or two less.
WINDOWS = ((4, "1 month"), (13, "3 months"), (26, "6 months"), (52, "1 year"))
# A drift smaller than this, in percentage points of NAV, is not traded.
DEFAULT_BAND_PCT = 0.25
STRESS_WEEKS = 4
MARKET_SHOCK_PCT = -10.0
# Rows kept in each ranked list on the page.
TOP = 10
# A variance below this is a flat line, not a market: a beta against it is
# rounding error divided by rounding error.
_FLAT = 1e-10

LIMIT_LABELS = {
    "max_stock_pct": "Largest position, % of NAV",
    "max_sector_pct": "Largest sector, % of NAV",
    "max_group_pct": "Largest business group, % of NAV",
    "max_days_to_exit": "Days to exit any position",
    "max_ownership_pct": "Share of any company owned, %",
    "max_beta": "Beta to the benchmark",
    "max_tracking_error_pct": "Tracking error, % a year",
}

Fetcher = Callable[[List[str]], Dict[str, List[List[Any]]]]


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_portfolios(path: str = PORTFOLIOS_PATH) -> List[Dict[str, Any]]:
    """The books in portfolios.json; [] when there is no readable file."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            body = json.load(f)
    except (OSError, ValueError) as e:
        log.warning(f"Portfolio: {path} could not be read: {e!r}")
        return []
    books = body.get("portfolios") if isinstance(body, dict) else None
    return [b for b in books or [] if isinstance(b, dict)]


def load_groups(path: str = GROUPS_PATH) -> Dict[str, str]:
    """``{TICKER: group}`` from business_groups.json; {} without the file."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            body = json.load(f)
    except (OSError, ValueError) as e:
        log.warning(f"Portfolio: {path} could not be read: {e!r}")
        return {}
    groups = body.get("groups") if isinstance(body, dict) else None
    out: Dict[str, str] = {}
    for group, tickers in (groups if isinstance(groups, dict) else {}).items():
        for t in tickers if isinstance(tickers, list) else []:
            out[str(t).upper()] = str(group)
    return out


def yahoo_weekly(symbols: List[str]) -> Dict[str, List[List[Any]]]:
    """A year of weekly closes per Yahoo symbol, one batched download."""
    import yfinance as yf

    from analysis.growth import _weekly_closes

    if not symbols:
        return {}
    frame = yf.download(
        symbols,
        period="1y",
        interval="1wk",
        group_by="ticker",
        threads=True,
        timeout=20,
        progress=False,
    )
    out = {}
    for symbol in symbols:
        series = _weekly_closes(_frame_for(frame, symbol))
        if series:
            out[symbol] = series
    return out


def _frame_for(frame: Any, symbol: str) -> Any:
    """One symbol's columns from a yf.download frame.

    yfinance 1.x keeps the (ticker, field) column levels even for a single
    symbol, so "the frame is the symbol's when one was asked for" -- the
    rule track_record.py relies on -- would find no Close column and return
    nothing, silently. Which shape arrived is read off the columns instead.
    """
    cols = getattr(frame, "columns", None)
    if cols is None:
        return None
    if getattr(cols, "nlevels", 1) > 1:
        return frame[symbol] if symbol in cols.get_level_values(0) else None
    return frame


# --------------------------------------------------------------------------
# Small numeric helpers
# --------------------------------------------------------------------------


def _num(value: Any) -> Optional[float]:
    """A positive finite number, or None."""
    v = to_float(value)
    if v is None or not math.isfinite(v) or v <= 0:
        return None
    return v


def _r(value: Optional[float], digits: int = 2) -> Optional[float]:
    return None if value is None else round(value, digits)


def _cov(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (n - 1)


def _stdev(xs: List[float]) -> float:
    return math.sqrt(_cov(xs, xs)) if len(xs) > 1 else 0.0


def _quantile(values: List[float], q: float) -> float:
    """Linear-interpolated quantile of an unsorted list."""
    xs = sorted(values)
    pos = q * (len(xs) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def _compound(returns: List[float]) -> float:
    level = 1.0
    for r in returns:
        level *= 1 + r
    return level - 1


def _closes(series: Any) -> Dict[str, float]:
    """``{iso_date: close}`` from ``[[iso, close], ...]``, bad rows dropped."""
    out = {}
    for row in series or []:
        try:
            d, c = str(row[0]), float(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        if math.isfinite(c) and c > 0:
            out[d] = c
    return out


def _week_returns(closes: Dict[str, float], grid: List[str]) -> Dict[str, float]:
    """Each grid week's return, keyed by its date, where both ends are priced.

    Returns are taken between neighbouring grid dates only. A holding missing
    a week would otherwise get a two-week return filed against one week of
    the benchmark's.
    """
    out = {}
    for prev, cur in zip(grid, grid[1:]):
        a, b = closes.get(prev), closes.get(cur)
        if a and b:
            out[cur] = b / a - 1
    return out


def _count(items: List[Any], noun: str) -> str:
    return f"{len(items)} {noun}{'' if len(items) == 1 else 's'}"


def _week_end(iso: str) -> str:
    """The Friday of the week a weekly bar is dated by (its Monday)."""
    return (datetime.date.fromisoformat(iso) + datetime.timedelta(days=4)).isoformat()


# --------------------------------------------------------------------------
# The book
# --------------------------------------------------------------------------


def _holdings(watchlist: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """What the watchlist knows about each holding, keyed by ticker."""
    out: Dict[str, Dict[str, Any]] = {}
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators" or not isinstance(stocks, list):
            continue
        for s in stocks:
            if not isinstance(s, dict) or not s.get("ticker"):
                continue
            sc = s.get("screener") if isinstance(s.get("screener"), dict) else {}
            ticker = str(s["ticker"]).upper()
            out[ticker] = {
                "name": s.get("name") or ticker,
                "sector": sector,
                "price": _num(s.get("price")),
                "advt_cr": _num(sc.get("advt_cr")),
                "market_cap_cr": _num(sc.get("market_cap")),
                "week52_low": _num(sc.get("week52_low")),
            }
    return out


def _exclusions(book: Dict[str, Any]) -> Dict[str, str]:
    """``{TICKER: reason}``; entries may be plain tickers or {ticker, reason}."""
    out = {}
    for e in book.get("exclusions") or []:
        if isinstance(e, dict) and e.get("ticker"):
            out[str(e["ticker"]).upper()] = str(e.get("reason") or "excluded")
        elif isinstance(e, str) and e.strip():
            out[e.strip().upper()] = "excluded"
    return out


def requested_targets(
    book: Dict[str, Any], holdings: Dict[str, Dict[str, Any]]
) -> Dict[str, float]:
    """Target weights, % of NAV, as the book states them.

    ``"equal_weight"`` spreads the invested share evenly over today's
    watchlist, so a holding the rotation engine adds becomes a buy and one it
    drops becomes a sale. A dict names weights directly; anything left out of
    it is a target of zero.
    """
    spec = book.get("targets", "equal_weight")
    excluded = _exclusions(book)
    invested = 100.0 - (_num(book.get("target_cash_pct")) or 0.0)
    if spec == "equal_weight":
        names = [t for t in holdings if t not in excluded]
        each = invested / len(names) if names else 0.0
        return {t: each for t in names}
    if isinstance(spec, dict):
        out = {}
        for t, w in spec.items():
            weight = _num(w)
            if weight and str(t).upper() not in excluded:
                out[str(t).upper()] = weight
        return out
    return {}


def _caps(
    tickers: List[str],
    info: Dict[str, Dict[str, Any]],
    nav_cr: float,
    limits: Dict[str, Any],
) -> Dict[str, Tuple[float, str]]:
    """The largest weight each name may be given, and the limit that sets it."""
    max_stock = _num(limits.get("max_stock_pct"))
    max_days = _num(limits.get("max_days_to_exit"))
    max_own = _num(limits.get("max_ownership_pct"))
    caps = {}
    for t in tickers:
        i = info.get(t) or {}
        options = []
        if max_stock:
            options.append((max_stock, f"the {max_stock:g}% position limit"))
        if max_days and i.get("advt_cr"):
            cap = max_days * i["advt_cr"] * PARTICIPATION_RATE / nav_cr * 100
            options.append(
                (
                    cap,
                    f"{max_days:g} days to exit at {PARTICIPATION_RATE:.0%} of "
                    f"₹{i['advt_cr']:.2f} Cr traded a day",
                )
            )
        if max_own and i.get("market_cap_cr"):
            cap = max_own / 100 * i["market_cap_cr"] / nav_cr * 100
            options.append(
                (cap, f"{max_own:g}% of a ₹{i['market_cap_cr']:,.0f} Cr company")
            )
        if options:
            caps[t] = min(options)
    return caps


def apply_caps(
    requested: Dict[str, float], caps: Dict[str, Tuple[float, str]]
) -> Tuple[Dict[str, float], Dict[str, Tuple[float, str]], float]:
    """Hold each name to its cap and hand the excess to the rest, pro rata.

    Returns (targets, the names capped, the excess nobody could take, which
    stays in cash). Repeated because a name that takes some excess can then
    exceed its own cap.
    """
    targets = dict(requested)
    capped: Dict[str, Tuple[float, str]] = {}
    left = 0.0
    for _ in range(len(targets) + 1):
        excess = 0.0
        for t, w in targets.items():
            cap = caps.get(t)
            if cap is not None and w > cap[0] + 1e-9:
                excess += w - cap[0]
                targets[t] = cap[0]
                capped[t] = cap
        if excess <= 1e-9:
            break
        free = {t: w for t, w in targets.items() if t not in capped and w > 0}
        room = sum(free.values())
        if room <= 0:
            left = excess
            break
        for t, w in free.items():
            targets[t] = w + excess * w / room
    return targets, capped, left


def _days(value_cr: Optional[float], advt_cr: Optional[float]) -> Optional[float]:
    if value_cr is None or not advt_cr:
        return None
    return value_cr / (advt_cr * PARTICIPATION_RATE)


def _position_list(book: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The book's positions, one per ticker.

    A ticker listed twice (two lots bought at different prices) is one
    position: its quantities add and its cost is their weighted average.
    Kept as two rows, every figure keyed by ticker -- orders above all --
    would silently use one lot and drop the other.
    """
    positions = book.get("positions")
    if not isinstance(positions, list):
        return []
    merged: Dict[str, Dict[str, Any]] = {}
    for p in positions:
        if not isinstance(p, dict) or not p.get("ticker"):
            continue
        t = str(p["ticker"]).upper()
        qty = to_float(p.get("quantity")) or 0.0
        if t not in merged:
            merged[t] = {**p, "ticker": t, "quantity": qty}
            continue
        m = merged[t]
        a, b = _num(m.get("avg_cost")), _num(p.get("avg_cost"))
        total = m["quantity"] + qty
        m["avg_cost"] = (
            (a * m["quantity"] + b * qty) / total if a and b and total > 0 else None
        )
        m["quantity"] = total
    return list(merged.values())


def _positions(
    book: Dict[str, Any],
    info: Dict[str, Dict[str, Any]],
    closes: Dict[str, Dict[str, float]],
    groups: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """One row per position, valued; and the tickers that could not be priced."""
    rows, unpriced = [], []
    for p in _position_list(book):
        ticker = p["ticker"]
        qty = to_float(p.get("quantity"))
        if not qty or qty <= 0:
            continue
        i = info.get(ticker) or {}
        price = i.get("price")
        if price is None and closes.get(ticker):
            price = closes[ticker][max(closes[ticker])]
        if price is None:
            unpriced.append(ticker)
            continue
        cost = _num(p.get("avg_cost"))
        value = qty * price / _RUPEES_PER_CRORE
        row = {
            "ticker": ticker,
            "name": i.get("name") or p.get("name") or ticker,
            "sector": i.get("sector") or p.get("sector") or "other",
            "in_watchlist": ticker in info,
            "quantity": int(qty) if float(qty).is_integer() else qty,
            "price": round(price, 2),
            "value_cr": value,
        }
        if ticker in groups:
            row["group"] = groups[ticker]
        if cost:
            row["avg_cost"] = round(cost, 2)
            row["cost_cr"] = qty * cost / _RUPEES_PER_CRORE
        advt = i.get("advt_cr")
        if advt:
            row["advt_cr"] = advt
        mcap = i.get("market_cap_cr")
        if mcap:
            row["market_cap_cr"] = mcap
        if i.get("week52_low"):
            row["week52_low"] = i["week52_low"]
        rows.append(row)
    return rows, unpriced


# --------------------------------------------------------------------------
# Exposure, liquidity, ownership
# --------------------------------------------------------------------------


def exposure(
    rows: List[Dict[str, Any]],
    targets: Dict[str, float],
    sector_of: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Weight by sector and business group, and how concentrated the book is.

    ``sector_of`` places targets the book does not hold yet; held names are
    placed by their own rows.
    """
    sectors: Dict[str, Dict[str, Any]] = {}
    groups: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        s = sectors.setdefault(r["sector"], {"weight_pct": 0.0, "tickers": []})
        s["weight_pct"] += r["weight_pct"]
        s["tickers"].append(r["ticker"])
        if r.get("group"):
            g = groups.setdefault(r["group"], {"weight_pct": 0.0, "tickers": []})
            g["weight_pct"] += r["weight_pct"]
            g["tickers"].append(r["ticker"])
    sector_of = {**(sector_of or {}), **{r["ticker"]: r["sector"] for r in rows}}
    target_by_sector: Dict[str, float] = {}
    for t, w in targets.items():
        sec = sector_of.get(t)
        if sec:
            target_by_sector[sec] = target_by_sector.get(sec, 0.0) + w

    weights = sorted((r["weight_pct"] for r in rows), reverse=True)
    invested = sum(weights)
    shares = [w / invested for w in weights] if invested else []
    return {
        "sectors": sorted(
            (
                {
                    "sector": k,
                    "weight_pct": round(v["weight_pct"], 2),
                    "target_pct": round(target_by_sector.get(k, 0.0), 2),
                    "count": len(v["tickers"]),
                }
                for k, v in sectors.items()
            ),
            key=lambda x: -x["weight_pct"],
        ),
        # Only groups the book holds more than one member of: a group of one
        # is the position itself, already on the list of positions.
        "groups": sorted(
            (
                {
                    "group": k,
                    "weight_pct": round(v["weight_pct"], 2),
                    "tickers": sorted(v["tickers"]),
                }
                for k, v in groups.items()
                if len(v["tickers"]) > 1
            ),
            key=lambda x: -x["weight_pct"],
        ),
        "concentration": {
            "largest_pct": round(weights[0], 2) if weights else None,
            "top5_pct": round(sum(weights[:5]), 2),
            "top10_pct": round(sum(weights[:10]), 2),
            # 1/sum(w^2): the number of equal positions with the same spread.
            "effective_names": (
                round(1 / sum(s * s for s in shares), 1) if shares else None
            ),
        },
    }


def liquidity(rows: List[Dict[str, Any]], nav_cr: float) -> Dict[str, Any]:
    """How much of the book could be sold how fast, at the real sizes."""
    measured = [r for r in rows if r.get("advt_cr")]
    unmeasured = sorted(r["ticker"] for r in rows if not r.get("advt_cr"))

    def exitable(days: int) -> float:
        sold = sum(
            min(r["value_cr"], r["advt_cr"] * PARTICIPATION_RATE * days)
            for r in measured
        )
        return sold / nav_cr * 100 if nav_cr else 0.0

    def pro_rata(share: float) -> Optional[float]:
        # Selling the same slice of every position at once: the slowest
        # position sets the pace.
        days = [_days(r["value_cr"] * share, r["advt_cr"]) for r in measured]
        return max(days) if days else None

    weighted = (
        sum(r["days_to_exit"] * r["value_cr"] for r in measured)
        / sum(r["value_cr"] for r in measured)
        if measured
        else None
    )
    slowest = sorted(measured, key=lambda r: -r["days_to_exit"])[:TOP]
    return {
        "participation_pct": round(PARTICIPATION_RATE * 100),
        "exitable": [{"days": d, "pct": round(exitable(d), 1)} for d in (1, 5, 20)],
        "pro_rata": [
            {"share_pct": s, "days": _r(pro_rata(s / 100), 1)} for s in (25, 50)
        ],
        "weighted_days": _r(weighted, 1),
        "slowest": [
            {
                "ticker": r["ticker"],
                "value_cr": round(r["value_cr"], 2),
                "advt_cr": r["advt_cr"],
                "pct_of_adv": r["pct_of_adv"],
                "days_to_exit": r["days_to_exit"],
            }
            for r in slowest
        ],
        "unmeasured": unmeasured,
    }


# --------------------------------------------------------------------------
# Risk and returns from weekly closes
# --------------------------------------------------------------------------


def _book_series(
    weights: Dict[str, float], returns: Dict[str, Dict[str, float]], grid: List[str]
) -> Dict[str, float]:
    """The book's weekly return at today's weights (fractions of NAV).

    A week where some holdings are unpriced (listed later, suspended) is
    scaled up from the ones that are, so a recent listing does not read as
    cash. A week with less than MIN_COVER of the book priced is skipped.
    """
    invested = sum(weights.values())
    out = {}
    for d in grid[1:]:
        have = [
            (w, returns[t][d]) for t, w in weights.items() if d in returns.get(t, {})
        ]
        cover = sum(w for w, _ in have)
        if invested <= 0 or cover < MIN_COVER * invested:
            continue
        out[d] = sum(w * r for w, r in have) * invested / cover
    return out


def _paired(a: Dict[str, float], b: Dict[str, float]) -> Tuple[List[float], List]:
    dates = sorted(set(a) & set(b))
    return [a[d] for d in dates], [b[d] for d in dates]


def _drawdown(series: Dict[str, float], start: str) -> Optional[Dict[str, Any]]:
    """Deepest fall from a peak, with the weeks it ran between.

    ``start`` is the week the series is measured from, so a fall that begins
    at once is dated from it rather than from nowhere.
    """
    if not series:
        return None
    level = peak = 1.0
    peak_date = start
    worst, worst_peak, trough = 0.0, None, None
    for d in sorted(series):
        level *= 1 + series[d]
        if level > peak:
            peak, peak_date = level, d
        dd = level / peak - 1
        if dd < worst:
            worst, worst_peak, trough = dd, peak_date, d
    return {
        "pct": round(worst * 100, 2),
        "peak": _week_end(worst_peak) if worst_peak else None,
        "trough": _week_end(trough) if trough else None,
    }


def _window_return(closes: Dict[str, float], start: str, end: str) -> Optional[float]:
    a, b = closes.get(start), closes.get(end)
    return b / a - 1 if a and b else None


def _attributed(
    weights: Dict[str, float], moves: Dict[str, float]
) -> Tuple[Optional[float], Dict[str, float]]:
    """Book return over a window and each name's share of it.

    Weights are rescaled over the names that have a return for the window, so
    the contributions add up to the total exactly.
    """
    invested = sum(weights.values())
    have = {t: w for t, w in weights.items() if t in moves}
    cover = sum(have.values())
    if not invested or cover < MIN_COVER * invested:
        return None, {}
    scale = invested / cover
    parts = {t: w * scale * moves[t] for t, w in have.items()}
    return sum(parts.values()), parts


def _moves(
    weights: Dict[str, float], closes: Dict[str, Dict[str, float]], start, end
) -> Dict[str, float]:
    return {
        t: m
        for t in weights
        for m in [_window_return(closes.get(t, {}), start, end)]
        if m is not None
    }


def _ranked(parts: Dict[str, float], n: int = 5, best: bool = False) -> List:
    order = sorted(parts.items(), key=lambda kv: kv[1], reverse=best)
    return [{"ticker": t, "pct": round(v * 100, 2)} for t, v in order[:n]]


def _stock_stats(
    weights: Dict[str, float],
    rets: Dict[str, Dict[str, float]],
    bench_rets: Dict[str, float],
    book: Dict[str, float],
) -> Dict[str, Dict[str, Any]]:
    """Volatility, beta and share of the book's risk, per holding.

    The risk share is the holding's weight times its covariance with the book,
    over the book's variance: the shares add up to the whole (exactly, where
    every holding is priced every week), so they say which names the book's
    swings actually come from.
    """
    var_book = _stdev(list(book.values())) ** 2 if len(book) > 1 else 0.0
    stats: Dict[str, Dict[str, Any]] = {}
    for t, series in rets.items():
        s: Dict[str, Any] = {"weeks": len(series)}
        if len(series) >= MIN_WEEKS:
            s["vol_pct"] = round(
                _stdev(list(series.values())) * math.sqrt(WEEKS_PER_YEAR) * 100, 1
            )
            xs, ys = _paired(series, bench_rets)
            if len(xs) >= MIN_WEEKS and _cov(ys, ys) > _FLAT:
                s["beta"] = round(_cov(xs, ys) / _cov(ys, ys), 2)
            xs, ys = _paired(series, book)
            if len(xs) >= MIN_WEEKS and var_book > _FLAT:
                s["risk_share_pct"] = round(
                    weights[t] * _cov(xs, ys) / var_book * 100, 1
                )
        stats[t] = s
    return stats


def _returns(
    rows: List[Dict[str, Any]],
    weights: Dict[str, float],
    closes: Dict[str, Dict[str, float]],
    bench: Dict[str, float],
    grid: List[str],
    stats: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Backcast returns: today's weights held through each window.

    Only the year is shortened to fit the download; a shorter window that
    does not fit is left out rather than relabelled.
    """
    out: Dict[str, Any] = {"windows": []}
    span = len(grid) - 1
    longest = None
    for want, label in WINDOWS:
        n = min(want, span) if want == WINDOWS[-1][0] else want
        if n > span or n < STRESS_WEEKS or (longest and n <= longest[0]):
            continue
        start, end = grid[-1 - n], grid[-1]
        moves = _moves(weights, closes, start, end)
        total, parts = _attributed(weights, moves)
        if total is None:
            continue
        bmove = _window_return(bench, start, end)
        out["windows"].append(
            {
                "label": label if n == want else f"{n} weeks",
                "weeks": n,
                "from": start,
                "portfolio_pct": round(total * 100, 2),
                "benchmark_pct": _r(bmove * 100) if bmove is not None else None,
                "active_pct": (
                    round((total - bmove) * 100, 2) if bmove is not None else None
                ),
                "unpriced": sorted(set(weights) - set(moves)),
            }
        )
        longest = (n, out["windows"][-1]["label"], moves, parts)
    if longest:
        _, label, moves, parts = longest
        out["contribution_window"] = label
        out["best"] = _ranked(parts, best=True)
        out["worst"] = _ranked(parts)
        sector_of = {r["ticker"]: r["sector"] for r in rows}
        by_sector: Dict[str, float] = {}
        for t, v in parts.items():
            by_sector[sector_of[t]] = by_sector.get(sector_of[t], 0.0) + v
        out["by_sector"] = [
            {"sector": k, "pct": round(v * 100, 2)}
            for k, v in sorted(by_sector.items(), key=lambda kv: -kv[1])
        ]
        for t, m in moves.items():
            stats[t]["return_pct"] = round(m * 100, 1)
    return out


def risk_and_returns(
    rows: List[Dict[str, Any]],
    nav_cr: float,
    closes: Dict[str, Dict[str, float]],
    bench: Dict[str, float],
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """(risk, returns, per-holding stats) from weekly closes."""
    grid = sorted(bench) if len(bench) > 1 else []
    if not grid:
        # No benchmark: the holdings' own calendar, so the book can still be
        # measured on its own terms.
        grid = max((sorted(c) for c in closes.values()), key=len, default=[])
    weights = {r["ticker"]: r["value_cr"] / nav_cr for r in rows if nav_cr}
    rets = {t: _week_returns(closes.get(t, {}), grid) for t in weights}
    bench_rets = _week_returns(bench, grid) if bench else {}
    book = _book_series(weights, rets, grid)
    stats = _stock_stats(weights, rets, bench_rets, book)
    returns = _returns(rows, weights, closes, bench, grid, stats)
    if book:
        last = max(book)
        returns["week"] = {
            "week_of": last,
            "portfolio_pct": round(book[last] * 100, 2),
            "benchmark_pct": (
                _r(bench_rets[last] * 100) if last in bench_rets else None
            ),
        }

    risk: Dict[str, Any] = {
        "weeks": len(book),
        "from": grid[0] if grid else None,
        "to": _week_end(grid[-1]) if grid else None,
        "no_history": sorted(t for t, s in stats.items() if s["weeks"] < MIN_WEEKS),
    }
    if len(book) < MIN_WEEKS:
        risk["insufficient"] = (
            f"{len(book)} weekly return(s); at least {MIN_WEEKS} are needed"
        )
        return risk, returns, stats

    values = list(book.values())
    annual = math.sqrt(WEEKS_PER_YEAR)
    risk["vol_pct"] = round(_stdev(values) * annual * 100, 1)
    # Historical, not modelled: the loss exceeded in one week of every twenty
    # in the last year, and the average week beyond it.
    var95 = -_quantile(values, 0.05)
    tail = [v for v in values if v <= -var95]
    risk["var_95"] = {
        "pct": round(var95 * 100, 2),
        "cr": round(var95 * nav_cr, 2),
        "shortfall_pct": round(-sum(tail) / len(tail) * 100, 2) if tail else None,
    }
    worst_d = min(book, key=book.get)
    risk["worst_week"] = {
        "week_of": worst_d,
        "pct": round(book[worst_d] * 100, 2),
        "benchmark_pct": (
            _r(bench_rets[worst_d] * 100) if worst_d in bench_rets else None
        ),
    }
    risk["max_drawdown"] = _drawdown(book, grid[0])
    xs, ys = _paired(book, bench_rets)
    if len(xs) >= MIN_WEEKS and _cov(ys, ys) > _FLAT:
        active = [x - y for x, y in zip(xs, ys)]
        risk["beta"] = round(_cov(xs, ys) / _cov(ys, ys), 2)
        risk["correlation"] = round(_cov(xs, ys) / (_stdev(xs) * _stdev(ys)), 2)
        risk["tracking_error_pct"] = round(_stdev(active) * annual * 100, 1)
        risk["benchmark_vol_pct"] = round(_stdev(ys) * annual * 100, 1)
        bdd = _drawdown(bench_rets, grid[0])
        risk["benchmark_max_drawdown_pct"] = bdd["pct"] if bdd else None
    elif bench_rets:
        risk["no_beta"] = (
            f"fewer than {MIN_WEEKS} weeks in common with the benchmark"
            if len(xs) < MIN_WEEKS
            else "the benchmark did not move"
        )

    # The worst run of STRESS_WEEKS consecutive weeks, and who drove it.
    weeks = grid[1:]
    worst = None
    for i in range(len(weeks) - STRESS_WEEKS + 1):
        span = weeks[i : i + STRESS_WEEKS]
        if all(d in book for d in span):
            total = _compound([book[d] for d in span])
            if worst is None or total < worst[0]:
                worst = (total, span)
    if worst:
        total, span = worst
        start = grid[grid.index(span[0]) - 1]
        _, parts = _attributed(weights, _moves(weights, closes, start, span[-1]))
        bmove = _window_return(bench, start, span[-1])
        risk["worst_4_weeks"] = {
            "from": span[0],
            "to": _week_end(span[-1]),
            "pct": round(total * 100, 2),
            "cr": round(total * nav_cr, 2),
            "benchmark_pct": _r(bmove * 100) if bmove is not None else None,
            "contributors": _ranked(parts),
        }

    risk["contributors"] = [
        {
            "ticker": t,
            "weight_pct": round(weights[t] * 100, 2),
            "risk_share_pct": s["risk_share_pct"],
            "vol_pct": s.get("vol_pct"),
            "beta": s.get("beta"),
        }
        for t, s in sorted(
            stats.items(), key=lambda kv: -kv[1].get("risk_share_pct", -1e9)
        )
        if "risk_share_pct" in s
    ][:TOP]

    # Pairs that move together: two names in different sectors can still be
    # one bet, and the sector table cannot show it.
    tickers = sorted(t for t, s in stats.items() if s["weeks"] >= MIN_WEEKS)
    pairs = []
    for i, a in enumerate(tickers):
        for b in tickers[i + 1 :]:
            xs, ys = _paired(rets[a], rets[b])
            if len(xs) < MIN_WEEKS:
                continue
            sx, sy = _stdev(xs), _stdev(ys)
            if sx * sx > _FLAT and sy * sy > _FLAT:
                pairs.append((_cov(xs, ys) / (sx * sy), a, b))
    pairs.sort(reverse=True)
    risk["correlated_pairs"] = [
        {
            "a": a,
            "b": b,
            "correlation": round(c, 2),
            "weight_pct": round((weights[a] + weights[b]) * 100, 2),
        }
        for c, a, b in pairs[:5]
    ]
    return risk, returns, stats


def scenarios(
    rows: List[Dict[str, Any]],
    nav_cr: float,
    stats: Dict[str, Dict[str, Any]],
    risk: Dict[str, Any],
    benchmark_label: str,
) -> List[Dict[str, Any]]:
    """What the book loses if the market falls, if every holding goes back to
    its 52-week low, and if last year's worst four weeks repeat.

    All three are read from prices the run already has. Shocks to crude, the
    rupee or rates are not here: a year of weekly prices cannot tell a
    holding's sensitivity to them from noise.
    """
    out = []
    weights = {r["ticker"]: r["value_cr"] / nav_cr for r in rows}

    def scenario(key, label, parts, basis):
        total = sum(parts.values())
        out.append(
            {
                "key": key,
                "label": label,
                "pct": round(total * 100, 2),
                "cr": round(total * nav_cr, 2),
                "basis": basis,
                "contributors": _ranked(parts),
            }
        )

    no_beta = [t for t in weights if stats.get(t, {}).get("beta") is None]
    scenario(
        "market_fall",
        f"{benchmark_label} falls {abs(MARKET_SHOCK_PCT):g}%",
        {
            t: w * (stats.get(t, {}).get("beta") or 1.0) * MARKET_SHOCK_PCT / 100
            for t, w in weights.items()
        },
        "Each holding moves by its beta to the benchmark"
        + (
            f"; {_count(no_beta, 'holding')} without {MIN_WEEKS} weeks of prices "
            f"{'is' if len(no_beta) == 1 else 'are'} taken at 1.0"
            if no_beta
            else ""
        )
        + ".",
    )

    # A price already under its weekly-close low counts as no further fall.
    lows = {
        r["ticker"]: min(0.0, r["week52_low"] / r["price"] - 1)
        for r in rows
        if r.get("week52_low")
    }
    missing = sorted(set(weights) - set(lows))
    scenario(
        "week52_lows",
        "Every holding back at its 52-week low",
        {t: weights[t] * lows[t] for t in lows},
        "Each holding's lowest weekly close of the last year"
        + (
            f"; {_count(missing, 'holding')} without a range "
            f"{'is' if len(missing) == 1 else 'are'} left unchanged"
            if missing
            else ""
        )
        + ".",
    )

    worst = risk.get("worst_4_weeks")
    if worst:
        out.append(
            {
                "key": "worst_4_weeks",
                "label": f"The worst {STRESS_WEEKS} weeks of the last year again",
                "pct": worst["pct"],
                "cr": worst["cr"],
                "basis": (
                    f"Today's weights through the weeks of {worst['from']} to "
                    f"{worst['to']}."
                ),
                "contributors": worst["contributors"],
            }
        )
    return out


# --------------------------------------------------------------------------
# Limits and orders
# --------------------------------------------------------------------------


def check_limits(
    rows: List[Dict[str, Any]],
    exp: Dict[str, Any],
    limits: Dict[str, Any],
    exclusions: Dict[str, str],
    risk: Optional[Dict[str, Any]] = None,
    groups_all: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """Every limit the book breaks, worst first within each kind."""
    out = []

    def breach(kind, subject, value, limit, message):
        out.append(
            {
                "kind": kind,
                "subject": subject,
                "value": round(value, 2),
                "limit": limit,
                "message": message,
            }
        )

    max_stock = _num(limits.get("max_stock_pct"))
    max_days = _num(limits.get("max_days_to_exit"))
    max_own = _num(limits.get("max_ownership_pct"))
    for r in sorted(rows, key=lambda r: -r["weight_pct"]):
        t = r["ticker"]
        if t in exclusions:
            breach(
                "excluded",
                t,
                r["weight_pct"],
                0,
                f"{t} is held ({r['weight_pct']:.2f}% of NAV) but excluded: {exclusions[t]}",
            )
        if max_stock and r["weight_pct"] > max_stock:
            breach(
                "stock",
                t,
                r["weight_pct"],
                max_stock,
                f"{t} is {r['weight_pct']:.2f}% of NAV; the limit is {max_stock:g}%",
            )
        if max_days and r.get("days_to_exit") and r["days_to_exit"] > max_days:
            breach(
                "liquidity",
                t,
                r["days_to_exit"],
                max_days,
                f"{t} takes {r['days_to_exit']:.1f} days to exit at "
                f"{PARTICIPATION_RATE:.0%} of daily value traded; the limit is "
                f"{max_days:g}",
            )
        if max_own and r.get("ownership_pct") and r["ownership_pct"] > max_own:
            breach(
                "ownership",
                t,
                r["ownership_pct"],
                max_own,
                f"The book owns {r['ownership_pct']:.2f}% of {t}; the limit is "
                f"{max_own:g}%",
            )
    max_sector = _num(limits.get("max_sector_pct"))
    for s in exp.get("sectors") or []:
        if max_sector and s["weight_pct"] > max_sector:
            breach(
                "sector",
                s["sector"],
                s["weight_pct"],
                max_sector,
                f"{_sector_label(s['sector'])} is {s['weight_pct']:.2f}% of NAV; "
                f"the limit is {max_sector:g}%",
            )
    max_group = _num(limits.get("max_group_pct"))
    for name, weight in sorted((groups_all or {}).items(), key=lambda kv: -kv[1]):
        if max_group and weight > max_group:
            breach(
                "group",
                name,
                weight,
                max_group,
                f"{name} companies are {weight:.2f}% of NAV; the limit is "
                f"{max_group:g}%",
            )
    risk = risk or {}
    max_beta = _num(limits.get("max_beta"))
    if max_beta and risk.get("beta") is not None and risk["beta"] > max_beta:
        breach(
            "beta",
            "book",
            risk["beta"],
            max_beta,
            f"Beta is {risk['beta']:.2f}; the limit is {max_beta:g}",
        )
    max_te = _num(limits.get("max_tracking_error_pct"))
    te = risk.get("tracking_error_pct")
    if max_te and te is not None and te > max_te:
        breach(
            "tracking_error",
            "book",
            te,
            max_te,
            f"Tracking error is {te:.1f}% a year; the limit is {max_te:g}%",
        )
    # Furthest over its limit first; a name that may not be held at all leads.
    out.sort(key=lambda b: -(b["value"] / b["limit"] if b["limit"] else math.inf))
    return out


def _sector_label(key: str) -> str:
    from config import SECTOR_METADATA

    return (SECTOR_METADATA.get(key) or {}).get("label") or key.replace("_", " ")


def _group_weights(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for r in rows:
        if r.get("group"):
            out[r["group"]] = out.get(r["group"], 0.0) + r["weight_pct"]
    return out


def _annotate(rows: List[Dict[str, Any]], nav_cr: float) -> None:
    """Weight, liquidity at the real size, and ownership, on each row."""
    for r in rows:
        r["weight_pct"] = r["value_cr"] / nav_cr * 100 if nav_cr else 0.0
        if r.get("advt_cr"):
            r["pct_of_adv"] = round(r["value_cr"] / r["advt_cr"] * 100, 1)
            r["days_to_exit"] = round(_days(r["value_cr"], r["advt_cr"]), 1)
        if r.get("market_cap_cr"):
            r["ownership_pct"] = round(r["value_cr"] / r["market_cap_cr"] * 100, 3)


def rebalance(
    rows: List[Dict[str, Any]],
    targets: Dict[str, float],
    nav_cr: float,
    info: Dict[str, Dict[str, Any]],
    band_pct: float,
    exclusions: Dict[str, str],
    capped: Optional[Dict[str, Tuple[float, str]]] = None,
    cash_cr: float = 0.0,
    target_cash_pct: float = 0.0,
) -> List[Dict[str, Any]]:
    """Orders that take the book to its targets, in whole shares.

    Two passes. The first trades what must move: a name leaving the targets
    or entering them, a position over its cap, and any drift wider than the
    band. The second settles the cash those trades leave -- proceeds spread
    over the names furthest under target, or a shortfall raised from the
    names furthest over it -- ignoring the band, since otherwise selling an
    illiquid name would leave its proceeds idle until every other position
    happened to drift.
    """
    capped = capped or {}
    held = {r["ticker"]: r for r in rows}
    price = {
        t: (held[t]["price"] if t in held else (info.get(t) or {}).get("price"))
        for t in set(held) | set(targets)
    }
    price = {t: p for t, p in price.items() if p}
    qty_now = {t: held[t]["quantity"] for t in held}
    weight_now = {t: held[t]["weight_pct"] for t in held}
    trade: Dict[str, int] = {}
    why: Dict[str, str] = {}

    def shares(pct: float, t: str, up: bool = False) -> int:
        n = abs(pct) / 100 * nav_cr * _RUPEES_PER_CRORE / price[t]
        return math.ceil(n - 1e-9) if up else math.floor(n + 1e-9)

    for t in sorted(price):
        now, want = weight_now.get(t, 0.0), targets.get(t, 0.0)
        if t in held and want <= 0:
            trade[t] = -qty_now[t]
            why[t] = (
                f"excluded: {exclusions[t]}"
                if t in exclusions
                else (
                    "no longer on the watchlist"
                    if not held[t].get("in_watchlist")
                    else "not in the targets"
                )
            )
        elif t not in held and want > 0:
            trade[t] = shares(want, t)
            why[t] = "new to the targets"
        elif t in capped and now > want + 1e-9:
            trade[t] = -min(shares(now - want, t, up=True), qty_now[t])
            why[t] = f"over its cap ({capped[t][1]})"
        elif t in held and abs(want - now) > band_pct:
            n = shares(want - now, t)
            trade[t] = n if want > now else -min(n, qty_now[t])
            why[t] = "drifted from its target"

    def value_after(t: str) -> float:
        return (qty_now.get(t, 0) + trade.get(t, 0)) * price[t] / _RUPEES_PER_CRORE

    cash = cash_cr - sum(n * price[t] / _RUPEES_PER_CRORE for t, n in trade.items())
    gap = cash - target_cash_pct / 100 * nav_cr
    tolerance = 0.0005 * nav_cr
    if gap > tolerance:
        # Proceeds to the names furthest under target, in proportion.
        short = {
            t: targets[t] / 100 * nav_cr - value_after(t)
            for t in targets
            if t in price and t not in exclusions
        }
        short = {t: v for t, v in short.items() if v > 0}
        total = sum(short.values())
        for t, v in short.items():
            n = math.floor(min(v, gap * v / total) * _RUPEES_PER_CRORE / price[t])
            if n > 0:
                trade[t] = trade.get(t, 0) + n
                why.setdefault(t, "reinvests the proceeds of the sales")
    elif gap < -tolerance:
        # A shortfall raised from the names furthest over target.
        over = {
            t: value_after(t) - targets.get(t, 0.0) / 100 * nav_cr
            for t in held
            if t in price
        }
        over = {t: v for t, v in over.items() if v > 0}
        total = sum(over.values())
        for t, v in over.items():
            n = math.ceil(min(v, -gap * v / total) * _RUPEES_PER_CRORE / price[t])
            n = min(n, qty_now[t] + trade.get(t, 0))
            if n > 0:
                trade[t] = trade.get(t, 0) - n
                why.setdefault(t, "raises cash for the purchases")

    orders = []
    for t, n in trade.items():
        if not n:
            continue
        value = abs(n) * price[t] / _RUPEES_PER_CRORE
        r = held.get(t) or {}
        i = info.get(t) or {}
        orders.append(
            {
                "ticker": t,
                "name": r.get("name") or i.get("name") or t,
                "side": "BUY" if n > 0 else "SELL",
                "quantity": abs(n),
                "price": round(price[t], 2),
                "value_cr": round(value, 2),
                "weight_now_pct": round(weight_now.get(t, 0.0), 2),
                "target_pct": round(targets.get(t, 0.0), 2),
                "days_to_trade": _r(
                    _days(value, r.get("advt_cr") or i.get("advt_cr")), 1
                ),
                "reason": why.get(t, ""),
            }
        )
    orders.sort(key=lambda o: (o["side"] != "SELL", -o["value_cr"], o["ticker"]))
    return orders


def _after(
    rows: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
    cash_cr: float,
    info: Dict[str, Dict[str, Any]],
    groups: Dict[str, str],
) -> Tuple[List[Dict[str, Any]], float]:
    """The book as it would stand once every order filled at today's price."""
    book = {r["ticker"]: dict(r) for r in rows}
    cash = cash_cr
    for o in orders:
        sign = 1 if o["side"] == "BUY" else -1
        cash -= sign * o["quantity"] * o["price"] / _RUPEES_PER_CRORE
        r = book.get(o["ticker"])
        if r is None:
            i = info.get(o["ticker"]) or {}
            r = book[o["ticker"]] = {
                "ticker": o["ticker"],
                "name": o["name"],
                "sector": i.get("sector") or "other",
                "quantity": 0,
                "price": o["price"],
                "value_cr": 0.0,
                **({"advt_cr": i["advt_cr"]} if i.get("advt_cr") else {}),
                **(
                    {"market_cap_cr": i["market_cap_cr"]}
                    if i.get("market_cap_cr")
                    else {}
                ),
            }
            if o["ticker"] in groups:
                r["group"] = groups[o["ticker"]]
        r["quantity"] += sign * o["quantity"]
        r["value_cr"] = r["quantity"] * r["price"] / _RUPEES_PER_CRORE
    after = [r for r in book.values() if r["quantity"] > 0]
    nav = sum(r["value_cr"] for r in after) + cash
    _annotate(after, nav)
    return after, cash


# --------------------------------------------------------------------------
# Putting it together
# --------------------------------------------------------------------------


def _benchmark(book: Dict[str, Any]) -> Tuple[str, str, str]:
    key = str(book.get("benchmark") or DEFAULT_BENCHMARK)
    if key.upper() in BENCHMARKS:
        label, symbol = BENCHMARKS[key.upper()]
        return key.upper(), label, symbol
    # A Yahoo symbol given directly: "^CNXIT", "MID150BEES.NS".
    return key, key, key


def build_book(
    book: Dict[str, Any],
    info: Dict[str, Dict[str, Any]],
    closes: Dict[str, Dict[str, float]],
    bench: Dict[str, float],
    groups: Dict[str, str],
    prior: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Everything the page and the email show for one book."""
    key, bench_label, symbol = _benchmark(book)
    limits = book.get("limits") if isinstance(book.get("limits"), dict) else {}
    exclusions = _exclusions(book)
    rows, unpriced = _positions(book, info, closes, groups)
    cash = to_float(book.get("cash_cr")) or 0.0
    invested = sum(r["value_cr"] for r in rows)
    nav = invested + cash
    out: Dict[str, Any] = {
        "id": str(book.get("id") or "book"),
        "name": str(book.get("name") or book.get("id") or "Portfolio"),
        "kind": book.get("kind") or "actual",
        **({"note": book["note"]} if book.get("note") else {}),
        **({"inception": book["inception"]} if book.get("inception") else {}),
        "benchmark": {"key": key, "label": bench_label, "symbol": symbol},
        "limits": {k: limits[k] for k in LIMIT_LABELS if _num(limits.get(k))},
    }
    if nav <= 0:
        out["error"] = "no priced positions and no cash"
        out["unpriced"] = unpriced
        return out
    _annotate(rows, nav)

    requested = requested_targets(book, info)
    caps = _caps(sorted(requested), info, nav, limits)
    targets, capped, to_cash = apply_caps(requested, caps)
    for r in rows:
        r["target_pct"] = round(targets.get(r["ticker"], 0.0), 2)

    risk, returns, stats = risk_and_returns(rows, nav, closes, bench)
    for r in rows:
        s = stats.get(r["ticker"]) or {}
        for k in ("beta", "vol_pct", "risk_share_pct", "return_pct"):
            if s.get(k) is not None:
                r[k] = s[k]
        r["weeks"] = s.get("weeks", 0)

    sector_of = {t: i["sector"] for t, i in info.items()}
    exp = exposure(rows, targets, sector_of)
    groups_all = _group_weights(rows)
    breaches = check_limits(rows, exp, limits, exclusions, risk, groups_all)
    unmeasured = []
    if _num(limits.get("max_days_to_exit")):
        unmeasured += [
            f"{r['ticker']}: no traded value on record, so days to exit are unknown"
            for r in rows
            if not r.get("advt_cr")
        ]
    if _num(limits.get("max_ownership_pct")):
        unmeasured += [
            f"{r['ticker']}: no market value on record, so the share owned is unknown"
            for r in rows
            if not r.get("market_cap_cr")
        ]
    seen = {
        (b.get("kind"), b.get("subject")) for b in (prior or {}).get("breaches") or []
    }
    if prior is not None:
        for b in breaches:
            b["new"] = (b["kind"], b["subject"]) not in seen

    band = _num(book.get("rebalance_band_pct")) or DEFAULT_BAND_PCT
    target_cash = _num(book.get("target_cash_pct")) or 0.0
    orders = rebalance(
        rows, targets, nav, info, band, exclusions, capped, cash, target_cash
    )
    after, cash_after = _after(rows, orders, cash, info, groups)
    breaches_after = check_limits(
        after,
        exposure(after, targets, sector_of),
        limits,
        exclusions,
        None,
        _group_weights(after),
    )
    buys = sum(o["value_cr"] for o in orders if o["side"] == "BUY")
    sells = sum(o["value_cr"] for o in orders if o["side"] == "SELL")

    cost = sum(r["cost_cr"] for r in rows if r.get("cost_cr"))
    with_cost = sum(r["value_cr"] for r in rows if r.get("cost_cr"))
    for r in rows:
        if r.get("cost_cr"):
            r["pnl_cr"] = round(r["value_cr"] - r["cost_cr"], 2)
            r["pnl_pct"] = round((r["value_cr"] / r["cost_cr"] - 1) * 100, 2)

    since = None
    if book.get("inception") and bench:
        at = [d for d in sorted(bench) if d <= str(book["inception"])]
        if at:
            since = round((bench[max(bench)] / bench[at[-1]] - 1) * 100, 2)

    out.update(
        {
            "summary": {
                "nav_cr": round(nav, 2),
                "invested_cr": round(invested, 2),
                "cash_cr": round(cash, 2),
                "cash_pct": round(cash / nav * 100, 2),
                "positions": len(rows),
                "unpriced": unpriced,
                **(
                    {
                        "cost_cr": round(cost, 2),
                        "pnl_cr": round(with_cost - cost, 2),
                        "pnl_pct": round((with_cost / cost - 1) * 100, 2),
                    }
                    if cost
                    else {}
                ),
                **(
                    {"benchmark_since_inception_pct": since}
                    if since is not None
                    else {}
                ),
            },
            "exposure": exp,
            "liquidity": liquidity(rows, nav),
            "risk": risk,
            "returns": returns,
            "scenarios": scenarios(rows, nav, stats, risk, bench_label),
            "breaches": breaches,
            "unmeasured": unmeasured,
            "orders": {
                "band_pct": band,
                "rows": orders,
                "buy_cr": round(buys, 2),
                "sell_cr": round(sells, 2),
                "turnover_pct": round((buys + sells) / 2 / nav * 100, 2),
                "cash_after_cr": round(cash_after, 2),
                "capped": [
                    {
                        "ticker": t,
                        "requested_pct": round(requested[t], 2),
                        "target_pct": round(cap, 2),
                        "because": why,
                    }
                    for t, (cap, why) in sorted(capped.items())
                ],
                **({"to_cash_pct": round(to_cash, 2)} if to_cash > 1e-6 else {}),
                "breaches_after": breaches_after,
            },
            "positions": [
                {
                    **{
                        k: v
                        for k, v in r.items()
                        # Inputs to figures already on the row, not shown.
                        if k not in ("cost_cr", "market_cap_cr", "week52_low")
                    },
                    "value_cr": round(r["value_cr"], 2),
                    "weight_pct": round(r["weight_pct"], 2),
                }
                for r in sorted(rows, key=lambda r: -r["value_cr"])
            ],
        }
    )
    return out


def build_portfolios(
    watchlist: Dict[str, Any],
    weekly_closes: Optional[Dict[str, List[List[Any]]]] = None,
    books: Optional[List[Dict[str, Any]]] = None,
    groups: Optional[Dict[str, str]] = None,
    fetch: Optional[Fetcher] = None,
    prior: Optional[Dict[str, Any]] = None,
    today: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """Every book in portfolios.json, measured. Never raises."""
    today = today or datetime.date.today()
    out: Dict[str, Any] = {"as_of": today.isoformat(), "books": []}
    try:
        books = load_portfolios() if books is None else books
        if not books:
            return out
        groups = load_groups() if groups is None else groups
        info = _holdings(watchlist)
        closes = {str(t).upper(): _closes(s) for t, s in (weekly_closes or {}).items()}
        wanted = {_benchmark(b)[2] for b in books}
        for b in books:
            for p in _position_list(b):
                t = str(p.get("ticker") or "").upper()
                if t and t not in closes:
                    wanted.add(f"{t}.NS")
        fetched: Dict[str, List[List[Any]]] = {}
        try:
            fetched = (fetch or yahoo_weekly)(sorted(wanted))
        except Exception as e:  # noqa: BLE001 - priced from the watchlist alone
            log.warning(f"Portfolio: weekly download failed safely: {e!r}")
        for symbol, series in fetched.items():
            if symbol.endswith(".NS"):
                closes[symbol[:-3]] = _closes(series)
        priors = {str(p.get("id")): p for p in ((prior or {}).get("books") or []) if p}
        for b in books:
            key, label, symbol = _benchmark(b)
            bench = _closes(fetched.get(symbol))
            try:
                result = build_book(
                    b, info, closes, bench, groups, priors.get(str(b.get("id")))
                )
            except Exception as e:  # noqa: BLE001 - one bad book must not end the rest
                log.warning(f"Portfolio {b.get('id')!r} failed safely: {e!r}")
                result = {"id": str(b.get("id") or "book"), "error": repr(e)}
            if not bench:
                result.setdefault("benchmark", {})[
                    "missing"
                ] = f"no weekly closes for {symbol}"
            out["books"].append(result)
            _log(result)
    except Exception as e:  # noqa: BLE001 - an enrichment must never break a run
        log.warning(f"Portfolio failed safely: {e!r}")
        out["error"] = repr(e)
    return out


def _log(result: Dict[str, Any]) -> None:
    if result.get("error"):
        log.warning(f"Portfolio {result.get('id')}: {result['error']}.")
        return
    s, risk = result["summary"], result["risk"]
    bench = result["benchmark"]
    log.info(
        f"Portfolio {result['id']}: ₹{s['nav_cr']:,.1f} Cr in {s['positions']} "
        f"position(s)"
        + (f", {len(s['unpriced'])} unpriced" if s["unpriced"] else "")
        + (
            f"; beta {risk['beta']:.2f} to the {bench['label']} over "
            f"{risk['weeks']} weeks"
            if risk.get("beta") is not None
            else "; no beta ("
            + (
                bench.get("missing")
                or risk.get("insufficient")
                or risk.get("no_beta")
                or "no benchmark"
            )
            + ")"
        )
        + f"; {len(result['breaches'])} limit breach(es); "
        f"{len(result['orders']['rows'])} order(s) to rebalance."
    )
