"""Portfolio: observable business outcomes and their protections."""

from datetime import date

import pytest

from chronos.api_schemas_requests_and_responses import TradeRequest
from chronos.business_investor_trading import execute_investor_trade
from chronos.business_portfolio_history import read_recorded_portfolio_values
from chronos.business_portfolio_valuation import (
    build_current_portfolio_snapshot,
    record_current_portfolio_value,
)


def trade(db, account, amount, side="BUY"):
    request = TradeRequest(
        user_id=account.user_id, symbol="AAPL", side=side, amount=amount
    )
    return execute_investor_trade(db, account, request)


def test_portfolio_valuation_uses_simulated_date_prices(db, alice_account):
    trade(db, alice_account, 10_800.0)
    alice_account.simulated_date = date(2020, 6, 8)  # AAPL close moves 108 -> 110

    portfolio = build_current_portfolio_snapshot(db, alice_account)
    holding = portfolio.holdings[0]
    assert holding.current_price == 110.0
    assert holding.market_value == pytest.approx(11_000.0)
    assert holding.cost_basis == pytest.approx(10_800.0)
    assert holding.unrealized_gain_loss == pytest.approx(200.0)
    assert portfolio.total_value == pytest.approx(89_200.0 + 11_000.0)
    assert portfolio.total_return_amount == pytest.approx(200.0)
    assert portfolio.total_return_percentage == pytest.approx(0.2)


def test_allocation_percentages_sum_with_cash(db, alice_account):
    trade(db, alice_account, 50_000.0)
    portfolio = build_current_portfolio_snapshot(db, alice_account)
    assert portfolio.holdings[0].allocation_percentage == pytest.approx(50.0)


def test_account_history_does_not_backfill_current_holdings(db, alice_account):
    alice_account.simulated_date = date(2020, 6, 8)
    trade(db, alice_account, 11_000.0)
    from chronos.business_simulated_time import advance_simulated_investment_date

    advance_simulated_investment_date(db, alice_account, "1W")

    history = read_recorded_portfolio_values(db, alice_account)
    points_by_date = {point.date: point for point in history}

    before_trade = points_by_date[date(2020, 6, 1)]
    assert before_trade.holdings_value == 0.0
    assert before_trade.total_value == pytest.approx(100_000.0)

    on_trade_date = points_by_date[date(2020, 6, 8)]
    assert on_trade_date.holdings_value == pytest.approx(11_000.0)
    assert on_trade_date.cash_balance == pytest.approx(89_000.0)

    after_trade = points_by_date[date(2020, 6, 15)]
    assert after_trade.holdings_value == pytest.approx(11_200.0)  # AAPL 112


def test_history_stops_at_simulated_date(db, alice_account):
    history = read_recorded_portfolio_values(db, alice_account)
    assert history
    assert max(point.date for point in history) <= alice_account.simulated_date


def test_snapshot_creation_does_not_hide_unpriced_holdings(db, alice_account):
    from chronos.storage_sqlite_tables_and_sessions import Price
    from chronos.app_business_errors_and_permissions import PriceUnavailableError

    trade(db, alice_account, 1080)
    db.query(Price).filter(Price.symbol == "AAPL").delete(synchronize_session=False)
    db.flush()
    with pytest.raises(PriceUnavailableError):
        record_current_portfolio_value(db, alice_account)


def test_zero_value_portfolio_has_zero_return_percentage(db, alice_account):
    alice_account.initial_cash = 0
    alice_account.cash_balance = 0
    portfolio = build_current_portfolio_snapshot(db, alice_account)
    assert portfolio.total_value == 0
    assert portfolio.total_return_percentage == 0


def test_same_day_trades_update_one_recorded_value(db, alice_account):
    for side, amount in [("BUY", 1080), ("SELL", 1080), ("BUY", 540)]:
        trade(db, alice_account, amount, side)
    history = read_recorded_portfolio_values(db, alice_account)
    assert len(history) == 1
    point = history[0]
    assert point.cash_balance == pytest.approx(99460)
    assert point.holdings_value == pytest.approx(540)
    assert point.total_value == pytest.approx(100000)


def test_history_records_only_dates_the_investor_visits(db, alice_account):
    from chronos.business_simulated_time import advance_simulated_investment_date

    trade(db, alice_account, 1080)
    advance_simulated_investment_date(db, alice_account, "1M")
    history = read_recorded_portfolio_values(db, alice_account)
    assert [point.date for point in history] == [date(2020, 6, 1), date(2020, 7, 1)]
    assert history[-1].cash_balance == pytest.approx(98_920)
    assert history[-1].holdings_value == pytest.approx(1160)
    assert history[-1].total_value == pytest.approx(100_080)


def test_recorded_values_survive_price_corrections(db, alice_account):
    from chronos.storage_sqlite_tables_and_sessions import Price

    trade(db, alice_account, 1080)
    before = read_recorded_portfolio_values(db, alice_account)
    db.query(Price).filter(Price.symbol == "AAPL").update({Price.close: 999})
    db.flush()
    assert read_recorded_portfolio_values(db, alice_account) == before


def test_demo_reset_restores_one_initial_snapshot(db, alice_account):
    from chronos.app_demo_data_and_reset import reset_demo_investor_accounts
    from chronos.business_simulated_time import advance_simulated_investment_date

    trade(db, alice_account, 1080)
    advance_simulated_investment_date(db, alice_account, "1M")
    reset_demo_investor_accounts(db)
    history = read_recorded_portfolio_values(db, alice_account)
    assert len(history) == 1
    assert history[0].date == date(2020, 6, 1)
    assert history[0].cash_balance == history[0].total_value == 100_000
    assert history[0].holdings_value == 0
