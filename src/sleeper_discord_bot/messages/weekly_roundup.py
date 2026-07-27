"""Discord-ready weekly roundup message formatting."""

from __future__ import annotations

from typing import Any

from sleeper_discord_bot.domain.players import format_player
from sleeper_discord_bot.domain.team_names import roster_display_names
from sleeper_discord_bot.domain.weekly_roundup import (
    letdown_starters,
    pair_matchups,
    standout_starters,
    weekly_high_low,
)


def format_points(points: Any) -> str:
    return f"{float(points or 0):.2f}".rstrip("0").rstrip(".")


def format_matchup_line(
    left: dict[str, Any],
    right: dict[str, Any],
    names_by_roster: dict[int, str],
) -> str:
    left_name = names_by_roster.get(left["roster_id"], f"Roster {left['roster_id']}")
    right_name = names_by_roster.get(right["roster_id"], f"Roster {right['roster_id']}")
    left_points = left.get("points") or 0
    right_points = right.get("points") or 0

    if left_points >= right_points:
        winner_name, winner_points = left_name, left_points
        loser_name, loser_points = right_name, right_points
    else:
        winner_name, winner_points = right_name, right_points
        loser_name, loser_points = left_name, left_points

    margin = abs(float(left_points) - float(right_points))
    return (
        f"- **{winner_name}** beat {loser_name} "
        f"{format_points(winner_points)}-{format_points(loser_points)} "
        f"({format_points(margin)} pt margin)"
    )


def format_weekly_roundup_message(
    week: int,
    matchups: list[dict[str, Any]],
    rosters: list[dict[str, Any]],
    users: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]] | None = None,
    prior_matchups_by_week: list[list[dict[str, Any]]] | None = None,
) -> str:
    players_by_id = players_by_id or {}
    prior_matchups_by_week = prior_matchups_by_week or []
    names_by_roster = roster_display_names(rosters, users)
    high, low = weekly_high_low(matchups)
    pairs = pair_matchups(matchups)

    high_name = names_by_roster.get(high["roster_id"], f"Roster {high['roster_id']}")
    low_name = names_by_roster.get(low["roster_id"], f"Roster {low['roster_id']}")

    lines = [
        f"**Week {week} Roundup**",
        "",
        "**Scoreboard**",
    ]
    lines.extend(format_matchup_line(left, right, names_by_roster) for left, right in pairs)
    lines.extend(
        [
            "",
            "**High / Low**",
            f"- Top score: **{high_name}** with {format_points(high['points'])} pts",
            f"- Low score: **{low_name}** with {format_points(low['points'])} pts",
        ]
    )

    standouts = standout_starters(matchups, players_by_id)
    if standouts:
        lines.extend(["", "**Standout Starters**"])
        for standout in standouts:
            team_name = names_by_roster.get(standout["roster_id"], f"Roster {standout['roster_id']}")
            player = format_player(standout["player_id"], players_by_id)
            lines.append(
                f"- **{player}** for {team_name}: {format_points(standout['points'])} pts "
                f"({format_points(standout['margin'])} over {standout['position']} starter avg)"
            )

    letdowns = letdown_starters(matchups, prior_matchups_by_week)
    if letdowns:
        lines.extend(["", "**Letdowns**"])
        for letdown in letdowns:
            team_name = names_by_roster.get(letdown["roster_id"], f"Roster {letdown['roster_id']}")
            player = format_player(letdown["player_id"], players_by_id)
            lines.append(
                f"- **{player}** for {team_name}: {format_points(letdown['points'])} pts "
                f"after averaging {format_points(letdown['prior_average'])}"
            )

    return "\n".join(lines)
