"""Prompt for the paper-execution planning role."""

EXECUTION_ANALYST_PROMPT = """
Create a paper-trading execution checklist for the supplied scenario.
Cover order assumptions, liquidity, slippage, review timing, cancellation conditions,
and maximum-risk documentation. Never connect to a broker or place an order.
"""
