from tests.conftest import load_sample

from sleeper_discord_bot.domain.players import player_lookup_from_stats
from sleeper_discord_bot.domain.trades import completed_trades
from sleeper_discord_bot.messages.trades import format_trade_message


def test_formats_trade_message_with_players_and_picks(week01_transactions):
    trade = completed_trades(week01_transactions)[0]
    players_by_id = player_lookup_from_stats(load_sample("weeks/01/stats.json"))

    message = format_trade_message(
        transaction=trade,
        rosters=load_sample("rosters.json"),
        users=load_sample("users.json"),
        players_by_id=players_by_id,
    )

    assert message.startswith("**Trade Alert: Team 9 <-> Team 2**")
    assert "RJ Harvey (RB/DEN)" in message
    assert "A.J. Brown (WR/NE)" in message
    assert "2027 round 2" in message
    assert "2027 round 3" in message
    assert len(message) < 2000
