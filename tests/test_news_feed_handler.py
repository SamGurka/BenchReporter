from sleeper_discord_bot.clients.storage import InMemoryStorage
from sleeper_discord_bot.domain.news import NewsItem
from sleeper_discord_bot.handlers.news_feed import run_news_feed


class FakeRssClient:
    def __init__(self, items):
        self._items = items

    def items(self, feed_url):
        return self._items


def _item(item_id: str, title: str) -> NewsItem:
    return NewsItem(
        item_id=item_id,
        title=title,
        link=f"https://example.test/{item_id}",
        source="Example Feed",
        published="Mon, 01 Sep 2025 10:00:00 GMT",
    )


def test_first_news_run_posts_newest_item_and_marks_backlog_seen():
    storage = InMemoryStorage()
    sent = []
    rss = FakeRssClient([_item("new", "Newest"), _item("old", "Older")])

    result = run_news_feed(rss=rss, storage=storage, feed_url="https://example.test/feed", send_message=sent.append)

    assert result.posted_count == 1
    assert result.skipped_count == 1
    assert [message.title for message in sent] == ["Newest"]
    assert storage.exists("RSS", "new")
    assert storage.exists("RSS", "old")


def test_later_news_run_posts_only_unseen_items_up_to_limit():
    storage = InMemoryStorage()
    first_rss = FakeRssClient([_item("one", "One")])
    run_news_feed(rss=first_rss, storage=storage, feed_url="https://example.test/feed", send_message=lambda message: None)

    sent = []
    later_rss = FakeRssClient([_item("three", "Three"), _item("two", "Two"), _item("one", "One")])
    result = run_news_feed(
        rss=later_rss,
        storage=storage,
        feed_url="https://example.test/feed",
        send_message=sent.append,
        max_items=2,
    )

    assert result.posted_count == 2
    assert result.skipped_count == 0
    assert [message.title for message in sent] == ["Three", "Two"]
