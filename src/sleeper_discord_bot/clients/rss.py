"""HTTP client for source-agnostic RSS and Atom feeds."""

from __future__ import annotations

from typing import Any, Protocol

import feedparser
import requests

from sleeper_discord_bot.domain.news import NewsItem, normalize_feed_entries


class RssHttpSession(Protocol):
    def get(self, url: str, *, timeout: int, headers: dict[str, str]) -> Any: ...


class RssClient:
    def __init__(self, session: RssHttpSession | None = None, timeout_sec: int = 20) -> None:
        self.session = session or requests
        self.timeout_sec = timeout_sec

    def items(self, feed_url: str) -> list[NewsItem]:
        if not feed_url:
            raise ValueError("RSS_FEED_URL is required.")

        response = self.session.get(
            feed_url,
            timeout=self.timeout_sec,
            headers={"User-Agent": "BenchReporter/0.1 (+https://github.com/Nexather/BenchReporter)"},
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise ValueError(f"Unable to parse RSS/Atom feed: {parsed.bozo_exception}")

        feed_title = str(parsed.feed.get("title") or "Fantasy News")
        return normalize_feed_entries(parsed.entries, feed_title)
