"""Build compact historical records for future season awards."""

from __future__ import annotations

from typing import Any

from sleeper_discord_bot.domain.players import format_player
from sleeper_discord_bot.domain.team_names import roster_display_names
from sleeper_discord_bot.domain.trades import trade_pick_moves, trade_player_moves, trade_roster_ids
from sleeper_discord_bot.domain.weekly_roundup import bench_player_ids, pair_matchups


def _opponents_by_roster(matchups: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    opponents: dict[int, dict[str, Any]] = {}
    for left, right in pair_matchups(matchups):
        opponents[int(left["roster_id"])] = right
        opponents[int(right["roster_id"])] = left
    return opponents


def _result(points_for: float, points_against: float) -> str:
    if points_for > points_against:
        return "win"
    if points_for < points_against:
        return "loss"
    return "tie"


def _position_points(
    starters: list[str],
    players_points: dict[str, float],
    players_by_id: dict[str, dict[str, Any]],
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for player_id in starters:
        player = players_by_id.get(str(player_id), {})
        position = player.get("position") or "UNKNOWN"
        totals[position] = round(totals.get(position, 0.0) + float(players_points.get(str(player_id), 0.0)), 2)
    return totals


def build_team_week_snapshots(
    season: str,
    week: int,
    matchups: list[dict[str, Any]],
    rosters: list[dict[str, Any]],
    users: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    names_by_roster = roster_display_names(rosters, users)
    opponents = _opponents_by_roster(matchups)
    snapshots = []

    for matchup in sorted(matchups, key=lambda row: row.get("roster_id") or 0):
        roster_id = int(matchup["roster_id"])
        opponent = opponents.get(roster_id)
        points_for = float(matchup.get("points") or 0.0)
        points_against = float(opponent.get("points") or 0.0) if opponent else 0.0
        starters = [str(player_id) for player_id in matchup.get("starters") or []]
        bench = [str(player_id) for player_id in bench_player_ids(matchup)]
        players_points = {str(player_id): points for player_id, points in (matchup.get("players_points") or {}).items()}

        snapshots.append(
            {
                "pk": f"TEAM#{roster_id}",
                "sk": f"WEEK#{season}#{week:02d}",
                "season": season,
                "week": week,
                "roster_id": roster_id,
                "team_name": names_by_roster.get(roster_id, f"Roster {roster_id}"),
                "opponent_roster_id": int(opponent["roster_id"]) if opponent else None,
                "opponent_team_name": names_by_roster.get(int(opponent["roster_id"]), f"Roster {opponent['roster_id']}") if opponent else None,
                "points_for": round(points_for, 2),
                "points_against": round(points_against, 2),
                "result": _result(points_for, points_against) if opponent else "unknown",
                "starters": starters,
                "bench": bench,
                "starter_points": {
                    player_id: players_points.get(player_id, 0.0)
                    for player_id in starters
                },
                "bench_points": {
                    player_id: players_points.get(player_id, 0.0)
                    for player_id in bench
                },
                "position_points": _position_points(starters, players_points, players_by_id),
            }
        )

    return snapshots


def build_trade_snapshot(
    season: str,
    week: int,
    transaction: dict[str, Any],
    rosters: list[dict[str, Any]],
    users: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    names_by_roster = roster_display_names(rosters, users)
    roster_ids = trade_roster_ids(transaction)
    player_moves = trade_player_moves(transaction)
    pick_moves = trade_pick_moves(transaction)

    sides = {}
    for roster_id in roster_ids:
        side_moves = player_moves.get(roster_id, {"adds": [], "drops": []})
        received_player_ids = side_moves.get("adds", [])
        sent_player_ids = side_moves.get("drops", [])
        sides[str(roster_id)] = {
            "team_name": names_by_roster.get(roster_id, f"Roster {roster_id}"),
            "received_player_ids": received_player_ids,
            "sent_player_ids": sent_player_ids,
            "received_players": [format_player(player_id, players_by_id) for player_id in received_player_ids],
            "sent_players": [format_player(player_id, players_by_id) for player_id in sent_player_ids],
            "received_picks": pick_moves.get(roster_id, []),
        }

    return {
        "pk": f"TRADE#{transaction['transaction_id']}",
        "sk": "META",
        "season": season,
        "week": week,
        "transaction_id": transaction["transaction_id"],
        "roster_ids": roster_ids,
        "created": transaction.get("created"),
        "status": transaction.get("status"),
        "status_updated": transaction.get("status_updated"),
        "sides": sides,
    }
