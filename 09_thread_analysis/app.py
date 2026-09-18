"""Streamlit UI for defensive cybersecurity thread analysis."""

import streamlit as st

from agent import analyze_thread, extract_indicators


def main() -> None:
    """Render thread input, defensive analysis, and extracted indicators."""

    st.set_page_config(page_title="Cybersecurity Thread Analysis", page_icon="🛡️", layout="wide")
    st.title("Cybersecurity Thread Analysis")
    st.caption("Analyze incident or threat-intelligence text without contacting indicators.")

    thread = st.text_area("Thread content", height=320, placeholder="Paste an incident response or threat-intelligence thread.")
    demo = st.checkbox("Use offline demo mode", value=True)
    if st.button("Analyze thread", type="primary"):
        if not thread.strip():
            st.warning("Paste thread content before selecting Analyze thread.")
            return
        with st.spinner("Analyzing defensively..."):
            try:
                result = analyze_thread(thread, demo=demo)
            except Exception as error:
                st.error(f"Analysis failed: {error}")
                return
        st.subheader("Analysis")
        st.markdown(result.report)
        with st.expander("Extracted indicators"):
            st.json(result.indicators)
            st.info("Indicators were extracted only. The application does not contact or execute them.")
        with st.expander("MITRE ATT&CK candidates"):
            if result.attack_mappings:
                st.json(result.attack_mappings)
            else:
                st.info("No ATT&CK candidate matched explicit evidence in the thread.")


if __name__ == "__main__":
    main()
