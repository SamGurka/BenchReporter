"""Discord formatting for objective season award candidates."""

from __future__ import annotations

from typing import Any

from sleeper_discord_bot.domain.players import format_player
from sleeper_discord_bot.domain.team_names import roster_display_names


def _team(roster_id: int, names: dict[int, str]) -> str:
    return names.get(roster_id, f"Roster {roster_id}")


def format_season_awards_message(
    season: str,
    awards: dict[str, list[dict[str, Any]]],
    rosters: list[dict[str, Any]],
    users: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
) -> str:
    names = roster_display_names(rosters, users)
    lines = [f"**{season} Raw-Data Awards**"]
    if awards["trade_impact"]:
        row = awards["trade_impact"][0]
        lines += ["", "**Trade Return**", f"- {_team(row['roster_id'], names)}: {row['total_points']:.1f} post-trade pts"]
    if awards["draft_value"]:
        row = awards["draft_value"][0]
        lines += ["", "**Draft Value**", f"- {format_player(row['player_id'], players_by_id)} for {_team(row['roster_id'], names)}: pick {row['pick_no']}, +{row['value_delta']} value delta"]
    if awards["early_qb_te"]:
        best = awards["early_qb_te"][0]
        worst = awards["early_qb_te"][-1]
        lines += ["", "**Early QB/TE Return**", f"- Best: {format_player(best['player_id'], players_by_id)} ({best['position']}, {best['points']:.1f} pts; {best['position_value_delta']:+d} versus drafted {best['position']}s)"]
        if worst["player_id"] != best["player_id"]:
            lines.append(f"- Lowest: {format_player(worst['player_id'], players_by_id)} ({worst['position']}, {worst['points']:.1f} pts; {worst['position_value_delta']:+d})")
    if awards["waiver_returns"]:
        row = awards["waiver_returns"][0]
        lines += ["", "**Waiver Return**", f"- {_team(row['roster_id'], names)}: {row['total_points']:.1f} pts from a Week {row['week']} addition"]
    if awards["bench_regrets"]:
        row = awards["bench_regrets"][0]
        lines += ["", "**Points Left on the Bench**", f"- {_team(row['roster_id'], names)}: {row['points_left']:.1f} same-position pts"]
    if awards["schedule_luck"]:
        row = awards["schedule_luck"][0]
        lines += ["", "**Schedule Luck**", f"- {_team(row['roster_id'], names)}: +{row['luck_delta']:.2f} all-play win delta"]
    return "\n".join(lines)
