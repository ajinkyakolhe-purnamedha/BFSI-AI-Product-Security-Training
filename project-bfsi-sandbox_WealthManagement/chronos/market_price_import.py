"""Prepare and import historical market data; runtime never downloads prices."""

from math import isfinite
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from chronos.storage_sqlite_tables_and_sessions import MARKET_PRICES_CSV_PATH, Price
from chronos.app_business_errors_and_permissions import MarketDataSetupError

CSV_COLUMNS = ["symbol", "date", "close", "source"]


def download_prices_from_yfinance(
    symbols: list[str], start: str, end: str
) -> pd.DataFrame:
    """Download daily historical prices for the requested symbols."""
    import yfinance as yf

    upper_symbols = [symbol.upper() for symbol in symbols]
    raw_prices = yf.download(
        upper_symbols,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        progress=False,
    )
    if raw_prices is None or raw_prices.empty:
        raise RuntimeError(
            f"yfinance returned no data for {upper_symbols} between {start} and {end}"
        )
    return raw_prices


def normalize_yfinance_prices(
    raw_prices: pd.DataFrame, symbols: list[str] | None = None
) -> pd.DataFrame:
    """Convert yfinance output into Chronos's portable CSV schema."""
    if isinstance(raw_prices.columns, pd.MultiIndex):
        frames = [
            _normalize_single_symbol(raw_prices[symbol], symbol)
            for symbol in raw_prices.columns.get_level_values(0).unique()
        ]
    else:
        if not symbols or len(symbols) != 1 or not symbols[0].strip():
            raise ValueError("A single symbol is required for unlabelled price data")
        frames = [_normalize_single_symbol(raw_prices, symbols[0])]
    normalized = pd.concat(frames, ignore_index=True).dropna(subset=["close"])
    return normalized.sort_values(["symbol", "date"]).reset_index(drop=True)[
        CSV_COLUMNS
    ]


def save_market_prices_to_csv(prices: pd.DataFrame, output_path: Path) -> Path:
    """Save normalized market prices to a portable CSV file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(output_path, index=False)
    return output_path


def load_market_prices_from_csv(input_path: Path) -> pd.DataFrame:
    """Load and validate normalized market prices from CSV."""
    prices = pd.read_csv(Path(input_path))
    validate_market_price_rows(prices)
    prices["symbol"] = prices["symbol"].str.strip().str.upper()
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    return prices


def load_market_prices_into_database(db: Session, prices: pd.DataFrame) -> int:
    """Insert or update normalized prices without duplicating symbol/date rows."""
    validate_market_price_rows(prices)
    prices = prices.copy()
    prices["symbol"] = prices["symbol"].str.strip().str.upper()
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    for row in prices.itertuples(index=False):
        price = db.scalar(
            select(Price).where(Price.symbol == row.symbol, Price.date == row.date)
        )
        if price is None:
            price = Price(symbol=row.symbol, date=row.date)
            db.add(price)
        price.close = float(row.close)
        price.source = str(row.source)
    db.flush()
    return len(prices)


def ensure_market_prices_loaded(db: Session) -> None:
    """Load the prepared local CSV when the application database has no prices."""
    if db.scalar(select(Price.id).limit(1)) is not None:
        return
    if not MARKET_PRICES_CSV_PATH.exists():
        raise MarketDataSetupError(
            f"No market prices found in the database and {MARKET_PRICES_CSV_PATH} "
            "does not exist. Run: uv run python -m scripts.load_market_data"
        )
    load_market_prices_into_database(
        db, load_market_prices_from_csv(MARKET_PRICES_CSV_PATH)
    )


def _normalize_single_symbol(symbol_prices: pd.DataFrame, symbol: str) -> pd.DataFrame:
    frame = symbol_prices.reset_index()
    frame.columns = [str(column) for column in frame.columns]
    return pd.DataFrame(
        {
            "symbol": symbol.strip().upper(),
            "date": pd.to_datetime(frame["Date"]).dt.date,
            "close": frame["Close"],
            "source": "YFINANCE",
        }
    )


def validate_market_price_rows(prices: pd.DataFrame) -> None:
    """Reject invalid input as a whole before changing any stored price rows."""
    missing_columns = [column for column in CSV_COLUMNS if column not in prices.columns]
    if missing_columns:
        raise ValueError(
            f"Market prices are missing required columns: {missing_columns}"
        )
    if (
        not prices["symbol"]
        .map(lambda symbol: isinstance(symbol, str) and bool(symbol.strip()))
        .all()
    ):
        raise ValueError("Market price symbols must be nonempty strings")
    parsed_dates = pd.to_datetime(prices["date"], errors="raise")
    if parsed_dates.isna().any():
        raise ValueError("Market price dates must not be empty")
    closes = pd.to_numeric(prices["close"], errors="raise")
    if not closes.map(lambda close: isfinite(close) and close > 0).all():
        raise ValueError("Market closing prices must be finite and positive")
    keys = pd.DataFrame(
        {"symbol": prices["symbol"].str.strip().str.upper(), "date": parsed_dates.dt.date}
    )
    if keys.duplicated(["symbol", "date"]).any():
        raise ValueError("Market prices contain duplicate symbol/date pairs")
