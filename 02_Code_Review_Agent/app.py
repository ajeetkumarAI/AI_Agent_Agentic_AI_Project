"""Streamlit interface for the code review agent."""

import streamlit as st

from agent import review_code


def main() -> None:
	"""Render the code input form and display the generated review."""

	st.set_page_config(page_title="Code Review Agent", page_icon="🔎", layout="wide")
	st.title("Code Review Agent")
	st.caption("Find correctness, security, performance, and style issues in source code.")

	with st.form("code_review_form"):
		language = st.selectbox(
			"Language",
			["python", "javascript", "typescript", "java", "go", "rust", "sql", "other"],
		)
		uploaded_file = st.file_uploader("Upload a source file", type=None)
		code = st.text_area(
			"Code to review",
			height=360,
			placeholder="Paste code here, or upload a file above.",
		)
		submitted = st.form_submit_button("Review code", type="primary")

	if not submitted:
		st.info("Paste code or upload a file, then select Review code.")
		return

	if uploaded_file is not None:
		try:
			code = uploaded_file.getvalue().decode("utf-8")
		except UnicodeDecodeError:
			st.error("The uploaded file must be UTF-8 text.")
			return

	if not code.strip():
		st.warning("Provide code to review before submitting.")
		return

	with st.spinner("Analyzing code..."):
		try:
			review = review_code(code, language)
		except Exception as error:
			st.error(f"Review failed: {error}")
			return

	st.subheader("Code review")
	st.markdown(review)


if __name__ == "__main__":
	main()
