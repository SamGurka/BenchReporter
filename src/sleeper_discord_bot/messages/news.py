"""Discord-ready RSS news message formatting."""

from sleeper_discord_bot.domain.news import NewsItem


def format_news_message(item: NewsItem) -> str:
    return f"**{item.title}**\n{item.link}\n*{item.source}, {item.published}*"
