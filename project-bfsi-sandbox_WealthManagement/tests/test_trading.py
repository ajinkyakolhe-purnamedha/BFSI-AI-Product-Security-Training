"""Buying and selling change cash, shares, and average cost."""

from datetime import date

import pytest
from sqlalchemy import select

from chronos.api_schemas_requests_and_responses import TradeRequest
from chronos.storage_sqlite_tables_and_sessions import Holding
from chronos.app_business_errors_and_permissions import (
    InsufficientCashError,
    InsufficientSharesError,
)
from chronos.business_investor_trading import (
    execute_investor_trade,
    preview_investor_trade,
)


def requested_trade(account, amount, side="BUY", symbol="AAPL"):
    return TradeRequest(
        user_id=account.user_id, symbol=symbol, side=side, amount=amount
    )


def trade(db, account, amount, side="BUY"):
    return execute_investor_trade(db, account, requested_trade(account, amount, side))


def holding_for(db, account):
    return db.scalar(
        select(Holding).where(
            Holding.account_id == account.id, Holding.symbol == "AAPL"
        )
    )


def test_buy_reduces_cash_and_creates_holding(db, alice_account):
    bought = trade(db, alice_account, 1080)  # Ten shares at $108.
    holding = holding_for(db, alice_account)
    assert alice_account.cash_balance == pytest.approx(98_920)
    assert bought.price == 108
    assert bought.shares == holding.shares == pytest.approx(10)
    assert holding.average_cost == pytest.approx(108)


def test_trade_preview_uses_the_account_simulated_date(db, alice_account):
    preview = preview_investor_trade(
        db, alice_account, requested_trade(alice_account, 1080, symbol="aapl")
    )
    assert preview.valid is True
    assert preview.symbol == "AAPL"
    assert preview.price == 108
    assert preview.shares == pytest.approx(10)


def test_sell_reduces_shares_and_increases_cash(db, alice_account):
    trade(db, alice_account, 1080)
    trade(db, alice_account, 540, "SELL")  # Sell five of the ten shares.
    assert alice_account.cash_balance == pytest.approx(99_460)
    assert holding_for(db, alice_account).shares == pytest.approx(5)


def test_selling_everything_removes_holding(db, alice_account):
    trade(db, alice_account, 1080)
    trade(db, alice_account, 1080, "SELL")
    assert holding_for(db, alice_account) is None
    assert alice_account.cash_balance == pytest.approx(100_000)


def test_buy_with_insufficient_cash_fails(db, alice_account):
    with pytest.raises(InsufficientCashError):
        trade(db, alice_account, 200_000)
    assert alice_account.cash_balance == pytest.approx(100_000)


def test_sell_with_insufficient_shares_fails(db, alice_account):
    with pytest.raises(InsufficientSharesError):
        trade(db, alice_account, 1000, "SELL")


def test_preview_writes_no_rows_and_flags_invalid_trades(db, alice_account):
    preview = preview_investor_trade(
        db, alice_account, requested_trade(alice_account, 200_000)
    )
    assert preview.valid is False
    assert "Insufficient cash" in preview.message
    assert db.scalar(select(Holding)) is None
    assert alice_account.cash_balance == pytest.approx(100_000)


def test_buy_averages_cost_across_dates(db, alice_account):
    trade(db, alice_account, 1080)  # Ten shares at $108.
    alice_account.simulated_date = date(2020, 6, 8)
    trade(db, alice_account, 1100)  # Ten more at $110.
    holding = holding_for(db, alice_account)
    assert holding.shares == pytest.approx(20)
    assert holding.average_cost == pytest.approx(109)


def test_sell_everything_then_rebuy_uses_fresh_average_cost(db, alice_account):
    trade(db, alice_account, 1080)
    trade(db, alice_account, 1080, "SELL")
    alice_account.simulated_date = date(2020, 6, 8)
    trade(db, alice_account, 1100)
    assert holding_for(db, alice_account).average_cost == pytest.approx(110)


def test_preview_and_execution_reject_tiny_sell_without_holding(db, alice_account):
    request = requested_trade(alice_account, 1e-10, "SELL")
    assert preview_investor_trade(db, alice_account, request).valid is False
    with pytest.raises(InsufficientSharesError):
        execute_investor_trade(db, alice_account, request)


def test_weekend_trade_uses_previous_price(db, alice_account):
    alice_account.simulated_date = date(2020, 6, 7)
    preview = preview_investor_trade(
        db, alice_account, requested_trade(alice_account, 1080)
    )
    assert preview.price == 108
    assert preview.shares == pytest.approx(10)
