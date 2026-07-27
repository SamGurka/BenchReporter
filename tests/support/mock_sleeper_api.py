"""FastAPI mock of the Sleeper routes used by the bot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "tests" / "data" / "sleeper_2025_sample"


def load_json(path: Path) -> Any:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing mock data: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def _stats_entries(stats: Any) -> Any:
    return stats.values() if isinstance(stats, dict) else stats


def build_players_directory(data_dir: Path) -> dict[str, Any]:
    players: dict[str, Any] = {}
    for stats_path in sorted((data_dir / "weeks").glob("*/stats.json")):
        for entry in _stats_entries(load_json(stats_path)):
            player_id = entry.get("player_id")
            player = entry.get("player") or {}
            if player_id:
                players[str(player_id)] = {
                    "player_id": str(player_id),
                    "first_name": player.get("first_name"),
                    "last_name": player.get("last_name"),
                    "full_name": player.get("full_name"),
                    "position": player.get("position"),
                    "team": player.get("team") or entry.get("team"),
                }
    return players


def create_mock_sleeper_app(data_dir: Path = DEFAULT_DATA_DIR) -> FastAPI:
    app = FastAPI(title="Mock Sleeper API")

    @app.get("/league/{league_id}")
    def league(league_id: str) -> Any:
        return load_json(data_dir / "league.json")

    @app.get("/league/{league_id}/users")
    def users(league_id: str) -> Any:
        return load_json(data_dir / "users.json")

    @app.get("/league/{league_id}/rosters")
    def rosters(league_id: str) -> Any:
        return load_json(data_dir / "rosters.json")

    @app.get("/league/{league_id}/matchups/{week}")
    def matchups(league_id: str, week: int) -> Any:
        return load_json(data_dir / "weeks" / f"{week:02d}" / "matchups.json")

    @app.get("/league/{league_id}/transactions/{week}")
    def transactions(league_id: str, week: int) -> Any:
        return load_json(data_dir / "weeks" / f"{week:02d}" / "transactions.json")

    @app.get("/league/{league_id}/drafts")
    def drafts(league_id: str) -> Any:
        return load_json(data_dir / "drafts" / "drafts.json")

    @app.get("/draft/{draft_id}/picks")
    def draft_picks(draft_id: str) -> Any:
        return load_json(data_dir / "drafts" / draft_id / "picks.json")

    @app.get("/state/nfl")
    def nfl_state() -> Any:
        return load_json(data_dir / "state_nfl.json")

    @app.get("/players/nfl")
    def players() -> Any:
        return build_players_directory(data_dir)

    @app.get("/stats/nfl/{season}/{week}")
    def weekly_stats(season: str, week: int, season_type: str = "regular") -> Any:
        if season_type != "regular":
            raise HTTPException(status_code=404, detail="Only regular-season mock stats exist.")
        return load_json(data_dir / "weeks" / f"{week:02d}" / "stats.json")

    return app


app = create_mock_sleeper_app()
