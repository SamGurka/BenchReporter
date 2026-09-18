"""Standout Free Agents handler orchestration."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from sleeper_discord_bot.clients.discord import DiscordClient
from sleeper_discord_bot.clients.sleeper import SleeperClient
from sleeper_discord_bot.clients.storage import DynamoDBStorage, Storage, utc_now_iso
from sleeper_discord_bot.config import AppConfig
from sleeper_discord_bot.delivery import DiscordDelivery
from sleeper_discord_bot.domain.free_agents import rank_free_agents, select_free_agent_sections
from sleeper_discord_bot.domain.nfl_state import completed_regular_season_week
from sleeper_discord_bot.domain.players import cached_player_lookup, merge_player_lookups, player_lookup_from_stats
from sleeper_discord_bot.domain.scoring import detect_scoring_profile
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage
from sleeper_discord_bot.messages.free_agents import format_free_agents_message
from sleeper_discord_bot.observability import log_job_result


class SleeperFreeAgentClient(Protocol):
    def league(self, league_id: str) -> dict[str, Any]: ...
    def rosters(self, league_id: str) -> list[dict[str, Any]]: ...
    def players(self) -> dict[str, Any]: ...
    def nfl_state(self) -> dict[str, Any]: ...
    def weekly_stats(self, season: str, week: int) -> Any: ...
    def weekly_projections(self, season: str, week: int) -> Any: ...


def resolve_free_agent_target(sleeper: SleeperFreeAgentClient, season: str | None, week: int | None) -> tuple[str, int]:
    target_season, target_week, _ = _resolve_free_agent_target(sleeper, season, week)
    return target_season, target_week


def _resolve_free_agent_target(
    sleeper: SleeperFreeAgentClient,
    season: str | None,
    week: int | None,
) -> tuple[str, int, bool]:
    if season is not None and week is not None:
        return season, week, False
    state = sleeper.nfl_state()
    try:
        state_season, state_week = completed_regular_season_week(state)
        preseason = False
    except ValueError:
        state_season = str(state.get("season") or "")
        if not state_season:
            raise
        state_week = int(state.get("week") or 1)
        preseason = True
    return season or state_season, week or state_week, preseason


def run_free_agents(
    *,
    sleeper: SleeperFreeAgentClient,
    storage: Storage,
    league_id: str,
    season: str | None,
    week: int | None,
    send_message: Callable[[BotMessage], None],
    prior_weeks: list[int] | None = None,
) -> HandlerResult:
    if season is None and week is None:
        # Scheduled reports support preseason projections and completed regular
        # weeks, but must not turn postseason/offseason state into a stale
        # regular-season report.
        if sleeper.nfl_state().get("season_type") not in {"pre", "regular"}:
            return HandlerResult(skipped_count=1)
    season, week, preseason = _resolve_free_agent_target(sleeper, season, week)
    profile = detect_scoring_profile(sleeper.league(league_id).get("scoring_settings") or {})
    if not profile.supported_for_generic_stats or not profile.stats_field:
        return HandlerResult(skipped_count=1)

    posted_flag = "preseason_free_agents_posted" if preseason else "free_agents_posted"
    weekly_state = storage.get_weekly_flags(season, week)
    if weekly_state.get(posted_flag):
        return HandlerResult(skipped_count=1)

    try:
        weekly_stats = (
            sleeper.weekly_projections(season, week) if preseason else sleeper.weekly_stats(season, week)
        )
    except Exception:
        if not preseason:
            raise
        weekly_stats = []
    prior_weeks = prior_weeks if prior_weeks is not None else list(range(1, week))
    prior_stats = []
    for prior_week in prior_weeks:
        if prior_week >= week:
            continue
        try:
            prior_stats.append(sleeper.weekly_stats(season, prior_week))
        except Exception:
            continue

    players_by_id = merge_player_lookups(
        cached_player_lookup(storage, sleeper),
        player_lookup_from_stats(weekly_stats),
    )
    candidates = select_free_agent_sections(rank_free_agents(
        weekly_stats=weekly_stats,
        rosters=sleeper.rosters(league_id),
        players_by_id=players_by_id,
        stats_field=profile.stats_field,
        prior_weekly_stats=prior_stats,
        injury_only_directory_fallback=not bool(weekly_stats),
        projected=preseason,
    ))
    if not candidates:
        return HandlerResult(skipped_count=1)

    reservation_key = f"{season}-{week:02d}-{posted_flag}"
    if not storage.put_if_absent("POST", reservation_key, {"posted_at": utc_now_iso()}):
        return HandlerResult(skipped_count=1)

    message = BotMessage(
        feature="free_agents",
        channel_key="standout_free_agents",
        title=f"Week {week} {'Projected ' if preseason else ''}Standout Free Agents",
        content=format_free_agents_message(week, candidates, projected=preseason),
    )
    try:
        send_message(message)
    except Exception:
        storage.delete("POST", reservation_key)
        raise
    storage.mark_weekly_flag(season, week, posted_flag)
    return HandlerResult(messages=[message], posted_count=1)


def _ssm_values(parameter_prefix: str) -> dict[str, str]:
    import boto3

    names = [
        f"{parameter_prefix}/discord-bot-token",
        f"{parameter_prefix}/discord-channel-standout-free-agents",
        f"{parameter_prefix}/sleeper-league-id",
    ]
    response = boto3.client("ssm").get_parameters(Names=names, WithDecryption=True)
    values = {parameter["Name"]: parameter["Value"] for parameter in response.get("Parameters", [])}
    missing = [name for name in names if name not in values]
    if missing:
        raise ValueError(f"Missing required SSM parameters: {', '.join(missing)}")
    return values


def lambda_handler(event: object, context: object) -> dict[str, int]:
    """AWS Lambda entrypoint for the weekly free-agent report."""

    import os

    parameter_prefix = os.environ["SSM_PARAMETER_PREFIX"].rstrip("/")
    values = _ssm_values(parameter_prefix)
    config = AppConfig.from_env(
        {
            **os.environ,
            "SLEEPER_LEAGUE_ID": values[f"{parameter_prefix}/sleeper-league-id"],
            "DISCORD_BOT_TOKEN": values[f"{parameter_prefix}/discord-bot-token"],
            "DISCORD_CHANNEL_STANDOUT_FREE_AGENTS": values[
                f"{parameter_prefix}/discord-channel-standout-free-agents"
            ],
        }
    )
    storage = DynamoDBStorage(os.environ["DYNAMODB_TABLE_NAME"])
    delivery = DiscordDelivery(
        client=DiscordClient(bot_token=config.discord_bot_token, dry_run=config.dry_run),
        channel_ids=config.channel_ids,
    )
    result = run_free_agents(
        sleeper=SleeperClient(
            base_url=config.sleeper_base_url,
            stats_base_url=config.sleeper_stats_base_url,
        ),
        storage=storage,
        league_id=config.require_league_id(),
        season=config.season,
        week=None,
        send_message=delivery.send,
    )
    log_job_result(job="free_agents", season=config.season, dry_run=config.dry_run, result=result)
    return {"posted": result.posted_count, "skipped": result.skipped_count}
