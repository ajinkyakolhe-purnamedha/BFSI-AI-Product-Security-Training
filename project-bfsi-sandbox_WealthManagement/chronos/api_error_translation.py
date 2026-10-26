"""Translate business rejections into HTTP responses at the API boundary."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException

from chronos.app_business_errors_and_permissions import (
    InsufficientCashError,
    InsufficientSharesError,
    InvalidSimulatedDateError,
    PriceUnavailableError,
    RecordNotFoundError,
    WrongRoleError,
)

_ERROR_STATUS_CODES = {
    RecordNotFoundError: 404,
    WrongRoleError: 403,
    PriceUnavailableError: 400,
    InsufficientCashError: 400,
    InsufficientSharesError: 400,
    InvalidSimulatedDateError: 400,
}


@contextmanager
def translate_domain_errors() -> Iterator[None]:
    try:
        yield
    except tuple(_ERROR_STATUS_CODES) as error:
        for error_type, status_code in _ERROR_STATUS_CODES.items():
            if isinstance(error, error_type):
                raise HTTPException(status_code=status_code, detail=str(error)) from error
        raise
