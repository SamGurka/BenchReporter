"""Sleeper transaction helpers."""

from __future__ import annotations

from typing import Any


def completed_trades(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        transaction
        for transaction in transactions
        if transaction.get("type") == "trade" and transaction.get("status") == "complete"
    ]


def trade_roster_ids(transaction: dict[str, Any]) -> list[int]:
    return sorted(transaction.get("roster_ids") or transaction.get("consenter_ids") or [])


def trade_player_moves(transaction: dict[str, Any]) -> dict[int, dict[str, list[str]]]:
    moves: dict[int, dict[str, list[str]]] = {}

    for player_id, roster_id in (transaction.get("adds") or {}).items():
        moves.setdefault(roster_id, {"adds": [], "drops": []})["adds"].append(player_id)

    for player_id, roster_id in (transaction.get("drops") or {}).items():
        moves.setdefault(roster_id, {"adds": [], "drops": []})["drops"].append(player_id)

    for roster_moves in moves.values():
        roster_moves["adds"].sort()
        roster_moves["drops"].sort()

    return moves


def trade_pick_moves(transaction: dict[str, Any]) -> dict[int, list[str]]:
    moves: dict[int, list[str]] = {}

    for pick in transaction.get("draft_picks") or []:
        owner_id = pick.get("owner_id")
        season = pick.get("season")
        round_number = pick.get("round")
        if owner_id is None or season is None or round_number is None:
            continue
        moves.setdefault(int(owner_id), []).append(f"{season} round {round_number}")

    for picks in moves.values():
        picks.sort()

    return moves


def trade_faab_moves(transaction: dict[str, Any]) -> dict[int, list[str]]:
    """Return FAAB received by roster, tolerating Sleeper's transfer shape."""

    moves: dict[int, list[str]] = {}
    for transfer in transaction.get("waiver_budget") or []:
        if not isinstance(transfer, dict):
            continue
        receiver = transfer.get("receiver_id", transfer.get("receiver"))
        amount = transfer.get("amount")
        if receiver is None or amount is None:
            continue
        moves.setdefault(int(receiver), []).append(f"${amount} FAAB")
    return moves
