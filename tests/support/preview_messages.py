"""Preview Discord-style messages from committed sample data.

Usage:
    python -m tests.support.preview_messages weekly --week 1
    python -m tests.support.preview_messages trades --week 1 --limit 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sleeper_discord_bot.domain.players import merge_player_lookups, player_lookup_from_stats
from sleeper_discord_bot.domain.trades import completed_trades
from sleeper_discord_bot.messages.trades import format_trade_message
from sleeper_discord_bot.messages.weekly_roundup import format_weekly_roundup_message


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA = PROJECT_ROOT / "tests" / "data" / "sleeper_2025_sample"


def load_sample(relative_path: str) -> Any:
    return json.loads((SAMPLE_DATA / relative_path).read_text(encoding="utf-8"))


def sample_player_lookup_through_week(week: int) -> dict[str, dict[str, Any]]:
    lookups = []
    for stats_path in sorted((SAMPLE_DATA / "weeks").glob("*/stats.json")):
        stats_week = int(stats_path.parent.name)
        if stats_week <= week:
            lookups.append(player_lookup_from_stats(load_sample(f"weeks/{stats_week:02d}/stats.json")))
    return merge_player_lookups(*lookups)


def print_weekly_roundup(week: int) -> None:
    prior_weeks = [
        load_sample(f"weeks/{prior_week:02d}/matchups.json")
        for prior_week in [1, 3, 10, 16]
        if prior_week < week and (SAMPLE_DATA / "weeks" / f"{prior_week:02d}" / "matchups.json").exists()
    ]
    print(
        format_weekly_roundup_message(
            week=week,
            matchups=load_sample(f"weeks/{week:02d}/matchups.json"),
            rosters=load_sample("rosters.json"),
            users=load_sample("users.json"),
            players_by_id=sample_player_lookup_through_week(week),
            prior_matchups_by_week=prior_weeks,
        )
    )


def print_trade_messages(week: int, limit: int | None) -> None:
    trades = completed_trades(load_sample(f"weeks/{week:02d}/transactions.json"))
    players_by_id = sample_player_lookup_through_week(week)
    rosters = load_sample("rosters.json")
    users = load_sample("users.json")

    for index, trade in enumerate(trades[:limit], start=1):
        if index > 1:
            print("\n---\n")
        print(format_trade_message(trade, rosters, users, players_by_id))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    weekly_parser = subparsers.add_parser("weekly", help="Preview weekly roundup message.")
    weekly_parser.add_argument("--week", type=int, required=True)

    trades_parser = subparsers.add_parser("trades", help="Preview trade announcement messages.")
    trades_parser.add_argument("--week", type=int, required=True)
    trades_parser.add_argument("--limit", type=int)

    args = parser.parse_args()

    if args.command == "weekly":
        print_weekly_roundup(args.week)
        return 0
    if args.command == "trades":
        print_trade_messages(args.week, args.limit)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
