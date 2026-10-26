"""Pydantic request and response models for the portfolio screen and its actions."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradeRequest(BaseModel):
    user_id: int
    symbol: str
    side: Literal["BUY", "SELL"]
    amount: float = Field(gt=0, allow_inf_nan=False)


class AdvanceSimulationRequest(BaseModel):
    user_id: int
    step: Literal["1W", "1M", "1Q"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    name: str


class MarketPriceHistoryPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: date
    close: float


class HoldingValueResponse(BaseModel):
    symbol: str
    shares: float
    average_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_gain_loss: float
    allocation_percentage: float


class PortfolioResponse(BaseModel):
    user_id: int
    simulated_date: date
    cash_balance: float
    holdings_value: float
    total_value: float
    total_return_amount: float
    total_return_percentage: float
    holdings: list[HoldingValueResponse]


class AccountValueHistoryPointResponse(BaseModel):
    date: date
    cash_balance: float
    holdings_value: float
    total_value: float


class TradePreviewResponse(BaseModel):
    symbol: str
    side: Literal["BUY", "SELL"]
    amount: float
    price: float
    shares: float
    simulated_date: date
    valid: bool
    message: str


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    side: str
    shares: float
    price: float
    amount: float
    simulated_date: date


class PortfolioScreenResponse(PortfolioResponse):
    investor_name: str
    assets: list[AssetResponse]
    history: list[AccountValueHistoryPointResponse]
    trades: list[TradeResponse]


class SimulationAdvanceResponse(BaseModel):
    previous_date: date
    current_date: date
    previous_value: float
    current_value: float


class LoginRequest(BaseModel):
    email: str


class DemoResetResponse(BaseModel):
    accounts_reset: int


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class InvestorAIQuestionRequest(BaseModel):
    user_id: int
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("question")
    @classmethod
    def require_question(cls, question: str) -> str:
        if not question.strip():
            raise ValueError("Enter a question")
        return question.strip()


class PortfolioChatRequest(InvestorAIQuestionRequest):
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=6)

    @field_validator("history")
    @classmethod
    def require_completed_turns(cls, history: list[ChatHistoryMessage]) -> list[ChatHistoryMessage]:
        expected_roles = ["user", "assistant"] * (len(history) // 2)
        if [message.role for message in history] != expected_roles:
            raise ValueError("History must contain completed user/assistant turns")
        return history


class PortfolioChatResponse(BaseModel):
    answer: str
    history: list[ChatHistoryMessage]


class HandbookSourceResponse(BaseModel):
    title: str
    passage: str
    score: float | None


class HandbookRagResponse(BaseModel):
    answer: str
    sources: list[HandbookSourceResponse]


class AgentToolReadResponse(BaseModel):
    tool_name: str
    arguments: dict[str, object]
    result: str


class PortfolioAgentResponse(BaseModel):
    answer: str
    tool_calls: list[AgentToolReadResponse]
