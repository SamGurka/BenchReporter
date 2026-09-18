"""Weekly Roundup handler orchestration."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from sleeper_discord_bot.clients.discord import DiscordClient
from sleeper_discord_bot.clients.sleeper import SleeperClient
from sleeper_discord_bot.clients.storage import DynamoDBStorage, utc_now_iso
from sleeper_discord_bot.config import AppConfig
from sleeper_discord_bot.delivery import DiscordDelivery
from sleeper_discord_bot.clients.storage import Storage
from sleeper_discord_bot.domain.history import build_draft_pick_snapshots, build_team_week_snapshots
from sleeper_discord_bot.domain.nfl_state import completed_regular_season_week
from sleeper_discord_bot.domain.players import cached_player_lookup, merge_player_lookups, player_lookup_from_stats
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage, split_content
from sleeper_discord_bot.messages.weekly_roundup import format_weekly_roundup_message
from sleeper_discord_bot.observability import log_job_result


class SleeperWeeklyClient(Protocol):
    def rosters(self, league_id: str) -> list[dict[str, Any]]: ...
    def users(self, league_id: str) -> list[dict[str, Any]]: ...
    def matchups(self, league_id: str, week: int) -> list[dict[str, Any]]: ...
    def players(self) -> dict[str, Any]: ...
    def nfl_state(self) -> dict[str, Any]: ...
    def weekly_stats(self, season: str, week: int) -> Any: ...
    def drafts(self, league_id: str) -> list[dict[str, Any]]: ...
    def draft_picks(self, draft_id: str) -> list[dict[str, Any]]: ...


def _safe_prior_matchups(
    sleeper: SleeperWeeklyClient,
    league_id: str,
    week: int,
    prior_weeks: list[int],
) -> list[list[dict[str, Any]]]:
    prior_matchups = []
    for prior_week in prior_weeks:
        if prior_week >= week:
            continue
        try:
            prior_matchups.append(sleeper.matchups(league_id, prior_week))
        except Exception:
            continue
    return prior_matchups


def _safe_player_lookup(
    sleeper: SleeperWeeklyClient,
    season: str,
    weeks: list[int],
) -> dict[str, dict[str, Any]]:
    lookups = []
    for week in weeks:
        try:
            lookups.append(player_lookup_from_stats(sleeper.weekly_stats(season, week)))
        except Exception:
            continue
    return merge_player_lookups(*lookups)


def resolve_weekly_target(sleeper: SleeperWeeklyClient, season: str | None, week: int | None) -> tuple[str, int]:
    if season is not None and week is not None:
        return season, week

    state_season, state_week = completed_regular_season_week(sleeper.nfl_state())
    return season or state_season, week or state_week


def run_weekly_roundup(
    *,
    sleeper: SleeperWeeklyClient,
    storage: Storage,
    league_id: str,
    season: str | None,
    week: int | None,
    send_message: Callable[[BotMessage], None],
    prior_weeks: list[int] | None = None,
    in_season_only: bool = False,
) -> HandlerResult:
    if in_season_only and sleeper.nfl_state().get("season_type") != "regular":
        return HandlerResult(skipped_count=1)
    season, week = resolve_weekly_target(sleeper, season, week)
    prior_weeks = prior_weeks or list(range(1, week))
    rosters = sleeper.rosters(league_id)
    users = sleeper.users(league_id)
    matchups = sleeper.matchups(league_id, week)
    prior_matchups = _safe_prior_matchups(sleeper, league_id, week, prior_weeks)
    players_by_id = merge_player_lookups(
        cached_player_lookup(storage, sleeper),
        _safe_player_lookup(sleeper, season, [*prior_weeks, week]),
    )

    weekly_state = storage.get_weekly_flags(season, week)
    snapshots_written = 0
    if not weekly_state.get("team_snapshots_written"):
        for snapshot in build_team_week_snapshots(season, week, matchups, rosters, users, players_by_id):
            storage.put_snapshot(snapshot)
            snapshots_written += 1
        storage.mark_weekly_flag(season, week, "team_snapshots_written")

    if weekly_state.get("roundup_posted"):
        return HandlerResult(skipped_count=1, snapshots_written=snapshots_written)

    if not weekly_state.get("draft_snapshots_written"):
        try:
            for draft in sleeper.drafts(league_id):
                if str(draft.get("season")) != season or draft.get("status") != "complete":
                    continue
                for snapshot in build_draft_pick_snapshots(
                    season, draft, sleeper.draft_picks(str(draft["draft_id"])), players_by_id,
                ):
                    storage.put_snapshot(snapshot)
            storage.mark_weekly_flag(season, week, "draft_snapshots_written")
        except Exception:
            # Draft preservation is useful, but must never suppress a weekly recap.
            pass

    content = format_weekly_roundup_message(
        week=week,
        matchups=matchups,
        rosters=rosters,
        users=users,
        players_by_id=players_by_id,
        prior_matchups_by_week=prior_matchups,
    )
    messages = [
        BotMessage(
            feature="weekly_roundup",
            channel_key="last_week_tldr",
            title=f"Week {week} Roundup" if index == 1 else f"Week {week} Roundup ({index})",
            content=part,
        )
        for index, part in enumerate(split_content(content), start=1)
    ]
    reservation_key = f"{season}-{week:02d}-roundup_posted"
    if not storage.put_if_absent("POST", reservation_key, {"posted_at": utc_now_iso()}):
        return HandlerResult(skipped_count=1, snapshots_written=snapshots_written)
    try:
        for message in messages:
            send_message(message)
    except Exception:
        storage.delete("POST", reservation_key)
        raise
    storage.mark_weekly_flag(season, week, "roundup_posted")

    return HandlerResult(
        messages=messages,
        posted_count=len(messages),
        snapshots_written=snapshots_written,
    )


def _ssm_values(parameter_prefix: str) -> dict[str, str]:
    import boto3

    names = [
        f"{parameter_prefix}/discord-bot-token",
        f"{parameter_prefix}/discord-channel-last-week-tldr",
        f"{parameter_prefix}/sleeper-league-id",
    ]
    response = boto3.client("ssm").get_parameters(Names=names, WithDecryption=True)
    values = {parameter["Name"]: parameter["Value"] for parameter in response.get("Parameters", [])}
    missing = [name for name in names if name not in values]
    if missing:
        raise ValueError(f"Missing required SSM parameters: {', '.join(missing)}")
    return values


def lambda_handler(event: object, context: object) -> dict[str, int]:
    """AWS Lambda entrypoint for completed-week league roundups."""

    import os

    parameter_prefix = os.environ["SSM_PARAMETER_PREFIX"].rstrip("/")
    values = _ssm_values(parameter_prefix)
    config = AppConfig.from_env(
        {
            **os.environ,
            "SLEEPER_LEAGUE_ID": values[f"{parameter_prefix}/sleeper-league-id"],
            "DISCORD_BOT_TOKEN": values[f"{parameter_prefix}/discord-bot-token"],
            "DISCORD_CHANNEL_LAST_WEEK_TLDR": values[f"{parameter_prefix}/discord-channel-last-week-tldr"],
        }
    )
    delivery = DiscordDelivery(
        client=DiscordClient(bot_token=config.discord_bot_token, dry_run=config.dry_run),
        channel_ids=config.channel_ids,
    )
    result = run_weekly_roundup(
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
    log_job_result(job="weekly_roundup", season=config.season, dry_run=config.dry_run, result=result)
    return {
        "posted": result.posted_count,
        "skipped": result.skipped_count,
        "snapshots_written": result.snapshots_written,
    }
