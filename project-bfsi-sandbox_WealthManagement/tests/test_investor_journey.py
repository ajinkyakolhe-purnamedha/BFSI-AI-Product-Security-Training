"""Alice invests, time passes, and her advisor sees the same portfolio."""

import pytest

from tests.conftest import ADVISOR_EMAIL, ALICE_EMAIL


def test_alice_buys_ten_shares_and_shares_the_result_with_her_advisor(client):
    # Alice starts with $100,000 and no investments on June 1.
    login = client.post("/auth/login", json={"email": ALICE_EMAIL})
    assert login.status_code == 200
    alice_id = login.json()["id"]
    response = client.get("/portfolio", params={"user_id": alice_id})
    assert response.status_code == 200
    portfolio = response.json()
    assert portfolio["simulated_date"] == "2020-06-01"
    assert portfolio["cash_balance"] == portfolio["total_value"] == 100_000
    assert portfolio["holdings"] == []

    # Ten shares at $108 cost $1,080. Previewing leaves her money untouched.
    purchase = {"user_id": alice_id, "symbol": "AAPL", "side": "BUY", "amount": 1080}
    response = client.post("/trades/preview", json=purchase)
    assert response.status_code == 200
    preview = response.json()
    assert preview["valid"] is True
    assert preview["price"] == 108
    assert preview["shares"] == pytest.approx(10)
    assert client.get("/portfolio", params={"user_id": alice_id}).json() == portfolio

    # Buying converts cash into shares and records one trade.
    assert client.post("/trades", json=purchase).status_code == 200
    portfolio = client.get("/portfolio", params={"user_id": alice_id}).json()
    assert portfolio["cash_balance"] == pytest.approx(98_920)
    assert portfolio["holdings"][0]["symbol"] == "AAPL"
    assert portfolio["holdings"][0]["shares"] == pytest.approx(10)
    assert len(portfolio["trades"]) == 1
    assert portfolio["history"]

    # On July 1 the latest available close is $116: Alice has gained $80.
    response = client.post(
        "/simulation/advance", json={"user_id": alice_id, "step": "1M"}
    )
    assert response.status_code == 200
    advance = response.json()
    assert advance["previous_date"] == "2020-06-01"
    assert advance["current_date"] == "2020-07-01"
    assert advance["previous_value"] == pytest.approx(100_000)
    assert advance["current_value"] == pytest.approx(100_080)
    portfolio = client.get("/portfolio", params={"user_id": alice_id}).json()
    assert portfolio["holdings_value"] == pytest.approx(1160)
    assert portfolio["total_value"] == pytest.approx(100_080)
    assert max(point["date"] for point in portfolio["history"]) <= "2020-07-01"

    # Her advisor reads exactly the same facts.
    login = client.post("/auth/login", json={"email": ADVISOR_EMAIL})
    assert login.status_code == 200
    response = client.get("/portfolio", params={"user_id": login.json()["id"]})
    assert response.status_code == 200
    assert response.json() == portfolio
