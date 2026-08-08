"""Price-based input-cost shocks per sector.

``compute_supply_stress`` in event_engine.py counts supply-side *headlines*
and is the forward-looking margin signal the pipeline already had. This is the
other half: what the inputs actually did. The two disagree usefully -- a
sector can be quiet in the news while its main raw material moves 20%.

Nothing here fabricates. A symbol that fails to fetch is recorded as
unmeasured with the reason attached, because a missing commodity rendered as
"no shock" is indistinguishable from a commodity that genuinely did not move,
and the second is a real finding while the first is a broken run.
"""

import math
from typing import Any, Dict

from config_commodities import (
    COMMODITY_MAP,
    MATERIAL_MOVE_PCT,
    SEVERE_MOVE_PCT,
    WINDOW_DAYS,
)
from logger import log


def _pct_change(first: float, last: float):
    """Percentage move, or None when the base cannot support one."""
    try:
        first, last = float(first), float(last)
    except (TypeError, ValueError):
        return None
    if not first or math.isnan(first) or math.isnan(last):
        return None
    return (last - first) / abs(first) * 100


def fetch_input_prices(window_days: int = WINDOW_DAYS) -> Dict[str, Dict[str, Any]]:
    """Window-open and window-close for every mapped input.

    One batched request, matching the pattern in analysis/growth.py. Never
    raises: an enrichment that can fail a run is worse than one that
    occasionally returns nothing.
    """
    results: Dict[str, Dict[str, Any]] = {}
    symbols = {key: cfg["symbol"] for key, cfg in COMMODITY_MAP.items()}
    try:
        import yfinance as yf

        data = yf.download(
            list(symbols.values()),
            period=f"{max(window_days, 5)}d",
            group_by="ticker",
            threads=True,
            timeout=15,
            progress=False,
        )
        # yfinance swallows a blocked or failed request and hands back an
        # empty frame, so an unreachable Yahoo looks exactly like a market
        # that did not trade. Checking the frame itself is the only way to
        # tell a fetch failure from a genuinely thin series, and the two
        # belong in the data-quality note under different words.
        fetch_failed = data is None or getattr(data, "empty", False)
        for key, symbol in symbols.items():
            if fetch_failed:
                results[key] = {"error": "price fetch returned no data this run"}
                continue
            try:
                frame = data[symbol] if symbol in data else data
                closes = frame["Close"].dropna()
                if closes.empty:
                    results[key] = {"error": "no sessions returned for this symbol"}
                    continue
                if len(closes) < 2:
                    results[key] = {"error": "only one session returned"}
                    continue
                results[key] = {
                    "first": float(closes.iloc[0]),
                    "last": float(closes.iloc[-1]),
                    "sessions": int(len(closes)),
                }
            except Exception as e:  # noqa: BLE001 - per-symbol, keep the rest
                results[key] = {"error": f"unreadable series ({e.__class__.__name__})"}
    except Exception as e:  # noqa: BLE001
        log.warning(f"Input-cost price fetch failed safely: {e!r}")
        for key in symbols:
            results.setdefault(key, {"error": "price fetch unavailable this run"})
    return results


def classify(pct: float) -> str:
    if pct is None:
        return "unmeasured"
    move = abs(pct)
    if move >= SEVERE_MOVE_PCT:
        return "severe"
    if move >= MATERIAL_MOVE_PCT:
        return "material"
    return "quiet"


