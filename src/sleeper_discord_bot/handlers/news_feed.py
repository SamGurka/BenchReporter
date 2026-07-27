"""RSS news-feed handler orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Callable, Protocol

from sleeper_discord_bot.clients.discord import DiscordClient
from sleeper_discord_bot.clients.rss import RssClient
from sleeper_discord_bot.clients.storage import DynamoDBStorage, Storage, utc_now_iso
from sleeper_discord_bot.config import AppConfig
from sleeper_discord_bot.delivery import DiscordDelivery
from sleeper_discord_bot.domain.news import NewsItem
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage
from sleeper_discord_bot.messages.news import format_news_message


RSS_DEDUPE_TTL_DAYS = 120
MAX_NEWS_ITEMS_PER_RUN = 5


class NewsFeedClient(Protocol):
    def items(self, feed_url: str) -> list[NewsItem]: ...


def _feed_key(feed_url: str) -> str:
    return sha256(feed_url.encode("utf-8")).hexdigest()


def _dedupe_attributes(item: NewsItem) -> dict[str, str | int]:
    ttl = datetime.now(timezone.utc) + timedelta(days=RSS_DEDUPE_TTL_DAYS)
    return {
        "posted_at": utc_now_iso(),
        "source": item.source,
        "ttl": int(ttl.timestamp()),
    }


def run_news_feed(
    *,
    rss: NewsFeedClient,
    storage: Storage,
    feed_url: str,
    send_message: Callable[[BotMessage], None],
    max_items: int = MAX_NEWS_ITEMS_PER_RUN,
) -> HandlerResult:
    """Post unseen items, limiting a fresh feed to its newest current story."""

    items = rss.items(feed_url)
    is_first_run = storage.put_if_absent(
        "RSS_FEED",
        _feed_key(feed_url),
        {"feed_url": feed_url, "initialized_at": utc_now_iso()},
    )

    if is_first_run:
        post_candidates = items[:1]
        seen_only = items[1:]
    else:
        post_candidates = items[:max_items]
        seen_only = []

    for item in seen_only:
        storage.put_if_absent("RSS", item.item_id, _dedupe_attributes(item))

    messages: list[BotMessage] = []
    posted_count = 0
    skipped_count = len(seen_only)
    for item in post_candidates:
        if storage.exists("RSS", item.item_id):
            skipped_count += 1
            continue

        message = BotMessage(
            feature="news_feed",
            channel_key="espn_news_feed",
            title=item.title,
            content=format_news_message(item),
        )
        send_message(message)
        storage.put_if_absent("RSS", item.item_id, _dedupe_attributes(item))
        messages.append(message)
        posted_count += 1

    return HandlerResult(messages=messages, posted_count=posted_count, skipped_count=skipped_count)


def _ssm_values(parameter_prefix: str) -> dict[str, str]:
    import boto3

    names = [
        f"{parameter_prefix}/discord-bot-token",
        f"{parameter_prefix}/discord-channel-espn-news-feed",
    ]
    response = boto3.client("ssm").get_parameters(Names=names, WithDecryption=True)
    values = {parameter["Name"]: parameter["Value"] for parameter in response.get("Parameters", [])}
    missing = [name for name in names if name not in values]
    if missing:
        raise ValueError(f"Missing required SSM parameters: {', '.join(missing)}")
    return values


def lambda_handler(event: object, context: object) -> dict[str, int]:
    """AWS Lambda entrypoint for the scheduled RSS feed."""

    import os

    parameter_prefix = os.environ["SSM_PARAMETER_PREFIX"].rstrip("/")
    values = _ssm_values(parameter_prefix)
    config = AppConfig.from_env(
        {
            **os.environ,
            "DISCORD_BOT_TOKEN": values[f"{parameter_prefix}/discord-bot-token"],
            "DISCORD_CHANNEL_ESPN_NEWS_FEED": values[f"{parameter_prefix}/discord-channel-espn-news-feed"],
        }
    )
    storage = DynamoDBStorage(os.environ["DYNAMODB_TABLE_NAME"])
    delivery = DiscordDelivery(
        client=DiscordClient(bot_token=config.discord_bot_token, dry_run=config.dry_run),
        channel_ids=config.channel_ids,
    )
    result = run_news_feed(
        rss=RssClient(),
        storage=storage,
        feed_url=config.rss_feed_url,
        send_message=delivery.send,
    )
    return {"posted": result.posted_count, "skipped": result.skipped_count}
