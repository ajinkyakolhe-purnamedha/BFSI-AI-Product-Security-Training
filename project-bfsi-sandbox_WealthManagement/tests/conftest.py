"""Shared test setup: isolated SQLite database, seeded demo data, fixture prices.

Tests never call yfinance or the network. Market prices come from
tests/fixtures/prices_sample.csv (AAPL rising, MSFT falling, weekly closes
2020-05-04 through 2020-09-14).
"""

# Database configuration must precede imports that construct the application engine.
# ruff: noqa: E402

import os
import tempfile
from pathlib import Path

_TEST_DATABASE_DIR = tempfile.mkdtemp(prefix="chronos_test_")
os.environ["CHRONOS_DATABASE_URL"] = f"sqlite:///{_TEST_DATABASE_DIR}/test_chronos.db"

import pytest
from fastapi.testclient import TestClient

from chronos.storage_sqlite_tables_and_sessions import (
    Account,
    Base,
    SessionLocal,
    User,
    engine,
    get_database_session,
)
from chronos.app_demo_data_and_reset import seed_demo_users_accounts_and_assets
from chronos.market_price_import import (
    load_market_prices_from_csv,
    load_market_prices_into_database,
)

FIXTURE_PRICES_CSV = Path(__file__).parent / "fixtures" / "prices_sample.csv"

ALICE_EMAIL = "alice@example.com"
ADVISOR_EMAIL = "advisor@example.com"


@pytest.fixture()
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_demo_users_accounts_and_assets(session)
    prices = load_market_prices_from_csv(FIXTURE_PRICES_CSV)
    load_market_prices_into_database(session, prices)
    session.commit()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(db):
    from chronos.app_startup import app

    def _shared_test_session():
        try:
            yield db
            db.flush()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_database_session] = _shared_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def alice(db) -> User:
    return db.query(User).filter(User.email == ALICE_EMAIL).one()


@pytest.fixture()
def advisor(db) -> User:
    return db.query(User).filter(User.email == ADVISOR_EMAIL).one()


@pytest.fixture()
def alice_account(db, alice) -> Account:
    return db.query(Account).filter(Account.user_id == alice.id).one()


@pytest.fixture()
def bob(db, alice_account) -> User:
    """A second investor, created only for tests of account privacy."""
    investor = User(email="bob@example.com", name="Bob Investor", role="INVESTOR")
    db.add(investor)
    db.flush()
    db.add(
        Account(
            user_id=investor.id,
            name="Bob Account",
            cash_balance=100000,
            initial_cash=100000,
            simulated_date=alice_account.simulated_date,
        )
    )
    db.flush()
    return investor
