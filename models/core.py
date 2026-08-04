from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class CompanyValuation(BaseModel):
    pe_ratio: Optional[float] = None
    graham_intrinsic_value: Optional[float] = None
    is_bargain: Optional[bool] = None
    ncav_per_share: Optional[float] = None
    owner_earnings: Optional[float] = None
    retained_earnings_ratio: Optional[float] = None
    moat_status: Optional[str] = None
    hyper_growth_warning: Optional[bool] = None
    valuation_alerts: List[str] = Field(default_factory=list)


class CompanyFinancials(BaseModel):
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    current_price: Optional[float] = None
    roce: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    dividend_yield: Optional[float] = None
    current_ratio: Optional[float] = None
    net_current_assets: Optional[float] = None

    q_sales: Optional[float] = None
    qoq_sales_growth: Optional[float] = None
    quarterly_revenue_growth: List[float] = Field(default_factory=list)
    # Trailing quarterly revenue (up to 8) and the annual P&L revenue row.
    # Valuation and growth measures read these rather than single-quarter
    # fields so seasonality cancels instead of compounding.
    sales_trend: List[float] = Field(default_factory=list)
    annual_sales_trend: List[float] = Field(default_factory=list)
    # Annotated by analysis/sector_growth.py before scoring runs. Declared
    # here so it survives coercion into this model — without it the scorer
    # read None and skipped growth entirely.
    revenue_ttm_growth_pct: Optional[float] = None
    revenue_yoy_pct: Optional[float] = None

    q_opm: Optional[float] = None
    opm_expansion: Optional[float] = None
    quarterly_ebitda_margin: List[float] = Field(default_factory=list)
    operating_margin_trend: List[float] = Field(default_factory=list)

    q_eps: Optional[float] = None
    q_net_profit: Optional[float] = None
    eps_trend: List[float] = Field(default_factory=list)
    ttm_eps: Optional[float] = None

    debt_trend: List[float] = Field(default_factory=list)
    cash_flow_trend: List[float] = Field(default_factory=list)
    roce_trend: List[float] = Field(default_factory=list)

    capex: Optional[float] = None
    rd_expenditure: Optional[float] = None
    rd_pct: Optional[float] = None

    promoter_pct: Optional[float] = None
    promoter_change: Optional[float] = None
    fii_pct: Optional[float] = None
    fii_change: Optional[float] = None
    dii_pct: Optional[float] = None
    dii_change: Optional[float] = None

    # Tradeability. Declared here for the same reason the TTM growth fields
    # are: anything absent from this model is silently dropped on coercion,
    # so the scorer would read None no matter what the fetcher attached.
    advt_cr: Optional[float] = None
    liquidity_band: Optional[str] = None
    days_to_exit_1cr: Optional[float] = None
    days_to_exit_5cr: Optional[float] = None
    sessions: Optional[int] = None


class CompanyScore(BaseModel):
    overall_score: int = 0
    # Reported separately so the headline number is readable: news flow and
    # balance-sheet quality move for different reasons and should not be
    # indistinguishable once summed.
    fundamental_score: int = 0
    momentum_score: int = 0
    confidence: str = "Low"
    reasons: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class Company(BaseModel):
    ticker: str
    name: str
    price: Optional[float] = 0.0
    percent_change: Optional[float] = 0.0
    volume_surge: Optional[float] = 0.0
    relative_volume: Optional[float] = 0.0
    price_to_ma: Optional[float] = 0.0
    momentum_score: Optional[float] = 0.0

    screener: Optional[Union[Dict[str, Any], CompanyFinancials]] = Field(
        default_factory=dict
    )
    valuation: Optional[CompanyValuation] = None
    score: Optional[CompanyScore] = None
    policy_events: List[Any] = Field(default_factory=list)


class NewsEvent(BaseModel):
    company: str
    industry: str
    title: Optional[str] = None
    product: Optional[str] = None
    event_type: Optional[str] = None
    date: str
    source: str
    link: str


class FilingEvent(BaseModel):
    company: str
    industry: str
    filing: str
    date: str
    source: str
    link: str


class EmergingCompetitor(BaseModel):
    company: str
    sector: str
    scheme: str
    approval_date: str
