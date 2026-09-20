"""Paper-execution planning role definition."""

from .prompt import EXECUTION_ANALYST_PROMPT

ROLE_NAME = "execution_analyst"
OUTPUT_KEY = "execution_plan_output"


def role_spec() -> dict[str, str]:
    """Return metadata used by a coordinator or an ADK adapter."""

    return {"name": ROLE_NAME, "output_key": OUTPUT_KEY, "prompt": EXECUTION_ANALYST_PROMPT}
