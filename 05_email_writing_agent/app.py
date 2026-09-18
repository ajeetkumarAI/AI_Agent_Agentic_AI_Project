"""Streamlit interface for the Email Drafting Agent."""

import streamlit as st

from agent import DEFAULT_CONTEXT, DEFAULT_RECIPIENT, DEFAULT_TONE, draft_email


def main() -> None:
	"""Render the email inputs and display the generated draft."""

	st.set_page_config(page_title="Email Drafting Agent", page_icon="✉️", layout="wide")
	st.title("Email Drafting Agent")
	st.caption("Turn a situation, tone, and recipient into a concise professional email.")

	with st.form("email_form"):
		context = st.text_area(
			"Email context",
			value=DEFAULT_CONTEXT,
			height=150,
			help="Explain the purpose, background, and important details.",
		)
		tone = st.text_input("Tone", value=DEFAULT_TONE)
		recipient = st.text_input("Recipient", value=DEFAULT_RECIPIENT)
		submitted = st.form_submit_button("Draft email", type="primary")

	if not submitted:
		st.info("Complete the fields and select Draft email.")
		return

	with st.spinner("Analyzing context and drafting email..."):
		try:
			email = draft_email(context, tone, recipient)
		except Exception as error:
			st.error(f"Drafting failed: {error}")
			return

	st.subheader("Email draft")
	st.markdown(email)


if __name__ == "__main__":
	main()
