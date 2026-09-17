"""Streamlit user interface for the web research agent."""

import streamlit as st

from agent import build_graph


DEFAULT_QUERY = "latest trends in AI and agentic AI"


@st.cache_resource
def get_agent():
    """Build the research graph once and reuse it across Streamlit reruns."""

    return build_graph()


def main() -> None:
    """Render the research form and display the generated report."""

    st.set_page_config(page_title="Web Research Agent", page_icon="🔎", layout="wide")
    st.title("Web Research Agent")
    st.caption("Search the web, then turn the findings into a concise research report.")

    with st.form("research_form"):
        query = st.text_area(
            "Research query",
            value=DEFAULT_QUERY,
            height=100,
            placeholder="What would you like to research?",
        )
        submitted = st.form_submit_button("Research", type="primary")

    if not submitted:
        st.info("Enter a question and select Research to begin.")
        return

    query = query.strip()
    if not query:
        st.warning("Please enter a research query.")
        return

    with st.spinner("Searching the web and synthesizing findings..."):
        try:
            result = get_agent().invoke(
                {
                    "query": query,
                    "messages": [],
                    "search_results": [],
                    "report": "",
                }
            )
        except Exception as error:
            st.error(f"Research failed: {error}")
            return

    st.subheader("Research report")
    st.markdown(result["report"])

    # Keep source links available without interrupting the report reading flow.
    with st.expander("Sources"):
        sources = result.get("search_results", [])
        if not sources:
            st.write("No sources were returned.")
        for source in sources:
            title = source.get("title", "Untitled source")
            url = source.get("url")
            if url:
                st.markdown(f"- [{title}]({url})")
            else:
                st.write(title)


if __name__ == "__main__":
    main()