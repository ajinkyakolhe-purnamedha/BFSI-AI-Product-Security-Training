"""The same financial facts and display for investor and advisor."""

import pandas as pd
import streamlit as st


def render_portfolio_view(portfolio: dict) -> None:
    st.caption(f"Simulated date: {portfolio['simulated_date']}")
    if notice := st.session_state.pop("advance_notice", None):
        st.info(notice)
    _render_portfolio_summary(portfolio)
    _render_holdings_table(portfolio)
    _render_recorded_portfolio_values_chart(portfolio)
    _render_trade_history(portfolio)


def format_gain_loss(value: float) -> str:
    if value > 0:
        return f":green[+${value:,.2f}]"
    if value < 0:
        return f":red[-${abs(value):,.2f}]"
    return f"${value:,.2f}"


def _render_portfolio_summary(portfolio: dict) -> None:
    cash, holdings, total, gain = st.columns(4)
    cash.metric("Cash", f"${portfolio['cash_balance']:,.2f}")
    holdings.metric("Holdings Value", f"${portfolio['holdings_value']:,.2f}")
    total.metric("Portfolio Value", f"${portfolio['total_value']:,.2f}")
    gain.metric(
        "Total Return",
        f"${portfolio['total_return_amount']:,.2f}",
        f"{portfolio['total_return_percentage']:.2f}%",
    )


def _render_holdings_table(portfolio: dict) -> None:
    st.subheader("Holdings")
    if not portfolio["holdings"]:
        st.info("No holdings yet.")
        return
    holdings_frame = pd.DataFrame(portfolio["holdings"])
    st.dataframe(
        holdings_frame.style.map(
            lambda value: (
                "color: green" if value > 0 else "color: red" if value < 0 else ""
            ),
            subset=["unrealized_gain_loss"],
        ),
        hide_index=True,
    )
    total_gain_loss = holdings_frame["unrealized_gain_loss"].sum()
    st.markdown(f"Unrealized gain/loss: {format_gain_loss(total_gain_loss)}")


def _render_recorded_portfolio_values_chart(portfolio: dict) -> None:
    st.subheader("Recorded Portfolio Values")
    st.caption(
        "Values recorded after trades and time advances; intervening dates are not recorded."
    )
    history = portfolio["history"]
    if history:
        history_frame = pd.DataFrame(history)
        st.line_chart(history_frame.set_index("date")["total_value"])


def _render_trade_history(portfolio: dict) -> None:
    st.subheader("Trade History")
    trades = portfolio["trades"]
    if trades:
        st.dataframe(
            pd.DataFrame(trades)[
                ["id", "simulated_date", "symbol", "side", "shares", "price", "amount"]
            ],
            hide_index=True,
        )
    else:
        st.info("No trades yet.")
