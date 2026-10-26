"""Advance an account's simulated date within available historical market data."""

import calendar
from datetime import date, timedelta

from sqlalchemy.orm import Session

from chronos.storage_sqlite_tables_and_sessions import Account
from chronos.api_schemas_requests_and_responses import PortfolioResponse
from chronos.business_portfolio_valuation import record_current_portfolio_value
from chronos.app_business_errors_and_permissions import InvalidSimulatedDateError
from chronos.market_historical_prices import get_available_market_date_range

STEP_MONTHS = {"1M": 1, "1Q": 3}


def calculate_next_simulated_date(current_date: date, step: str) -> date:
    if step == "1W":
        return current_date + timedelta(days=7)
    if step in STEP_MONTHS:
        return _add_calendar_months(current_date, STEP_MONTHS[step])
    raise InvalidSimulatedDateError(f"Unknown simulation step {step!r}")


def advance_simulated_investment_date(
    db: Session, account: Account, step: str
) -> PortfolioResponse:
    next_date = calculate_next_simulated_date(account.simulated_date, step)
    _, max_market_date = get_available_market_date_range(db)
    if next_date > max_market_date:
        raise InvalidSimulatedDateError(
            f"Cannot advance to {next_date}: market data ends {max_market_date}"
        )
    account.simulated_date = next_date
    db.flush()
    return record_current_portfolio_value(db, account)


def _add_calendar_months(current_date: date, months: int) -> date:
    total_months = current_date.year * 12 + current_date.month - 1 + months
    year, month = divmod(total_months, 12)
    return date(
        year, month + 1, min(current_date.day, calendar.monthrange(year, month + 1)[1])
    )
