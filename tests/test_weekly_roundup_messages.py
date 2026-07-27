from tests.conftest import load_sample

from sleeper_discord_bot.domain.players import merge_player_lookups, player_lookup_from_stats
from sleeper_discord_bot.messages.weekly_roundup import format_weekly_roundup_message


def test_formats_weekly_roundup_message_from_sample_data(week01_matchups):
    message = format_weekly_roundup_message(
        week=1,
        matchups=week01_matchups,
        rosters=load_sample("rosters.json"),
        users=load_sample("users.json"),
        players_by_id=player_lookup_from_stats(load_sample("weeks/01/stats.json")),
    )

    assert message.startswith("**Week 1 Roundup**")
    assert "**Scoreboard**" in message
    assert "**High / Low**" in message
    assert "Top score: **Team 9** with 174.33 pts" in message
    assert "Low score: **Team 3** with 50.3 pts" in message
    assert len(message) < 2000


def test_weekly_roundup_message_has_one_line_per_matchup(week01_matchups):
    message = format_weekly_roundup_message(
        week=1,
        matchups=week01_matchups,
        rosters=load_sample("rosters.json"),
        users=load_sample("users.json"),
        players_by_id=player_lookup_from_stats(load_sample("weeks/01/stats.json")),
    )

    matchup_lines = [line for line in message.splitlines() if line.startswith("- **Team")]

    assert len(matchup_lines) == 6


def test_weekly_roundup_message_includes_standouts_and_letdowns(week16_matchups):
    players_by_id = merge_player_lookups(
        player_lookup_from_stats(load_sample("weeks/01/stats.json")),
        player_lookup_from_stats(load_sample("weeks/03/stats.json")),
        player_lookup_from_stats(load_sample("weeks/10/stats.json")),
        player_lookup_from_stats(load_sample("weeks/16/stats.json")),
    )
    message = format_weekly_roundup_message(
        week=16,
        matchups=week16_matchups,
        rosters=load_sample("rosters.json"),
        users=load_sample("users.json"),
        players_by_id=players_by_id,
        prior_matchups_by_week=[
            load_sample("weeks/01/matchups.json"),
            load_sample("weeks/03/matchups.json"),
            load_sample("weeks/10/matchups.json"),
        ],
    )

    assert "**Standout Starters**" in message
    assert "Puka Nacua (WR/LAR)" in message
    assert "**Letdowns**" in message
    assert "Player " not in message
    assert len(message) < 2000
