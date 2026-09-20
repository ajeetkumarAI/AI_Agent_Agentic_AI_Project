"""Streamlit interface for the educational financial advisor."""

import streamlit as st

from agent import HORIZONS, RISK_LEVELS, plan_financial_request


def main() -> None:
    """Render advisor inputs and the educational planning report."""

    st.set_page_config(page_title="Financial Advisor", page_icon="📊", layout="wide")
    st.title("Financial Advisor")
    st.warning("Educational information only. This is not financial advice and does not place trades.")

    with st.form("advisor_form"):
        ticker = st.text_input("Ticker", value="AAPL")
        risk = st.selectbox("Risk attitude", sorted(RISK_LEVELS), index=2)
        period = st.selectbox("Investment period", sorted(HORIZONS), index=3)
        preferences = st.text_input("Execution preferences", placeholder="Example: paper trading, limit orders")
        submitted = st.form_submit_button("Create educational plan", type="primary")

    if not submitted:
        st.info("Enter a ticker and profile to create a planning template.")
        return
    try:
        report = plan_financial_request(ticker, risk, period, preferences)
    except ValueError as error:
        st.error(str(error))
        return

    st.subheader("Market analysis")
    st.text(report.market_analysis)
    st.subheader("Strategy options")
    for item in report.strategy_options:
        st.markdown(f"- {item}")
    st.subheader("Execution planning")
    for item in report.execution_plan:
        st.markdown(f"- {item}")
    st.subheader("Risk assessment")
    for item in report.risk_assessment:
        st.markdown(f"- {item}")
    st.caption(report.disclaimer)


if __name__ == "__main__":
    main()
