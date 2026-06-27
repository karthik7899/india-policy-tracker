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

    q_opm: Optional[float] = None
    opm_expansion: Optional[float] = None
    quarterly_ebitda_margin: List[float] = Field(default_factory=list)
    operating_margin_trend: List[float] = Field(default_factory=list)

    q_eps: Optional[float] = None
    q_net_profit: Optional[float] = None

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


class CompanyScore(BaseModel):
    overall_score: int = 0
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
