"""Educational trading-strategy role definition."""

from .prompt import TRADING_ANALYST_PROMPT

ROLE_NAME = "trading_analyst"
OUTPUT_KEY = "proposed_trading_strategies_output"


def role_spec() -> dict[str, str]:
    """Return metadata used by a coordinator or an ADK adapter."""

    return {"name": ROLE_NAME, "output_key": OUTPUT_KEY, "prompt": TRADING_ANALYST_PROMPT}
