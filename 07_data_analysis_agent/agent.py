"""Natural-language analysis of CSV and Excel data with pandas.

The pandas agent can execute model-generated Python code. Use it only with
trusted prompts and non-sensitive data, and opt in explicitly at runtime.
"""

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI


load_dotenv()

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
DEFAULT_SAMPLE_FILE = "sample_data.csv"
MAX_ROWS = 100_000


def create_sample_data(path: str | Path) -> pd.DataFrame:
    """Create a deterministic sample sales dataset and save it as CSV."""

    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    products = ["Laptop", "Phone", "Tablet", "Monitor", "Keyboard"]
    regions = ["North", "South", "East", "West"]
    start = date(2024, 1, 1)
    rows = []
    for _ in range(200):
        current_date = start + timedelta(days=random.randint(0, 364))
        quantity = random.randint(1, 20)
        unit_price = round(random.uniform(50, 2000), 2)
        rows.append(
            {
                "date": current_date.isoformat(),
                "product": random.choice(products),
                "region": random.choice(regions),
                "quantity": quantity,
                "unit_price": unit_price,
                "revenue": round(quantity * unit_price, 2),
            }
        )
    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(destination, index=False)
    return dataframe


def validate_file_path(file_path: str | Path) -> Path:
    """Validate that a data file exists and uses a supported extension."""

    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Data file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Supported types: {supported}")
    return path


def load_data(file_path: str | Path) -> pd.DataFrame:
    """Load a CSV or Excel file and enforce a bounded row count."""

    path = validate_file_path(file_path)
    dataframe = pd.read_excel(path) if path.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(path)
    if dataframe.empty:
        raise ValueError(f"Data file contains no rows: {path.name}")
    if len(dataframe) > MAX_ROWS:
        raise ValueError(f"Data file exceeds the {MAX_ROWS:,}-row limit")
    return dataframe


def build_analyzer(dataframe: pd.DataFrame, allow_dangerous_code: bool = False):
    """Build a pandas analyzer after explicit dangerous-code opt-in."""

    if not allow_dangerous_code:
        raise PermissionError(
            "Analysis requires explicit allow_dangerous_code=True because the "
            "pandas agent executes model-generated Python code."
        )

    
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return create_pandas_dataframe_agent(
        model,
        dataframe,
        verbose=False,
        allow_dangerous_code=True,
    )


def ask_data(analyzer, question: str) -> str:
    """Ask one natural-language question and return the formatted answer."""

    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Question cannot be empty.")
    return str(analyzer.invoke({"input": clean_question})["output"])


def main() -> None:
    """Parse CLI arguments and run one-question or interactive analysis."""

    parser = argparse.ArgumentParser(description="Natural-language Data Analysis Agent")
    parser.add_argument("--file", default=DEFAULT_SAMPLE_FILE, help="CSV or Excel file")
    parser.add_argument("--question", help="Ask one question and exit")
    parser.add_argument(
        "--allow-dangerous-code",
        action="store_true",
        help="Required opt-in for model-generated Python execution",
    )
    args = parser.parse_args()

    try:
        path = Path(args.file)
        if args.file == DEFAULT_SAMPLE_FILE and not path.exists():
            print("Creating sample sales dataset...")
            create_sample_data(path)
        dataframe = load_data(path)
        analyzer = build_analyzer(dataframe, args.allow_dangerous_code)
    except (FileNotFoundError, ValueError, PermissionError, ImportError) as error:
        parser.error(str(error))

    print(f"\nLoaded: {args.file} ({len(dataframe)} rows x {len(dataframe.columns)} columns)")
    print(f"Columns: {', '.join(map(str, dataframe.columns))}\n")

    if args.question:
        try:
            print(ask_data(analyzer, args.question))
        except Exception as error:
            parser.error(f"Analysis failed: {error}")
        return

    print("Data analysis agent ready. Type 'quit' to exit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in {"quit", "exit", "q"}:
            break
        if not question:
            continue
        try:
            print(f"\nAgent: {ask_data(analyzer, question)}\n")
        except Exception as error:
            print(f"\nAnalysis failed: {error}\n")


if __name__ == "__main__":
    main()
