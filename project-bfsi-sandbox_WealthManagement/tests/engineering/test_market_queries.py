"""Market queries: observable business outcomes and their protections."""

from datetime import date

import pytest

from chronos.app_business_errors_and_permissions import PriceUnavailableError
from chronos.market_historical_prices import (
    get_latest_price_on_or_before_date,
    get_symbol_price_histories,
)


def test_price_lookup_uses_latest_on_or_before_date(db):
    price = get_latest_price_on_or_before_date(db, "AAPL", date(2020, 6, 3))
    assert price.date == date(2020, 6, 1)
    assert price.close == 108.0


def test_price_lookup_on_exact_date(db):
    price = get_latest_price_on_or_before_date(db, "AAPL", date(2020, 6, 1))
    assert price.date == date(2020, 6, 1)


def test_price_lookup_before_first_price_fails(db):
    with pytest.raises(PriceUnavailableError):
        get_latest_price_on_or_before_date(db, "AAPL", date(2020, 1, 1))


def test_symbol_history_returns_no_future_prices(db):
    end_date = date(2020, 6, 1)
    history = get_symbol_price_histories(db, ["AAPL"], end_date)["AAPL"]
    assert history
    assert all(price.date <= end_date for price in history)
    assert [price.date for price in history] == sorted(price.date for price in history)


def test_symbol_history_respects_trading_days_limit(db):
    history = get_symbol_price_histories(
        db, ["AAPL"], date(2020, 9, 14), trading_days=5
    )["AAPL"]
    assert len(history) == 5
    assert history[-1].date == date(2020, 9, 14)


def test_trading_days_beyond_available_returns_everything(db):
    history = get_symbol_price_histories(
        db, ["AAPL"], date(2020, 9, 14), trading_days=500
    )["AAPL"]
    assert len(history) == 20


def test_lowercase_symbol_is_accepted(db):
    from chronos.market_historical_prices import require_supported_asset

    assert require_supported_asset(db, "aapl").symbol == "AAPL"


def test_unknown_symbol_is_rejected(db):
    from chronos.app_business_errors_and_permissions import RecordNotFoundError
    from chronos.market_historical_prices import require_supported_asset

    with pytest.raises(RecordNotFoundError):
        require_supported_asset(db, "ZZZZ")


def test_batch_prices_match_each_symbols_latest_known_date(db):
    from chronos.market_historical_prices import get_latest_prices_on_or_before_date

    prices = get_latest_prices_on_or_before_date(db, ["AAPL", "MSFT"], date(2020, 6, 7))
    assert prices["AAPL"].close == 108
    assert prices["MSFT"].close == 196
    assert all(price.date == date(2020, 6, 1) for price in prices.values())
    assert get_latest_prices_on_or_before_date(db, [], date(2020, 6, 7)) == {}
    with pytest.raises(PriceUnavailableError):
        get_latest_prices_on_or_before_date(db, ["AAPL", "SPY"], date(2020, 6, 7))
