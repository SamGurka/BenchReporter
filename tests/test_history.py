import pytest

from tests.conftest import load_sample

from sleeper_discord_bot.domain.history import (
    build_draft_pick_snapshots,
    build_roster_move_snapshot,
    build_team_week_snapshots,
    build_trade_snapshot,
)
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
    assert sum(first["position_points"].values()) == pytest.approx(163.61)


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


def test_builds_draft_pick_snapshots():
    snapshots = build_draft_pick_snapshots(
        "2025",
        load_sample("drafts/drafts.json")[0],
        load_sample("drafts/sample_draft_01/picks.json"),
        player_lookup_from_stats(load_sample("weeks/01/stats.json")),
    )

    assert snapshots[0]["pk"] == "DRAFT#sample_draft_01"
    assert snapshots[0]["sk"] == "PICK#001"
    assert snapshots[0]["player"] == "Jahmyr Gibbs (RB/DET)"
    assert snapshots[0]["auction_amount"] == "199"


def test_builds_waiver_snapshot_with_faab():
    transaction = {
        "transaction_id": "waiver-1",
        "type": "waiver",
        "adds": {"8138": 2},
        "drops": {"5859": 2},
        "waiver_budget": [{"sender": 2, "receiver": 0, "amount": 17}],
    }
    snapshot = build_roster_move_snapshot(
        "2025",
        1,
        transaction,
        load_sample("rosters.json"),
        load_sample("users.json"),
        player_lookup_from_stats(load_sample("weeks/01/stats.json")),
    )

    assert snapshot["pk"] == "MOVE#waiver-1"
    assert snapshot["sides"]["2"]["added_players"] == ["James Cook (RB/BUF)"]
    assert snapshot["faab"] == {0: ["$17 FAAB"]}
