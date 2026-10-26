"""Time: observable business outcomes and their protections."""

from datetime import date

import pytest

from chronos.app_business_errors_and_permissions import InvalidSimulatedDateError
from chronos.business_simulated_time import (
    advance_simulated_investment_date,
    calculate_next_simulated_date,
)


def test_one_week_adds_seven_days():
    assert calculate_next_simulated_date(date(2020, 6, 1), "1W") == date(2020, 6, 8)


def test_one_month_adds_calendar_month():
    assert calculate_next_simulated_date(date(2020, 6, 1), "1M") == date(2020, 7, 1)


def test_one_quarter_adds_three_months():
    assert calculate_next_simulated_date(date(2020, 6, 1), "1Q") == date(2020, 9, 1)


def test_month_end_day_is_clamped():
    assert calculate_next_simulated_date(date(2020, 1, 31), "1M") == date(2020, 2, 29)
    assert calculate_next_simulated_date(date(2020, 11, 30), "1Q") == date(2021, 2, 28)


def test_advance_updates_account(db, alice_account):
    advanced = advance_simulated_investment_date(db, alice_account, "1W")
    assert advanced.simulated_date == date(2020, 6, 8)


def test_advance_past_market_data_is_rejected(db, alice_account):
    advance_simulated_investment_date(db, alice_account, "1Q")  # -> 2020-09-01
    with pytest.raises(InvalidSimulatedDateError):
        advance_simulated_investment_date(db, alice_account, "1Q")
    assert alice_account.simulated_date == date(2020, 9, 1)


def test_advance_api_returns_before_and_after_snapshots(client, alice):
    trade = client.post(
        "/trades",
        json={"user_id": alice.id, "symbol": "AAPL", "side": "BUY", "amount": 10800.0},
    )
    assert trade.status_code == 200

    response = client.post(
        "/simulation/advance", json={"user_id": alice.id, "step": "1W"}
    )
    assert response.status_code == 200
    advance = response.json()

    assert advance["previous_date"] == "2020-06-01"
    assert advance["current_date"] == "2020-06-08"
    assert advance["previous_value"] == pytest.approx(100_000.0)
    assert advance["current_value"] == pytest.approx(100_200.0)


def test_compact_advance_response_keeps_before_and_after_values(client, alice):
    result = client.post(
        "/simulation/advance", json={"user_id": alice.id, "step": "1W"}
    )
    assert result.status_code == 200
    assert result.json() == {
        "previous_date": "2020-06-01",
        "current_date": "2020-06-08",
        "previous_value": 100000,
        "current_value": 100000,
    }
