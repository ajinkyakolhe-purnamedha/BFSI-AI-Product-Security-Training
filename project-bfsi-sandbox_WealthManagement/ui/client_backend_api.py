"""All HTTP calls from the Streamlit UI to the Chronos Wealth API."""

import os

import requests

API_BASE_URL = os.environ.get("CHRONOS_API_URL", "http://127.0.0.1:8000")


class ApiError(Exception):
    """API returned an error status; message carries the backend detail."""


def _handle(response: requests.Response) -> dict | list:
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ApiError(str(detail))
    return response.json()


def fetch_demo_user_options() -> list:
    return _handle(requests.get(f"{API_BASE_URL}/auth/demo-users"))


def login_as_demo_user(email: str) -> dict:
    return _handle(requests.post(f"{API_BASE_URL}/auth/login", json={"email": email}))


def fetch_portfolio_screen(user_id: int) -> dict:
    return _handle(
        requests.get(f"{API_BASE_URL}/portfolio", params={"user_id": user_id})
    )


def ask_portfolio_chat(user_id: int, question: str, history: list[dict]) -> dict:
    try:
        return _handle(requests.post(
            f"{API_BASE_URL}/portfolio/chat",
            json={"user_id": user_id, "question": question, "history": history},
            timeout=135,
        ))
    except requests.RequestException as error:
        raise ApiError("Could not reach the chat API. Check the backend and try again.") from error


def ask_handbook_rag(user_id: int, question: str) -> dict:
    try:
        return _handle(requests.post(
            f"{API_BASE_URL}/portfolio/rag",
            json={"user_id": user_id, "question": question}, timeout=375,
        ))
    except requests.RequestException as error:
        raise ApiError("Could not reach the RAG API. Check the backend and try again.") from error


def ask_portfolio_agent(user_id: int, question: str) -> dict:
    try:
        return _handle(requests.post(
            f"{API_BASE_URL}/portfolio/agent",
            json={"user_id": user_id, "question": question}, timeout=630,
        ))
    except requests.RequestException as error:
        raise ApiError("Could not reach the agent API. Check the backend and try again.") from error


def preview_investor_trade(user_id: int, symbol: str, side: str, amount: float) -> dict:
    return _handle(
        requests.post(
            f"{API_BASE_URL}/trades/preview",
            json={"user_id": user_id, "symbol": symbol, "side": side, "amount": amount},
        )
    )


def execute_investor_trade(user_id: int, symbol: str, side: str, amount: float) -> dict:
    return _handle(
        requests.post(
            f"{API_BASE_URL}/trades",
            json={"user_id": user_id, "symbol": symbol, "side": side, "amount": amount},
        )
    )


def advance_investor_simulated_date(user_id: int, step: str) -> dict:
    return _handle(
        requests.post(
            f"{API_BASE_URL}/simulation/advance",
            json={"user_id": user_id, "step": step},
        )
    )


def fetch_market_comparison(
    user_id: int, investor_id: int, symbols: list[str], trading_days: int = 60
) -> dict:
    return _handle(
        requests.get(
            f"{API_BASE_URL}/market/history",
            params={
                "user_id": user_id,
                "investor_id": investor_id,
                "symbols": symbols,
                "trading_days": trading_days,
            },
        )
    )
