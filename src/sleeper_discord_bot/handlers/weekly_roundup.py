"""Weekly Roundup handler orchestration."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from sleeper_discord_bot.clients.storage import Storage
from sleeper_discord_bot.domain.history import build_team_week_snapshots
from sleeper_discord_bot.domain.nfl_state import completed_regular_season_week
from sleeper_discord_bot.domain.players import cached_player_lookup, merge_player_lookups, player_lookup_from_stats
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage
from sleeper_discord_bot.messages.weekly_roundup import format_weekly_roundup_message


class SleeperWeeklyClient(Protocol):
    def rosters(self, league_id: str) -> list[dict[str, Any]]: ...
    def users(self, league_id: str) -> list[dict[str, Any]]: ...
    def matchups(self, league_id: str, week: int) -> list[dict[str, Any]]: ...
    def players(self) -> dict[str, Any]: ...
    def nfl_state(self) -> dict[str, Any]: ...
    def weekly_stats(self, season: str, week: int) -> Any: ...


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
) -> HandlerResult:
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

    content = format_weekly_roundup_message(
        week=week,
        matchups=matchups,
        rosters=rosters,
        users=users,
        players_by_id=players_by_id,
        prior_matchups_by_week=prior_matchups,
    )
    message = BotMessage(
        feature="weekly_roundup",
        channel_key="last_week_tldr",
        title=f"Week {week} Roundup",
        content=content,
    )
    send_message(message)
    storage.mark_weekly_flag(season, week, "roundup_posted")

    return HandlerResult(
        messages=[message],
        posted_count=1,
        snapshots_written=snapshots_written,
    )
