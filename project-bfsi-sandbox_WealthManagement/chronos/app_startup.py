"""Chronos Wealth FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from chronos import api_routes_portfolio, api_routes_system
from chronos.storage_sqlite_tables_and_sessions import (
    SessionLocal,
    create_database_tables,
)
from chronos.app_demo_data_and_reset import seed_demo_users_accounts_and_assets
from chronos.market_price_import import ensure_market_prices_loaded
from chronos.business_portfolio_valuation import record_missing_portfolio_snapshots


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_database_tables()
    session = SessionLocal()
    try:
        seed_demo_users_accounts_and_assets(session)
        ensure_market_prices_loaded(session)
        record_missing_portfolio_snapshots(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    yield


app = FastAPI(title="Chronos Wealth", lifespan=lifespan)

app.include_router(api_routes_system.router)
app.include_router(api_routes_portfolio.router)
