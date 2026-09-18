"""Free-agent ranking and context helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


FREE_AGENT_POSITIONS = {"QB", "RB", "WR", "TE"}
INJURY_OPPORTUNITY_STATUSES = {
    "Q",
    "QUESTIONABLE",
    "D",
    "DOUBTFUL",
    "OUT",
    "IR",
    "INJURED RESERVE",
    "PUP",
    "PHYSICALLY UNABLE TO PERFORM",
}


def _entries(stats: Any) -> Iterable[dict[str, Any]]:
    if isinstance(stats, dict):
        values = stats.values()
    elif isinstance(stats, list):
        values = stats
    else:
        return []
    return (entry for entry in values if isinstance(entry, dict))


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def rostered_player_ids(rosters: list[dict[str, Any]]) -> set[str]:
    return {
        str(player_id)
        for roster in rosters
        for player_id in roster.get("players") or []
        if player_id is not None
    }


def _injury_status(player: dict[str, Any]) -> str | None:
    for field in ("injury_status", "status"):
        value = player.get(field)
        if not isinstance(value, str):
            continue
        normalized = value.upper().replace("_", " ").replace("-", " ").strip()
        if normalized in INJURY_OPPORTUNITY_STATUSES:
            return normalized
    return None


def injury_context_by_team_and_position(
    rostered_ids: set[str],
    players_by_id: dict[str, dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Return rostered, injury-designated players grouped by team and position."""

    context: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for player_id in rostered_ids:
        player = players_by_id.get(player_id, {})
        team, position, status = player.get("team"), player.get("position"), _injury_status(player)
        if team and position in FREE_AGENT_POSITIONS and status:
            context[(team, position)].append(
                {
                    "name": player.get("name", f"Player {player_id}"),
                    "status": status,
                    "depth_chart_order": _depth_chart_order(player),
                }
            )
    return context


def _depth_chart_order(player: dict[str, Any]) -> int | None:
    try:
        return int(player["depth_chart_order"])
    except (KeyError, TypeError, ValueError):
        return None


def _blocked_by_healthy_depth_chart_player(
    player: dict[str, Any],
    players_by_id: dict[str, dict[str, Any]],
) -> bool:
    """Whether a third-or-later-string player has a healthy first/second string ahead."""

    order = _depth_chart_order(player)
    team = player.get("team")
    if not team or order is None or order <= 2:
        return False
    depth_position = player.get("depth_chart_position") or player.get("position")
    return any(
        teammate.get("team") == team
        and (teammate.get("depth_chart_position") or teammate.get("position")) == depth_position
        and (_depth_chart_order(teammate) or 99) <= 2
        and _injury_status(teammate) is None
        for teammate in players_by_id.values()
    )


def _prior_points_by_player(
    prior_weekly_stats: list[Any],
    stats_field: str,
) -> dict[str, list[float]]:
    points: dict[str, list[float]] = defaultdict(list)
    for stats in prior_weekly_stats:
        for entry in _entries(stats):
            player_id = entry.get("player_id")
            stat_block = entry.get("stats")
            if player_id is None or not isinstance(stat_block, dict) or stats_field not in stat_block:
                continue
            points[str(player_id)].append(_number(stat_block[stats_field]))
    return points


