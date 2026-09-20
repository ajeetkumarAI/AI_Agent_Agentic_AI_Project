"""Educational financial planning assistant.

This local implementation creates an evidence-aware planning template. It does
not fetch live prices, place orders, manage accounts, or provide financial advice.
"""

import argparse
from dataclasses import asdict, dataclass
import json
import re
from datetime import datetime, timezone

DISCLAIMER = (
    "Educational and informational purposes only. This is not financial advice "
    "or a recommendation to buy or sell securities. Consult a qualified adviser."
)
RISK_LEVELS = {"very conservative", "conservative", "balanced", "aggressive", "very aggressive"}
HORIZONS = {"intraday", "short-term", "medium-term", "long-term"}


@dataclass(frozen=True)
class AdvisorRequest:
    """Validated inputs for one educational planning request."""

    ticker: str
    risk_attitude: str
    investment_period: str
    execution_preferences: str


@dataclass(frozen=True)
class AdvisorReport:
    """Structured educational report returned by the local workflow."""

    disclaimer: str
    market_analysis: str
    strategy_options: list[str]
    execution_plan: list[str]
    risk_assessment: list[str]


@dataclass(frozen=True)
class MarketSnapshot:
    """Read-only market data returned by Yahoo Finance."""

    ticker: str
    latest_price: float
    daily_change_percent: float | None
    period_high: float
    period_low: float
    latest_volume: int
    as_of: str
    source: str = "Yahoo Finance via yfinance"


def validate_request(ticker: str, risk_attitude: str, investment_period: str, execution_preferences: str = "") -> AdvisorRequest:
    """Validate ticker, risk attitude, horizon, and execution preferences."""

    clean_ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9.\-]{1,10}", clean_ticker):
        raise ValueError("Ticker must contain 1-10 letters, numbers, dots, or hyphens.")
    clean_risk = risk_attitude.strip().lower()
    if clean_risk not in RISK_LEVELS:
        raise ValueError(f"Risk attitude must be one of: {', '.join(sorted(RISK_LEVELS))}.")
    clean_horizon = investment_period.strip().lower()
    if clean_horizon not in HORIZONS:
        raise ValueError(f"Investment period must be one of: {', '.join(sorted(HORIZONS))}.")
    return AdvisorRequest(clean_ticker, clean_risk, clean_horizon, execution_preferences.strip())


def fetch_market_snapshot(ticker: str) -> MarketSnapshot:
    """Fetch recent daily market data without placing trades or using a broker."""

    try:
        import yfinance as yf

        history = yf.Ticker(ticker).history(period="1mo", interval="1d", auto_adjust=False)
    except Exception as error:
        raise RuntimeError(f"Yahoo Finance data request failed: {error}") from error
    if history.empty or "Close" not in history or "Volume" not in history:
        raise RuntimeError(f"No recent Yahoo Finance data found for {ticker}.")
    closes = history["Close"].dropna()
    volumes = history["Volume"].dropna()
    if closes.empty:
        raise RuntimeError(f"No closing price found for {ticker}.")
    latest_price = float(closes.iloc[-1])
    previous_price = float(closes.iloc[-2]) if len(closes) > 1 else None
    daily_change = ((latest_price - previous_price) / previous_price * 100) if previous_price else None
    return MarketSnapshot(
        ticker=ticker,
        latest_price=latest_price,
        daily_change_percent=daily_change,
        period_high=float(closes.max()),
        period_low=float(closes.min()),
        latest_volume=int(volumes.iloc[-1]),
        as_of=datetime.now(timezone.utc).isoformat(),
    )


def create_report(request: AdvisorRequest, snapshot: MarketSnapshot | None = None, market_error: str | None = None) -> AdvisorReport:
    """Create a transparent, non-personalized educational planning report."""

    if snapshot:
        change = f"{snapshot.daily_change_percent:+.2f}%" if snapshot.daily_change_percent is not None else "unavailable"
        market_analysis = (
            f"Yahoo Finance snapshot for {snapshot.ticker}: latest close ${snapshot.latest_price:,.2f}; "
            f"daily change {change}; 1-month range ${snapshot.period_low:,.2f}-${snapshot.period_high:,.2f}; "
            f"latest volume {snapshot.latest_volume:,}; retrieved {snapshot.as_of}. "
            "This is market context, not a valuation or recommendation."
        )
    else:
        market_analysis = (
            f"Live market data was unavailable for {request.ticker}: {market_error or 'no snapshot requested'}. "
            "Verify price, filings, valuation, liquidity, and current news from authoritative sources before acting."
        )
    strategy_options = [
        f"{request.investment_period.title()} observation plan: define entry assumptions, invalidation conditions, and review dates.",
        "Diversified, position-sized exposure may reduce concentration risk; do not infer a target allocation from this report.",
        "Compare the thesis with a passive benchmark and record what evidence would change your view.",
    ]
    execution_plan = [
        "Use a paper-trading or simulation workflow first.",
        "Document order type, maximum loss, liquidity assumptions, and cancellation conditions before any independent decision.",
        f"Respect the stated {request.risk_attitude} risk attitude and {request.investment_period} horizon; preferences: {request.execution_preferences or 'none provided'}.",
        "This tool does not connect to brokers or place orders.",
    ]
    risk_assessment = [
        "Market, volatility, liquidity, gap, currency, regulatory, operational, and model risks remain.",
        "AI-generated analysis may be incomplete, stale, or wrong; independently verify every material fact.",
        "Never use borrowed money or risk funds needed for essential expenses based on this output.",
    ]
    return AdvisorReport(DISCLAIMER, market_analysis, strategy_options, execution_plan, risk_assessment)


def plan_financial_request(ticker: str, risk_attitude: str, investment_period: str, execution_preferences: str = "") -> AdvisorReport:
    """Validate a request, fetch read-only market context, and report safely."""

    request = validate_request(ticker, risk_attitude, investment_period, execution_preferences)
    try:
        snapshot = fetch_market_snapshot(request.ticker)
        return create_report(request, snapshot=snapshot)
    except RuntimeError as error:
        return create_report(request, market_error=str(error))


def main() -> None:
    """Run the educational advisor from Command Prompt."""

    parser = argparse.ArgumentParser(description="Educational Financial Advisor")
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--risk", default="balanced", choices=sorted(RISK_LEVELS))
    parser.add_argument("--period", default="long-term", choices=sorted(HORIZONS))
    parser.add_argument("--preferences", default="")
    args = parser.parse_args()
    try:
        report = plan_financial_request(args.ticker, args.risk, args.period, args.preferences)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
