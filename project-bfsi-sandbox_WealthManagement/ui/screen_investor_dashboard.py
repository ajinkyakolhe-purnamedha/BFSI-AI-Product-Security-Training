"""Investor dashboard: portfolio, charts, trading, and simulated time."""

import json

import client_backend_api as api_client
import charts_asset_performance as performance_comparison_charts
import streamlit as st
from client_backend_api import ApiError
from view_shared_portfolio import format_gain_loss, render_portfolio_view


def render_investor_dashboard_screen(user: dict) -> None:
    user_id = user["id"]
    st.title(f"Investor Dashboard — {user['name']}")

    portfolio = api_client.fetch_portfolio_screen(user_id)
    render_portfolio_view(portfolio)
    _render_ai_demo(user_id)
    _render_performance_comparison(user_id, portfolio)
    _render_trade_form(user_id, portfolio["assets"])
    _render_time_advance_buttons(user_id)


def _render_ai_demo(user_id: int) -> None:
    st.subheader("AI Demo")
    if st.session_state.get("chat_user_id") != user_id:
        st.session_state.pop("rag_result", None)
        st.session_state.pop("agent_result", None)
    chatbot_tab, rag_tab, agent_tab = st.tabs(["Chatbot", "RAG", "Agent"], key="ai_demo_tabs")
    with chatbot_tab:
        _render_portfolio_chat(user_id)
    with rag_tab:
        _render_handbook_rag(user_id)
    with agent_tab:
        _render_portfolio_agent(user_id)


def _render_portfolio_chat(user_id: int) -> None:
    st.caption("Ask about your virtual portfolio. Answers use its latest simulated date.")
    # Session memory is scoped to the investor; logout clears all session state.
    if st.session_state.get("chat_user_id") != user_id:
        st.session_state["chat_user_id"] = user_id
        st.session_state["chat_history"] = []
    if st.button("Clear chat"):
        st.session_state["chat_history"] = []

    history = st.session_state["chat_history"]
    with st.container(border=True):
        for message in history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        question = st.chat_input("Try: Why is portfolio value different from cash?", max_chars=2000)
        if question:
            try:
                with st.spinner("Reading your portfolio and asking Ollama…"):
                    reply = api_client.ask_portfolio_chat(user_id, question, history)
                st.session_state["chat_history"] = reply["history"]
                st.rerun()
            except ApiError as error:
                st.error(str(error))


def _render_handbook_rag(user_id: int) -> None:
    st.caption("Ask the investing handbook. See the passages retrieved before the answer.")
    with st.form("rag_question_form"):
        question = st.text_input("Handbook question", placeholder="What is unrealized gain?", max_chars=2000)
        submitted = st.form_submit_button("Ask handbook")
    if submitted:
        if not question.strip():
            st.info("Enter a handbook question.")
        else:
            try:
                with st.spinner("Embedding your question and searching the handbook…"):
                    result = api_client.ask_handbook_rag(user_id, question)
                st.session_state["rag_result"] = {"question": question, **result}
            except ApiError as error:
                st.error(str(error))
    result = st.session_state.get("rag_result")
    if result:
        st.write(f"Question: {result['question']}")
        st.markdown(result["answer"])
        for number, source in enumerate(result["sources"], start=1):
            with st.expander(f"[{number}] {source['title']}"):
                st.write(source["passage"])
                if source["score"] is not None:
                    st.caption(f"Similarity: {source['score']:.3f}")
        if not result["sources"]:
            st.info("No handbook passage passed the retrieval threshold.")


def _render_portfolio_agent(user_id: int) -> None:
    st.caption("Let the model choose read-only portfolio tools. Inspect what Python executed.")
    with st.form("agent_question_form"):
        question = st.text_input(
            "Agent question", placeholder="Explain my portfolio journey using current facts and recorded values", max_chars=2000
        )
        submitted = st.form_submit_button("Run agent")
    if submitted:
        if not question.strip():
            st.info("Enter an agent question.")
        else:
            try:
                with st.spinner("Exploring your portfolio with up to four read-tool calls…"):
                    result = api_client.ask_portfolio_agent(user_id, question)
                st.session_state["agent_result"] = {"question": question, **result}
            except ApiError as error:
                st.error(str(error))
    result = st.session_state.get("agent_result")
    if result:
        st.write(f"Question: {result['question']}")
        st.markdown(result["answer"])
        for number, call in enumerate(result["tool_calls"], start=1):
            with st.expander(f"Tool {number}: {call['tool_name']}"):
                st.write("Arguments")
                st.json(call["arguments"])
                st.write("Result")
                st.json(json.loads(call["result"]))
        if not result["tool_calls"]:
            st.info("The model answered without requesting a tool.")