def rank_free_agents(
    *,
    weekly_stats: Any,
    rosters: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
    stats_field: str,
    prior_weekly_stats: list[Any] | None = None,
    limit: int = 100,
    injury_only_directory_fallback: bool = False,
    projected: bool = False,
) -> list[dict[str, Any]]:
    """Rank available QB/RB/WR/TE options by their positional weekly margin."""

    rostered_ids = rostered_player_ids(rosters)
    injury_context = injury_context_by_team_and_position(rostered_ids, players_by_id)
    prior_by_player = _prior_points_by_player(prior_weekly_stats or [], stats_field)
    candidates: list[dict[str, Any]] = []

    for entry in _entries(weekly_stats):
        player_id = entry.get("player_id")
        stat_block = entry.get("stats")
        if player_id is None or not isinstance(stat_block, dict) or stats_field not in stat_block:
            continue
        player_id = str(player_id)
        if player_id in rostered_ids:
            continue

        stat_player = entry.get("player") if isinstance(entry.get("player"), dict) else {}
        player = players_by_id.get(player_id, {})
        position = player.get("position") or stat_player.get("position")
        if position not in FREE_AGENT_POSITIONS:
            continue

        prior_points = prior_by_player.get(player_id, [])
        candidate = {
                "player_id": player_id,
                "name": player.get("name") or " ".join(
                    part for part in [stat_player.get("first_name"), stat_player.get("last_name")] if part
                ) or f"Player {player_id}",
                "position": position,
                "team": player.get("team") or stat_player.get("team") or entry.get("team"),
                "years_exp": player.get("years_exp", stat_player.get("years_exp")),
                "points": round(_number(stat_block[stats_field]), 2),
                "prior_games": len(prior_points),
                "prior_average": round(sum(prior_points) / len(prior_points), 2) if prior_points else None,
        }
        if projected:
            candidate["projected"] = True
        candidates.append(candidate)

    if not candidates and injury_only_directory_fallback:
        for player_id, player in players_by_id.items():
            position, team = player.get("position"), player.get("team")
            if player_id in rostered_ids or position not in FREE_AGENT_POSITIONS or not team:
                continue
            if not injury_context.get((team, position)):
                continue
            candidates.append(
                {
                    "player_id": player_id,
                    "name": player.get("name") or f"Player {player_id}",
                    "position": position,
                    "team": team,
                    "years_exp": player.get("years_exp"),
                    "points": 0.0,
                    "prior_games": 0,
                    "prior_average": None,
                    "preseason": True,
                }
            )

    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        totals[candidate["position"]] += candidate["points"]
        counts[candidate["position"]] += 1

    for candidate in candidates:
        position = candidate["position"]
        average = round(totals[position] / counts[position], 2)
        candidate["position_average"] = average
        candidate["margin"] = round(candidate["points"] - average, 2)
        candidate_order = _depth_chart_order(players_by_id.get(candidate["player_id"], {}))
        candidate["injury_context"] = [
            injured
            for injured in injury_context.get((candidate.get("team"), position), [])
            if candidate_order is None
            or injured["depth_chart_order"] is None
            or candidate_order > injured["depth_chart_order"]
        ]
        if candidate["injury_context"] and _blocked_by_healthy_depth_chart_player(
            players_by_id.get(candidate["player_id"], {}), players_by_id
        ):
            candidate["injury_context"] = []
        candidate["label"] = "Injury Opportunity" if candidate["injury_context"] else _label(candidate)

    if injury_only_directory_fallback:
        candidates = [candidate for candidate in candidates if candidate["injury_context"]]

    return sorted(candidates, key=lambda candidate: (candidate["margin"], candidate["points"]), reverse=True)[:limit]


def select_free_agent_sections(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the three report sections without repeating a player."""
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    for section, rows, max_items in (
        ("standout", [row for row in candidates if row["margin"] > 0 and not row["injury_context"] and row["label"] != "Proven Free Agent"], 4),
        ("proven", [row for row in candidates if row["label"] == "Proven Free Agent" and not row["injury_context"]], 3),
        ("injury", [row for row in candidates if row["injury_context"]], 3),
    ):
        for candidate in rows:
            if candidate["player_id"] in selected_ids:
                continue
            candidate["report_section"] = section
            selected.append(candidate)
            selected_ids.add(candidate["player_id"])
            if sum(row["report_section"] == section for row in selected) >= max_items:
                break
    return selected


def _label(candidate: dict[str, Any]) -> str | None:
    prior_average = candidate["prior_average"]
    years_exp = candidate["years_exp"]
    if candidate["prior_games"] >= 2 and prior_average is not None and prior_average >= 8:
        return "Proven Free Agent"
    return None
