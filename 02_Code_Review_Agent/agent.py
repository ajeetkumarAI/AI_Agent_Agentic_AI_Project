"""
Code Review Agent using LangChain.

Reviews Python code for bugs, security issues, style violations, and
suggests improvements. Accepts a file path or inline code snippet.

Usage:
    python agent.py --file path/to/code.py
    python agent.py --code "def add(a,b): return a+b"
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv()

SYSTEM_PROMPT = """You are an expert code reviewer. Analyze the provided code and return a structured review covering:

1. **Bugs & Correctness** — logic errors, edge cases, exception handling
2. **Security Issues** — injection risks, secrets exposure, unsafe operations
3. **Performance** — inefficiencies, unnecessary computation, memory issues
4. **Code Style** — PEP 8 violations, naming conventions, readability
5. **Improvements** — refactoring suggestions, better patterns

Format: Use markdown. Rate overall quality as: 🟢 Good / 🟡 Needs Work / 🔴 Critical Issues."""
MAX_CODE_LENGTH = 100_000


def build_review_messages(code: str, language: str) -> list:
    """Build the system and user messages sent to the review model."""

    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Review this {language} code:\n\n```{language}\n{code}\n```"),
    ]


def create_reviewer() -> ChatOpenAI:
    """Create the configured chat model used for code reviews."""

    return ChatOpenAI(model="gpt-4o", temperature=0)


def validate_code(code: str) -> str:
    """Validate and normalize code input before sending it to the API."""

    normalized_code = code.strip()
    if not normalized_code:
        raise ValueError("Code to review cannot be empty.")
    if len(normalized_code) > MAX_CODE_LENGTH:
        raise ValueError(
            f"Code is too large to review ({len(normalized_code):,} characters). "
            f"Maximum supported size is {MAX_CODE_LENGTH:,} characters."
        )
    return normalized_code


def read_code_file(file_path: str) -> str:
    """Read UTF-8 source code from a file and validate its contents."""

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Code file not found: {path}")
    return validate_code(path.read_text(encoding="utf-8"))


def review_code(code: str, language: str = "python") -> str:
    """Review source code and return a structured Markdown report."""

    validated_code = validate_code(code)
    response = create_reviewer().invoke(build_review_messages(validated_code, language))
    return response.content


def main() -> None:
    """Parse CLI arguments, run a review, and print the report."""

    parser = argparse.ArgumentParser(description="Code Review Agent")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to file to review")
    group.add_argument("--code", help="Inline code snippet to review")
    parser.add_argument("--language", default="python", help="Programming language (default: python)")
    args = parser.parse_args()

    if args.file:
        try:
            code = read_code_file(args.file)
        except (FileNotFoundError, UnicodeDecodeError, ValueError) as error:
            parser.error(str(error))
        print(f"\n🔍 Reviewing: {args.file}\n")
    else:
        try:
            code = validate_code(args.code)
        except ValueError as error:
            parser.error(str(error))
        print(f"\n🔍 Reviewing inline code snippet\n")

    review = review_code(code, args.language)

    print("=" * 60)
    print("📋 CODE REVIEW")
    print("=" * 60)
    print(review)


if __name__ == "__main__":
    main()