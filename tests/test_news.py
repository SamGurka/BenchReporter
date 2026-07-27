from sleeper_discord_bot.domain.news import normalize_feed_entries
from sleeper_discord_bot.messages.news import format_news_message


def test_normalizes_feed_entries_newest_first_and_deduplicates():
    entries = [
        {
            "id": "older",
            "title": "Older story",
            "link": "https://example.test/older",
            "published": "Mon, 01 Sep 2025 10:00:00 GMT",
            "published_parsed": (2025, 9, 1, 10, 0, 0, 0, 244, 0),
        },
        {
            "id": "newer",
            "title": "Newer story",
            "link": "https://example.test/newer",
            "published": "Mon, 01 Sep 2025 11:00:00 GMT",
            "published_parsed": (2025, 9, 1, 11, 0, 0, 0, 244, 0),
        },
        {
            "id": "newer",
            "title": "Duplicate story",
            "link": "https://example.test/duplicate",
        },
        {"id": "invalid", "title": "Missing link"},
    ]

    items = normalize_feed_entries(entries, "Example Feed")

    assert [item.title for item in items] == ["Newer story", "Older story"]
    assert items[0].source == "Example Feed"
    assert "**Newer story**" in format_news_message(items[0])
    assert "https://example.test/newer" in format_news_message(items[0])
