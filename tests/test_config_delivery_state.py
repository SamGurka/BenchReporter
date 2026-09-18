from __future__ import annotations

import pytest

from sleeper_discord_bot.config import AppConfig
from sleeper_discord_bot.delivery import ConsoleDelivery, DiscordDelivery
from sleeper_discord_bot.domain.nfl_state import completed_regular_season_week
from sleeper_discord_bot.messages.bot_message import split_content
from sleeper_discord_bot.messages.bot_message import BotMessage


class FakeDiscordClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def send_message(self, channel_id: str, content: str) -> str:
        self.calls.append((channel_id, content))
        return "sent"


def test_config_loads_expected_environment_values():
    config = AppConfig.from_env(
        {
            "SLEEPER_LEAGUE_ID": "league-1",
            "SEASON": "2025",
            "SLEEPER_BASE_URL": "http://sleeper.test",
            "SLEEPER_STATS_BASE_URL": "http://stats.test",
            "DRY_RUN": "false",
            "DISCORD_BOT_TOKEN": "token",
            "DISCORD_CHANNEL_LAST_WEEK_TLDR": "channel-1",
        }
    )

    assert config.sleeper_league_id == "league-1"
    assert config.season == "2025"
    assert config.sleeper_base_url == "http://sleeper.test"
    assert config.sleeper_stats_base_url == "http://stats.test"
    assert config.dry_run is False
    assert config.discord_bot_token == "token"
    assert config.channel_ids["last_week_tldr"] == "channel-1"


def test_config_requires_league_id():
    with pytest.raises(ValueError, match="SLEEPER_LEAGUE_ID"):
        AppConfig(sleeper_league_id="").require_league_id()


def test_console_delivery_prints_structured_message(capsys):
    delivery = ConsoleDelivery()
    message = BotMessage(
        feature="weekly_roundup",
        channel_key="last_week_tldr",
        title="Week 1 Roundup",
        content="hello",
    )

    delivery.send(message)

    assert delivery.messages == [message]
    output = capsys.readouterr().out
    assert "[last_week_tldr] Week 1 Roundup" in output
    assert "hello" in output


def test_discord_delivery_maps_channel_key_to_channel_id():
    client = FakeDiscordClient()
    delivery = DiscordDelivery(client=client, channel_ids={"trade_block": "channel-2"})

    delivery.send(BotMessage(feature="trade_watch", channel_key="trade_block", title="Trade", content="hello"))

    assert client.calls == [("channel-2", "hello")]
    assert delivery.sent == ["sent"]


def test_discord_delivery_requires_channel_mapping():
    delivery = DiscordDelivery(client=FakeDiscordClient(), channel_ids={})

    with pytest.raises(ValueError, match="trade_block"):
        delivery.send(BotMessage(feature="trade_watch", channel_key="trade_block", title="Trade", content="hello"))


def test_completed_regular_season_week_during_regular_season():
    assert completed_regular_season_week({"season": "2025", "season_type": "regular", "week": 4}) == ("2025", 3)


def test_completed_regular_season_week_rejects_preseason():
    with pytest.raises(ValueError):
        completed_regular_season_week({"season": "2025", "season_type": "pre", "week": 1})


def test_completed_regular_season_week_rejects_unfinished_week_one():
    with pytest.raises(ValueError):
        completed_regular_season_week({"season": "2025", "season_type": "regular", "week": 1})


def test_completed_regular_season_week_handles_postseason_and_offseason():
    assert completed_regular_season_week({"season": "2025", "season_type": "post", "leg": 18}) == ("2025", 18)
    assert completed_regular_season_week({"previous_season": "2025", "season_type": "off", "leg": 18}) == ("2025", 18)


def test_split_content_is_line_safe_and_never_exceeds_discord_limit():
    chunks = split_content("first\n" + "x" * 2001)

    assert all(len(chunk) <= 2000 for chunk in chunks)
    assert "first" in chunks[0]
