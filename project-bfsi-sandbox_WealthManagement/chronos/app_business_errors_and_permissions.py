"""Chronos domain errors and investor/advisor role checks."""

from chronos.storage_sqlite_tables_and_sessions import User

INVESTOR_ROLE = "INVESTOR"
ADVISOR_ROLE = "ADVISOR"


class DomainError(Exception):
    """Base class for business errors raised by the application."""


class RecordNotFoundError(DomainError):
    pass


class WrongRoleError(DomainError):
    pass


class PriceUnavailableError(DomainError):
    pass


class InsufficientCashError(DomainError):
    pass


class InsufficientSharesError(DomainError):
    pass


class InvalidSimulatedDateError(DomainError):
    pass


class MarketDataSetupError(DomainError):
    pass


def require_investor_user(user: User) -> User:
    if user.role != INVESTOR_ROLE:
        raise WrongRoleError(f"User {user.id} is {user.role}, not an investor")
    return user


def require_advisor_user(user: User) -> User:
    if user.role != ADVISOR_ROLE:
        raise WrongRoleError(f"User {user.id} is {user.role}, not an advisor")
    return user
