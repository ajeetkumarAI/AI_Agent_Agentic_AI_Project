"""Streamlit interface for the multi-format Document Q&A Agent."""

import tempfile
from pathlib import Path

import streamlit as st

from agent import SUPPORTED_EXTENSIONS, answer_question, build_index, create_chat_engine


def initialize_state() -> None:
    """Create the session values used by the document and chat workflow."""

    defaults = {
        "index": None,
        "chat_engine": None,
        "document_name": None,
        "messages": [],
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def index_uploaded_document(uploaded_file) -> None:
    """Save an upload temporarily and build its searchable index."""

    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        temporary_file.write(uploaded_file.getvalue())
        temporary_path = Path(temporary_file.name)

    try:
        st.session_state.index = build_index(str(temporary_path))
        st.session_state.chat_engine = create_chat_engine(st.session_state.index)
        st.session_state.document_name = uploaded_file.name
        st.session_state.messages = []
    finally:
        temporary_path.unlink(missing_ok=True)


def render_sources(sources: list[dict], document_name: str) -> None:
    """Render the document and chunk metadata used to produce an answer."""

    with st.expander(f"Sources ({len(sources)} chunks)"):
        if not sources:
            st.info("No source chunks were returned.")
            return

        for source in sources:
            source_name = source.get("document_name") or document_name
            title = source.get("title") or source_name
            page = source.get("page")
            page_text = f" | page {page}" if page else ""
            st.markdown(
                f"**Chunk {source['chunk_number']}** | **{title}** | "
                f"`{source_name}`{page_text}"
            )
            preview = source.get("text", "")
            st.caption(preview[:500] + ("..." if len(preview) > 500 else ""))


def render_sidebar() -> None:
    """Render upload controls and index the selected document on request."""

    with st.sidebar:
        st.header("Document")
        allowed_types = sorted(extension.removeprefix(".") for extension in SUPPORTED_EXTENSIONS)
        uploaded_file = st.file_uploader(
            "Upload a document",
            type=allowed_types,
            help="Supported: PDF, DOCX, TXT, Markdown, CSV, JSON, and HTML.",
        )

        if st.button("Build index", type="primary", disabled=uploaded_file is None):
            with st.spinner("Loading and indexing document..."):
                try:
                    index_uploaded_document(uploaded_file)
                except Exception as error:
                    st.error(f"Could not index document: {error}")

        if st.session_state.document_name:
            st.success(f"Ready: {st.session_state.document_name}")


def render_single_question() -> None:
    """Render a form for one question and show source metadata."""

    with st.form("single_question_form"):
        question = st.text_input("Ask one question", placeholder="What is the main finding?")
        submitted = st.form_submit_button("Get answer")

    if submitted and question.strip():
        with st.spinner("Searching the document..."):
            try:
                answer, sources = answer_question(
                    st.session_state.index,
                    question.strip(),
                    st.session_state.document_name,
                )
            except Exception as error:
                st.error(f"Question failed: {error}")
                return
        st.markdown(answer)
        render_sources(sources, st.session_state.document_name)
    elif submitted:
        st.warning("Enter a question first.")


def render_chat() -> None:
    """Render the follow-up chat history and accept the next question."""

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a follow-up question")
    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.chat_engine.chat(question)
                answer = response.response
            except Exception as error:
                answer = f"Question failed: {error}"
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})


def main() -> None:
    """Render the document upload, single-question, and chat experience."""

    st.set_page_config(page_title="Document Q&A Agent", page_icon="📚", layout="wide")
    initialize_state()

    st.title("Document Q&A Agent")
    st.caption("Upload a document, build an index, and ask questions about its content.")
    render_sidebar()

    if st.session_state.index is None:
        st.info("Upload a document in the sidebar and select Build index to begin.")
        return

    st.subheader(f"Questions about {st.session_state.document_name}")
    single_tab, chat_tab = st.tabs(["Single question", "Follow-up chat"])
    with single_tab:
        render_single_question()
    with chat_tab:
        render_chat()


if __name__ == "__main__":
    main()