"""
News Summarizer Agent using AutoGen.

Fetches news articles and produces structured summaries with key insights.

Usage:
    python agent.py --topic "artificial intelligence"
    python agent.py --topic "climate change" --count 5
"""

import argparse
import os

import requests
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

load_dotenv()

DEFAULT_TOPIC = "artificial intelligence"
DEFAULT_COUNT = 5
MAX_COUNT = 20


def validate_request(topic: str, count: int) -> tuple[str, int]:
    """Normalize and validate the topic and requested article count."""

    clean_topic = topic.strip()
    if not clean_topic:
        raise ValueError("Topic cannot be empty.")
    if not 1 <= count <= MAX_COUNT:
        raise ValueError(f"Count must be between 1 and {MAX_COUNT}.")
    return clean_topic, count


def fetch_news(topic: str, count: int = 5) -> list[dict]:
    """Fetch NewsAPI articles or return predictable demo articles offline."""

    topic, count = validate_request(topic, count)
    news_api_key = os.getenv("NEWS_API_KEY")
    if not news_api_key:
        # Mock mode keeps local development and demos independent of NewsAPI.
        mock_articles = [
            {"title": f"Major development in {topic}", "description": f"Researchers announce breakthrough in {topic} field.", "url": "https://example.com/1", "source": {"name": "Tech News"}},
            {"title": f"{topic.title()} industry sees rapid growth", "description": f"New report shows {topic} adoption up 40% year-over-year.", "url": "https://example.com/2", "source": {"name": "Business Daily"}},
            {"title": f"Experts weigh in on {topic} challenges", "description": f"Leading experts discuss obstacles facing the {topic} space.", "url": "https://example.com/3", "source": {"name": "Science Weekly"}},
        ]
        return mock_articles[:count]

    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": topic,
            "language": "en",
            "pageSize": count,
            "sortBy": "publishedAt",
            "apiKey": news_api_key,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "NewsAPI request failed."))
    return data.get("articles", [])


def summarize_news(topic: str, articles: list[dict]) -> str:
    """Create a structured briefing from fetched article metadata."""

    if not articles:
        raise ValueError("No articles are available to summarize.")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    articles_text = "\n\n".join(
        f"Title: {article.get('title', 'Untitled')}\n"
        f"Source: {article.get('source', {}).get('name', 'Unknown')}\n"
        f"Summary: {article.get('description', 'N/A')}"
        for article in articles[:5]
    )

    messages = [
        SystemMessage(content="You are a news analyst. Create a structured news briefing with: 1) Top Story, 2) Key Themes (3 bullet points), 3) What to Watch, 4) Quick Headlines list."),
        HumanMessage(content=f"Topic: {topic}\n\nArticles:\n{articles_text}"),
    ]

    response = llm.invoke(messages)
    return response.content


def summarize_topic(topic: str, count: int = DEFAULT_COUNT) -> tuple[str, list[dict]]:
    """Fetch articles for a topic and return the briefing plus its sources."""

    topic, count = validate_request(topic, count)
    articles = fetch_news(topic, count)
    return summarize_news(topic, articles), articles


def main() -> None:
    """Parse CLI arguments, fetch news, and print a structured briefing."""

    parser = argparse.ArgumentParser(description="News Summarizer Agent")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="News topic to search")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Number of articles to fetch (1-20)")
    args = parser.parse_args()

    try:
        topic, count = validate_request(args.topic, args.count)
        print(f"\n📰 Fetching news about: {topic}\n")
        summary, articles = summarize_topic(topic, count)
    except (ValueError, requests.RequestException, RuntimeError) as error:
        parser.error(str(error))

    print(f"✅ Found {len(articles)} articles")

    print("\n" + "=" * 60)
    print(f"📋 NEWS BRIEFING: {topic.upper()}")
    print("=" * 60)
    print(summary)


if __name__ == "__main__":
    main()