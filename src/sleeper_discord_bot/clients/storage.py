"""Storage abstractions for bot state, cache data, and historical records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Protocol


class Storage(Protocol):
    def put_if_absent(self, pk: str, sk: str, attributes: dict[str, Any] | None = None) -> bool:
        """Create an item only if it does not already exist."""

    def exists(self, pk: str, sk: str) -> bool:
        """Return whether an item exists."""

    def get(self, pk: str, sk: str) -> dict[str, Any] | None:
        """Return an item by key."""

    def put_snapshot(self, item: dict[str, Any]) -> None:
        """Store a complete historical snapshot item."""

    def mark_weekly_flag(self, season: str, week: int, flag: str) -> None:
        """Mark one weekly idempotency flag."""

    def get_weekly_flags(self, season: str, week: int) -> dict[str, Any]:
        """Return weekly idempotency state."""

    def set_players_cache(self, data: Any, fetched_at: str | None = None) -> None:
        """Store cached Sleeper player data."""

    def get_players_cache(self) -> dict[str, Any] | None:
        """Return cached Sleeper player data."""


def weekly_key(season: str, week: int) -> tuple[str, str]:
    return "WEEK", f"{season}-{week:02d}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class InMemoryStorage:
    """Simple storage implementation for tests and local handler development."""

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict[str, Any]] = {}

    def put_if_absent(self, pk: str, sk: str, attributes: dict[str, Any] | None = None) -> bool:
        key = (pk, sk)
        if key in self._items:
            return False

        item = {"pk": pk, "sk": sk}
        item.update(deepcopy(attributes or {}))
        self._items[key] = item
        return True

    def exists(self, pk: str, sk: str) -> bool:
        return (pk, sk) in self._items

    def get(self, pk: str, sk: str) -> dict[str, Any] | None:
        item = self._items.get((pk, sk))
        return deepcopy(item) if item else None

    def put_snapshot(self, item: dict[str, Any]) -> None:
        pk = item.get("pk")
        sk = item.get("sk")
        if not pk or not sk:
            raise ValueError("Snapshot item must include pk and sk.")
        self._items[(pk, sk)] = deepcopy(item)

    def mark_weekly_flag(self, season: str, week: int, flag: str) -> None:
        pk, sk = weekly_key(season, week)
        item = self._items.setdefault((pk, sk), {"pk": pk, "sk": sk})
        item[flag] = True
        item["updated_at"] = utc_now_iso()

    def get_weekly_flags(self, season: str, week: int) -> dict[str, Any]:
        pk, sk = weekly_key(season, week)
        return self.get(pk, sk) or {"pk": pk, "sk": sk}

    def set_players_cache(self, data: Any, fetched_at: str | None = None) -> None:
        self._items[("PLAYERS_CACHE", "latest")] = {
            "pk": "PLAYERS_CACHE",
            "sk": "latest",
            "data": deepcopy(data),
            "fetched_at": fetched_at or utc_now_iso(),
        }

    def get_players_cache(self) -> dict[str, Any] | None:
        return self.get("PLAYERS_CACHE", "latest")
