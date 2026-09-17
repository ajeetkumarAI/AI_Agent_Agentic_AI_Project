"""
Document Q&A Agent using LlamaIndex.

Loads a Document PDF or other documents docx, indexes it, and answers questions about its content.
Maintains conversation history for follow-up questions.

Usage:
    python agent.py --pdf path/to/document
    python agent.py --pdf report.pdf --question "What is the main finding?"
"""

import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

SUPPORTED_EXTENSIONS = {
    ".csv",
    ".docx",
    ".html",
    ".json",
    ".md",
    ".pdf",
    ".txt",
}


def validate_document_path(document_path: str) -> Path:
    """Validate a document path and return it as a Path object."""

    path = Path(document_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported document type '{path.suffix or '[no extension]'}'. "
            f"Supported types: {supported}"
        )
    return path


def build_index(document_path: str):
    """Load a supported document and build a searchable vector index."""

    path = validate_document_path(document_path)

    # Import the indexing stack only after local input validation succeeds.
    from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

    print(f"📄 Loading and indexing {path}...")
    reader = SimpleDirectoryReader(input_files=[str(path)])
    docs = reader.load_data()
    if not docs:
        raise ValueError(f"No readable content found in {path}")
    index = VectorStoreIndex.from_documents(docs)
    print(f"✅ Indexed {len(docs)} document chunk(s)")
    return index


def create_chat_engine(index):
    """Create a context-aware chat engine with conversation memory."""

    from llama_index.core.memory import ChatMemoryBuffer
    from llama_index.llms.openai import OpenAI

    llm = OpenAI(model="gpt-4o-mini", temperature=0)
    memory = ChatMemoryBuffer.from_defaults(token_limit=4096)
    return index.as_chat_engine(
        chat_mode="context",
        llm=llm,
        memory=memory,
        verbose=False,
    )


def answer_question(index, question: str, document_name: str | None = None) -> tuple[str, list[dict]]:
    """Answer a question and return the answer plus source metadata."""

    query_engine = index.as_query_engine(similarity_top_k=5)
    response = query_engine.query(question)
    sources = []
    for chunk_number, source_node in enumerate(getattr(response, "source_nodes", []), start=1):
        metadata = source_node.node.metadata or {}
        sources.append(
            {
                "chunk_number": chunk_number,
                "document_name": document_name or metadata.get("file_name", "Unknown document"),
                "title": metadata.get("title", document_name or metadata.get("file_name", "Untitled source")),
                "page": metadata.get("page_label", metadata.get("page_number")),
                "text": source_node.node.get_content().strip(),
            }
        )
    return response.response, sources


def interactive_qa(index, document_name: str) -> None:
    """Run an interactive follow-up question loop for an indexed document."""

    chat_engine = create_chat_engine(index)

    print(f"\n💬 Document Q&A Agent ready for {document_name}. Type 'quit' to exit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue
        response = chat_engine.chat(question)
        print(f"\nAgent: {response.response}\n")


def single_question(index, question: str) -> None:
    """Answer one question and report how many source chunks were referenced."""

    answer, sources = answer_question(index, question)
    print("\n" + "=" * 60)
    print("📋 ANSWER")
    print("=" * 60)
    print(answer)
    print(f"\n📚 Sources: {len(sources)} chunk(s) referenced")
    for source in sources:
        print(f"- {source['document_name']} | chunk {source['chunk_number']}")


def main() -> None:
    """Parse arguments, index a document, and start the selected Q&A mode."""

    parser = argparse.ArgumentParser(description="Document Q&A Agent")
    parser.add_argument(
        "--document",
        "--pdf",
        dest="document",
        required=True,
        help="Path to a PDF, DOCX, TXT, Markdown, CSV, JSON, or HTML file",
    )
    parser.add_argument("--question", help="Single question (omit for interactive mode)")
    args = parser.parse_args()

    try:
        index = build_index(args.document)
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    if args.question:
        single_question(index, args.question)
    else:
        interactive_qa(index, Path(args.document).name)


if __name__ == "__main__":
    main()