"""Save and read recorded portfolio values; no historical trade replay."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from chronos.api_schemas_requests_and_responses import AccountValueHistoryPointResponse
from chronos.storage_sqlite_tables_and_sessions import Account, PortfolioValueSnapshot


def save_portfolio_value_snapshot(
    db: Session, account: Account, holdings_value: float
) -> None:
    """Save the date's latest value in the same transaction as the account change."""
    snapshot = db.scalar(
        select(PortfolioValueSnapshot).where(
            PortfolioValueSnapshot.account_id == account.id,
            PortfolioValueSnapshot.simulated_date == account.simulated_date,
        )
    )
    if snapshot is None:
        snapshot = PortfolioValueSnapshot(
            account_id=account.id, simulated_date=account.simulated_date
        )
        db.add(snapshot)
    snapshot.cash_balance = account.cash_balance
    snapshot.holdings_value = holdings_value
    snapshot.total_value = account.cash_balance + holdings_value
    db.flush()


def read_recorded_portfolio_values(
    db: Session, account: Account
) -> list[AccountValueHistoryPointResponse]:
    """Read observations as saved, without consulting trades or market prices."""
    snapshots = db.scalars(
        select(PortfolioValueSnapshot)
        .where(
            PortfolioValueSnapshot.account_id == account.id,
            PortfolioValueSnapshot.simulated_date <= account.simulated_date,
        )
        .order_by(PortfolioValueSnapshot.simulated_date)
    )
    return [
        AccountValueHistoryPointResponse(
            date=snapshot.simulated_date,
            cash_balance=snapshot.cash_balance,
            holdings_value=snapshot.holdings_value,
            total_value=snapshot.total_value,
        )
        for snapshot in snapshots
    ]
