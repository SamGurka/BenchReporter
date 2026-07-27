from sleeper_discord_bot.domain.weekly_roundup import (
    bench_player_ids,
    has_player_points,
    letdown_starters,
    pair_matchups,
    standout_starters,
    starter_position_averages,
    weekly_high_low,
)
from sleeper_discord_bot.domain.players import player_lookup_from_stats
from tests.conftest import load_sample


def test_pairs_weekly_matchups(week01_matchups):
    pairs = pair_matchups(week01_matchups)

    assert len(pairs) == 6
    assert all(left["matchup_id"] == right["matchup_id"] for left, right in pairs)


def test_finds_weekly_high_and_low(week01_matchups):
    high, low = weekly_high_low(week01_matchups)

    assert high["points"] == 174.33
    assert low["points"] == 50.3


def test_sample_matchups_include_player_points(week01_matchups):
    assert has_player_points(week01_matchups)


def test_bench_players_are_players_minus_starters(week01_matchups):
    matchup = week01_matchups[0]
    bench = bench_player_ids(matchup)

    assert set(bench).isdisjoint(set(matchup["starters"]))
    assert len(bench) == len(set(matchup["players"]) - set(matchup["starters"]))


def test_computes_starter_position_averages(week01_matchups):
    players_by_id = player_lookup_from_stats(load_sample("weeks/01/stats.json"))

    averages = starter_position_averages(week01_matchups, players_by_id)

    assert averages["QB"] == 19.94
    assert averages["RB"] > 10
    assert averages["WR"] > 10


def test_finds_standout_starters(week16_matchups):
    players_by_id = player_lookup_from_stats(load_sample("weeks/16/stats.json"))

    standouts = standout_starters(week16_matchups, players_by_id)

    assert standouts
    assert standouts[0]["player_id"] == "9493"
    assert standouts[0]["points"] == 46.5


def test_finds_letdown_starters_with_prior_weeks(week16_matchups):
    prior_weeks = [
        load_sample("weeks/01/matchups.json"),
        load_sample("weeks/03/matchups.json"),
        load_sample("weeks/10/matchups.json"),
    ]

    letdowns = letdown_starters(week16_matchups, prior_weeks, min_prior_games=2)

    assert letdowns
    assert all(row["points"] <= row["prior_average"] * 0.5 for row in letdowns)
