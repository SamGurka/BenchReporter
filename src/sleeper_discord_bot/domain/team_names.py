"""Helpers for resolving Sleeper roster IDs to display names."""

from __future__ import annotations

from typing import Any


def user_display_name(user: dict[str, Any]) -> str:
    metadata = user.get("metadata") or {}
    return (
        metadata.get("team_name")
        or user.get("display_name")
        or user.get("username")
        or f"User {user.get('user_id')}"
    )


def roster_display_names(
    rosters: list[dict[str, Any]],
    users: list[dict[str, Any]],
) -> dict[int, str]:
    users_by_id = {user.get("user_id"): user for user in users}
    names: dict[int, str] = {}

    for roster in rosters:
        roster_id = roster.get("roster_id")
        if roster_id is None:
            continue

        owner = users_by_id.get(roster.get("owner_id"))
        names[int(roster_id)] = user_display_name(owner) if owner else f"Roster {roster_id}"

    return names
