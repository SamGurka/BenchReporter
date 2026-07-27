from tests.conftest import load_sample

from sleeper_discord_bot.domain.history import build_team_week_snapshots, build_trade_snapshot
from sleeper_discord_bot.domain.players import player_lookup_from_stats
from sleeper_discord_bot.domain.trades import completed_trades


def test_builds_team_week_snapshots(week01_matchups):
    players_by_id = player_lookup_from_stats(load_sample("weeks/01/stats.json"))

    snapshots = build_team_week_snapshots(
        season="2025",
        week=1,
        matchups=week01_matchups,
        rosters=load_sample("rosters.json"),
        users=load_sample("users.json"),
        players_by_id=players_by_id,
    )

    first = snapshots[0]

    assert len(snapshots) == 12
    assert first["pk"] == "TEAM#1"
    assert first["sk"] == "WEEK#2025#01"
    assert first["team_name"] == "Team 4"
    assert first["points_for"] == 163.61
    assert first["result"] == "win"
    assert len(first["starters"]) == 10
    assert len(first["bench"]) > 0
    assert sum(first["position_points"].values()) == 163.61


def test_builds_trade_snapshot(week01_transactions):
    trade = completed_trades(week01_transactions)[0]
    players_by_id = player_lookup_from_stats(load_sample("weeks/01/stats.json"))

    snapshot = build_trade_snapshot(
        season="2025",
        week=1,
        transaction=trade,
        rosters=load_sample("rosters.json"),
        users=load_sample("users.json"),
        players_by_id=players_by_id,
    )

    assert snapshot["pk"] == f"TRADE#{trade['transaction_id']}"
    assert snapshot["sk"] == "META"
    assert snapshot["roster_ids"] == [2, 5]
    assert snapshot["sides"]["2"]["team_name"] == "Team 9"
    assert snapshot["sides"]["2"]["received_players"] == ["RJ Harvey (RB/DEN)"]
    assert snapshot["sides"]["2"]["received_picks"] == ["2027 round 2"]
