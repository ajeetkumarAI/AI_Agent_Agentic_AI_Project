"""Defensive customer-support agent with optional RAG and escalation routing."""

import argparse
import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

SAMPLE_KB = [
    "CloudSync Pro syncs across 5 devices with 1TB storage, offline mode, and 30-day version history.",
    "Basic costs $9/mo for 100GB and 2 devices. Pro costs $19/mo for 1TB and 5 devices. Business costs $49/mo for 5TB and unlimited devices.",
    "Cancel from Account > Subscription > Cancel. Refunds are available within 14 days of the charge.",
    "Reset a password from the login page using Forgot Password. The reset link expires in 1 hour.",
    "For sync issues, check the internet connection, update the app, and sign out and in again.",
    "CloudSync Pro supports Windows 10+, macOS 12+, iOS 15+, Android 10+, and Linux Beta.",
]
ESCALATION_TERMS = ("refund", "lawsuit", "fraud", "data loss", "billing error", "charge dispute", "account takeover")


@dataclass
class SupportState:
    """Conversation state passed between support operations."""

    history: list[dict[str, str]] = field(default_factory=list)
    last_context: list[str] = field(default_factory=list)
    last_response: str = ""
    escalated: bool = False


@dataclass(frozen=True)
class SupportResult:
    """One support response and its routing metadata."""

    response: str
    escalated: bool
    case_id: str | None
    context: list[str]


class SupportService:
    """Answer CloudSync Pro questions with local context and optional OpenAI."""

    def __init__(self, kb_texts: list[str] | None = None, demo: bool = False):
        self.kb_texts = kb_texts or SAMPLE_KB
        self.demo = demo
        self._vectorstore = None

    def retrieve(self, question: str, limit: int = 3) -> list[str]:
        """Return the most relevant local knowledge-base entries."""

        terms = {word.lower() for word in question.split() if len(word) > 2}
        ranked = sorted(
            self.kb_texts,
            key=lambda text: sum(term in text.lower() for term in terms),
            reverse=True,
        )
        return ranked[:limit]

    def should_escalate(self, question: str) -> bool:
        """Route billing, fraud, legal, account-takeover, and data-loss cases."""

        lowered = question.lower()
        return any(term in lowered for term in ESCALATION_TERMS)

    def case_id(self, question: str) -> str:
        """Create a stable non-sensitive case identifier from the question."""

        digest = hashlib.sha256(question.strip().encode("utf-8")).hexdigest()[:8].upper()
        return f"CS-{digest}"

    def respond(self, question: str, state: SupportState) -> SupportResult:
        """Answer one question and update explicit conversation state."""

        clean_question = question.strip()
        if not clean_question:
            raise ValueError("Question cannot be empty.")
        context = self.retrieve(clean_question)
        escalated = self.should_escalate(clean_question)
        case_id = self.case_id(clean_question) if escalated else None

        if escalated:
            answer = (
                "I understand this needs specialist attention. I have routed it "
                f"to senior support under case {case_id}. Please do not share "
                "additional payment credentials in chat."
            )
        elif self.demo or not os.getenv("OPENAI_API_KEY"):
            answer = self.demo_answer(clean_question, context)
        else:
            answer = self.llm_answer(clean_question, context, state.history)

        state.history.extend([
            {"role": "user", "content": clean_question},
            {"role": "assistant", "content": answer},
        ])
        state.last_context = context
        state.last_response = answer
        state.escalated = escalated
        return SupportResult(answer, escalated, case_id, context)

    def demo_answer(self, question: str, context: list[str]) -> str:
        """Give a transparent offline answer from the best local context."""

        if not context:
            return "I could not find that in the product knowledge base. Please contact support."
        return "Based on the CloudSync Pro knowledge base:\n\n" + "\n".join(f"- {item}" for item in context)

    def llm_answer(self, question: str, context: list[str], history: list[dict[str, str]]) -> str:
        """Generate a grounded answer with OpenAI when configured."""

        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI

        messages: list[Any] = [SystemMessage(content=(
            "You are a helpful CloudSync Pro support agent. Answer only from the "
            f"provided context. If unsure, say so. Context:\n{chr(10).join(context)}"
        ))]
        messages.extend(HumanMessage(content=item["content"]) if item["role"] == "user" else SystemMessage(content=item["content"]) for item in history[-6:])
        messages.append(HumanMessage(content=question))
        return str(ChatOpenAI(model="gpt-4o-mini", temperature=0.2).invoke(messages).content)


def load_kb_texts(kb_dir: str | None) -> list[str]:
    """Load UTF-8 Markdown/text knowledge-base files or use the sample KB."""

    if not kb_dir:
        return SAMPLE_KB
    root = Path(kb_dir)
    if not root.is_dir():
        raise ValueError(f"Knowledge base directory does not exist: {kb_dir}")
    paths = [path for path in sorted(root.rglob("*")) if path.is_file() and path.suffix.lower() in {".txt", ".md"}]
    if not paths:
        raise ValueError("No .txt or .md files found in the knowledge base directory.")
    return [path.read_text(encoding="utf-8") for path in paths]


def main() -> None:
    """Run the support agent in an interactive Command Prompt session."""

    parser = argparse.ArgumentParser(description="CloudSync Pro Customer Support Agent")
    parser.add_argument("--kb-dir", help="Directory containing .txt or .md knowledge-base files")
    parser.add_argument("--demo", action="store_true", help="Use offline responses without OpenAI")
    args = parser.parse_args()
    try:
        service = SupportService(load_kb_texts(args.kb_dir), demo=args.demo)
    except ValueError as error:
        parser.error(str(error))
    state = SupportState()
    print("\nCloudSync Pro Support Agent. Type 'quit' to exit.\n")
    while True:
        question = input("Customer: ").strip()
        if question.lower() in {"quit", "exit", "q"}:
            break
        if not question:
            continue
        result = service.respond(question, state)
        marker = " [ESCALATED]" if result.escalated else ""
        print(f"\nAgent{marker}: {result.response}\n")


if __name__ == "__main__":
    main()
