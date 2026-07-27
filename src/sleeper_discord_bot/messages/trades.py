"""Discord-ready trade announcement formatting."""

from __future__ import annotations

from typing import Any

from sleeper_discord_bot.domain.players import format_player
from sleeper_discord_bot.domain.team_names import roster_display_names
from sleeper_discord_bot.domain.trades import trade_pick_moves, trade_player_moves, trade_roster_ids


def _format_assets(items: list[str]) -> str:
    if not items:
        return "nothing listed"
    return ", ".join(items)


def format_trade_message(
    transaction: dict[str, Any],
    rosters: list[dict[str, Any]],
    users: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
) -> str:
    names_by_roster = roster_display_names(rosters, users)
    roster_ids = trade_roster_ids(transaction)
    player_moves = trade_player_moves(transaction)
    pick_moves = trade_pick_moves(transaction)

    header_names = [names_by_roster.get(roster_id, f"Roster {roster_id}") for roster_id in roster_ids]
    lines = [f"**Trade Alert: {' <-> '.join(header_names)}**"]

    for roster_id in roster_ids:
        team_name = names_by_roster.get(roster_id, f"Roster {roster_id}")
        players_received = [
            format_player(player_id, players_by_id)
            for player_id in player_moves.get(roster_id, {}).get("adds", [])
        ]
        picks_received = pick_moves.get(roster_id, [])
        assets = players_received + picks_received
        lines.append(f"- **{team_name} receives:** {_format_assets(assets)}")

    return "\n".join(lines)
