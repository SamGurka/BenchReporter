from __future__ import annotations

from sleeper_discord_bot.clients.storage import InMemoryStorage
from sleeper_discord_bot.domain.players import cached_player_lookup, player_lookup_from_directory


class FakeSleeper:
    def __init__(self) -> None:
        self.calls = 0

    def players(self) -> dict[str, dict[str, str]]:
        self.calls += 1
        return {
            "1": {
                "first_name": "Puka",
                "last_name": "Nacua",
                "position": "WR",
                "team": "LAR",
            }
        }


def test_player_lookup_from_directory_normalizes_sleeper_players():
    lookup = player_lookup_from_directory(
        {
            "1": {
                "full_name": "Puka Nacua",
                "position": "WR",
                "team": "LAR",
            }
        }
    )

    assert lookup["1"] == {
        "player_id": "1",
        "name": "Puka Nacua",
        "position": "WR",
        "team": "LAR",
    }


def test_cached_player_lookup_fetches_once():
    storage = InMemoryStorage()
    sleeper = FakeSleeper()

    first = cached_player_lookup(storage, sleeper)
    second = cached_player_lookup(storage, sleeper)

    assert first == second
    assert sleeper.calls == 1
