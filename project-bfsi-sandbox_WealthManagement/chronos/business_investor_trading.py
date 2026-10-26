"""Price, preview, execute, and record an investor's virtual trades.

Python enforces affordability. These workflows flush changes; the caller owns
commit and rollback. A preview neither reserves funds nor locks a quote.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from chronos.api_schemas_requests_and_responses import (
    TradePreviewResponse,
    TradeRequest,
)
from chronos.storage_sqlite_tables_and_sessions import Account, Holding, Trade
from chronos.app_business_errors_and_permissions import (
    InsufficientCashError,
    InsufficientSharesError,
)
from chronos.business_portfolio_valuation import record_current_portfolio_value
from chronos.market_historical_prices import (
    get_latest_price_on_or_before_date,
    require_supported_asset,
)
from chronos.rules_trade_eligibility_and_cost import (
    SHARE_EPSILON,
    FailureReason,
    PricedTrade,
    calculate_average_cost_after_buy,
    trade_rejection_reason,
)


def preview_investor_trade(
    db: Session, account: Account, request: TradeRequest
) -> TradePreviewResponse:
    """Explain whether a trade is affordable without changing financial records."""
    trade = price_requested_trade(db, account, request)
    holding = find_account_holding(db, account.id, trade.symbol)
    rejection_reason = trade_rejection_reason(
        trade,
        account.cash_balance,
        holding.shares if holding else 0.0,
        holding_exists=holding is not None,
    )
    return TradePreviewResponse(
        symbol=trade.symbol,
        side=trade.side,
        amount=trade.amount,
        price=trade.price,
        shares=trade.shares,
        simulated_date=trade.simulated_date,
        valid=rejection_reason is None,
        message=describe_trade_eligibility(account, holding, trade, rejection_reason),
    )


def execute_investor_trade(
    db: Session, account: Account, request: TradeRequest
) -> Trade:
    """Recheck current facts, apply the permitted trade, and record its execution."""
    priced_trade = price_requested_trade(db, account, request)
    holding = find_account_holding(db, account.id, priced_trade.symbol)
    rejection_reason = trade_rejection_reason(
        priced_trade,
        account.cash_balance,
        holding.shares if holding else 0.0,
        holding_exists=holding is not None,
    )
    require_trade_is_permitted(
        rejection_reason,
        describe_trade_eligibility(account, holding, priced_trade, rejection_reason),
    )
    apply_trade_to_cash_and_holdings(db, account, holding, priced_trade)
    trade = record_executed_trade(db, account, priced_trade)
    db.flush()
    record_current_portfolio_value(db, account)
    return trade


def price_requested_trade(
    db: Session, account: Account, request: TradeRequest
) -> PricedTrade:
    """Normalize the symbol and use the latest price known at the account date."""
    symbol = require_supported_asset(db, request.symbol).symbol
    price = get_latest_price_on_or_before_date(db, symbol, account.simulated_date).close
    return PricedTrade(
        symbol,
        request.side,
        request.amount,
        price,
        request.amount / price,
        account.simulated_date,
    )


def find_account_holding(db: Session, account_id: int, symbol: str) -> Holding | None:
    return db.scalar(
        select(Holding).where(
            Holding.account_id == account_id, Holding.symbol == symbol
        )
    )


def describe_trade_eligibility(
    account: Account,
    holding: Holding | None,
    trade: PricedTrade,
    rejection_reason: FailureReason | None,
) -> str:
    if rejection_reason == "insufficient_cash":
        return (
            f"Insufficient cash: buy needs ${trade.amount:,.2f} "
            f"but the account has ${account.cash_balance:,.2f}"
        )
    if rejection_reason == "insufficient_shares":
        return (
            f"Insufficient shares: sell needs {trade.shares:.4f} {trade.symbol} "
            f"but the account holds {holding.shares if holding else 0.0:.4f}"
        )
    return f"{trade.side} {trade.shares:.4f} shares of {trade.symbol} at ${trade.price:.2f}"


def require_trade_is_permitted(
    rejection_reason: FailureReason | None, message: str
) -> None:
    if rejection_reason == "insufficient_cash":
        raise InsufficientCashError(message)
    if rejection_reason == "insufficient_shares":
        raise InsufficientSharesError(message)


def apply_trade_to_cash_and_holdings(
    db: Session, account: Account, holding: Holding | None, trade: PricedTrade
) -> None:
    """Apply an already-permitted trade using the holding loaded by the workflow."""
    if trade.side == "BUY":
        account.cash_balance -= trade.amount
        if holding is None:
            db.add(
                Holding(
                    account_id=account.id,
                    symbol=trade.symbol,
                    shares=trade.shares,
                    average_cost=trade.price,
                )
            )
        else:
            holding.average_cost = calculate_average_cost_after_buy(
                holding.shares, holding.average_cost, trade.shares, trade.price
            )
            holding.shares += trade.shares
    else:
        # Eligibility guarantees that a sell has an existing holding.
        assert holding is not None
        account.cash_balance += trade.amount
        holding.shares -= trade.shares
        if holding.shares <= SHARE_EPSILON:
            db.delete(holding)


def record_executed_trade(db: Session, account: Account, trade: PricedTrade) -> Trade:
    recorded = Trade(
        account_id=account.id,
        symbol=trade.symbol,
        side=trade.side,
        shares=trade.shares,
        price=trade.price,
        amount=trade.amount,
        simulated_date=trade.simulated_date,
    )
    db.add(recorded)
    return recorded
