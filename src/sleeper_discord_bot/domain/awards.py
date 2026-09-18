"""Objective V1.2 award signals derived from Sleeper's raw league records.

These helpers intentionally return measurements, not editorial verdicts.  A later
message/report layer can choose thresholds and tone without changing the data model.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from sleeper_discord_bot.domain.weekly_roundup import bench_player_ids, pair_matchups


def trade_player_impact(
    transaction: dict[str, Any],
    matchups_by_week: Iterable[list[dict[str, Any]]],
) -> dict[int, dict[str, Any]]:
    """Return post-trade fantasy points for players acquired by each roster."""

    acquired = {str(player_id): int(roster_id) for player_id, roster_id in (transaction.get("adds") or {}).items()}
    totals: dict[int, dict[str, float]] = defaultdict(dict)
    for matchups in matchups_by_week:
        for matchup in matchups:
            roster_id = int(matchup.get("roster_id") or 0)
            points = matchup.get("players_points") or {}
            for player_id, recipient_id in acquired.items():
                if recipient_id != roster_id or player_id not in points:
                    continue
                totals[recipient_id][player_id] = round(
                    totals[recipient_id].get(player_id, 0.0) + float(points[player_id]), 2
                )

    return {
        roster_id: {
            "player_points": player_points,
            "total_points": round(sum(player_points.values()), 2),
        }
        for roster_id, player_points in sorted(totals.items())
    }


def draft_pick_value(picks: list[dict[str, Any]], season_points: dict[str, float]) -> list[dict[str, Any]]:
    """Rank completed picks by season points and report their draft-order delta.

    Positive ``value_delta`` means the player finished better by points rank than
    their selection number; negative means the selection finished worse.
    """

    selected = [pick for pick in picks if pick.get("player_id") and pick.get("pick_no")]
    ranked = sorted(
        selected,
        key=lambda pick: (-float(season_points.get(str(pick["player_id"]), 0.0)), int(pick["pick_no"])),
    )
    result = []
    for points_rank, pick in enumerate(ranked, start=1):
        pick_no = int(pick["pick_no"])
        result.append(
            {
                "player_id": str(pick["player_id"]),
                "roster_id": pick.get("roster_id"),
                "pick_no": pick_no,
                "round": pick.get("round"),
                "points": round(float(season_points.get(str(pick["player_id"]), 0.0)), 2),
                "points_rank": points_rank,
                "value_delta": pick_no - points_rank,
            }
        )
    return sorted(result, key=lambda row: (-row["value_delta"], row["pick_no"]))


def bench_regrets(matchups: list[dict[str, Any]], players_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Find bench players who outscored a started player at the same position."""

    regrets = []
    for matchup in matchups:
        points = matchup.get("players_points")
        if not isinstance(points, dict):
            continue
        lowest_starter: dict[str, tuple[str, float]] = {}
        for player_id in matchup.get("starters") or []:
            player_id = str(player_id)
            position = players_by_id.get(player_id, {}).get("position")
            if not position:
                continue
            score = float(points.get(player_id, 0.0))
            if position not in lowest_starter or score < lowest_starter[position][1]:
                lowest_starter[position] = (player_id, score)
        for player_id in bench_player_ids(matchup):
            player_id = str(player_id)
            position = players_by_id.get(player_id, {}).get("position")
            replacement = lowest_starter.get(position)
            if not replacement:
                continue
            bench_points = float(points.get(player_id, 0.0))
            if bench_points <= replacement[1]:
                continue
            regrets.append(
                {
                    "roster_id": int(matchup["roster_id"]),
                    "position": position,
                    "bench_player_id": player_id,
                    "starter_player_id": replacement[0],
                    "bench_points": round(bench_points, 2),
                    "starter_points": round(replacement[1], 2),
                    "points_left": round(bench_points - replacement[1], 2),
                }
            )
    return sorted(regrets, key=lambda row: row["points_left"], reverse=True)


def schedule_luck(matchups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Measure a team's weekly result against its all-play expected wins."""

    if not matchups:
        return []
    scores = [float(matchup.get("points") or 0.0) for matchup in matchups]
    result = []
    opponents = {int(left["roster_id"]): right for left, right in pair_matchups(matchups)}
    opponents.update({int(right["roster_id"]): left for left, right in pair_matchups(matchups)})
    for matchup in matchups:
        roster_id = int(matchup["roster_id"])
        points = float(matchup.get("points") or 0.0)
        all_play_wins = sum(points > score for score in scores if score != points)
        all_play_games = max(len(scores) - 1, 1)
        expected_win_probability = all_play_wins / all_play_games
        opponent = opponents.get(roster_id)
        actual_win = 1.0 if opponent and points > float(opponent.get("points") or 0.0) else 0.0
        result.append(
            {
                "roster_id": roster_id,
                "points": round(points, 2),
                "all_play_wins": all_play_wins,
                "all_play_games": all_play_games,
                "expected_win_probability": round(expected_win_probability, 3),
                "actual_win": actual_win,
                "luck_delta": round(actual_win - expected_win_probability, 3),
            }
        )
    return sorted(result, key=lambda row: row["luck_delta"], reverse=True)
