"""Helpers for deriving target fantasy weeks from Sleeper NFL state."""

from __future__ import annotations

from typing import Any


def completed_regular_season_week(state: dict[str, Any]) -> tuple[str, int]:
    season = str(state.get("season") or state.get("previous_season") or "")
    season_type = state.get("season_type")
    week = int(state.get("week") or 0)

    if season_type == "regular":
        completed_week = week - 1
    elif season_type in {"post", "off"}:
        completed_week = int(state.get("leg") or state.get("week") or 0)
        if not season and state.get("previous_season"):
            season = str(state["previous_season"])
    else:
        completed_week = 0

    if not season or completed_week < 1:
        raise ValueError("Sleeper state does not identify a completed regular-season week.")

    return season, completed_week
