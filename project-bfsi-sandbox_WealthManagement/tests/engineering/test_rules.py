"""Rules: observable business outcomes and their protections."""

import subprocess
import sys
from datetime import date

import pytest


def priced_trade(side, amount=1080):
    from chronos.rules_trade_eligibility_and_cost import PricedTrade

    return PricedTrade("AAPL", side, amount, 108, amount / 108, date(2020, 6, 1))


@pytest.mark.parametrize(
    "side,cash,shares,exists,allowed,reason",
    [
        ("BUY", 1080, 0, False, True, None),
        ("BUY", 100, 0, False, False, "insufficient_cash"),
        ("SELL", 0, 10, True, True, None),
        ("SELL", 0, 5, True, False, "insufficient_shares"),
        ("SELL", 0, 0, False, False, "insufficient_shares"),
    ],
)
def test_trade_eligibility(side, cash, shares, exists, allowed, reason):
    from chronos.rules_trade_eligibility_and_cost import trade_rejection_reason

    result = trade_rejection_reason(
        priced_trade(side), cash, shares, holding_exists=exists
    )
    assert result == reason
    assert (result is None) is allowed


def test_average_cost_weights_owned_and_bought_shares():
    from chronos.rules_trade_eligibility_and_cost import (
        calculate_average_cost_after_buy,
    )

    assert calculate_average_cost_after_buy(100, 108, 100, 110) == 109
    assert calculate_average_cost_after_buy(0, 0, 100, 110) == 110


def test_rules_import_without_database_http_or_ui_dependencies():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import chronos.rules_trade_eligibility_and_cost; "
            "assert not {'sqlalchemy', 'fastapi', 'streamlit', 'pandas', 'pydantic'} & set(sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_business_errors_and_permissions_import_without_http_framework():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import chronos.app_business_errors_and_permissions; "
            "assert 'fastapi' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
