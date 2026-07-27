"""HTTP client for Sleeper API routes used by the bot."""

from __future__ import annotations

from typing import Any

import requests


class SleeperClient:
    def __init__(
        self,
        base_url: str = "https://api.sleeper.app/v1",
        stats_base_url: str = "https://api.sleeper.com/stats/nfl",
        timeout_sec: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.stats_base_url = stats_base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    def _get(self, path: str) -> Any:
        response = requests.get(f"{self.base_url}{path}", timeout=self.timeout_sec)
        response.raise_for_status()
        return response.json()

    def _get_stats(self, path: str) -> Any:
        response = requests.get(f"{self.stats_base_url}{path}", timeout=self.timeout_sec)
        response.raise_for_status()
        return response.json()

    def league(self, league_id: str) -> dict[str, Any]:
        return self._get(f"/league/{league_id}")

    def rosters(self, league_id: str) -> list[dict[str, Any]]:
        return self._get(f"/league/{league_id}/rosters")

    def users(self, league_id: str) -> list[dict[str, Any]]:
        return self._get(f"/league/{league_id}/users")

    def matchups(self, league_id: str, week: int) -> list[dict[str, Any]]:
        return self._get(f"/league/{league_id}/matchups/{week}")

    def transactions(self, league_id: str, week: int) -> list[dict[str, Any]]:
        return self._get(f"/league/{league_id}/transactions/{week}")

    def drafts(self, league_id: str) -> list[dict[str, Any]]:
        return self._get(f"/league/{league_id}/drafts")

    def draft_picks(self, draft_id: str) -> list[dict[str, Any]]:
        return self._get(f"/draft/{draft_id}/picks")

    def players(self) -> dict[str, Any]:
        return self._get("/players/nfl")

    def nfl_state(self) -> dict[str, Any]:
        return self._get("/state/nfl")

    def weekly_stats(self, season: str, week: int) -> Any:
        return self._get_stats(f"/{season}/{week}?season_type=regular")
