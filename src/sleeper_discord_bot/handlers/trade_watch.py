"""Trade Watch handler orchestration."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from datetime import datetime, timedelta, timezone

from sleeper_discord_bot.clients.discord import DiscordClient
from sleeper_discord_bot.clients.sleeper import SleeperClient
from sleeper_discord_bot.clients.storage import DynamoDBStorage, Storage, utc_now_iso
from sleeper_discord_bot.config import AppConfig
from sleeper_discord_bot.delivery import DiscordDelivery
from sleeper_discord_bot.domain.history import build_roster_move_snapshot, build_trade_snapshot
from sleeper_discord_bot.domain.nfl_state import completed_regular_season_week
from sleeper_discord_bot.domain.players import cached_player_lookup, merge_player_lookups, player_lookup_from_stats
from sleeper_discord_bot.domain.trades import completed_trades
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage, split_content
from sleeper_discord_bot.messages.trades import format_trade_message
from sleeper_discord_bot.observability import log_job_result


TRADE_DEDUPE_TTL_DAYS = 400


class SleeperTradeClient(Protocol):
    def rosters(self, league_id: str) -> list[dict[str, Any]]: ...
    def users(self, league_id: str) -> list[dict[str, Any]]: ...
    def transactions(self, league_id: str, week: int) -> list[dict[str, Any]]: ...
    def players(self) -> dict[str, Any]: ...
    def nfl_state(self) -> dict[str, Any]: ...
    def weekly_stats(self, season: str, week: int) -> Any: ...


def resolve_trade_target(sleeper: SleeperTradeClient, season: str | None, week: int | None) -> tuple[str, int]:
    if season is not None and week is not None:
        return season, week

    state_season, state_week = completed_regular_season_week(sleeper.nfl_state())
    return season or state_season, week or state_week


def run_trade_watch(
    *,
    sleeper: SleeperTradeClient,
    storage: Storage,
    league_id: str,
    season: str | None,
    week: int | None,
    send_message: Callable[[BotMessage], None],
    in_season_only: bool = False,
) -> HandlerResult:
    if in_season_only and sleeper.nfl_state().get("season_type") != "regular":
        return HandlerResult(skipped_count=1)
    season, week = resolve_trade_target(sleeper, season, week)
    rosters = sleeper.rosters(league_id)
    users = sleeper.users(league_id)
    transactions = sleeper.transactions(league_id, week)
    players_by_id = merge_player_lookups(
        cached_player_lookup(storage, sleeper),
        player_lookup_from_stats(sleeper.weekly_stats(season, week)),
    )

    messages: list[BotMessage] = []
    posted_count = 0
    skipped_count = 0
    snapshots_written = 0

    for transaction in transactions:
        if transaction.get("status") != "complete" or transaction.get("type") not in {"waiver", "free_agent"}:
            continue
        storage.put_snapshot(build_roster_move_snapshot(season, week, transaction, rosters, users, players_by_id))
        snapshots_written += 1

    for trade in completed_trades(transactions):
        transaction_id = str(trade["transaction_id"])
        reservation = {
            "season": season,
            "week": week,
            "posted_at": utc_now_iso(),
            "ttl": int((datetime.now(timezone.utc) + timedelta(days=TRADE_DEDUPE_TTL_DAYS)).timestamp()),
        }
        if not storage.put_if_absent("TXN", transaction_id, reservation):
            skipped_count += 1
            continue

        content = format_trade_message(trade, rosters, users, players_by_id)
        trade_messages = [
            BotMessage(
                feature="trade_watch",
                channel_key="trade_block",
                title="Trade Alert" if index == 1 else f"Trade Alert ({index})",
                content=part,
            )
            for index, part in enumerate(split_content(content), start=1)
        ]
        try:
            for message in trade_messages:
                send_message(message)
        except Exception:
            storage.delete("TXN", transaction_id)
            raise
        storage.put_snapshot(build_trade_snapshot(season, week, trade, rosters, users, players_by_id))

        messages.extend(trade_messages)
        posted_count += len(trade_messages)
        snapshots_written += 1

    return HandlerResult(
        messages=messages,
        posted_count=posted_count,
        skipped_count=skipped_count,
        snapshots_written=snapshots_written,
    )


def _ssm_values(parameter_prefix: str) -> dict[str, str]:
    import boto3

    names = [
        f"{parameter_prefix}/discord-bot-token",
        f"{parameter_prefix}/discord-channel-trade-block",
        f"{parameter_prefix}/sleeper-league-id",
    ]
    response = boto3.client("ssm").get_parameters(Names=names, WithDecryption=True)
    values = {parameter["Name"]: parameter["Value"] for parameter in response.get("Parameters", [])}
    missing = [name for name in names if name not in values]
    if missing:
        raise ValueError(f"Missing required SSM parameters: {', '.join(missing)}")
    return values


def lambda_handler(event: object, context: object) -> dict[str, int]:
    """AWS Lambda entrypoint for in-season completed trade announcements."""

    import os

    parameter_prefix = os.environ["SSM_PARAMETER_PREFIX"].rstrip("/")
    values = _ssm_values(parameter_prefix)
    config = AppConfig.from_env(
        {
            **os.environ,
            "SLEEPER_LEAGUE_ID": values[f"{parameter_prefix}/sleeper-league-id"],
            "DISCORD_BOT_TOKEN": values[f"{parameter_prefix}/discord-bot-token"],
            "DISCORD_CHANNEL_TRADE_BLOCK": values[f"{parameter_prefix}/discord-channel-trade-block"],
        }
    )
    delivery = DiscordDelivery(
        client=DiscordClient(bot_token=config.discord_bot_token, dry_run=config.dry_run),
        channel_ids=config.channel_ids,
    )
    result = run_trade_watch(
        sleeper=SleeperClient(
            base_url=config.sleeper_base_url,
            stats_base_url=config.sleeper_stats_base_url,
        ),
        storage=DynamoDBStorage(os.environ["DYNAMODB_TABLE_NAME"]),
        league_id=config.require_league_id(),
        season=config.season,
        week=None,
        send_message=delivery.send,
        in_season_only=True,
    )
    log_job_result(job="trade_watch", season=config.season, dry_run=config.dry_run, result=result)
    return {
        "posted": result.posted_count,
        "skipped": result.skipped_count,
        "snapshots_written": result.snapshots_written,
    }