def _render_performance_comparison(user_id: int, portfolio: dict) -> None:
    """Symbols indexed to a common start so growth is comparable,
    always ending at the account's simulated date."""
    st.subheader("Performance Comparison")
    assets = portfolio["assets"]
    all_symbols = [asset["symbol"] for asset in assets]
    symbols = st.multiselect("Symbols", all_symbols, default=all_symbols)
    horizon = st.pills("Horizon (trading days)", [30, 60, 90, 120], default=60)
    if len(symbols) < 2:
        st.info("Pick at least two symbols to compare.")
        return
    normalized = performance_comparison_charts.fetch_normalized_price_frame(
        user_id, portfolio["user_id"], symbols, horizon or 60
    )
    missing_symbols = sorted(set(symbols) - set(normalized.columns))
    if missing_symbols:
        st.info(f"No price history for: {', '.join(missing_symbols)}.")
    if normalized.empty:
        st.info("No price history before the simulated date.")
        return
    if len(normalized.columns) < 2:
        st.info("Comparison needs at least two symbols with price history.")
        return
    st.altair_chart(
        performance_comparison_charts.normalized_performance_chart(normalized),
        use_container_width=True,
    )
    best_symbol, best_growth, worst_symbol, worst_growth = (
        performance_comparison_charts.best_and_worst_performers(normalized)
    )
    best_column, worst_column = st.columns(2)
    best_column.metric(f"Best: {best_symbol}", f"{best_growth:+.1%}")
    worst_column.metric(f"Worst: {worst_symbol}", f"{worst_growth:+.1%}")


def _render_trade_form(user_id: int, assets: list[dict]) -> None:
    st.subheader("Trade")
    symbol_column, side_column, amount_column = st.columns(3)
    symbol = symbol_column.selectbox(
        "Trade symbol", [asset["symbol"] for asset in assets]
    )
    side = side_column.selectbox("Side", ["BUY", "SELL"])
    amount = amount_column.number_input(
        "Amount ($)", min_value=1.0, value=1000.0, step=100.0
    )

    if st.button("Preview trade"):
        try:
            st.session_state["pending_preview"] = api_client.preview_investor_trade(
                user_id, symbol, side, amount
            )
        except ApiError as error:
            st.error(str(error))
            st.session_state.pop("pending_preview", None)

    preview = st.session_state.get("pending_preview")
    if preview and (preview["symbol"], preview["side"], preview["amount"]) != (
        symbol,
        side,
        amount,
    ):
        st.session_state.pop("pending_preview", None)
        preview = None
    if preview:
        if preview["valid"]:
            st.success(preview["message"])
            if st.button("Confirm trade", type="primary"):
                try:
                    api_client.execute_investor_trade(
                        user_id,
                        preview["symbol"],
                        preview["side"],
                        preview["amount"],
                    )
                    st.session_state.pop("pending_preview", None)
                    st.rerun()
                except ApiError as error:
                    st.error(str(error))
        else:
            st.error(preview["message"])


def _render_time_advance_buttons(user_id: int) -> None:
    st.subheader("Simulated Time")
    week, month, quarter = st.columns(3)
    step = None
    if week.button("+1 week"):
        step = "1W"
    if month.button("+1 month"):
        step = "1M"
    if quarter.button("+1 quarter"):
        step = "1Q"

    if step:
        try:
            advance = api_client.advance_investor_simulated_date(user_id, step)
            change = advance["current_value"] - advance["previous_value"]
            st.session_state["advance_notice"] = (
                f"Moved {advance['previous_date']} → {advance['current_date']}: "
                f"portfolio ${advance['previous_value']:,.2f} → "
                f"${advance['current_value']:,.2f} ({format_gain_loss(change)})"
            )
            st.session_state.pop("pending_preview", None)
            st.rerun()
        except ApiError as error:
            st.error(str(error))
