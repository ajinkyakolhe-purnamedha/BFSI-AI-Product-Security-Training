"""Advisor dashboard: Alice's portfolio, observed without mutation."""

import client_backend_api as api_client
import charts_asset_performance as performance_comparison_charts
import streamlit as st
from view_shared_portfolio import render_portfolio_view


def render_advisor_dashboard_screen(user: dict) -> None:
    advisor_user_id = user["id"]
    st.title(f"Advisor Workspace — {user['name']}")
    st.caption("Read-only view of Alice Investor. Advisors never trade for clients.")

    portfolio = api_client.fetch_portfolio_screen(advisor_user_id)
    st.subheader(f"{portfolio['investor_name']} — Portfolio")
    render_portfolio_view(portfolio)
    _render_client_performance_vs_peers(advisor_user_id, portfolio)


def _render_client_performance_vs_peers(viewer_user_id: int, portfolio: dict) -> None:
    """One held symbol against the average of the other supported assets.
    History is authorized for the advisor and ends at the client's
    simulated date — the advisor sees no further than the client can."""
    st.subheader("Performance vs Peers")
    assets = portfolio["assets"]
    holdings = portfolio["holdings"]
    all_symbols = [asset["symbol"] for asset in assets]
    held_symbols = [holding["symbol"] for holding in holdings]
    default_symbol = held_symbols[0] if held_symbols else all_symbols[0]
    symbol = st.selectbox(
        "Focus symbol", all_symbols, index=all_symbols.index(default_symbol)
    )
    if not symbol:
        return
    normalized = performance_comparison_charts.fetch_normalized_price_frame(
        viewer_user_id, portfolio["user_id"], all_symbols
    )
    missing_symbols = sorted(set(all_symbols) - set(normalized.columns))
    if missing_symbols:
        st.info(f"No price history for: {', '.join(missing_symbols)}.")
    if normalized.empty or symbol not in normalized.columns:
        st.info("No price history before this client's simulated date.")
        return
    if len(normalized.columns) < 2:
        st.info("Comparison needs at least two symbols with price history.")
        return
    line_column, delta_column = st.columns(2)
    line_column.altair_chart(
        performance_comparison_charts.symbol_vs_peer_average_chart(normalized, symbol),
        use_container_width=True,
    )
    delta_column.altair_chart(
        performance_comparison_charts.performance_delta_area_chart(normalized, symbol),
        use_container_width=True,
    )
