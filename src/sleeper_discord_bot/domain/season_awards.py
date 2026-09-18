"""Aggregate raw Sleeper records into end-of-season award candidates."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sleeper_discord_bot.domain.awards import bench_regrets, draft_pick_value, schedule_luck, trade_player_impact
from sleeper_discord_bot.domain.trades import completed_trades


def _season_player_points(matchups_by_week: list[list[dict[str, Any]]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for matchups in matchups_by_week:
        for matchup in matchups:
            for player_id, points in (matchup.get("players_points") or {}).items():
                totals[str(player_id)] += float(points or 0.0)
    return {player_id: round(points, 2) for player_id, points in totals.items()}


def _aggregate_by_roster(rows_by_week: list[list[dict[str, Any]]], metric: str) -> list[dict[str, Any]]:
    totals: dict[int, float] = defaultdict(float)
    for rows in rows_by_week:
        for row in rows:
            totals[int(row["roster_id"])] += float(row[metric])
    return [
        {"roster_id": roster_id, metric: round(value, 2)}
        for roster_id, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
    ]


def build_season_awards(
    *,
    matchups_by_week: list[list[dict[str, Any]]],
    transactions_by_week: list[list[dict[str, Any]]],
    draft_picks: list[dict[str, Any]],
    players_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return objective candidates for trade, draft, waiver, lineup, and schedule awards."""

    season_points = _season_player_points(matchups_by_week)
    trades = []
    waivers = []
    for week, transactions in enumerate(transactions_by_week, start=1):
        future_matchups = matchups_by_week[week:]
        for transaction in completed_trades(transactions):
            for roster_id, impact in trade_player_impact(transaction, future_matchups).items():
                trades.append({"transaction_id": transaction["transaction_id"], "week": week, "roster_id": roster_id, **impact})
        for transaction in transactions:
            if transaction.get("status") != "complete" or transaction.get("type") not in {"waiver", "free_agent"}:
                continue
            for roster_id, impact in trade_player_impact(transaction, future_matchups).items():
                waivers.append({"transaction_id": transaction["transaction_id"], "week": week, "roster_id": roster_id, **impact})

    regrets_by_roster: dict[int, float] = defaultdict(float)
    for matchups in matchups_by_week:
        for regret in bench_regrets(matchups, players_by_id):
            regrets_by_roster[regret["roster_id"]] += regret["points_left"]

    draft_values = [
        {**row, "position": players_by_id.get(row["player_id"], {}).get("position")}
        for row in draft_pick_value(draft_picks, season_points)
    ]
    by_position: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in draft_values:
        if row["position"]:
            by_position[row["position"]].append(row)
    for rows in by_position.values():
        drafted = sorted(rows, key=lambda row: row["pick_no"])
        produced = sorted(rows, key=lambda row: (-row["points"], row["pick_no"]))
        draft_rank = {row["player_id"]: index for index, row in enumerate(drafted, start=1)}
        production_rank = {row["player_id"]: index for index, row in enumerate(produced, start=1)}
        for row in rows:
            row["position_value_delta"] = draft_rank[row["player_id"]] - production_rank[row["player_id"]]
    early_qb_te = sorted(
        [row for row in draft_values if row["pick_no"] <= 36 and row["position"] in {"QB", "TE"}],
        key=lambda row: (-row["position_value_delta"], row["pick_no"]),
    )
    return {
        "trade_impact": sorted(trades, key=lambda row: row["total_points"], reverse=True),
        "draft_value": draft_values,
        "early_qb_te": early_qb_te,
        "waiver_returns": sorted(waivers, key=lambda row: row["total_points"], reverse=True),
        "bench_regrets": [
            {"roster_id": roster_id, "points_left": round(points, 2)}
            for roster_id, points in sorted(regrets_by_roster.items(), key=lambda item: item[1], reverse=True)
        ],
        "schedule_luck": _aggregate_by_roster(
            [schedule_luck(matchups) for matchups in matchups_by_week], "luck_delta"
        ),
    }
