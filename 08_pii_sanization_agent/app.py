"""Streamlit interface for the PII Sanitization Agent."""

import streamlit as st

from agent import CONTEXTS, result_to_dict, sanitize_text


def main() -> None:
    """Render text/context controls and a redacted result."""

    st.set_page_config(page_title="PII Sanitization Agent", page_icon="🛡️", layout="wide")
    st.title("PII Sanitization Agent")
    st.caption("Redact sensitive data before it reaches an LLM or external API.")

    text = st.text_area("Text to sanitize", height=220, placeholder="Paste text containing emails, phones, or secrets.")
    context = st.selectbox("Context", sorted(CONTEXTS))
    demo = st.checkbox("Use local demo mode", value=True, help="Uses deterministic local redaction without an API call.")

    if st.button("Sanitize text", type="primary"):
        if not text.strip():
            st.warning("Enter text before selecting Sanitize text.")
            return
        with st.spinner("Sanitizing..."):
            result = sanitize_text(text, context, demo=demo)
        if result.status == "success":
            st.subheader("Sanitized text")
            st.code(result.sanitized_content)
            st.metric("Safety score", result.safety_score)
            st.write(f"Risk category: {result.risk_category}")
            with st.expander("Audit details"):
                st.json(result_to_dict(result))
        else:
            st.error(f"Sanitization failed closed: {result.error}")
            st.code(result.sanitized_content)


if __name__ == "__main__":
    main()