def compute_input_cost_shock(
    prices: Dict[str, Dict[str, Any]] = None, window_days: int = WINDOW_DAYS
) -> Dict[str, Any]:
    """Per-sector input-cost pressure, with the inputs that caused it.

    Returns ``{"sectors": {...}, "inputs": {...}, "unmeasured": [...]}``.

    A sector is listed once any input it is exposed to made a material move,
    and keeps its weighted score even when that score lands back in ``quiet``
    -- "we measured this and it came to nothing" is a different statement
    from silence, and only the first is evidence. ``unmeasured`` carries the
    inputs that could not be priced at all, so a failed fetch can never be
    read as a calm market.

    The weighted score stays in percentage points: an 18% copper move against
    a 0.30 weight is a 5.4% effective move on the share of the cost base
    copper represents, which is why it is banded on the same thresholds as
    the raw input move.
    """
    out: Dict[str, Any] = {"sectors": {}, "inputs": {}, "unmeasured": []}
    try:
        if prices is None:
            prices = fetch_input_prices(window_days)

        for key, cfg in COMMODITY_MAP.items():
            quote = (prices or {}).get(key) or {}
            if quote.get("error") or "first" not in quote:
                out["unmeasured"].append(
                    {
                        "input": key,
                        "label": cfg["label"],
                        "reason": quote.get("error") or "no price returned",
                    }
                )
                continue

            pct = _pct_change(quote["first"], quote["last"])
            band = classify(pct)
            out["inputs"][key] = {
                "label": cfg["label"],
                "unit": cfg["unit"],
                "change_pct": round(pct, 2) if pct is not None else None,
                "band": band,
                "sessions": quote.get("sessions"),
            }
            if pct is None:
                out["unmeasured"].append(
                    {
                        "input": key,
                        "label": cfg["label"],
                        "reason": "opening price was zero or missing",
                    }
                )
                continue
            if band == "quiet":
                continue

            for sector, weight, side in cfg["exposure"]:
                # The sign convention this map exists for. A rise in an input
                # a sector consumes is pressure; a rise in one it earns from
                # is relief. Collapsing the two would flag exporters and
                # importers identically on every currency move.
                pressure = pct if side == "consumer" else -pct
                row = out["sectors"].setdefault(
                    sector, {"score": 0.0, "drivers": [], "band": "quiet"}
                )
                row["score"] += pressure * weight
                row["drivers"].append(
                    {
                        "input": key,
                        "label": cfg["label"],
                        "change_pct": round(pct, 2),
                        "side": side,
                        "weight": weight,
                        "direction": "cost pressure" if pressure > 0 else "tailwind",
                    }
                )

        for sector, row in out["sectors"].items():
            row["score"] = round(row["score"], 2)
            row["band"] = classify(row["score"])
            row["direction"] = "cost pressure" if row["score"] > 0 else "tailwind"
            row["drivers"].sort(key=lambda d: -abs(d["change_pct"] * d["weight"]))

        measured = len(out["inputs"])
        if measured or out["unmeasured"]:
            # Counted on the weighted band, not on membership of the map. A
            # sector is listed once any input it touches moves, but most of
            # those land back in "quiet" after weighting, and reporting the
            # list length would claim twelve shocks on a day with one.
            shocked = sum(
                1
                for r in out["sectors"].values()
                if r["band"] in ("material", "severe")
            )
            log.info(
                f"Input costs ({window_days}d): {measured}/{len(COMMODITY_MAP)} "
                f"input(s) priced, {shocked} sector(s) with a material shock "
                f"({len(out['sectors'])} touched), "
                f"{len(out['unmeasured'])} unmeasured."
            )
    except Exception as e:  # noqa: BLE001 - an enrichment must never break a run
        log.warning(f"Input-cost computation failed safely: {e!r}")
    return out


def input_cost_warnings(shock: Dict[str, Any]) -> list:
    """Sector-level alerts for material input-cost moves.

    Severity ladders on the weighted move, not the raw commodity move: a 20%
    copper spike matters more to clean energy than to logistics, and the
    weights are the only place that difference is expressed.
    """
    alerts = []
    try:
        for sector, row in (shock or {}).get("sectors", {}).items():
            score = row.get("score")
            if not isinstance(score, (int, float)) or row.get("band") == "quiet":
                continue
            pressure = score > 0
            top = (row.get("drivers") or [{}])[0]
            alerts.append(
                {
                    # A commodity move is a property of the sector, not of any
                    # one holding in it, so there is no ticker to name. Carried
                    # as an explicit empty string rather than omitted: every
                    # other alert producer sets this key, and consumers -- the
                    # ranking sort, the email cards, the coverage badge -- all
                    # read it positionally.
                    "ticker": "",
                    "name": "",
                    "sector": sector,
                    "severity": "High" if row.get("band") == "severe" else "Medium",
                    "direction": "risk" if pressure else "opportunity",
                    "category": "Input Cost Shock",
                    "signal": (
                        f"{top.get('label', 'An input')} moved "
                        f"{top.get('change_pct', 0):+.1f}% over "
                        f"{WINDOW_DAYS} days; weighted "
                        f"{'cost pressure' if pressure else 'tailwind'} "
                        f"of {abs(score):.1f} for this sector."
                    ),
                }
            )
        alerts.sort(key=lambda a: (a["severity"] != "High", a["sector"]))
    except Exception as e:  # noqa: BLE001
        log.warning(f"Input-cost warnings failed safely: {e!r}")
    return alerts
