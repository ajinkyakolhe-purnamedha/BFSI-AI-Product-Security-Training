"""Query counts: observable business outcomes and their protections."""

from datetime import date

import pytest
from sqlalchemy import event

from chronos.api_schemas_requests_and_responses import TradeRequest
from chronos.business_investor_trading import execute_investor_trade
from chronos.business_portfolio_history import read_recorded_portfolio_values
from chronos.business_portfolio_valuation import (
    build_current_portfolio_snapshot,
    record_current_portfolio_value,
)


def measure_selects(db, operation):
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        result = operation()
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    return result, len(statements)


@pytest.mark.parametrize("symbols", [("AAPL",), ("AAPL", "MSFT")])
@pytest.mark.parametrize("end_date", [date(2020, 6, 8), date(2020, 9, 14)])
def test_portfolio_queries_are_bounded(db, alice_account, symbols, end_date):
    for symbol in symbols:
        execute_investor_trade(
            db,
            alice_account,
            TradeRequest(
                user_id=alice_account.user_id, symbol=symbol, side="BUY", amount=1080
            ),
        )
    alice_account.simulated_date = end_date
    db.flush()
    record_current_portfolio_value(db, alice_account)
    portfolio, count = measure_selects(
        db, lambda: build_current_portfolio_snapshot(db, alice_account)
    )
    assert count <= 2
    history, count = measure_selects(
        db, lambda: read_recorded_portfolio_values(db, alice_account)
    )
    assert count == 1
    assert history[-1].total_value == pytest.approx(portfolio.total_value)


def test_batch_history_reads_all_symbols_in_one_query(db):
    from chronos.market_historical_prices import get_symbol_price_histories

    result, count = measure_selects(
        db,
        lambda: get_symbol_price_histories(
            db, ["AAPL", "MSFT", "SPY"], date(2020, 6, 1), 2
        ),
    )
    assert count == 1
    assert result["SPY"] == []
    assert [point.date for point in result["AAPL"]] == [
        date(2020, 5, 25),
        date(2020, 6, 1),
    ]
    assert len(result["MSFT"]) == 2


def test_batch_route_query_count_does_not_grow_with_symbols(client, db, alice):
    counts = []
    for symbols in [["AAPL"], ["AAPL", "MSFT", "GLD", "JPM", "SPY"]]:
        response, count = measure_selects(
            db,
            lambda: client.get(
                "/market/history", params={"user_id": alice.id, "symbols": symbols}
            ),
        )
        assert response.status_code == 200
        counts.append(count)
    assert counts[0] == counts[1]
