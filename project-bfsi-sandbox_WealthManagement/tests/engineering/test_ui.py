"""Ui: observable business outcomes and their protections."""

from pathlib import Path
from urllib.parse import urlsplit

import pytest
import requests
from streamlit.testing.v1 import AppTest


@pytest.fixture
def ui_requests():
    return []


@pytest.fixture
def offline_ui(client, monkeypatch, ui_requests):
    ui_directory = Path(__file__).resolve().parents[2] / "ui"
    monkeypatch.syspath_prepend(str(ui_directory))

    def get(url, params=None, **kwargs):
        ui_requests.append(urlsplit(url).path)
        return client.get(urlsplit(url).path, params=params)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(
        requests,
        "post",
        lambda url, json=None, **kwargs: client.post(urlsplit(url).path, json=json),
    )
    return AppTest.from_file(
        str(ui_directory / "app_navigation.py"), default_timeout=15
    )


def test_login_renders_and_opens_investor_dashboard(offline_ui):
    app = offline_ui.run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["user"]["role"] == "INVESTOR"
    assert app.title[0].value == "Investor Dashboard — Alice Investor"
    assert any(metric.label == "Portfolio Value" for metric in app.metric)


def test_advisor_dashboard_renders_client_portfolio(offline_ui, advisor):
    offline_ui.session_state["user"] = {
        "id": advisor.id,
        "role": advisor.role,
        "name": advisor.name,
    }
    app = offline_ui.run()
    assert not app.exception
    assert app.title[0].value == "Advisor Workspace — Demo Advisor"
    assert any(metric.label == "Portfolio Value" for metric in app.metric)


def test_investor_screen_uses_two_read_requests(offline_ui, alice, ui_requests):
    offline_ui.session_state["user"] = {
        "id": alice.id,
        "role": alice.role,
        "name": alice.name,
    }
    app = offline_ui.run()
    assert not app.exception
    assert ui_requests == ["/portfolio", "/market/history"]


def test_advancing_time_refreshes_portfolio_and_clears_preview(
    offline_ui, client, alice
):
    client.post(
        "/trades",
        json={"user_id": alice.id, "symbol": "AAPL", "side": "BUY", "amount": 10800},
    )
    offline_ui.session_state["user"] = {
        "id": alice.id,
        "role": alice.role,
        "name": alice.name,
    }
    offline_ui.session_state["pending_preview"] = client.post(
        "/trades/preview",
        json={
            "user_id": alice.id,
            "symbol": "AAPL",
            "side": "BUY",
            "amount": 1000,
        },
    ).json()
    app = offline_ui.run()
    next(button for button in app.button if button.label == "+1 week").click().run()
    assert not app.exception
    assert any("2020-06-08" in caption.value for caption in app.caption)
    assert (
        next(metric.value for metric in app.metric if metric.label == "Portfolio Value")
        == "$100,200.00"
    )
    assert "pending_preview" not in app.session_state.filtered_state


def test_advisor_screen_has_no_financial_controls(offline_ui, advisor, ui_requests):
    offline_ui.session_state["user"] = {
        "id": advisor.id,
        "role": advisor.role,
        "name": advisor.name,
    }
    app = offline_ui.run()
    assert not app.exception
    assert ui_requests == ["/portfolio", "/market/history"]
    assert not any(
        button.label
        in {"Preview trade", "Confirm trade", "+1 week", "+1 month", "+1 quarter"}
        for button in app.button
    )
    assert not app.chat_input


def test_changing_trade_inputs_requires_a_new_preview(offline_ui, alice):
    offline_ui.session_state["user"] = {
        "id": alice.id,
        "role": alice.role,
        "name": alice.name,
    }
    app = offline_ui.run()
    next(
        button for button in app.button if button.label == "Preview trade"
    ).click().run()
    assert any(button.label == "Confirm trade" for button in app.button)
    app.number_input[0].set_value(2000.0).run()
    assert not app.exception
    assert not any(button.label == "Confirm trade" for button in app.button)
    assert "pending_preview" not in app.session_state.filtered_state
    assert (
        next(metric.value for metric in app.metric if metric.label == "Cash")
        == "$100,000.00"
    )


@pytest.mark.parametrize("role", ["INVESTOR", "ADVISOR"])
def test_comparison_requires_two_symbols_with_available_history(
    offline_ui, db, alice, advisor, role
):
    from chronos.storage_sqlite_tables_and_sessions import Price

    db.query(Price).filter(Price.symbol == "MSFT").delete()
    db.flush()
    user = alice if role == "INVESTOR" else advisor
    offline_ui.session_state["user"] = {
        "id": user.id, "role": user.role, "name": user.name
    }
    app = offline_ui.run()
    assert not app.exception
    assert any("MSFT" in message.value for message in app.info)
    assert any("at least two" in message.value.lower() for message in app.info)
    assert not any(metric.label.startswith(("Best:", "Worst:")) for metric in app.metric)
    assert not app.get("arrow_vega_lite_chart")


def test_partial_comparison_identifies_missing_symbols(offline_ui, alice):
    offline_ui.session_state["user"] = {
        "id": alice.id, "role": alice.role, "name": alice.name
    }
    app = offline_ui.run()
    assert not app.exception
    assert any(
        all(symbol in message.value for symbol in ["GLD", "JPM", "SPY"])
        for message in app.info
    )
    assert any(metric.label == "Best: AAPL" for metric in app.metric)
    assert any(metric.label == "Worst: MSFT" for metric in app.metric)


