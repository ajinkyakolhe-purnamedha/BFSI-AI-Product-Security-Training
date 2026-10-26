"""Api: observable business outcomes and their protections."""

from datetime import date

from sqlalchemy import select

from chronos.storage_sqlite_tables_and_sessions import Price
from tests.conftest import ADVISOR_EMAIL, ALICE_EMAIL


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_user_is_404(client):
    assert client.get("/portfolio", params={"user_id": 999}).status_code == 404


def test_market_history_endpoint_hides_future(client, alice):
    response = client.get(
        "/market/history",
        params={"user_id": alice.id, "symbols": ["AAPL"], "trading_days": 60},
    )
    assert response.status_code == 200
    history = response.json()["AAPL"]
    assert history
    assert max(point["date"] for point in history) <= "2020-06-01"


def test_market_history_unknown_symbol_is_404(client, alice):
    response = client.get(
        "/market/history", params={"user_id": alice.id, "symbols": ["ZZZZ"]}
    )
    assert response.status_code == 404


def test_symbol_without_prices_is_400_on_trade(client, alice):
    response = client.post(
        "/trades",
        json={"user_id": alice.id, "symbol": "SPY", "side": "BUY", "amount": 1000.0},
    )
    assert response.status_code == 400


def test_insufficient_cash_is_400(client, alice):
    response = client.post(
        "/trades",
        json={"user_id": alice.id, "symbol": "AAPL", "side": "BUY", "amount": 500000.0},
    )
    assert response.status_code == 400


def test_invalid_side_is_422(client, alice):
    response = client.post(
        "/trades",
        json={"user_id": alice.id, "symbol": "AAPL", "side": "HOLD", "amount": 100.0},
    )
    assert response.status_code == 422


def test_demo_reset_restores_starting_state(client, alice):
    client.post(
        "/trades",
        json={"user_id": alice.id, "symbol": "AAPL", "side": "BUY", "amount": 10800.0},
    )
    reset = client.post("/demo/reset")
    assert reset.status_code == 200
    assert reset.json()["accounts_reset"] == 1

    portfolio = client.get("/portfolio", params={"user_id": alice.id}).json()
    assert portfolio["cash_balance"] == 100_000.0
    assert portfolio["holdings"] == []


def test_invalid_advance_step_is_422(client, alice):
    response = client.post(
        "/simulation/advance", json={"user_id": alice.id, "step": "2W"}
    )
    assert response.status_code == 422


def test_login_demo_investor(client):
    response = client.post("/auth/login", json={"email": ALICE_EMAIL})
    assert response.status_code == 200
    assert response.json()["role"] == "INVESTOR"


def test_login_normalizes_email(client):
    response = client.post("/auth/login", json={"email": "  Alice@Example.com  "})
    assert response.status_code == 200
    assert response.json()["email"] == ALICE_EMAIL


def test_login_unknown_email_fails(client):
    response = client.post("/auth/login", json={"email": "nobody@example.com"})
    assert response.status_code == 404


def test_demo_users_listed(client):
    response = client.get("/auth/demo-users")
    assert response.status_code == 200
    assert [
        (user["email"], user["name"], user["role"]) for user in response.json()
    ] == [
        (ALICE_EMAIL, "Alice Investor", "INVESTOR"),
        (ADVISOR_EMAIL, "Demo Advisor", "ADVISOR"),
    ]


def test_simplified_api_contracts(client, alice, advisor):
    payload = {"user_id": alice.id, "symbol": "AAPL", "side": "BUY", "amount": 1080}
    assert set(client.post("/trades/preview", json=payload).json()) == {
        "symbol",
        "side",
        "amount",
        "price",
        "shares",
        "simulated_date",
        "valid",
        "message",
    }
    assert set(client.post("/trades", json=payload).json()) == {
        "id",
        "symbol",
        "side",
        "shares",
        "price",
        "amount",
        "simulated_date",
    }
    portfolio = client.get("/portfolio", params={"user_id": alice.id}).json()
    assert set(portfolio) == {
        "user_id",
        "simulated_date",
        "cash_balance",
        "holdings_value",
        "total_value",
        "total_return_amount",
        "total_return_percentage",
        "holdings",
        "investor_name",
        "assets",
        "history",
        "trades",
    }
    assert set(
        client.post(
            "/simulation/advance", json={"user_id": alice.id, "step": "1W"}
        ).json()
    ) == {"previous_date", "current_date", "previous_value", "current_value"}
    assert set(
        client.get(
            "/portfolio",
            params={"user_id": advisor.id},
        ).json()
    ) == set(portfolio)


def test_investor_cannot_use_an_advisor_as_the_target(client, alice, advisor):
    response = client.get(
        "/portfolio", params={"user_id": alice.id, "investor_id": advisor.id}
    )
    assert response.status_code == 403


def test_advisor_market_view_uses_the_investor_date(client, alice, advisor):
    response = client.get(
        "/market/history",
        params={
            "user_id": advisor.id,
            "investor_id": alice.id,
            "symbols": ["AAPL", "MSFT"],
            "trading_days": 2,
        },
    )
    assert response.status_code == 200
    assert set(response.json()) == {"AAPL", "MSFT"}
    for points in response.json().values():
        assert len(points) == 2
        assert max(point["date"] for point in points) <= "2020-06-01"


def test_batch_chart_rejects_invalid_stored_close(client, db, alice):
    row = db.scalar(
        select(Price).where(Price.symbol == "AAPL", Price.date == date(2020, 6, 1))
    )
    row.close = 0
    db.flush()
    assert (
        client.get(
            "/market/history", params={"user_id": alice.id, "symbols": ["AAPL"]}
        ).status_code
        == 400
    )
