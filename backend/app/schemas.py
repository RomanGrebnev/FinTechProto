from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

SavingsGoal = Literal["retirement", "home", "education", "wealth_growth", "emergency_fund", "other"]

InvestmentKnowledge = Literal["none", "basic", "informed", "advanced"]
MaxLossPct = Literal[0, 5, 10, 20, 30, 50]


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class DeleteAccount(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileIn(BaseModel):
    age: int = Field(ge=18, le=100)
    annual_income: float = Field(ge=0)
    savings_goal: SavingsGoal
    monthly_investment: float = Field(ge=0)
    risk_tolerance: int = Field(ge=1, le=5)
    horizon_years: int = Field(ge=1, le=50)
    investment_knowledge: InvestmentKnowledge
    investment_experience_years: int = Field(ge=0, le=50)
    max_acceptable_loss_pct: MaxLossPct


class ProfileOut(ProfileIn):
    model_config = {"from_attributes": True}
    # Nullable on read: profiles created before FR-SUITABILITY-01 lack these until the client completes them.
    investment_knowledge: InvestmentKnowledge | None = None
    investment_experience_years: int | None = None
    max_acceptable_loss_pct: MaxLossPct | None = None


class Me(BaseModel):
    id: int
    email: str
    profile: ProfileOut | None


class HoldingIn(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    quantity: float = Field(gt=0)
    avg_buy_price: float = Field(gt=0)


class HoldingOut(BaseModel):
    id: int
    ticker: str
    name: str | None
    instrument_type: str | None
    quantity: float
    avg_buy_price: float
    current_price: float | None
    currency: str
    value: float
    cost_basis: float
    pnl: float
    pnl_pct: float
    weight: float
    price_available: bool


class PortfolioOut(BaseModel):
    holdings: list[HoldingOut]
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    currency: str
    risk_score: float
    risk_label: str
    volatility: float | None
    target_risk: int | None


class Recommendation(BaseModel):
    action: Literal["buy", "sell", "hold", "rebalance"]
    ticker: str
    title: str
    rationale: str


class Rebalancing(BaseModel):
    summary: str
    target_allocation: list[dict]


class RiskFlag(BaseModel):
    severity: Literal["low", "medium", "high"]
    title: str
    detail: str


class Analysis(BaseModel):
    summary: str
    recommendations: list[Recommendation]
    rebalancing: Rebalancing
    risk_flag: RiskFlag


class AnalysisOut(BaseModel):
    id: int
    created_at: datetime
    source: str
    analysis: Analysis
    disclaimer: str
    outdated: bool = False


class AnalysisSummary(BaseModel):
    id: int
    created_at: datetime
    mode: str
    outdated: bool


class MarketIndex(BaseModel):
    symbol: str
    name: str
    price: float | None
    change_pct: float | None
