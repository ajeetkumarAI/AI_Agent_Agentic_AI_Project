"""Fail-closed PII sanitization client with CLI support."""

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONTEXT = "general"
CONTEXTS = {"general", "financial", "legal", "medical", "code"}
REDACTION = "[REDACTED]"
MAX_INPUT_LENGTH = 100_000


@dataclass(frozen=True)
class SanitizationResult:
    """Auditable result returned by a sanitization operation."""

    status: str
    sanitized_content: str
    safety_score: float | None
    risk_category: str
    entities: list[dict[str, Any]]
    tx_hash: str | None = None
    error: str | None = None


def validate_input(text: str, context: str = DEFAULT_CONTEXT) -> tuple[str, str]:
    """Validate text and context before processing."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Text cannot be empty.")
    clean_context = context.strip().lower()
    if clean_context not in CONTEXTS:
        raise ValueError(f"Context must be one of: {', '.join(sorted(CONTEXTS))}")
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(f"Text cannot exceed {MAX_INPUT_LENGTH:,} characters.")
    return text, clean_context


def redact_locally(text: str) -> SanitizationResult:
    """Redact common PII patterns locally for offline demos and tests."""

    patterns = [
        ("name", re.compile(r"(?i)(?<=\bname is )([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})")),
        ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
        ("api_key", re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{12,}\b")),
        ("phone", re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")),
    ]
    sanitized = text
    entities = []
    for entity_type, pattern in patterns:
        matches = pattern.findall(sanitized)
        if matches:
            sanitized = pattern.sub(REDACTION, sanitized)
            entities.extend({"type": entity_type, "category": "PRIVATE"} for _ in matches)
    return SanitizationResult(
        status="success",
        sanitized_content=sanitized,
        safety_score=1.0 if not entities else 0.6,
        risk_category="PRIVATE" if entities else "PUBLIC",
        entities=entities,
        tx_hash="LOCAL_DEMO",
    )


def _parse_response(payload: dict[str, Any]) -> SanitizationResult:
    """Normalize the documented or nested TrustBoost response shape."""

    data = payload.get("data", payload)
    sanitized = data.get("sanitized_content")
    if not isinstance(sanitized, str):
        raise ValueError("TrustBoost response did not contain sanitized_content.")
    return SanitizationResult(
        status=str(payload.get("status", "success")),
        sanitized_content=sanitized,
        safety_score=data.get("safety_score"),
        risk_category=str(data.get("risk_category", "UNKNOWN")),
        entities=data.get("entities", []),
        tx_hash=data.get("tx_hash"),
    )


def sanitize_text(
    text: str,
    context: str = DEFAULT_CONTEXT,
    api_url: str | None = None,
    api_key: str | None = None,
    tx_hash: str | None = None,
    demo: bool = False,
) -> SanitizationResult:
    """Sanitize text locally or through TrustBoost, failing closed on errors."""

    text, context = validate_input(text, context)
    if demo:
        return redact_locally(text)

    endpoint = api_url or os.getenv("TRUSTBOOST_API_URL")
    if not endpoint:
        return SanitizationResult(
            status="failed",
            sanitized_content=REDACTION,
            safety_score=0.0,
            risk_category="UNKNOWN",
            entities=[],
            error="TRUSTBOOST_API_URL is not configured.",
        )

    headers = {"Content-Type": "application/json"}
    token = api_key or os.getenv("TRUSTBOOST_API_KEY")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"text": text, "context": context}
    if tx_hash:
        payload["tx_hash"] = tx_hash
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        result = _parse_response(response.json())
        return result
    except (requests.RequestException, ValueError, TypeError) as error:
        # Never return input text after a remote failure.
        return SanitizationResult(
            status="failed",
            sanitized_content=REDACTION,
            safety_score=0.0,
            risk_category="UNKNOWN",
            entities=[],
            error=str(error),
        )


def sanitize_file(file_path: str, context: str = DEFAULT_CONTEXT, **kwargs) -> SanitizationResult:
    """Read a UTF-8 text file and sanitize its contents."""

    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return sanitize_text(path.read_text(encoding="utf-8"), context, **kwargs)


def result_to_dict(result: SanitizationResult) -> dict[str, Any]:
    """Convert a result into a JSON-friendly dictionary."""

    return {
        "status": result.status,
        "data": {
            "sanitized_content": result.sanitized_content,
            "safety_score": result.safety_score,
            "risk_category": result.risk_category,
            "entities": result.entities,
            "tx_hash": result.tx_hash,
        },
        "error": result.error,
    }


def main() -> None:
    """Parse CLI arguments and print a JSON sanitization result."""

    parser = argparse.ArgumentParser(description="Fail-closed PII Sanitization Agent")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Text to sanitize")
    source.add_argument("--file", help="UTF-8 text file to sanitize")
    parser.add_argument("--context", default=DEFAULT_CONTEXT, choices=sorted(CONTEXTS))
    parser.add_argument("--tx-hash", help="Optional TrustBoost payment transaction hash")
    parser.add_argument("--demo", action="store_true", help="Use local regex demo mode")
    args = parser.parse_args()

    try:
        result = sanitize_text(args.text, args.context, tx_hash=args.tx_hash, demo=True) if args.text and args.demo else None
        if args.file:
            result = sanitize_file(args.file, args.context, tx_hash=args.tx_hash, demo=args.demo)
        elif result is None:
            result = sanitize_text(args.text, args.context, tx_hash=args.tx_hash)
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as error:
        parser.error(str(error))
    print(__import__("json").dumps(result_to_dict(result), indent=2))


if __name__ == "__main__":
    main()
