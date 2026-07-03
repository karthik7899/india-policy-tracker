"""Variant perception: where does our independent estimate disagree with
consensus the most?

The interesting stock in a hedge-fund research process is rarely the one
with the highest headline upside — it's the one where an independent model
and the market's estimate diverge sharply, because that gap is the actual
bet being made. This pipeline already computes both sides for
analyst-covered stocks: ``target`` is the Street's consensus (from
``dashboard/builder.py``), and ``fundamental_value`` is this pipeline's own
Graham intrinsic-value estimate, computed unconditionally as a reference
even when analyst coverage exists. No new data is fetched; this only ranks
by the gap between numbers already on the stock.
"""

from logger import log


def _to_float(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace("%", "").replace("+", "").replace(",", "")
        if not cleaned or cleaned.upper() in {"N/A", "NA", "-", "—"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def compute_variant_perception(watchlist, min_divergence_pct=15.0):
    """Ranks analyst-covered stocks by |our estimate - consensus| / consensus.

    Only meaningful where both figures are independent: stocks tagged
    ``estimate_method == "Fundamental Estimate"`` have no analyst consensus
    to diverge from (their target *is* the model), so they're excluded.
    Returns a list sorted by divergence magnitude, largest first.
    """
    rows = []
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
            if not consensus or not our_estimate or consensus <= 0:
                continue

            divergence_pct = round((our_estimate - consensus) / consensus * 100, 1)
            if abs(divergence_pct) < min_divergence_pct:
                continue

            rows.append(
                {
                    "ticker": stock.get("ticker"),
                    "name": stock.get("name"),
                    "sector": sector,
                    "consensus_target": consensus,
                    "our_estimate": our_estimate,
                    "divergence_pct": divergence_pct,
                    "direction": (
                        "more_bullish" if divergence_pct > 0 else "more_bearish"
                    ),
                }
            )

    rows.sort(key=lambda r: abs(r["divergence_pct"]), reverse=True)
    if rows:
        log.info(f"Variant perception: {len(rows)} stocks diverge from consensus.")
    return rows
