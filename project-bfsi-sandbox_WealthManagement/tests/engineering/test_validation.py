"""Validation: observable business outcomes and their protections."""

from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from chronos.api_schemas_requests_and_responses import TradeRequest
from chronos.storage_sqlite_tables_and_sessions import Price
from chronos.app_business_errors_and_permissions import PriceUnavailableError
from chronos.business_investor_trading import execute_investor_trade
from chronos.market_price_import import (
    load_market_prices_from_csv,
    load_market_prices_into_database,
)
from chronos.market_historical_prices import (
    get_latest_price_on_or_before_date,
    get_latest_prices_on_or_before_date,
    get_symbol_price_histories,
)
from chronos.business_portfolio_valuation import record_current_portfolio_value
from chronos.business_portfolio_history import read_recorded_portfolio_values
from tests.conftest import FIXTURE_PRICES_CSV


@pytest.mark.parametrize("amount", [float("inf"), float("-inf"), float("nan"), 0, -1])
def test_trade_amount_must_be_finite_and_positive(amount):
    with pytest.raises(ValidationError):
        TradeRequest(user_id=1, symbol="AAPL", side="BUY", amount=amount)


@pytest.mark.parametrize("close", [0, -1, float("inf"), float("nan")])
def test_invalid_import_close_is_rejected_before_writes(db, close):
    prices = load_market_prices_from_csv(FIXTURE_PRICES_CSV)
    first = db.scalar(select(Price).order_by(Price.id))
    original_close = first.close
    prices["close"] = prices["close"].astype(float)
    prices.loc[0, "close"] = close
    with pytest.raises(ValueError):
        load_market_prices_into_database(db, prices)
    assert first.close == original_close
    assert db.scalar(select(func.count(Price.id))) == 40
    assert not db.new and not db.dirty


def test_duplicate_incoming_prices_are_rejected_before_writes(db):
    prices = load_market_prices_from_csv(FIXTURE_PRICES_CSV)
    duplicated = pd.concat([prices.iloc[:1], prices.iloc[:1]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        load_market_prices_into_database(db, duplicated)
    assert db.scalar(select(func.count(Price.id))) == 40
    assert not db.new and not db.dirty


@pytest.mark.parametrize("close", [0, -1, float("inf")])
def test_stored_invalid_price_is_rejected_by_single_and_batch_queries(db, close):
    price = db.scalar(
        select(Price).where(Price.symbol == "AAPL", Price.date == date(2020, 6, 1))
    )
    price.close = close
    db.flush()
    with pytest.raises(PriceUnavailableError):
        get_latest_price_on_or_before_date(db, "AAPL", date(2020, 6, 1))
    with pytest.raises(PriceUnavailableError):
        get_latest_prices_on_or_before_date(db, ["AAPL"], date(2020, 6, 1))


def test_snapshot_creation_rejects_invalid_price_for_owned_shares(db, alice_account):
    execute_investor_trade(
        db,
        alice_account,
        TradeRequest(
            user_id=alice_account.user_id, symbol="AAPL", side="BUY", amount=1080
        ),
    )
    price = db.scalar(
        select(Price).where(Price.symbol == "AAPL", Price.date == date(2020, 6, 1))
    )
    price.close = 0
    db.flush()
    with pytest.raises(PriceUnavailableError):
        record_current_portfolio_value(db, alice_account)


@pytest.mark.parametrize("days", [0, -1, 1001])
def test_invalid_history_bound_is_rejected_by_api_and_python(client, db, alice, days):
    response = client.get(
        "/market/history",
        params={"user_id": alice.id, "symbols": ["AAPL"], "trading_days": days},
    )
    assert response.status_code == 422
    with pytest.raises(ValueError):
        get_symbol_price_histories(db, ["AAPL"], date(2020, 6, 1), days)["AAPL"]


def test_market_history_target_must_be_an_investor(client, advisor):
    assert (
        client.get(
            "/market/history",
            params={
                "user_id": advisor.id,
                "investor_id": advisor.id,
                "symbols": ["AAPL"],
            },
        ).status_code
        == 403
    )


@pytest.mark.parametrize("keep_pre_purchase_prices", [False, True])
def test_recorded_values_remain_readable_when_market_prices_are_missing(
    db, alice_account, keep_pre_purchase_prices
):
    execute_investor_trade(
        db,
        alice_account,
        TradeRequest(
            user_id=alice_account.user_id, symbol="AAPL", side="BUY", amount=1080
        ),
    )
    recorded_values = read_recorded_portfolio_values(db, alice_account)
    if keep_pre_purchase_prices:
        db.query(Price).filter(Price.date >= alice_account.simulated_date).delete()
        db.query(Price).filter(Price.symbol == "AAPL").delete()
    else:
        db.query(Price).delete()
    db.flush()
    assert read_recorded_portfolio_values(db, alice_account) == recorded_values
    with pytest.raises(PriceUnavailableError, match="No price for AAPL"):
        record_current_portfolio_value(db, alice_account)


@pytest.mark.parametrize("date_kind", ["string", "timestamp"])
def test_direct_import_persists_validated_dates_without_changing_input(db, date_kind):
    prices = load_market_prices_from_csv(FIXTURE_PRICES_CSV).iloc[:1].copy()
    prices["date"] = pd.to_datetime(prices["date"]) + pd.Timedelta(days=1)
    if date_kind == "string":
        prices["date"] = prices["date"].dt.strftime("%Y-%m-%d")
    original = prices.copy(deep=True)
    assert load_market_prices_into_database(db, prices) == 1
    imported = db.scalar(
        select(Price).where(Price.symbol == "AAPL", Price.date == date(2020, 5, 5))
    )
    assert imported is not None and imported.close == prices.iloc[0]["close"]
    pd.testing.assert_frame_equal(prices, original)


def test_imported_symbols_are_readable_by_normal_price_queries(db):
    prices = pd.DataFrame(
        [{"symbol": " aapl ", "date": "2020-06-02", "close": 109, "source": "TEST"}]
    )
    original = prices.copy(deep=True)
    load_market_prices_into_database(db, prices)
    price = get_latest_price_on_or_before_date(db, "AAPL", date(2020, 6, 2))
    assert price.date == date(2020, 6, 2)
    assert price.close == 109
    pd.testing.assert_frame_equal(prices, original)


def test_import_rejects_duplicate_symbols_after_normalization_before_writes(db):
    prices = pd.DataFrame(
        [
            {"symbol": symbol, "date": "2020-06-02", "close": 109, "source": "TEST"}
            for symbol in ["AAPL", " aapl "]
        ]
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_market_prices_into_database(db, prices)
    assert db.scalar(select(func.count(Price.id))) == 40
    assert not db.new and not db.dirty
