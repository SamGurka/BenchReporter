"""Local runner for bot workflows without AWS or live Discord sends."""

from __future__ import annotations

import argparse

from sleeper_discord_bot.clients.sleeper import SleeperClient
from sleeper_discord_bot.clients.storage import InMemoryStorage
from sleeper_discord_bot.clients.rss import RssClient
from sleeper_discord_bot.config import AppConfig
from sleeper_discord_bot.delivery import ConsoleDelivery
from sleeper_discord_bot.handlers.trade_watch import run_trade_watch
from sleeper_discord_bot.handlers.weekly_roundup import run_weekly_roundup
from sleeper_discord_bot.handlers.news_feed import run_news_feed


def build_sleeper(config: AppConfig) -> SleeperClient:
    return SleeperClient(
        base_url=config.sleeper_base_url,
        stats_base_url=config.sleeper_stats_base_url,
    )


def _parse_prior_weeks(value: str | None) -> list[int] | None:
    if not value:
        return None
    return [int(week.strip()) for week in value.split(",") if week.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-id", help="Sleeper league ID. Defaults to SLEEPER_LEAGUE_ID.")
    parser.add_argument("--season", help="NFL season. Defaults to SEASON or Sleeper state.")
    parser.add_argument("--base-url", help="Sleeper API base URL.")
    parser.add_argument("--stats-base-url", help="Sleeper stats API base URL.")
    parser.add_argument("--rss-feed-url", help="RSS/Atom URL. Defaults to RSS_FEED_URL.")

    subparsers = parser.add_subparsers(dest="command", required=True)
    weekly_parser = subparsers.add_parser("weekly", help="Run Weekly Roundup locally.")
    weekly_parser.add_argument("--week", type=int)
    weekly_parser.add_argument("--prior-weeks", help="Comma-separated prior weeks to use for letdowns.")

    trades_parser = subparsers.add_parser("trades", help="Run Trade Watch locally.")
    trades_parser.add_argument("--week", type=int)

    subparsers.add_parser("news", help="Run the RSS news feed locally.")

    args = parser.parse_args()
    env_config = AppConfig.from_env()
    config = AppConfig(
        sleeper_league_id=args.league_id or env_config.sleeper_league_id,
        season=args.season or env_config.season,
        sleeper_base_url=args.base_url or env_config.sleeper_base_url,
        sleeper_stats_base_url=args.stats_base_url or env_config.sleeper_stats_base_url,
        rss_feed_url=args.rss_feed_url or env_config.rss_feed_url,
        dry_run=True,
        discord_bot_token=env_config.discord_bot_token,
        channel_ids=env_config.channel_ids,
    )

    storage = InMemoryStorage()
    delivery = ConsoleDelivery()

    if args.command == "weekly":
        sleeper = build_sleeper(config)
        league_id = config.require_league_id()
        result = run_weekly_roundup(
            sleeper=sleeper,
            storage=storage,
            league_id=league_id,
            season=config.season,
            week=args.week,
            prior_weeks=_parse_prior_weeks(args.prior_weeks),
            send_message=delivery.send,
        )
    elif args.command == "trades":
        sleeper = build_sleeper(config)
        league_id = config.require_league_id()
        result = run_trade_watch(
            sleeper=sleeper,
            storage=storage,
            league_id=league_id,
            season=config.season,
            week=args.week,
            send_message=delivery.send,
        )
    elif args.command == "news":
        result = run_news_feed(
            rss=RssClient(),
            storage=storage,
            feed_url=config.rss_feed_url,
            send_message=delivery.send,
        )
    else:
        parser.error(f"Unknown command: {args.command}")
        return 2

    print(
        f"\nResult: posted={result.posted_count} "
        f"skipped={result.skipped_count} snapshots={result.snapshots_written}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
