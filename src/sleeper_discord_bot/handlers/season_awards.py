"""End-of-season objective award report orchestration."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from sleeper_discord_bot.clients.discord import DiscordClient
from sleeper_discord_bot.clients.sleeper import SleeperClient
from sleeper_discord_bot.clients.storage import DynamoDBStorage, Storage
from sleeper_discord_bot.config import AppConfig
from sleeper_discord_bot.delivery import DiscordDelivery
from sleeper_discord_bot.domain.players import cached_player_lookup
from sleeper_discord_bot.domain.season_awards import build_season_awards
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage, split_content
from sleeper_discord_bot.messages.season_awards import format_season_awards_message


class SleeperSeasonAwardsClient(Protocol):
    def rosters(self, league_id: str) -> list[dict[str, Any]]: ...
    def users(self, league_id: str) -> list[dict[str, Any]]: ...
    def matchups(self, league_id: str, week: int) -> list[dict[str, Any]]: ...
    def transactions(self, league_id: str, week: int) -> list[dict[str, Any]]: ...
    def drafts(self, league_id: str) -> list[dict[str, Any]]: ...
    def draft_picks(self, draft_id: str) -> list[dict[str, Any]]: ...
    def players(self) -> dict[str, Any]: ...
    def nfl_state(self) -> dict[str, Any]: ...


def _target(sleeper: SleeperSeasonAwardsClient, season: str | None, week: int | None) -> tuple[str, int]:
    if season is not None and week is not None:
        return season, week
    state = sleeper.nfl_state()
    target_season = season or str(state.get("season") or state.get("previous_season") or "")
    if not target_season:
        raise ValueError("Sleeper state does not identify a season for awards.")
    if week is not None:
        return target_season, week
    if state.get("season_type") == "regular":
        return target_season, max(int(state.get("week") or 1) - 1, 1)
    # Postseason/offseason state uses a playoff leg, not a completed regular
    # season week. Awards always evaluate all 18 regular-season weeks.
    return target_season, 18


def run_season_awards(
    *, sleeper: SleeperSeasonAwardsClient, storage: Storage, league_id: str, season: str | None,
    week: int | None, send_message: Callable[[BotMessage], None],
) -> HandlerResult:
    season, week = _target(sleeper, season, week)
    if storage.get_weekly_flags(season, 0).get("season_awards_posted"):
        return HandlerResult(skipped_count=1)
    rosters, users = sleeper.rosters(league_id), sleeper.users(league_id)
    matchups = [sleeper.matchups(league_id, target_week) for target_week in range(1, week + 1)]
    transactions = [sleeper.transactions(league_id, target_week) for target_week in range(1, week + 1)]
    draft_picks = [
        pick
        for draft in sleeper.drafts(league_id)
        if str(draft.get("season")) == season and draft.get("status") == "complete"
        for pick in sleeper.draft_picks(str(draft["draft_id"]))
    ]
    players = cached_player_lookup(storage, sleeper)
    awards = build_season_awards(
        matchups_by_week=matchups, transactions_by_week=transactions, draft_picks=draft_picks, players_by_id=players,
    )
    content = format_season_awards_message(season, awards, rosters, users, players)
    messages = [
        BotMessage("season_awards", "season_awards", f"{season} Awards" if index == 1 else f"{season} Awards ({index})", part)
        for index, part in enumerate(split_content(content), start=1)
    ]
    for message in messages:
        send_message(message)
    storage.mark_weekly_flag(season, 0, "season_awards_posted")
    return HandlerResult(messages=messages, posted_count=len(messages))


def _ssm_values(prefix: str) -> dict[str, str]:
    import boto3
    names = [f"{prefix}/discord-bot-token", f"{prefix}/discord-channel-season-awards", f"{prefix}/sleeper-league-id"]
    response = boto3.client("ssm").get_parameters(Names=names, WithDecryption=True)
    values = {item["Name"]: item["Value"] for item in response.get("Parameters", [])}
    missing = [name for name in names if name not in values]
    if missing:
        raise ValueError(f"Missing required SSM parameters: {', '.join(missing)}")
    return values


def lambda_handler(event: object, context: object) -> dict[str, int]:
    import os
    prefix = os.environ["SSM_PARAMETER_PREFIX"].rstrip("/")
    values = _ssm_values(prefix)
    config = AppConfig.from_env({**os.environ, "SLEEPER_LEAGUE_ID": values[f"{prefix}/sleeper-league-id"], "DISCORD_BOT_TOKEN": values[f"{prefix}/discord-bot-token"], "DISCORD_CHANNEL_SEASON_AWARDS": values[f"{prefix}/discord-channel-season-awards"]})
    result = run_season_awards(
        sleeper=SleeperClient(base_url=config.sleeper_base_url, stats_base_url=config.sleeper_stats_base_url),
        storage=DynamoDBStorage(os.environ["DYNAMODB_TABLE_NAME"]), league_id=config.require_league_id(), season=config.season,
        week=None, send_message=DiscordDelivery(DiscordClient(config.discord_bot_token, dry_run=config.dry_run), config.channel_ids).send,
    )
    return {"posted": result.posted_count, "skipped": result.skipped_count}
