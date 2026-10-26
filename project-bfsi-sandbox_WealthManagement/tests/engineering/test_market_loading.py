"""Market loading: observable business outcomes and their protections."""

from datetime import date

import pandas as pd
import pytest
from sqlalchemy import func, select

import chronos.market_price_import as price_loading
from chronos.storage_sqlite_tables_and_sessions import Price
from chronos.app_business_errors_and_permissions import MarketDataSetupError
from chronos.market_price_import import (
    ensure_market_prices_loaded,
    load_market_prices_from_csv,
    load_market_prices_into_database,
)
from tests.conftest import FIXTURE_PRICES_CSV


def test_fixture_csv_loads_into_sqlite(db):
    row_count = db.scalar(select(func.count(Price.id)))
    assert row_count == 40
    symbols = set(db.scalars(select(Price.symbol).distinct()))
    assert symbols == {"AAPL", "MSFT"}


def test_duplicate_load_does_not_duplicate_symbol_date(db):
    prices = load_market_prices_from_csv(FIXTURE_PRICES_CSV)
    load_market_prices_into_database(db, prices)
    db.commit()

    total_rows = db.scalar(select(func.count(Price.id)))
    distinct_pairs = db.scalar(
        select(func.count()).select_from(
            select(Price.symbol, Price.date).distinct().subquery()
        )
    )
    assert total_rows == 40
    assert distinct_pairs == 40


def test_reload_updates_changed_close_instead_of_duplicating(db):
    prices = load_market_prices_from_csv(FIXTURE_PRICES_CSV)
    prices.loc[
        (prices["symbol"] == "AAPL") & (prices["date"] == prices["date"].min()),
        "close",
    ] = 999.0
    load_market_prices_into_database(db, prices)
    db.commit()

    from chronos.storage_sqlite_tables_and_sessions import Price

    updated = db.scalar(
        select(Price.close).where(Price.symbol == "AAPL").order_by(Price.date).limit(1)
    )
    assert updated == 999.0
    assert db.scalar(select(func.count(Price.id))) == 40


def test_csv_with_missing_columns_is_rejected(tmp_path):
    from chronos.market_price_import import load_market_prices_from_csv as load_csv

    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("symbol,date,close\nAAPL,2020-06-01,108\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_csv(bad_csv)


def test_ensure_prices_errors_when_database_and_csv_are_both_empty(
    db, tmp_path, monkeypatch
):
    from chronos.storage_sqlite_tables_and_sessions import Price

    db.query(Price).delete()
    db.flush()
    monkeypatch.setattr(
        price_loading, "MARKET_PRICES_CSV_PATH", tmp_path / "missing.csv"
    )
    with pytest.raises(MarketDataSetupError, match="load_market_data"):
        ensure_market_prices_loaded(db)


def test_ensure_prices_is_a_no_op_when_prices_exist(db):
    ensure_market_prices_loaded(db)  # must not raise or need the CSV

    from chronos.storage_sqlite_tables_and_sessions import Price

    assert db.scalar(select(func.count(Price.id))) == 40


def test_yfinance_normalization_keeps_only_dated_closes():
    import pandas as pd

    from chronos.market_price_import import normalize_yfinance_prices

    raw = pd.DataFrame(
        {"Close": [108.0, 110.0]},
        index=pd.DatetimeIndex(["2020-06-01", "2020-06-08"], name="Date"),
    )
    for prices, symbols in [
        (raw, ["AAPL"]),
        (pd.concat({"AAPL": raw, "MSFT": raw * 2}, axis=1), None),
    ]:
        normalized = normalize_yfinance_prices(prices, symbols)
        assert list(normalized.columns) == ["symbol", "date", "close", "source"]
        assert normalized.iloc[0]["close"] == 108
        assert normalized.iloc[0]["source"] == "YFINANCE"


def test_import_accepts_legacy_csv_and_preserves_unmapped_price_columns(db):
    from sqlalchemy import text

    db.execute(text("ALTER TABLE prices ADD COLUMN open FLOAT"))
    db.execute(text("UPDATE prices SET open = 77"))
    prices = load_market_prices_from_csv(FIXTURE_PRICES_CSV)
    prices.loc[0, "close"] = 999.0
    load_market_prices_into_database(db, prices)
    assert db.scalar(text("SELECT open FROM prices LIMIT 1")) == 77
    assert (
        db.scalar(
            select(Price.close).where(Price.symbol == "AAPL").order_by(Price.date)
        )
        == 999
    )


def test_minimal_price_import(db):
    prices = pd.DataFrame(
        [{"symbol": "AAPL", "date": date(2020, 6, 2), "close": 109, "source": "TEST"}]
    )
    assert load_market_prices_into_database(db, prices) == 1
    assert (
        db.scalar(
            select(Price.close).where(
                Price.symbol == "AAPL", Price.date == date(2020, 6, 2)
            )
        )
        == 109
    )


def test_csv_symbols_are_normalized_for_price_lookup(tmp_path):
    path = tmp_path / "prices.csv"
    path.write_text("symbol,date,close,source\n aapl ,2020-06-01,108,TEST\n")
    assert load_market_prices_from_csv(path).iloc[0]["symbol"] == "AAPL"


@pytest.mark.parametrize("symbols", [None, [], [""], ["   "], ["AAPL", "MSFT"]])
def test_single_symbol_download_requires_an_unambiguous_symbol(symbols):
    raw = pd.DataFrame(
        {"Close": [108.0]},
        index=pd.DatetimeIndex(["2020-06-01"], name="Date"),
    )
    with pytest.raises(ValueError, match="single symbol"):
        price_loading.normalize_yfinance_prices(raw, symbols)
