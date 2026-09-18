"""Storage abstractions for bot state, cache data, and historical records."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from datetime import datetime, timezone
import json
from typing import Any, Protocol


class Storage(Protocol):
    def put_if_absent(self, pk: str, sk: str, attributes: dict[str, Any] | None = None) -> bool:
        """Create an item only if it does not already exist."""

    def exists(self, pk: str, sk: str) -> bool:
        """Return whether an item exists."""

    def delete(self, pk: str, sk: str) -> None:
        """Delete a reservation after a delivery failure."""

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

    def delete(self, pk: str, sk: str) -> None:
        self._items.pop((pk, sk), None)

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


def _to_dynamodb(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb(item) for item in value]
    return value


def _from_dynamodb(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _from_dynamodb(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_from_dynamodb(item) for item in value]
    return value


class DynamoDBStorage:
    """DynamoDB implementation used by deployed Lambda handlers."""

    def __init__(self, table_name: str, table: Any | None = None) -> None:
        if not table_name:
            raise ValueError("DYNAMODB_TABLE_NAME is required.")
        if table is None:
            import boto3

            table = boto3.resource("dynamodb").Table(table_name)
        self.table = table

    def put_if_absent(self, pk: str, sk: str, attributes: dict[str, Any] | None = None) -> bool:
        item = {"pk": pk, "sk": sk}
        item.update(attributes or {})
        try:
            self.table.put_item(
                Item=_to_dynamodb(item),
                ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
            )
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if error_code == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def exists(self, pk: str, sk: str) -> bool:
        return self.get(pk, sk) is not None

    def delete(self, pk: str, sk: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": sk})

    def get(self, pk: str, sk: str) -> dict[str, Any] | None:
        response = self.table.get_item(Key={"pk": pk, "sk": sk})
        item = response.get("Item")
        return _from_dynamodb(item) if item else None

    def put_snapshot(self, item: dict[str, Any]) -> None:
        if not item.get("pk") or not item.get("sk"):
            raise ValueError("Snapshot item must include pk and sk.")
        self.table.put_item(Item=_to_dynamodb(item))

    def mark_weekly_flag(self, season: str, week: int, flag: str) -> None:
        pk, sk = weekly_key(season, week)
        self.table.update_item(
            Key={"pk": pk, "sk": sk},
            UpdateExpression="SET #flag = :value, updated_at = :updated_at",
            ExpressionAttributeNames={"#flag": flag},
            ExpressionAttributeValues={":value": True, ":updated_at": utc_now_iso()},
        )

    def get_weekly_flags(self, season: str, week: int) -> dict[str, Any]:
        pk, sk = weekly_key(season, week)
        return self.get(pk, sk) or {"pk": pk, "sk": sk}

    def set_players_cache(self, data: Any, fetched_at: str | None = None) -> None:
        """Store the large Sleeper directory in DynamoDB-safe map chunks.

        DynamoDB caps one item at 400 KB.  A full NFL player directory is much
        larger, so only the small metadata record uses ``latest``; data lives
        in stable numbered parts.
        """

        if not isinstance(data, dict):
            raise ValueError("Player cache data must be a dictionary.")
        chunks = _players_cache_chunks(data)
        for index, chunk in enumerate(chunks):
            self.table.put_item(
                Item=_to_dynamodb(
                    {
                        "pk": "PLAYERS_CACHE",
                        "sk": f"part#{index:04d}",
                        "data": chunk,
                    }
                )
            )
        self.table.put_item(
            Item={
                "pk": "PLAYERS_CACHE",
                "sk": "latest",
                "fetched_at": fetched_at or utc_now_iso(),
                "chunk_count": len(chunks),
            }
        )

    def get_players_cache(self) -> dict[str, Any] | None:
        metadata = self.get("PLAYERS_CACHE", "latest")
        if not metadata:
            return None
        # Supports the pre-chunking record shape during a rolling deployment.
        if isinstance(metadata.get("data"), dict):
            return metadata
        chunk_count = metadata.get("chunk_count")
        if not isinstance(chunk_count, (int, float)) or int(chunk_count) < 1:
            return None
        data: dict[str, Any] = {}
        for index in range(int(chunk_count)):
            chunk = self.get("PLAYERS_CACHE", f"part#{index:04d}")
            if not chunk or not isinstance(chunk.get("data"), dict):
                return None
            data.update(chunk["data"])
        return {**metadata, "data": data}


PLAYERS_CACHE_CHUNK_BYTES = 250_000


def _players_cache_chunks(data: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    chunk: dict[str, Any] = {}
    chunk_size = 2
    for player_id, player in data.items():
        encoded_size = len(json.dumps({player_id: player}, separators=(",", ":"), default=str).encode("utf-8"))
        if chunk and chunk_size + encoded_size > PLAYERS_CACHE_CHUNK_BYTES:
            chunks.append(chunk)
            chunk, chunk_size = {}, 2
        chunk[player_id] = player
        chunk_size += encoded_size
    if chunk:
        chunks.append(chunk)
    return chunks or [{}]
