"""Decide whether a priced trade fits the available cash and owned shares."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

TradeSide = Literal["BUY", "SELL"]
FailureReason = Literal["insufficient_cash", "insufficient_shares"]
CASH_EPSILON = 1e-9
SHARE_EPSILON = 1e-9


@dataclass(frozen=True)
class PricedTrade:
    symbol: str
    side: TradeSide
    amount: float
    price: float
    shares: float
    simulated_date: date


def trade_rejection_reason(
    trade: PricedTrade,
    available_cash: float,
    available_shares: float,
    *,
    holding_exists: bool,
) -> FailureReason | None:
    """Check affordability without changing an account or holding."""
    if trade.side == "BUY" and trade.amount > available_cash + CASH_EPSILON:
        return "insufficient_cash"
    if trade.side == "SELL" and (
        not holding_exists or trade.shares > available_shares + SHARE_EPSILON
    ):
        return "insufficient_shares"
    return None


def calculate_average_cost_after_buy(
    current_shares: float,
    current_average_cost: float,
    bought_shares: float,
    purchase_price: float,
) -> float:
    """Spread the combined cost over the combined owned shares."""
    total_cost = current_shares * current_average_cost + bought_shares * purchase_price
    return total_cost / (current_shares + bought_shares)
