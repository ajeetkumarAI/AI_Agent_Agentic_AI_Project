"""Streamlit interface for the News Summarizer Agent."""

import streamlit as st

from agent import DEFAULT_COUNT, DEFAULT_TOPIC, MAX_COUNT, summarize_topic


def render_sources(articles: list[dict]) -> None:
	"""Show the article titles, publishers, and links used in the briefing."""

	with st.expander(f"Sources ({len(articles)} articles)"):
		for article in articles:
			title = article.get("title", "Untitled article")
			source = article.get("source", {}).get("name", "Unknown source")
			url = article.get("url")
			if url:
				st.markdown(f"- **{source}**: [{title}]({url})")
			else:
				st.markdown(f"- **{source}**: {title}")


def main() -> None:
	"""Render topic controls and the generated news briefing."""

	st.set_page_config(page_title="News Summarizer Agent", page_icon="📰", layout="wide")
	st.title("News Summarizer Agent")
	st.caption("Fetch recent headlines and turn them into a structured briefing.")

	with st.form("news_form"):
		topic = st.text_input("Topic", value=DEFAULT_TOPIC)
		count = st.slider("Number of articles", min_value=1, max_value=MAX_COUNT, value=DEFAULT_COUNT)
		submitted = st.form_submit_button("Create briefing", type="primary")

	if not submitted:
		st.info("Enter a topic and select Create briefing.")
		return

	with st.spinner("Fetching articles and preparing the briefing..."):
		try:
			summary, articles = summarize_topic(topic, count)
		except Exception as error:
			st.error(f"News summarization failed: {error}")
			return

	st.subheader(f"Briefing: {topic.strip()}")
	st.markdown(summary)
	render_sources(articles)


if __name__ == "__main__":
	main()
