"""Two-agent email drafting workflow built with CrewAI."""

import argparse

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CONTEXT = (
    "Follow up on our product demo from last Tuesday. "
    "They seemed interested but have not responded."
)
DEFAULT_TONE = "professional and friendly"
DEFAULT_RECIPIENT = "a potential client"
MAX_CONTEXT_LENGTH = 10_000


def validate_inputs(context: str, tone: str, recipient: str) -> tuple[str, str, str]:
    """Normalize and validate the information needed to draft an email."""

    values = {
        "context": context.strip(),
        "tone": tone.strip(),
        "recipient": recipient.strip(),
    }
    for name, value in values.items():
        if not value:
            raise ValueError(f"{name.capitalize()} cannot be empty.")
    if len(values["context"]) > MAX_CONTEXT_LENGTH:
        raise ValueError(f"Context cannot exceed {MAX_CONTEXT_LENGTH:,} characters.")
    return values["context"], values["tone"], values["recipient"]


def build_email_crew(context: str, tone: str, recipient: str):
    """Build the analyst and writer agents and connect their sequential tasks."""

    from crewai import Agent, Crew, Process, Task
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    analyst = Agent(
        role="Email Context Analyst",
        goal="Understand the context, extract key points, and define the email structure.",
        backstory="You are an expert business communication analyst who distills complex situations into clear requirements.",
        llm=llm,
        verbose=False,
    )
    writer = Agent(
        role="Professional Email Writer",
        goal="Draft clear, concise, and effective professional emails.",
        backstory="You specialize in business emails that are respectful, useful, and likely to get a response.",
        llm=llm,
        verbose=False,
    )

    # The writer receives the analyst's brief through task context.
    analyze_task = Task(
        description=(
            "Analyze this email requirement:\n"
            f"Context: {context}\nRecipient: {recipient}\nDesired tone: {tone}\n\n"
            "Extract the purpose, key points, call to action, and subject suggestion."
        ),
        agent=analyst,
        expected_output="A structured brief with purpose, key points, CTA, and subject suggestion.",
    )
    write_task = Task(
        description=(
            "Using the analysis, draft a complete professional email.\n"
            f"Tone: {tone}\nRecipient: {recipient}\n"
            "Include a subject line, greeting, concise body under 200 words, closing, and signature placeholder."
        ),
        agent=writer,
        expected_output="A complete formatted email ready to send.",
        context=[analyze_task],
    )
    return Crew(
        agents=[analyst, writer],
        tasks=[analyze_task, write_task],
        process=Process.sequential,
        verbose=False,
    )


def draft_email(context: str, tone: str = DEFAULT_TONE, recipient: str = DEFAULT_RECIPIENT) -> str:
    """Validate inputs, run the crew, and return the drafted email."""

    clean_context, clean_tone, clean_recipient = validate_inputs(context, tone, recipient)
    crew = build_email_crew(clean_context, clean_tone, clean_recipient)
    return str(crew.kickoff())


def main() -> None:
    """Parse CLI arguments and print one generated email draft."""

    parser = argparse.ArgumentParser(description="Email Drafting Agent")
    parser.add_argument("--context", default=DEFAULT_CONTEXT, help="Email context or purpose")
    parser.add_argument("--tone", default=DEFAULT_TONE, help="Desired email tone")
    parser.add_argument("--recipient", default=DEFAULT_RECIPIENT, help="Email recipient")
    args = parser.parse_args()

    try:
        email = draft_email(args.context, args.tone, args.recipient)
    except (ValueError, ImportError) as error:
        parser.error(str(error))

    print("\n" + "=" * 60)
    print("EMAIL DRAFT")
    print("=" * 60)
    print(email)


if __name__ == "__main__":
    main()
