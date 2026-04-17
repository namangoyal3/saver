"""Pydantic schemas for Saver agent — matches PRD §15."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class Market(str, Enum):
    SG = "SG"
    ID = "ID"


class PartnerType(str, Enum):
    RIDE = "ride"
    DELIVERY = "delivery"
    MERCHANT = "merchant"


class EarningsTier(str, Enum):
    LOW = "L"
    MEDIUM = "M"
    HIGH = "H"


class FinancialPersona(str, Enum):
    STABILIZER = "stabilizer"
    GROWER = "grower"
    FIREFIGHTER = "firefighter"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Intent(str, Enum):
    DESCRIBE_SPEND = "describe_spend"
    DESCRIBE_INCOME = "describe_income"
    CASHFLOW_EXPLAIN = "cashflow_explain"
    SET_GOAL = "set_goal"
    SIMULATE_GOAL = "simulate_goal"
    ADJUST_GOAL = "adjust_goal"
    FORECAST = "forecast"
    CONCEPT_QUESTION = "concept_question"
    HOW_DOES_X_WORK = "how_does_x_work"
    NUDGE_CHECK_IN = "nudge_check_in"
    # Out-of-scope intents → routed to refusal
    INVESTMENT_ADVICE = "investment_advice"
    SPECIFIC_PRODUCT = "specific_product"
    TAX = "tax"
    LEGAL = "legal"
    SMALLTALK = "smalltalk"
    META = "meta"


OUT_OF_SCOPE_INTENTS = {
    Intent.INVESTMENT_ADVICE,
    Intent.SPECIFIC_PRODUCT,
    Intent.TAX,
    Intent.LEGAL,
}

ANALYST_INTENTS = {
    Intent.DESCRIBE_SPEND,
    Intent.DESCRIBE_INCOME,
    Intent.CASHFLOW_EXPLAIN,
}

PLANNER_INTENTS = {
    Intent.SET_GOAL,
    Intent.SIMULATE_GOAL,
    Intent.ADJUST_GOAL,
    Intent.FORECAST,
}


# ── User profile ───────────────────────────────────────────────────────

class UserProfileSnapshot(BaseModel):
    user_id: str
    name: str
    market: Market
    preferred_lang: str
    partner_types: list[PartnerType]
    consents: dict[str, bool] = Field(default_factory=lambda: {
        "txn_read": True, "grab_link": True, "notifications": True, "autosave": True
    })
    earnings_tier: EarningsTier = EarningsTier.MEDIUM
    financial_persona: FinancialPersona = FinancialPersona.STABILIZER
    currency: str = "SGD"


# ── Agent turn request / response ──────────────────────────────────────

class AgentTurnRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    message: str
    locale: str = "en"


class ReasoningStep(BaseModel):
    idx: int
    agent: Literal["supervisor", "analyst", "planner"]
    action: Literal["plan", "tool_call", "compose", "refuse", "handoff"]
    tool_name: Optional[str] = None
    tool_args_summary: Optional[str] = None
    result_summary: Optional[str] = None
    latency_ms: int = 0


class GuardrailReport(BaseModel):
    input_pii_redacted: bool = False
    input_scope_check: Literal["pass", "blocked"] = "pass"
    output_grounding_check: Literal["pass", "violation_cleaned", "blocked"] = "pass"
    output_scope_check: Literal["pass", "blocked"] = "pass"


class AgentTurnResponse(BaseModel):
    reply: str
    reply_language: str = "en"
    reasoning_trace: list[ReasoningStep] = Field(default_factory=list)
    guardrail_report: GuardrailReport = Field(default_factory=GuardrailReport)
    confirmation_required: Optional[dict] = None


# ── Tool input/output schemas ──────────────────────────────────────────

class TransactionRecord(BaseModel):
    txn_id: str
    posted_at: str
    amount: float
    currency: str
    direction: Literal["debit", "credit"]
    category: Optional[str] = None
    counterparty: Optional[str] = None
    channel: Optional[str] = None


class ExpenseCategory(BaseModel):
    category: str
    amount: float
    percentage: float


class ExpenseBreakdownResult(BaseModel):
    total: float
    currency: str
    window_days: int
    top_categories: list[ExpenseCategory]


class IncomeSummaryResult(BaseModel):
    total_income: float
    currency: str
    window_days: int
    avg_weekly: float
    source_breakdown: dict[str, float]


class GrabEarningsResult(BaseModel):
    gross_earnings: float
    net_earnings: float
    currency: str
    window_days: int
    platform_fees: float
    incentives: float


class GrabTripSummaryResult(BaseModel):
    total_trips: int
    total_hours: float
    avg_earnings_per_trip: float
    fuel_ratio: float
    currency: str
    window_days: int


class ForecastPoint(BaseModel):
    date: str
    net_p50: float
    net_p10: float
    net_p90: float
    currency: str


class ForecastSummary(BaseModel):
    expected_min_balance: float
    probability_negative_balance: float
    high_risk_dates: list[str]


class ForecastResult(BaseModel):
    points: list[ForecastPoint]
    summary: ForecastSummary
    method: str = "naive_seasonal"
    currency: str = "SGD"


class GoalRecord(BaseModel):
    goal_id: str
    user_id: str
    name: str
    target_amount: float
    current_amount: float = 0.0
    currency: str
    target_date: Optional[str] = None
    status: GoalStatus = GoalStatus.ACTIVE
    contribution_plan: dict = Field(default_factory=dict)
    created_at: Optional[str] = None


class SimulateGoalResult(BaseModel):
    feasible: bool
    suggested_weekly_contribution: float
    risk_weeks: list[str]
    narrative: str
    currency: str
