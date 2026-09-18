"""Streamlit interface for the SQLite SQL Query Agent."""

import tempfile
from pathlib import Path

import streamlit as st

from agent import build_agent, create_demo_database, ask_database


def initialize_state() -> None:
	"""Initialize the database and agent stored across Streamlit reruns."""

	st.session_state.setdefault("agent", None)
	st.session_state.setdefault("database", None)
	st.session_state.setdefault("database_name", None)


def load_database(uploaded_file) -> None:
	"""Persist an uploaded SQLite file temporarily and build a read-only agent."""

	suffix = Path(uploaded_file.name).suffix.lower()
	with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
		temporary_file.write(uploaded_file.getvalue())
		temporary_path = Path(temporary_file.name)

	try:
		agent, database = build_agent(temporary_path, read_only=True)
		st.session_state.agent = agent
		st.session_state.database = database
		st.session_state.database_name = uploaded_file.name
	finally:
		temporary_path.unlink(missing_ok=True)


def render_sidebar() -> None:
	"""Render demo and uploaded database controls."""

	with st.sidebar:
		st.header("Database")
		uploaded_file = st.file_uploader("Upload SQLite database", type=["sqlite", "sqlite3", "db"])

		if st.button("Use demo database", type="primary"):
			with st.spinner("Creating demo database..."):
				path = create_demo_database(Path(tempfile.gettempdir()) / "sql_query_agent_demo.sqlite")
				st.session_state.agent, st.session_state.database = build_agent(path)
				st.session_state.database_name = "demo.sqlite"

		if uploaded_file is not None and st.button("Connect uploaded database"):
			with st.spinner("Connecting to database..."):
				try:
					load_database(uploaded_file)
				except Exception as error:
					st.error(f"Could not connect: {error}")

		if st.session_state.database_name:
			st.success(f"Connected: {st.session_state.database_name}")


def main() -> None:
	"""Render the database selector and natural-language query form."""

	st.set_page_config(page_title="SQL Query Agent", page_icon="📊", layout="wide")
	initialize_state()
	st.title("SQL Query Agent")
	st.caption("Ask questions about SQLite data in plain English.")
	render_sidebar()

	if st.session_state.agent is None:
		st.info("Choose Use demo database or upload a SQLite database in the sidebar.")
		return

	question = st.text_area(
		"Question",
		placeholder="What are the top three products by revenue?",
		height=100,
	)
	if st.button("Run query", type="primary"):
		if not question.strip():
			st.warning("Enter a question first.")
			return
		with st.spinner("Generating and running a read-only SQL query..."):
			try:
				st.markdown(ask_database(st.session_state.agent, question))
			except Exception as error:
				st.error(f"Query failed: {error}")


if __name__ == "__main__":
	main()
