"""Streamlit interface for the Data Analysis Agent."""

import tempfile
from pathlib import Path

import streamlit as st

from agent import ask_data, build_analyzer, create_sample_data, load_data


def initialize_state() -> None:
    """Initialize the dataset and analyzer held across Streamlit reruns."""

    st.session_state.setdefault("dataframe", None)
    st.session_state.setdefault("analyzer", None)
    st.session_state.setdefault("file_name", None)


def load_uploaded_file(uploaded_file):
    """Save an uploaded data file temporarily and load it with pandas."""

    suffix = Path(uploaded_file.name).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
        temporary_file.write(uploaded_file.getvalue())
        temporary_path = Path(temporary_file.name)
    try:
        return load_data(temporary_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def render_sidebar() -> None:
    """Render dataset selection and explicit code-execution consent."""

    with st.sidebar:
        st.header("Dataset")
        uploaded_file = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
        allow_code = st.checkbox(
            "Allow model-generated Python code",
            help="Required because the pandas agent executes generated code locally.",
        )

        if st.button("Use demo data", type="primary"):
            with st.spinner("Creating sample sales data..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temporary_file:
                    temporary_path = Path(temporary_file.name)
                try:
                    st.session_state.dataframe = create_sample_data(temporary_path)
                    st.session_state.file_name = "sample_data.csv"
                finally:
                    temporary_path.unlink(missing_ok=True)
                st.session_state.analyzer = None

        if uploaded_file is not None and st.button("Load uploaded data"):
            with st.spinner("Loading dataset..."):
                try:
                    st.session_state.dataframe = load_uploaded_file(uploaded_file)
                    st.session_state.file_name = uploaded_file.name
                    st.session_state.analyzer = None
                except Exception as error:
                    st.error(f"Could not load data: {error}")

        if st.session_state.file_name:
            st.success(f"Loaded: {st.session_state.file_name}")

        if st.session_state.dataframe is not None:
            if st.button("Enable analysis"):
                if not allow_code:
                    st.warning("Check the code-execution consent box first.")
                else:
                    with st.spinner("Preparing analyzer..."):
                        st.session_state.analyzer = build_analyzer(
                            st.session_state.dataframe,
                            allow_dangerous_code=True,
                        )


def main() -> None:
    """Render the data upload, preview, and natural-language analysis UI."""

    st.set_page_config(page_title="Data Analysis Agent", page_icon="📈", layout="wide")
    initialize_state()
    st.title("Data Analysis Agent")
    st.caption("Upload tabular data and ask analytical questions in plain English.")
    render_sidebar()

    dataframe = st.session_state.dataframe
    if dataframe is None:
        st.info("Choose Use demo data or load a CSV/Excel file from the sidebar.")
        return

    st.subheader("Dataset preview")
    st.dataframe(dataframe.head(10), use_container_width=True)
    st.caption(f"{len(dataframe):,} rows x {len(dataframe.columns)} columns")

    question = st.text_area(
        "Question",
        placeholder="What is the total revenue by product?",
        height=100,
    )
    if st.button("Analyze", type="primary"):
        if not question.strip():
            st.warning("Enter an analytical question before selecting Analyze.")
            return
        if st.session_state.analyzer is None:
            st.warning("Enable analysis in the sidebar first.")
            return
        with st.spinner("Analyzing data..."):
            try:
                st.markdown(ask_data(st.session_state.analyzer, question))
            except Exception as error:
                st.error(f"Analysis failed: {error}")


if __name__ == "__main__":
    main()