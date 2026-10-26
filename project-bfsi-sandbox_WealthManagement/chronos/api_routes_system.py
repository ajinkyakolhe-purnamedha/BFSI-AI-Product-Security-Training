"""System, authentication, demo reset, and simulated-time routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from chronos.api_schemas_requests_and_responses import (
    AdvanceSimulationRequest,
    DemoResetResponse,
    LoginRequest,
    SimulationAdvanceResponse,
    UserResponse,
)
from chronos.storage_sqlite_tables_and_sessions import get_database_session
from chronos.api_error_translation import translate_domain_errors
from chronos.app_demo_data_and_reset import (
    list_demo_users,
    login_demo_user_by_email,
    reset_demo_investor_accounts,
    seed_demo_users_accounts_and_assets,
)
from chronos.business_investor_accounts import get_account_for_investor_user
from chronos.business_portfolio_valuation import build_current_portfolio_snapshot
from chronos.business_simulated_time import advance_simulated_investment_date

router = APIRouter()


@router.get("/health")
def read_health() -> dict:
    return {"status": "ok"}


@router.get("/auth/demo-users", response_model=list[UserResponse])
def read_demo_users(db: Session = Depends(get_database_session)):
    return list_demo_users(db)


@router.post("/auth/login", response_model=UserResponse)
def login_demo_user(request: LoginRequest, db: Session = Depends(get_database_session)):
    with translate_domain_errors():
        return login_demo_user_by_email(db, request.email)


@router.post("/demo/reset", response_model=DemoResetResponse)
def reset_demo_data(db: Session = Depends(get_database_session)):
    seed_demo_users_accounts_and_assets(db)
    return DemoResetResponse(accounts_reset=reset_demo_investor_accounts(db))


@router.post("/simulation/advance", response_model=SimulationAdvanceResponse)
def advance_simulation(
    request: AdvanceSimulationRequest, db: Session = Depends(get_database_session)
):
    with translate_domain_errors():
        account = get_account_for_investor_user(db, request.user_id)
        previous_portfolio = build_current_portfolio_snapshot(db, account)
        portfolio = advance_simulated_investment_date(db, account, request.step)
    return SimulationAdvanceResponse(
        previous_date=previous_portfolio.simulated_date,
        current_date=portfolio.simulated_date,
        previous_value=previous_portfolio.total_value,
        current_value=portfolio.total_value,
    )
