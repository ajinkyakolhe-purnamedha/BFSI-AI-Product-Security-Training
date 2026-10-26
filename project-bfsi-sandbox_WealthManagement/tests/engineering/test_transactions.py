"""Transactions: observable business outcomes and their protections."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chronos import (
    storage_sqlite_tables_and_sessions as application_database,
    business_investor_trading as investor_trades,
)
from chronos.api_schemas_requests_and_responses import TradeRequest
from chronos.storage_sqlite_tables_and_sessions import (
    Account,
    Base,
    Holding,
    Trade,
    PortfolioValueSnapshot,
)
from chronos.app_demo_data_and_reset import seed_demo_users_accounts_and_assets
from chronos.business_investor_trading import (
    execute_investor_trade,
    preview_investor_trade,
)
from chronos.app_startup import app
from chronos.market_price_import import (
    load_market_prices_from_csv,
    load_market_prices_into_database,
)
from tests.conftest import FIXTURE_PRICES_CSV


@pytest.fixture
def request_database(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'transactions.db'}",
        connect_args={"check_same_thread": False},
    )
    factory = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(engine)
    with factory() as db:
        seed_demo_users_accounts_and_assets(db)
        load_market_prices_into_database(
            db, load_market_prices_from_csv(FIXTURE_PRICES_CSV)
        )
        investor_id = db.scalar(select(Account.user_id))
        db.commit()
    monkeypatch.setattr(application_database, "SessionLocal", factory)
    assert application_database.get_database_session not in app.dependency_overrides
    # No lifespan here: setup has already populated this isolated database.
    try:
        yield factory, investor_id, TestClient(app, raise_server_exceptions=False)
    finally:
        engine.dispose()


def test_successful_trade_commits_cash_holding_and_trade(request_database):
    factory, investor_id, client = request_database
    response = client.post(
        "/trades",
        json={"user_id": investor_id, "symbol": "AAPL", "side": "BUY", "amount": 1080},
    )
    assert response.status_code == 200
    with factory() as db:
        assert db.scalar(select(Account.cash_balance)) == pytest.approx(98920)
        assert db.scalar(select(Holding.shares)) == pytest.approx(10)
        assert db.scalar(select(func.count(Trade.id))) == 1
        snapshot = db.scalar(select(PortfolioValueSnapshot))
        assert snapshot.cash_balance == 98920
        assert snapshot.holdings_value == 1080
        assert snapshot.total_value == 100000


def test_recording_failure_rolls_back_cash_holding_and_trade(
    request_database, monkeypatch
):
    factory, investor_id, client = request_database

    def fail_recording(*args, **kwargs):
        raise RuntimeError("injected recording failure")

    monkeypatch.setattr(investor_trades, "record_executed_trade", fail_recording)
    response = client.post(
        "/trades",
        json={"user_id": investor_id, "symbol": "AAPL", "side": "BUY", "amount": 1080},
    )
    assert response.status_code == 500
    with factory() as db:
        assert db.scalar(select(Account.cash_balance)) == 100000
        assert db.scalar(select(func.count(Holding.id))) == 0
        assert db.scalar(select(func.count(Trade.id))) == 0
        assert db.scalar(select(PortfolioValueSnapshot.cash_balance)) == 100000
        assert db.scalar(select(func.count(PortfolioValueSnapshot.id))) == 1


def test_preview_persists_no_financial_changes(request_database):
    factory, investor_id, client = request_database
    assert (
        client.post(
            "/trades/preview",
            json={
                "user_id": investor_id,
                "symbol": "AAPL",
                "side": "BUY",
                "amount": 1080,
            },
        ).status_code
        == 200
    )
    with factory() as db:
        assert db.scalar(select(Account.cash_balance)) == 100000
        assert db.scalar(select(func.count(Holding.id))) == 0
        assert db.scalar(select(func.count(Trade.id))) == 0
        assert db.scalar(select(PortfolioValueSnapshot.cash_balance)) == 100000
        assert db.scalar(select(func.count(PortfolioValueSnapshot.id))) == 1


def test_failed_time_advance_keeps_persisted_date(request_database):
    factory, investor_id, client = request_database
    with factory() as db:
        account = db.scalar(select(Account))
        account.simulated_date = date(2020, 9, 1)
        db.commit()
    assert (
        client.post(
            "/simulation/advance", json={"user_id": investor_id, "step": "1Q"}
        ).status_code
        == 400
    )
    with factory() as db:
        assert db.scalar(select(Account.simulated_date)) == date(2020, 9, 1)


def test_failed_valuation_after_time_advance_rolls_back_date(request_database):
    from chronos.storage_sqlite_tables_and_sessions import Price

    factory, investor_id, client = request_database
    assert (
        client.post(
            "/trades",
            json={
                "user_id": investor_id,
                "symbol": "AAPL",
                "side": "BUY",
                "amount": 1080,
            },
        ).status_code
        == 200
    )
    with factory() as db:
        price = db.scalar(
            select(Price).where(Price.symbol == "AAPL", Price.date == date(2020, 6, 8))
        )
        price.close = 0
        db.commit()
    assert (
        client.post(
            "/simulation/advance", json={"user_id": investor_id, "step": "1W"}
        ).status_code
        == 400
    )
    with factory() as db:
        assert db.scalar(select(Account.simulated_date)) == date(2020, 6, 1)
        assert db.scalar(select(Account.cash_balance)) == 98920
        assert db.scalar(select(Holding.shares)) == 10
        assert db.scalar(select(func.count(PortfolioValueSnapshot.id))) == 1
        assert db.scalar(select(PortfolioValueSnapshot.simulated_date)) == date(
            2020, 6, 1
        )


def request(account, side="BUY", amount=1080):
    return TradeRequest(
        user_id=account.user_id, symbol="AAPL", side=side, amount=amount
    )


@pytest.mark.parametrize("amount", [540, 200000])
def test_preview_leaves_existing_financial_records_unchanged(db, alice_account, amount):
    execute_investor_trade(db, alice_account, request(alice_account))
    holding = db.scalar(select(Holding))
    before = (
        alice_account.cash_balance,
        holding.shares,
        db.scalar(select(func.count(Trade.id))),
    )
    preview_investor_trade(db, alice_account, request(alice_account, amount=amount))
    assert (
        alice_account.cash_balance,
        holding.shares,
        db.scalar(select(func.count(Trade.id))),
    ) == before
    assert not db.new and not db.dirty and not db.deleted


def test_snapshot_failure_rolls_back_the_trade_and_saved_value(
    request_database, monkeypatch
):
    factory, investor_id, client = request_database
    record_value = investor_trades.record_current_portfolio_value

    def record_then_fail(db, account):
        record_value(db, account)
        raise RuntimeError("injected failure after saving the snapshot")

    monkeypatch.setattr(
        investor_trades, "record_current_portfolio_value", record_then_fail
    )
    response = client.post(
        "/trades",
        json={
            "user_id": investor_id,
            "symbol": "AAPL",
            "side": "BUY",
            "amount": 1080,
        },
    )
    assert response.status_code == 500
    with factory() as db:
        assert db.scalar(select(Account.cash_balance)) == 100000
        assert db.scalar(select(func.count(Holding.id))) == 0
        assert db.scalar(select(func.count(Trade.id))) == 0
        snapshot = db.scalar(select(PortfolioValueSnapshot))
        assert snapshot.cash_balance == snapshot.total_value == 100000
        assert snapshot.holdings_value == 0


def test_startup_adds_current_snapshot_to_existing_database(
    request_database, monkeypatch
):
    from chronos import app_startup

    factory, investor_id, _ = request_database
    with factory() as db:
        execute_investor_trade(
            db,
            db.scalar(select(Account)),
            TradeRequest(
                user_id=investor_id,
                symbol="AAPL",
                side="BUY",
                amount=1080,
            ),
        )
        db.scalar(select(Account)).simulated_date = date(2020, 6, 8)
        db.commit()
    # Emulate the existing application database before the new table was added.
    engine = factory.kw["bind"]
    PortfolioValueSnapshot.__table__.drop(engine)
    monkeypatch.setattr(app_startup, "SessionLocal", factory)
    monkeypatch.setattr(
        app_startup, "create_database_tables", lambda: Base.metadata.create_all(engine)
    )
    with TestClient(app) as client:
        view = client.get("/portfolio", params={"user_id": investor_id}).json()
        assert view["history"] == [
            {
                "date": "2020-06-08",
                "cash_balance": 98920,
                "holdings_value": 1100,
                "total_value": 100020,
            }
        ]
    # A second startup preserves the observation instead of rewriting it.
    with TestClient(app):
        pass
    with factory() as db:
        assert db.scalar(select(func.count(PortfolioValueSnapshot.id))) == 1
        assert db.scalar(select(func.count(Trade.id))) == 1
        assert db.scalar(select(Holding.shares)) == 10
