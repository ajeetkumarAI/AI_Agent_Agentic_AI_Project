"""Market-data analyst role definition."""

from .prompt import DATA_ANALYST_PROMPT

ROLE_NAME = "data_analyst"
OUTPUT_KEY = "market_data_analysis_output"


def role_spec() -> dict[str, str]:
    """Return metadata used by a coordinator or an ADK adapter."""

    return {"name": ROLE_NAME, "output_key": OUTPUT_KEY, "prompt": DATA_ANALYST_PROMPT}
