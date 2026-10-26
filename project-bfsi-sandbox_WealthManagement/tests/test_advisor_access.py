"""Advisor access: observable business outcomes and their protections."""

import pytest

from chronos.app_business_errors_and_permissions import WrongRoleError
from chronos.business_investor_accounts import (
    get_account_for_investor_user,
    get_account_for_viewer,
)


def test_advisor_opens_alices_account(db, alice, advisor):
    assert get_account_for_viewer(db, advisor.id).user_id == alice.id
    assert get_account_for_viewer(db, advisor.id, alice.id).user_id == alice.id


def test_alice_cannot_read_bobs_portfolio(db, client, alice, bob):
    with pytest.raises(WrongRoleError):
        get_account_for_viewer(db, alice.id, bob.id)
    response = client.get(
        "/portfolio", params={"user_id": alice.id, "investor_id": bob.id}
    )
    assert response.status_code == 403


@pytest.mark.parametrize("route", ["/trades/preview", "/trades", "/simulation/advance"])
def test_advisor_cannot_change_an_investors_finances(client, advisor, route):
    payload = (
        {"user_id": advisor.id, "step": "1W"}
        if route == "/simulation/advance"
        else {"user_id": advisor.id, "symbol": "AAPL", "side": "BUY", "amount": 1080}
    )
    assert client.post(route, json=payload).status_code == 403


def test_account_lookup_enforces_its_investor_contract(db, advisor):
    with pytest.raises(WrongRoleError):
        get_account_for_investor_user(db, advisor.id)


def test_viewer_target_must_be_an_investor(db, advisor):
    with pytest.raises(WrongRoleError):
        get_account_for_viewer(db, advisor.id, advisor.id)


def test_investor_and_advisor_read_the_same_screen(client, alice, advisor):
    investor = client.get("/portfolio", params={"user_id": alice.id})
    observed = client.get("/portfolio", params={"user_id": advisor.id})
    assert investor.status_code == observed.status_code == 200
    assert investor.json() == observed.json()
    view = investor.json()
    assert view["investor_name"] == alice.name
    assert view["history"][-1]["total_value"] == view["total_value"]
    assert view["trades"] == []
    assert [asset["symbol"] for asset in view["assets"]] == [
        "AAPL",
        "GLD",
        "JPM",
        "MSFT",
        "SPY",
    ]
