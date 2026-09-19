"""Streamlit interface for CloudSync Pro customer support."""

import streamlit as st

from agent import SupportService, SupportState, load_kb_texts


def main() -> None:
    """Render a support chat with visible escalation status and context."""

    st.set_page_config(page_title="Customer Support Agent", page_icon="🎧", layout="wide")
    st.title("Customer Support Agent")
    st.caption("CloudSync Pro support with grounded answers and escalation routing.")
    st.session_state.setdefault("state", SupportState())
    st.session_state.setdefault("messages", [])

    with st.sidebar:
        demo = st.checkbox("Use offline demo mode", value=True)
        kb_dir = st.text_input("Knowledge base folder", placeholder="Optional path to .txt/.md files")
        if st.button("Reset conversation"):
            st.session_state.state = SupportState()
            st.session_state.messages = []
            st.rerun()

    service = SupportService(load_kb_texts(kb_dir or None), demo=demo)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("How can we help?")
    if not question:
        st.info("Ask about pricing, passwords, syncing, platforms, or cancellation.")
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Reviewing your request..."):
            try:
                result = service.respond(question, st.session_state.state)
                st.markdown(result.response)
                if result.escalated:
                    st.warning(f"Escalated case: {result.case_id}")
            except Exception as error:
                st.error(f"Support request failed: {error}")
                return
    st.session_state.messages.append({"role": "assistant", "content": result.response})


if __name__ == "__main__":
    main()
