from pydantic import BaseModel
from typing import Dict, Any


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
