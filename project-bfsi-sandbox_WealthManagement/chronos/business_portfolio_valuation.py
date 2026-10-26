"""Value the investor's current holdings using prices known at their account date."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from chronos.api_schemas_requests_and_responses import (
    HoldingValueResponse,
    PortfolioResponse,
    PortfolioScreenResponse,
    TradeResponse,
)
from chronos.storage_sqlite_tables_and_sessions import (
    Account,
    Holding,
    Trade,
    PortfolioValueSnapshot,
)
from chronos.app_demo_data_and_reset import get_demo_user_by_id
from chronos.market_historical_prices import (
    get_latest_prices_on_or_before_date,
    get_supported_assets,
)
from chronos.business_portfolio_history import (
    read_recorded_portfolio_values,
    save_portfolio_value_snapshot,
)


def build_current_portfolio_snapshot(
    db: Session, account: Account
) -> PortfolioResponse:
    """Load holdings, value them at dated prices, and report cash plus investments."""
    holdings = list_account_holdings(db, account.id)
    prices = get_latest_prices_on_or_before_date(
        db, [holding.symbol for holding in holdings], account.simulated_date
    )
    holdings_value = sum(
        holding.shares * prices[holding.symbol].close for holding in holdings
    )
    total_value = account.cash_balance + holdings_value
    valued_holdings = [
        build_holding_value(holding, prices[holding.symbol].close, total_value)
        for holding in holdings
    ]
    return PortfolioResponse(
        user_id=account.user_id,
        simulated_date=account.simulated_date,
        cash_balance=account.cash_balance,
        holdings_value=holdings_value,
        total_value=total_value,
        total_return_amount=total_value - account.initial_cash,
        total_return_percentage=(total_value - account.initial_cash)
        / account.initial_cash
        * 100
        if account.initial_cash
        else 0,
        holdings=valued_holdings,
    )


def list_account_holdings(db: Session, account_id: int) -> list[Holding]:
    return list(
        db.scalars(
            select(Holding)
            .where(Holding.account_id == account_id)
            .order_by(Holding.symbol)
        )
    )


def build_holding_value(
    holding: Holding, current_price: float, portfolio_total_value: float
) -> HoldingValueResponse:
    market_value = holding.shares * current_price
    cost_basis = holding.shares * holding.average_cost
    return HoldingValueResponse(
        symbol=holding.symbol,
        shares=holding.shares,
        average_cost=holding.average_cost,
        current_price=current_price,
        market_value=market_value,
        cost_basis=cost_basis,
        unrealized_gain_loss=market_value - cost_basis,
        allocation_percentage=market_value / portfolio_total_value * 100
        if portfolio_total_value
        else 0,
    )


def build_portfolio_screen(db: Session, account: Account) -> PortfolioScreenResponse:
    """Give both personas the same dated financial facts in one screen response."""
    portfolio = build_current_portfolio_snapshot(db, account)
    return PortfolioScreenResponse(
        **portfolio.model_dump(),
        investor_name=get_demo_user_by_id(db, account.user_id).name,
        assets=get_supported_assets(db),
        history=read_recorded_portfolio_values(db, account),
        trades=[
            TradeResponse.model_validate(trade)
            for trade in db.scalars(
                select(Trade).where(Trade.account_id == account.id).order_by(Trade.id)
            )
        ],
    )


def record_current_portfolio_value(db: Session, account: Account) -> PortfolioResponse:
    """Value current holdings at known prices, then save today's observation."""
    portfolio = build_current_portfolio_snapshot(db, account)
    save_portfolio_value_snapshot(db, account, portfolio.holdings_value)
    return portfolio


def record_missing_portfolio_snapshots(db: Session) -> None:
    """Initialize existing accounts without inventing observations for past dates."""
    accounts = db.scalars(
        select(Account).where(
            ~select(PortfolioValueSnapshot.id)
            .where(PortfolioValueSnapshot.account_id == Account.id)
            .exists()
        )
    )
    for account in accounts:
        record_current_portfolio_value(db, account)
