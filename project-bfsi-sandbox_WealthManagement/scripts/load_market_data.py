"""One-time setup: yfinance -> data/market/prices.csv -> SQLite prices table.

Run from the project root:

    uv run python -m scripts.load_market_data
"""

from chronos.storage_sqlite_tables_and_sessions import (
    MARKET_PRICES_CSV_PATH,
    SessionLocal,
    create_database_tables,
)
from chronos.market_price_import import (
    download_prices_from_yfinance,
    load_market_prices_into_database,
    normalize_yfinance_prices,
    save_market_prices_to_csv,
)

SYMBOLS = ["AAPL", "MSFT", "SPY", "GLD", "JPM"]
START_DATE = "2020-01-01"
END_DATE = "2021-12-31"


def main() -> None:
    print(f"Downloading {SYMBOLS} from yfinance ({START_DATE} to {END_DATE})...")
    raw_prices = download_prices_from_yfinance(SYMBOLS, START_DATE, END_DATE)
    prices = normalize_yfinance_prices(raw_prices, SYMBOLS)
    print(f"Normalized {len(prices)} price rows.")

    save_market_prices_to_csv(prices, MARKET_PRICES_CSV_PATH)
    print(f"Saved CSV to {MARKET_PRICES_CSV_PATH}")

    create_database_tables()
    session = SessionLocal()
    try:
        rows_written = load_market_prices_into_database(session, prices)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    print(f"Loaded {rows_written} price rows into SQLite.")


if __name__ == "__main__":
    main()
