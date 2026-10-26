"""Read supported assets and prices available on or before a simulation date."""

from datetime import date
from math import isfinite

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from chronos.storage_sqlite_tables_and_sessions import Asset, Price
from chronos.app_business_errors_and_permissions import (
    InvalidSimulatedDateError,
    PriceUnavailableError,
    RecordNotFoundError,
)


def get_latest_price_on_or_before_date(
    db: Session, symbol: str, simulated_date: date
) -> Price:
    """Return the latest available price, never after the simulated date.

    Trades use this lookup; portfolio snapshots use the matching batch lookup.
    Later market data cannot affect an earlier simulation date.
    """
    price = db.scalar(
        select(Price)
        .where(Price.symbol == symbol, Price.date <= simulated_date)
        .order_by(Price.date.desc())
        .limit(1)
    )
    if price is None:
        raise PriceUnavailableError(
            f"No price for {symbol} on or before {simulated_date}"
        )
    require_valid_market_close(price.close, price.symbol, price.date)
    return price


def get_supported_assets(db: Session) -> list[Asset]:
    return list(db.scalars(select(Asset).order_by(Asset.symbol)))


def require_supported_asset(db: Session, symbol: str) -> Asset:
    asset = db.get(Asset, symbol.upper())
    if asset is None:
        raise RecordNotFoundError(f"Unknown symbol {symbol!r}")
    return asset


def get_available_market_date_range(db: Session) -> tuple[date, date]:
    min_date, max_date = db.execute(
        select(func.min(Price.date), func.max(Price.date))
    ).one()
    if min_date is None or max_date is None:
        raise InvalidSimulatedDateError("No market prices loaded")
    return min_date, max_date


def get_latest_prices_on_or_before_date(
    db: Session, symbols: list[str], simulated_date: date
) -> dict[str, Price]:
    """Read each requested symbol's latest known price in one database query."""
    if not symbols:
        return {}
    latest_dates = (
        select(Price.symbol, func.max(Price.date).label("latest_date"))
        .where(Price.symbol.in_(symbols), Price.date <= simulated_date)
        .group_by(Price.symbol)
        .subquery()
    )
    statement = select(Price).join(
        latest_dates,
        (Price.symbol == latest_dates.c.symbol)
        & (Price.date == latest_dates.c.latest_date),
    )
    prices = {price.symbol: price for price in db.scalars(statement)}
    for symbol in sorted(set(symbols)):
        if symbol not in prices:
            raise PriceUnavailableError(
                f"No price for {symbol} on or before {simulated_date}"
            )
    for price in prices.values():
        require_valid_market_close(price.close, price.symbol, price.date)
    return prices


def require_valid_market_close(close: float, symbol: str, price_date: date) -> None:
    """A financial valuation requires a finite, positive closing price."""
    if not isfinite(close) or close <= 0:
        raise PriceUnavailableError(
            f"Invalid closing price for {symbol} on {price_date}"
        )


def get_symbol_price_histories(
    db: Session, symbols: list[str], end_date: date, trading_days: int = 60
) -> dict[str, list[Price]]:
    """Read each symbol's last N known closes together, in chronological order."""
    if not 1 <= trading_days <= 1000:
        raise ValueError("trading_days must be between 1 and 1000")
    histories: dict[str, list[Price]] = {symbol: [] for symbol in symbols}
    if not symbols:
        return histories
    ranked_prices = (
        select(
            Price.id,
            func.row_number()
            .over(partition_by=Price.symbol, order_by=Price.date.desc())
            .label("position"),
        )
        .where(Price.symbol.in_(symbols), Price.date <= end_date)
        .subquery()
    )
    prices = db.scalars(
        select(Price)
        .join(ranked_prices, Price.id == ranked_prices.c.id)
        .where(ranked_prices.c.position <= trading_days)
        .order_by(Price.symbol, Price.date)
    )
    for price in prices:
        require_valid_market_close(price.close, price.symbol, price.date)
        histories[price.symbol].append(price)
    return histories
