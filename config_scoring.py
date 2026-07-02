from pydantic import BaseModel


class ScoringWeights(BaseModel):
    # Weights for different events in Policy Tailwind
    pli_approval: int = 5
    pib_announcement: int = 4
    government_contract: int = 4
    policy_news: int = 3
    sector_mapping_fallback: int = 1

    # Financial Strength thresholds
    max_debt_to_equity: float = 0.5
    min_current_ratio: float = 2.0

    # Growth Momentum thresholds
    min_qoq_sales_growth: float = 15.0
    min_operating_margin_expansion: float = 2.0

    # Capital Allocation thresholds
    min_roce: float = 20.0
    min_roe: float = 15.0

    # Institutional Interest weights
    fii_accumulation_points: int = 2
    dii_accumulation_points: int = 1

    # Valuation points
    bargain_points: int = 3
    graham_undervalued_points: int = 2

    # Competitive Advantage points
    wide_moat_points: int = 3
    narrow_moat_points: int = 1

    # Thresholds for final Recommendations
    strong_buy_threshold: int = 15
    buy_threshold: int = 10
    hold_threshold: int = 5

    # Total points possible to compute confidence or normalization (approximate)
    # The actual max is dynamic based on policy tailwinds.


SCORING_CONFIG = ScoringWeights()


class EarlyWarningThresholds(BaseModel):
    """Severity cutoffs for the Early Warning System.

    Only thresholds not already expressed in ``ScoringWeights`` live here; the
    early-warning rules reuse ``SCORING_CONFIG`` (e.g. ``max_debt_to_equity``,
    ``min_current_ratio``, ``min_qoq_sales_growth``) wherever a value already exists.
    """

    # Institutional ownership shifts (quarterly % point change)
    fii_outflow_high: float = -1.0
    fii_outflow_critical: float = -3.0
    promoter_exit_high: float = -1.0
    promoter_exit_critical: float = -2.0

    # Operating margin contraction (% point change vs prior period)
    margin_compression: float = -2.0

    # Leverage above which the position is flagged as critical
    leverage_critical: float = 1.0

    # Intraday price action (percent change for the session)
    intraday_drop_high: float = -5.0
    intraday_drop_critical: float = -8.0

    # Momentum breakout — relative volume multiple that confirms a move
    volume_surge_breakout: float = 2.0

    # Peer-group market share shifts (percentage points over the lookback)
    share_loss_pp: float = -0.75
    share_loss_critical_pp: float = -2.0
    share_gain_pp: float = 0.75

    # Growth-laggard fallback (QoQ percentage points below sector median),
    # used only for stocks without peer-share data
    growth_laggard_gap: float = 10.0


EARLY_WARNING_CONFIG = EarlyWarningThresholds()
