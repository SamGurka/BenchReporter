"""Player lookup helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from sleeper_discord_bot.clients.storage import Storage


def player_name(player: dict[str, Any]) -> str:
    first_name = player.get("first_name")
    last_name = player.get("last_name")
    full_name = " ".join(part for part in [first_name, last_name] if part)
    return full_name or player.get("full_name") or player.get("player_id") or "Unknown Player"


def player_lookup_from_stats(stats: list[dict[str, Any]] | dict[str, Any]) -> dict[str, dict[str, Any]]:
    if isinstance(stats, dict):
        entries = stats.values()
    else:
        entries = stats

    lookup = {}
    for entry in entries:
        player_id = entry.get("player_id")
        player = entry.get("player") or {}
        if player_id:
            normalized = {
                "player_id": str(player_id),
                "name": player_name({**player, "player_id": str(player_id)}),
                "position": player.get("position"),
                "team": player.get("team") or entry.get("team"),
            }
            if player.get("years_exp") is not None:
                normalized["years_exp"] = player["years_exp"]
            for field in ("status", "injury_status", "depth_chart_order", "depth_chart_position"):
                if player.get(field) is not None:
                    normalized[field] = player[field]
            lookup[str(player_id)] = normalized
    return lookup


def player_lookup_from_directory(directory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup = {}
    for player_id, player in directory.items():
        if not isinstance(player, dict):
            continue
        normalized = {
            "player_id": str(player_id),
            "name": player_name({**player, "player_id": str(player_id)}),
            "position": player.get("position"),
            "team": player.get("team"),
        }
        if player.get("years_exp") is not None:
            normalized["years_exp"] = player["years_exp"]
        for field in ("status", "injury_status", "depth_chart_order", "depth_chart_position"):
            if player.get(field) is not None:
                normalized[field] = player[field]
        lookup[str(player_id)] = normalized
    return lookup


def merge_player_lookups(*lookups: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for lookup in lookups:
        for player_id, player in lookup.items():
            if player_id not in merged or merged[player_id]["name"].startswith("Player "):
                merged[player_id] = player
    return merged


def format_player(player_id: str, players_by_id: dict[str, dict[str, Any]]) -> str:
    player = players_by_id.get(str(player_id))
    if not player:
        return f"Player {player_id}"

    suffix_parts = [player.get("position"), player.get("team")]
    suffix = "/".join(part for part in suffix_parts if part)
    return f"{player['name']} ({suffix})" if suffix else player["name"]


class PlayerDirectoryClient(Protocol):
    def players(self) -> dict[str, Any]: ...


PLAYER_CACHE_TTL = timedelta(hours=24)


def _cache_is_fresh(cached: dict[str, Any], now: datetime) -> bool:
    fetched_at = cached.get("fetched_at")
    if not isinstance(fetched_at, str):
        return False
    try:
        timestamp = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if timestamp.tzinfo is None:
        return False
    return now - timestamp.astimezone(timezone.utc) < PLAYER_CACHE_TTL


def cached_player_lookup(
    storage: Storage,
    sleeper: PlayerDirectoryClient,
    *,
    now: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    cached = storage.get_players_cache()
    now = now or datetime.now(timezone.utc)
    if cached is not None and isinstance(cached.get("data"), dict) and _cache_is_fresh(cached, now):
        return cached["data"]

    lookup = player_lookup_from_directory(sleeper.players())
    storage.set_players_cache(lookup, fetched_at=now.replace(microsecond=0).isoformat())
    return lookup
