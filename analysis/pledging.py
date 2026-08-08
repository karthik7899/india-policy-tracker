"""Promoter share pledging: a standing condition that becomes urgent on price.

A pledge is collateral. On its own it says the promoter borrowed against their
holding, which is common and not by itself a warning. It turns into one when
the pledge is large, when it is growing, or when the share price falls far
enough that the lender can call for more collateral -- and the promoter's
options at that point are to post more shares, sell, or be sold out of. Each
of those is bad for the minority holder, which is why proximity to the
52-week low matters more here than in any other rule.

The three inputs are graded separately and never substituted for one another.
A holding whose pledge could not be read is "not disclosed", never 0%: the
row is absent from Screener both for companies with no pledge and for a page
this parser failed to match, and asserting an all-clear on the second is the
kind of confident-wrong output the rest of this codebase keeps having to
undo.
"""

from typing import Any, Dict, List

from logger import log

# Pledge share of promoter holding at which the condition is worth stating at
# all. Below this the collateral is small enough that a normal drawdown does
# not threaten it.
NOTABLE_PCT = 5.0

# The level the spec calls Critical when it is also rising.
HIGH_PCT = 15.0

# A pledge above this is a standing risk regardless of trend or price.
SEVERE_PCT = 40.0

# Rise over the last disclosed quarter that counts as "rising". Pledge
# percentages are reported to one decimal and move in steps, so a threshold
# below this would fire on rounding.
RISING_PP = 0.5

# Distance above the 52-week low inside which a pledge becomes urgent. The
# spec's figure: a lender's margin call does not wait for a new low.
NEAR_LOW_PCT = 20.0


def assess(
    pledged_pct: float = None,
    pledged_change: float = None,
    pct_above_low: float = None,
) -> Dict[str, Any]:
    """Grade one holding's pledge exposure.

    Returns ``status`` (``not_disclosed`` / ``none`` / ``notable`` / ``high``
    / ``severe``), the ``severity`` an alert would carry, and the reasons, so
    the finding can be argued with rather than just asserted.
    """
    if pledged_pct is None:
        return {
            "status": "not_disclosed",
            "severity": None,
            "pledged_pct": None,
            "reasons": ["Pledge not disclosed or not parsed this run"],
        }

    try:
        pledged_pct = float(pledged_pct)
    except (TypeError, ValueError):
        return {
            "status": "not_disclosed",
            "severity": None,
            "pledged_pct": None,
            "reasons": ["Pledge value unreadable"],
        }

    if pledged_pct <= 0:
        return {
            "status": "none",
            "severity": None,
            "pledged_pct": 0.0,
            "reasons": ["No promoter shares pledged"],
        }

    rising = isinstance(pledged_change, (int, float)) and pledged_change >= RISING_PP
    near_low = (
        isinstance(pct_above_low, (int, float)) and 0 <= pct_above_low <= NEAR_LOW_PCT
    )

    reasons = [f"{pledged_pct:.1f}% of promoter holding pledged"]
    if rising:
        reasons.append(f"up {pledged_change:+.1f}pp since the prior disclosure")
    if near_low:
        reasons.append(f"trading {pct_above_low:.0f}% above its 52-week low")
    # Stated explicitly, because "we could not check the price" and "the price
    # is comfortably off its low" lead to different conclusions and must not
    # look the same in the output.
    if pct_above_low is None:
        reasons.append(
            "52-week range not available, so proximity to the low is unknown"
        )

    if pledged_pct >= SEVERE_PCT:
        status, severity = "severe", "Critical"
    elif pledged_pct >= HIGH_PCT:
        status = "high"
        # The spec's rule: high *and* deteriorating is Critical. High and
        # stable, with the price off its low, is a High -- real, but not the
        # same thing as a squeeze in progress.
        severity = "Critical" if (rising or near_low) else "High"
    elif pledged_pct >= NOTABLE_PCT:
        status = "notable"
        severity = "High" if (rising and near_low) else "Medium"
    else:
        status = "notable" if rising else "none"
        severity = "Medium" if rising else None

    return {
        "status": status,
        "severity": severity,
        "pledged_pct": round(pledged_pct, 2),
        "pledged_change": pledged_change,
        "pct_above_low": pct_above_low,
        "rising": rising,
        "near_low": near_low,
        "reasons": reasons,
    }


def pledge_warnings(watchlist: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Alerts for every holding whose pledge exposure warrants one.

    Never raises. Holdings with no disclosed pledge produce nothing at all --
    the absence is reported once in the data-quality note rather than as
    sixty-nine separate all-clears.
    """
    alerts: List[Dict[str, Any]] = []
    disclosed = not_disclosed = 0
    try:
        from config import SECTOR_METADATA

        for sector, stocks in (watchlist or {}).items():
            if sector == "macro_indicators" or sector not in SECTOR_METADATA:
                continue
            label = (SECTOR_METADATA[sector] or {}).get("label") or sector
            for stock in stocks or []:
                if not isinstance(stock, dict) or not stock.get("ticker"):
                    continue
                sc = stock.get("screener") or {}
                verdict = assess(
                    sc.get("pledged_pct"),
                    sc.get("pledged_change"),
                    sc.get("pct_above_low"),
                )
                if verdict["status"] == "not_disclosed":
                    not_disclosed += 1
                    continue
                disclosed += 1
                if not verdict["severity"]:
                    continue
                alerts.append(
                    {
                        "ticker": stock["ticker"],
                        "name": stock.get("name", ""),
                        "sector": label,
                        "severity": verdict["severity"],
                        "direction": "risk",
                        "category": "Promoter Pledging",
                        "signal": "; ".join(verdict["reasons"]) + ".",
                        "pledged_pct": verdict["pledged_pct"],
                    }
                )

        if disclosed or not_disclosed:
            log.info(
                f"Promoter pledging: {len(alerts)} alert(s) from {disclosed} "
                f"holding(s) with a disclosed pledge; {not_disclosed} not "
                f"disclosed or not parsed."
            )
    except Exception as e:  # noqa: BLE001 - an enrichment must never break a run
        log.warning(f"Pledge assessment failed safely: {e!r}")
    return alerts
