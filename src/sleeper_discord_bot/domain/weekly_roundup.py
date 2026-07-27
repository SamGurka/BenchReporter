"""Weekly matchup parsing and summary helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def pair_matchups(matchups: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    grouped: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for matchup in matchups:
        matchup_id = matchup.get("matchup_id")
        if matchup_id is not None:
            grouped[matchup_id].append(matchup)

    pairs = []
    for matchup_id in sorted(grouped):
        teams = sorted(grouped[matchup_id], key=lambda row: row.get("roster_id") or 0)
        if len(teams) == 2:
            pairs.append((teams[0], teams[1]))
    return pairs


def weekly_high_low(matchups: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not matchups:
        raise ValueError("Cannot find high/low scores without matchup data.")

    high = max(matchups, key=lambda row: row.get("points") or 0)
    low = min(matchups, key=lambda row: row.get("points") or 0)
    return high, low


def bench_player_ids(matchup: dict[str, Any]) -> list[str]:
    starters = set(matchup.get("starters") or [])
    return [player_id for player_id in matchup.get("players") or [] if player_id not in starters]


def has_player_points(matchups: list[dict[str, Any]]) -> bool:
    return all(isinstance(matchup.get("players_points"), dict) for matchup in matchups)


def starter_position_averages(
    matchups: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)

    for matchup in matchups:
        players_points = matchup.get("players_points") or {}
        for player_id in matchup.get("starters") or []:
            player = players_by_id.get(str(player_id), {})
            position = player.get("position")
            if not position:
                continue
            totals[position] += float(players_points.get(str(player_id), 0.0))
            counts[position] += 1

    return {
        position: round(totals[position] / counts[position], 2)
        for position in totals
        if counts[position]
    }


def standout_starters(
    matchups: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
    threshold_points: float = 10.0,
    limit: int = 5,
) -> list[dict[str, Any]]:
    averages = starter_position_averages(matchups, players_by_id)
    standouts = []

    for matchup in matchups:
        roster_id = int(matchup["roster_id"])
        players_points = matchup.get("players_points") or {}
        for player_id in matchup.get("starters") or []:
            player = players_by_id.get(str(player_id), {})
            position = player.get("position")
            if not position or position not in averages:
                continue

            points = float(players_points.get(str(player_id), 0.0))
            margin = round(points - averages[position], 2)
            if margin >= threshold_points:
                standouts.append(
                    {
                        "roster_id": roster_id,
                        "player_id": str(player_id),
                        "position": position,
                        "points": round(points, 2),
                        "position_average": averages[position],
                        "margin": margin,
                    }
                )

    return sorted(standouts, key=lambda row: row["margin"], reverse=True)[:limit]


def prior_player_averages(
    prior_matchups_by_week: list[list[dict[str, Any]]],
) -> dict[str, dict[str, float]]:
    totals: dict[str, float] = defaultdict(float)
    games: dict[str, int] = defaultdict(int)

    for matchups in prior_matchups_by_week:
        for matchup in matchups:
            players_points = matchup.get("players_points") or {}
            for player_id in matchup.get("starters") or []:
                player_id = str(player_id)
                totals[player_id] += float(players_points.get(player_id, 0.0))
                games[player_id] += 1

    return {
        player_id: {"average": round(totals[player_id] / games[player_id], 2), "games": games[player_id]}
        for player_id in totals
        if games[player_id]
    }


def letdown_starters(
    matchups: list[dict[str, Any]],
    prior_matchups_by_week: list[list[dict[str, Any]]],
    min_prior_games: int = 3,
    ratio_threshold: float = 0.5,
    min_prior_average: float = 8.0,
    limit: int = 5,
) -> list[dict[str, Any]]:
    prior_averages = prior_player_averages(prior_matchups_by_week)
    letdowns = []

    for matchup in matchups:
        roster_id = int(matchup["roster_id"])
        players_points = matchup.get("players_points") or {}
        for player_id in matchup.get("starters") or []:
            player_id = str(player_id)
            prior = prior_averages.get(player_id)
            if not prior or prior["games"] < min_prior_games or prior["average"] < min_prior_average:
                continue

            points = float(players_points.get(player_id, 0.0))
            if points <= prior["average"] * ratio_threshold:
                letdowns.append(
                    {
                        "roster_id": roster_id,
                        "player_id": player_id,
                        "points": round(points, 2),
                        "prior_average": prior["average"],
                        "prior_games": prior["games"],
                        "drop": round(prior["average"] - points, 2),
                    }
                )

    return sorted(letdowns, key=lambda row: row["drop"], reverse=True)[:limit]
