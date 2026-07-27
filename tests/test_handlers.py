from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sleeper_discord_bot.clients.storage import InMemoryStorage
from sleeper_discord_bot.domain.trades import completed_trades
from sleeper_discord_bot.handlers.trade_watch import run_trade_watch
from sleeper_discord_bot.handlers.weekly_roundup import run_weekly_roundup
from sleeper_discord_bot.messages.bot_message import BotMessage


SAMPLE_DATA = Path(__file__).resolve().parent / "data" / "sleeper_2025_sample"


class SampleSleeper:
    def _load(self, relative_path: str) -> Any:
        return json.loads((SAMPLE_DATA / relative_path).read_text(encoding="utf-8"))

    def rosters(self, league_id: str) -> list[dict[str, Any]]:
        return self._load("rosters.json")

    def users(self, league_id: str) -> list[dict[str, Any]]:
        return self._load("users.json")

    def matchups(self, league_id: str, week: int) -> list[dict[str, Any]]:
        return self._load(f"weeks/{week:02d}/matchups.json")

    def transactions(self, league_id: str, week: int) -> list[dict[str, Any]]:
        return self._load(f"weeks/{week:02d}/transactions.json")

    def weekly_stats(self, season: str, week: int) -> Any:
        return self._load(f"weeks/{week:02d}/stats.json")

    def players(self) -> dict[str, Any]:
        lookup = {}
        for week in [1, 3, 10, 16]:
            stats = self._load(f"weeks/{week:02d}/stats.json")
            entries = stats.values() if isinstance(stats, dict) else stats
            for entry in entries:
                player_id = entry.get("player_id")
                player = entry.get("player") or {}
                if player_id:
                    lookup[str(player_id)] = {
                        "player_id": str(player_id),
                        "first_name": player.get("first_name"),
                        "last_name": player.get("last_name"),
                        "full_name": player.get("full_name"),
                        "position": player.get("position"),
                        "team": player.get("team") or entry.get("team"),
                    }
        return lookup

    def nfl_state(self) -> dict[str, Any]:
        return self._load("state_nfl.json")


def test_weekly_roundup_posts_once_and_writes_team_snapshots():
    sleeper = SampleSleeper()
    storage = InMemoryStorage()
    sent_messages: list[BotMessage] = []

    result = run_weekly_roundup(
        sleeper=sleeper,
        storage=storage,
        league_id="sample_league",
        season="2025",
        week=16,
        prior_weeks=[1, 3, 10],
        send_message=sent_messages.append,
    )

    assert result.posted_count == 1
    assert result.snapshots_written == 12
    assert sent_messages == result.messages
    assert sent_messages[0].feature == "weekly_roundup"
    assert sent_messages[0].channel_key == "last_week_tldr"
    assert sent_messages[0].title == "Week 16 Roundup"
    assert "**Week 16 Roundup**" in sent_messages[0].content
    assert storage.get_weekly_flags("2025", 16)["roundup_posted"] is True
    assert storage.get("TEAM#1", "WEEK#2025#16") is not None

    second_result = run_weekly_roundup(
        sleeper=sleeper,
        storage=storage,
        league_id="sample_league",
        season="2025",
        week=16,
        prior_weeks=[1, 3, 10],
        send_message=sent_messages.append,
    )

    assert second_result.posted_count == 0
    assert second_result.skipped_count == 1
    assert second_result.snapshots_written == 0
    assert len(sent_messages) == 1


def test_trade_watch_posts_new_completed_trades_once_and_writes_snapshots():
    sleeper = SampleSleeper()
    storage = InMemoryStorage()
    sent_messages: list[BotMessage] = []
    expected_trades = completed_trades(sleeper.transactions("sample_league", 1))

    result = run_trade_watch(
        sleeper=sleeper,
        storage=storage,
        league_id="sample_league",
        season="2025",
        week=1,
        send_message=sent_messages.append,
    )

    assert result.posted_count == len(expected_trades)
    assert result.snapshots_written == len(expected_trades)
    assert sent_messages == result.messages
    assert sent_messages[0].feature == "trade_watch"
    assert sent_messages[0].channel_key == "trade_block"
    assert sent_messages[0].title == "Trade Alert"
    assert sent_messages[0].content.startswith("**Trade Alert:")

    second_result = run_trade_watch(
        sleeper=sleeper,
        storage=storage,
        league_id="sample_league",
        season="2025",
        week=1,
        send_message=sent_messages.append,
    )

    assert second_result.posted_count == 0
    assert second_result.skipped_count == len(expected_trades)
    assert len(sent_messages) == len(expected_trades)
