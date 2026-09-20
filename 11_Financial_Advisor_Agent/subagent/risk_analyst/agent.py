"""Risk-assessment role definition."""

from .prompt import RISK_ANALYST_PROMPT

ROLE_NAME = "risk_analyst"
OUTPUT_KEY = "final_risk_assessment_output"


def role_spec() -> dict[str, str]:
    """Return metadata used by a coordinator or an ADK adapter."""

    return {"name": ROLE_NAME, "output_key": OUTPUT_KEY, "prompt": RISK_ANALYST_PROMPT}
