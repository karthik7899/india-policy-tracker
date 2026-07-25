"""Variant perception: where does our independent estimate disagree with
consensus the most?

The interesting stock in a hedge-fund research process is rarely the one
with the highest headline upside — it's the one where an independent model
and the market's estimate diverge sharply, because that gap is the actual
bet being made. This pipeline computes both sides for analyst-covered
stocks: ``target`` is the Street's consensus (from ``dashboard/builder.py``),
and ``fundamental_value`` is this pipeline's own Graham intrinsic-value
estimate. No new data is fetched; this only ranks by the gap between numbers
already on the stock.

A gap is only evidence of disagreement if both sides are sound. When the
intrinsic value was built by annualizing a single quarter's earnings, 72% of
covered holdings "diverged" from consensus and the list was really a ranking
of which companies had the most seasonal quarters. So every row now has to
clear a plausibility gate first: an estimate that sits at a small fraction or
a large multiple of the live share price is a model artifact, and artifacts
are excluded from the screen and counted in the log rather than published as
a view.
"""

from analysis.data_quality import (
    INTRINSIC_VALUE_MULTIPLE_BAND,
    classify,
    is_trustworthy,
)
from logger import log
from utils import to_float as _to_float


def compute_variant_perception(watchlist, min_divergence_pct=15.0):
    """Ranks analyst-covered stocks by |our estimate - consensus| / consensus.

    Only meaningful where both figures are independent: stocks tagged
    ``estimate_method == "Fundamental Estimate"`` have no analyst consensus
    to diverge from (their target *is* the model), so they're excluded.
    Returns a list sorted by divergence magnitude, largest first.
    """
    rows = []
    rejected = 0
    for sector, stocks in (watchlist or {}).items():
        if sector == "macro_indicators":
            continue
        for stock in stocks or []:
            if not isinstance(stock, dict):
                continue
            if stock.get("estimate_method") != "Analyst Consensus":
                continue

            consensus = _to_float(stock.get("target"))
            our_estimate = _to_float(stock.get("fundamental_value"))
            price = _to_float(stock.get("price"))
            if not consensus or not our_estimate or consensus <= 0:
                continue

            # An intrinsic value is only a view if it is tethered to the
            # traded price; otherwise the "divergence" is the model's noise.
            quality = classify(
                (our_estimate / price) if price and price > 0 else None,
                band=INTRINSIC_VALUE_MULTIPLE_BAND,
            )
            if not is_trustworthy(quality):
                rejected += 1
                continue

            divergence_pct = round((our_estimate - consensus) / consensus * 100, 1)
            if abs(divergence_pct) < min_divergence_pct:
                continue

            rows.append(
                {
                    "ticker": stock.get("ticker"),
                    "name": stock.get("name"),
                    "sector": sector,
                    "price": price,
                    "consensus_target": consensus,
                    "our_estimate": our_estimate,
                    "divergence_pct": divergence_pct,
                    "direction": (
                        "more_bullish" if divergence_pct > 0 else "more_bearish"
                    ),
                }
            )

    rows.sort(key=lambda r: abs(r["divergence_pct"]), reverse=True)
    if rows or rejected:
        log.info(
            f"Variant perception: {len(rows)} stocks diverge from consensus"
            f"{f'; {rejected} estimate(s) failed the plausibility gate' if rejected else ''}."
        )
    return rows