def test_investor_chat_displays_replies_and_clears_conversation(offline_ui, alice, monkeypatch):
    import client_backend_api

    def answer(user_id, question, history):
        assert user_id == alice.id
        return {"answer": "You have $100,000 in virtual cash.", "history": [
            *history, {"role": "user", "content": question},
            {"role": "assistant", "content": "You have $100,000 in virtual cash."},
        ]}

    monkeypatch.setattr(client_backend_api, "ask_portfolio_chat", answer, raising=False)
    offline_ui.session_state["user"] = {"id": alice.id, "role": alice.role, "name": alice.name}
    app = offline_ui.run()
    assert len(app.chat_input) == 1
    app.chat_input[0].set_value("What do I own?").run()
    assert not app.exception
    assert [message.value for message in app.markdown if "virtual cash" in message.value]
    assert len(app.chat_message) == 2
    next(button for button in app.button if button.label == "Clear chat").click().run()
    assert not app.chat_message


def test_chat_connection_failure_preserves_conversation(offline_ui, alice, monkeypatch):
    import client_backend_api

    def unavailable(*args):
        raise client_backend_api.ApiError("Ollama is unavailable. Start Ollama and try again.")

    monkeypatch.setattr(client_backend_api, "ask_portfolio_chat", unavailable, raising=False)
    offline_ui.session_state["user"] = {"id": alice.id, "role": alice.role, "name": alice.name}
    offline_ui.session_state["chat_user_id"] = alice.id
    offline_ui.session_state["chat_history"] = [
        {"role": "user", "content": "What is cash?"},
        {"role": "assistant", "content": "Your uninvested virtual money."},
    ]
    app = offline_ui.run()
    assert len(app.chat_input) == 1
    app.chat_input[0].set_value("Explain cash").run()
    assert not app.exception
    assert any("Ollama" in error.value for error in app.error)
    assert len(app.chat_message) == 2
    assert app.session_state["chat_history"][-1]["content"] == "Your uninvested virtual money."


def test_chat_ui_calls_real_endpoint_and_keeps_follow_up(offline_ui, alice, monkeypatch):
    pytest.importorskip("llama_index.llms.ollama")
    from llama_index.llms.ollama import Ollama
    from ollama import ChatResponse
    from chronos import api_routes_portfolio

    llm = Ollama(model="offline-test", context_window=4096)
    prompts = []

    def chat(**kwargs):
        prompts.append(kwargs["messages"])
        return ChatResponse(model="offline-test", message={
            "role": "assistant", "content": "Your virtual cash is $100,000."
        })

    monkeypatch.setattr(llm.client, "chat", chat)
    monkeypatch.setattr(api_routes_portfolio, "get_chat_model", lambda: llm)
    offline_ui.session_state["user"] = {"id": alice.id, "role": alice.role, "name": alice.name}
    app = offline_ui.run()
    app.chat_input[0].set_value("What is my cash?").run()
    app.chat_input[0].set_value("Explain that").run()
    assert not app.exception
    assert len(app.chat_message) == 4
    assert '"cash_balance":100000.0' in prompts[1][0]["content"]
    assert prompts[1][2]["content"] == "Your virtual cash is $100,000."


def test_ai_demo_tabs_show_rag_sources_and_agent_tool_results(offline_ui, alice, monkeypatch):
    import client_backend_api

    monkeypatch.setattr(client_backend_api, "ask_handbook_rag", lambda *args: {
        "answer": "An unsold gain [1].", "sources": [
            {"title": "Unrealized gain", "passage": "Market value minus cost basis.", "score": 0.9}
        ],
    }, raising=False)
    monkeypatch.setattr(client_backend_api, "ask_portfolio_agent", lambda *args: {
        "answer": "Your cash is $100,000.", "tool_calls": [
            {"tool_name": "read_my_portfolio", "arguments": {}, "result": '{"cash_balance":100000}'}
        ],
    }, raising=False)
    offline_ui.session_state["user"] = {"id": alice.id, "role": alice.role, "name": alice.name}
    app = offline_ui.run()
    assert [tab.label for tab in app.tabs] == ["Chatbot", "RAG", "Agent"]
    assert not any(header.value == "Portfolio Chat" for header in app.subheader)
    next(input for input in app.text_input if input.label == "Handbook question").set_value("What is unrealized gain?")
    next(button for button in app.button if button.label == "Ask handbook").click().run()
    assert not app.exception
    assert any("An unsold gain" in text.value for text in app.markdown)
    assert any("[1] Unrealized gain" in expander.label for expander in app.expander)
    next(input for input in app.text_input if input.label == "Agent question").set_value("Explain my journey")
    next(button for button in app.button if button.label == "Run agent").click().run()
    assert not app.exception
    assert any("read_my_portfolio" in expander.label for expander in app.expander)
    assert any("100000" in result.value for result in app.json)
    # Results survive ordinary rerenders without another generation request.
    app.run()
    assert any("An unsold gain" in text.value for text in app.markdown)


@pytest.mark.parametrize("feature,label,button", [
    ("rag", "Handbook question", "Ask handbook"),
    ("agent", "Agent question", "Run agent"),
])
def test_ai_demo_errors_render_without_breaking_dashboard(offline_ui, alice, monkeypatch, feature, label, button):
    import client_backend_api

    def unavailable(*args):
        raise client_backend_api.ApiError("Ollama is unavailable")

    function = "ask_handbook_rag" if feature == "rag" else "ask_portfolio_agent"
    monkeypatch.setattr(client_backend_api, function, unavailable)
    offline_ui.session_state["user"] = {"id": alice.id, "role": alice.role, "name": alice.name}
    app = offline_ui.run()
    next(input for input in app.text_input if input.label == label).set_value("Explain")
    next(widget for widget in app.button if widget.label == button).click().run()
    assert not app.exception
    assert any("Ollama" in error.value for error in app.error)
    assert any(metric.label == "Portfolio Value" for metric in app.metric)
