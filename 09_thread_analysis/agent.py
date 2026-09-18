"""Defensive cybersecurity thread analysis agent."""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MAX_THREAD_LENGTH = 100_000

MITRE_TECHNIQUE_RULES = [
    {
        "id": "T1566",
        "name": "Phishing",
        "tactic": "Initial Access",
        "keywords": ("phishing", "spearphishing", "malicious attachment", "credential harvest"),
        "detection": "Review email gateway events, attachment detonation, and user-reported messages.",
    },
    {
        "id": "T1059",
        "name": "Command and Scripting Interpreter",
        "tactic": "Execution",
        "keywords": ("powershell", "cmd.exe", "command shell", "scripting", "bash"),
        "detection": "Correlate process creation with command-line logging and parent-child process relationships.",
    },
    {
        "id": "T1071.001",
        "name": "Web Protocols",
        "tactic": "Command and Control",
        "keywords": ("http beacon", "https beacon", "web shell", "c2 over https", "callback"),
        "detection": "Use proxy, DNS, and network telemetry to identify unusual periodic outbound connections.",
    },
    {
        "id": "T1078",
        "name": "Valid Accounts",
        "tactic": "Defense Evasion",
        "keywords": ("stolen credentials", "valid account", "account takeover", "impossible travel"),
        "detection": "Review authentication anomalies, MFA events, geolocation, and device history.",
    },
    {
        "id": "T1110",
        "name": "Brute Force",
        "tactic": "Credential Access",
        "keywords": ("brute force", "password spray", "credential stuffing", "multiple failed logins"),
        "detection": "Aggregate failed authentication events by account, source, and time window.",
    },
]

SYSTEM_PROMPT = """You are a defensive cybersecurity analyst. Analyze the supplied incident or threat-intelligence thread without executing commands or visiting indicators. Return a structured Markdown report with:
1. Executive Summary
2. Severity and Confidence
3. Timeline
4. Indicators of Compromise (IPs, domains, URLs, hashes, emails)
5. MITRE ATT&CK techniques when supported by evidence
6. Key Findings
7. Recommended Defensive Actions
Clearly label assumptions and never invent evidence."""


@dataclass(frozen=True)
class AnalysisResult:
    """Structured result returned by the analyzer."""

    report: str
    indicators: dict[str, list[str]]
    attack_mappings: list[dict[str, object]]
    mode: str


def validate_thread(thread: str) -> str:
    """Validate and normalize a cybersecurity thread before analysis."""

    if not isinstance(thread, str) or not thread.strip():
        raise ValueError("Thread content cannot be empty.")
    if len(thread) > MAX_THREAD_LENGTH:
        raise ValueError(f"Thread content cannot exceed {MAX_THREAD_LENGTH:,} characters.")
    return thread.strip()


def extract_indicators(thread: str) -> dict[str, list[str]]:
    """Extract common indicators locally without contacting them."""

    patterns = {
        "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "domain": r"\b(?:[A-Za-z0-9-]+\.)+(?:com|net|org|io|ru|cn|info|biz)\b",
        "sha256": r"\b[a-fA-F0-9]{64}\b",
        "md5": r"\b[a-fA-F0-9]{32}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "url": r"https?://[^\s)]+",
    }
    return {name: sorted(set(re.findall(pattern, thread))) for name, pattern in patterns.items()}


def map_mitre_attack(thread: str) -> list[dict[str, object]]:
    """Map explicit thread language to conservative MITRE ATT&CK candidates."""

    lowered_thread = thread.lower()
    mappings = []
    for rule in MITRE_TECHNIQUE_RULES:
        evidence = [keyword for keyword in rule["keywords"] if keyword in lowered_thread]
        if evidence:
            mappings.append(
                {
                    "technique_id": rule["id"],
                    "technique": rule["name"],
                    "tactic": rule["tactic"],
                    "evidence": evidence,
                    "detection": rule["detection"],
                }
            )
    return mappings


def build_analysis_messages(thread: str, indicators: dict[str, list[str]], attack_mappings: list[dict[str, object]]) -> list:
    """Build a bounded prompt containing thread evidence and local indicators."""

    from langchain_core.messages import HumanMessage, SystemMessage

    evidence = json.dumps(
        {"indicators": indicators, "mitre_attack_candidates": attack_mappings},
        indent=2,
    )
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Thread:\n\n{thread}\n\nLocal defensive evidence:\n{evidence}"),
    ]


def analyze_thread(thread: str, demo: bool = False) -> AnalysisResult:
    """Analyze a thread locally or with OpenAI and return defensive findings."""

    clean_thread = validate_thread(thread)
    indicators = extract_indicators(clean_thread)
    attack_mappings = map_mitre_attack(clean_thread)
    if demo:
        indicator_count = sum(len(values) for values in indicators.values())
        report = (
            "## Executive Summary\n"
            "Offline demo analysis completed. Review the extracted indicators and validate them with approved security tooling.\n\n"
            f"## Findings\n- Extracted indicator values: {indicator_count}\n"
            "- No indicators were contacted or executed.\n\n"
            "## MITRE ATT&CK Candidates\n"
            + ("\n".join(
                f"- **{mapping['technique_id']} {mapping['technique']}** ({mapping['tactic']}) "
                f"based on: {', '.join(mapping['evidence'])}"
                for mapping in attack_mappings
            ) or "- No ATT&CK candidate matched explicit evidence.")
            + "\n\n## Recommended Defensive Actions\n"
            "- Preserve the original thread and record chain of custody.\n"
            "- Enrich indicators only in an approved sandbox or threat-intelligence platform.\n"
            "- Search authorized logs for matching activity and begin containment according to your incident plan."
        )
        return AnalysisResult(report, indicators, attack_mappings, "demo")

    from langchain_openai import ChatOpenAI

    response = ChatOpenAI(model="gpt-4o-mini", temperature=0).invoke(
        build_analysis_messages(clean_thread, indicators, attack_mappings)
    )
    return AnalysisResult(response.content, indicators, attack_mappings, "openai")


def main() -> None:
    """Run the thread analyzer from the command line."""

    parser = argparse.ArgumentParser(description="Defensive Cybersecurity Thread Analyzer")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Thread content")
    source.add_argument("--file", help="UTF-8 thread file")
    parser.add_argument("--demo", action="store_true", help="Use offline analysis without an API call")
    args = parser.parse_args()

    try:
        thread = args.text or Path(args.file).read_text(encoding="utf-8")
        result = analyze_thread(thread, demo=args.demo)
    except (OSError, ValueError, ImportError) as error:
        parser.error(str(error))

    print(result.report)
    print("\nIndicators:")
    print(json.dumps(result.indicators, indent=2))
    print("\nMITRE ATT&CK candidates:")
    print(json.dumps(result.attack_mappings, indent=2))


if __name__ == "__main__":
    main()
