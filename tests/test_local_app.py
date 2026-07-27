from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sleeper_discord_bot import local_app


SAMPLE_DATA = Path(__file__).resolve().parent / "data" / "sleeper_2025_sample"


class LocalAppSleeper:
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
        return {}

    def nfl_state(self) -> dict[str, Any]:
        return self._load("state_nfl.json")


def test_local_app_runs_weekly_command(monkeypatch, capsys):
    monkeypatch.setattr(local_app, "build_sleeper", lambda config: LocalAppSleeper())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "local_app",
            "--league-id",
            "sample_league",
            "--season",
            "2025",
            "weekly",
            "--week",
            "16",
            "--prior-weeks",
            "1,3,10",
        ],
    )

    assert local_app.main() == 0

    output = capsys.readouterr().out
    assert "[last_week_tldr] Week 16 Roundup" in output
    assert "Result: posted=1 skipped=0 snapshots=12" in output


def test_local_app_runs_trades_command(monkeypatch, capsys):
    monkeypatch.setattr(local_app, "build_sleeper", lambda config: LocalAppSleeper())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "local_app",
            "--league-id",
            "sample_league",
            "--season",
            "2025",
            "trades",
            "--week",
            "1",
        ],
    )

    assert local_app.main() == 0

    output = capsys.readouterr().out
    assert "[trade_block] Trade Alert" in output
    assert "Result: posted=" in output
