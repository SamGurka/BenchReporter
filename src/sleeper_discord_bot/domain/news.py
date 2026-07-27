"""Normalize RSS and Atom entries into stable bot news items."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Iterable


@dataclass(frozen=True)
class NewsItem:
    item_id: str
    title: str
    link: str
    source: str
    published: str
    published_timestamp: float = 0.0


def _entry_value(entry: Any, key: str, default: Any = "") -> Any:
    if hasattr(entry, "get"):
        return entry.get(key, default)
    return default


def _stable_item_id(entry: Any, title: str, link: str) -> str:
    raw_id = str(_entry_value(entry, "id") or _entry_value(entry, "guid") or link or title)
    return sha256(raw_id.encode("utf-8")).hexdigest()


def _published_timestamp(entry: Any) -> float:
    parsed = _entry_value(entry, "published_parsed") or _entry_value(entry, "updated_parsed")
    if not parsed:
        return 0.0
    try:
        return float(calendar.timegm(parsed))
    except (TypeError, ValueError, OverflowError):
        return 0.0


def normalize_feed_entries(entries: Iterable[Any], feed_title: str) -> list[NewsItem]:
    """Return valid feed entries newest first, deduplicated by stable item ID."""

    items_by_id: dict[str, NewsItem] = {}
    for entry in entries:
        title = str(_entry_value(entry, "title")).strip()
        link = str(_entry_value(entry, "link")).strip()
        if not title or not link:
            continue

        source_data = _entry_value(entry, "source", {})
        source = str(_entry_value(source_data, "title") or feed_title).strip()
        published = str(
            _entry_value(entry, "published") or _entry_value(entry, "updated") or "Publication date unavailable"
        ).strip()
        item = NewsItem(
            item_id=_stable_item_id(entry, title, link),
            title=title,
            link=link,
            source=source or "Fantasy News",
            published=published,
            published_timestamp=_published_timestamp(entry),
        )
        items_by_id.setdefault(item.item_id, item)

    return sorted(items_by_id.values(), key=lambda item: item.published_timestamp, reverse=True)
