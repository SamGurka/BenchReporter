"""Trade Watch handler orchestration."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from sleeper_discord_bot.clients.storage import Storage, utc_now_iso
from sleeper_discord_bot.domain.history import build_trade_snapshot
from sleeper_discord_bot.domain.nfl_state import completed_regular_season_week
from sleeper_discord_bot.domain.players import cached_player_lookup, merge_player_lookups, player_lookup_from_stats
from sleeper_discord_bot.domain.trades import completed_trades
from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.messages.bot_message import BotMessage
from sleeper_discord_bot.messages.trades import format_trade_message


class SleeperTradeClient(Protocol):
    def rosters(self, league_id: str) -> list[dict[str, Any]]: ...
    def users(self, league_id: str) -> list[dict[str, Any]]: ...
    def transactions(self, league_id: str, week: int) -> list[dict[str, Any]]: ...
    def players(self) -> dict[str, Any]: ...
    def nfl_state(self) -> dict[str, Any]: ...
    def weekly_stats(self, season: str, week: int) -> Any: ...


def resolve_trade_target(sleeper: SleeperTradeClient, season: str | None, week: int | None) -> tuple[str, int]:
    if season is not None and week is not None:
        return season, week

    state_season, state_week = completed_regular_season_week(sleeper.nfl_state())
    return season or state_season, week or state_week


def run_trade_watch(
    *,
    sleeper: SleeperTradeClient,
    storage: Storage,
    league_id: str,
    season: str | None,
    week: int | None,
    send_message: Callable[[BotMessage], None],
) -> HandlerResult:
    season, week = resolve_trade_target(sleeper, season, week)
    rosters = sleeper.rosters(league_id)
    users = sleeper.users(league_id)
    transactions = sleeper.transactions(league_id, week)
    players_by_id = merge_player_lookups(
        cached_player_lookup(storage, sleeper),
        player_lookup_from_stats(sleeper.weekly_stats(season, week)),
    )

    messages: list[BotMessage] = []
    posted_count = 0
    skipped_count = 0
    snapshots_written = 0

    for trade in completed_trades(transactions):
        transaction_id = str(trade["transaction_id"])
        if storage.exists("TXN", transaction_id):
            skipped_count += 1
            continue

        content = format_trade_message(trade, rosters, users, players_by_id)
        message = BotMessage(
            feature="trade_watch",
            channel_key="trade_block",
            title="Trade Alert",
            content=content,
        )
        send_message(message)
        storage.put_if_absent(
            "TXN",
            transaction_id,
            {
                "season": season,
                "week": week,
                "posted_at": utc_now_iso(),
            },
        )
        storage.put_snapshot(build_trade_snapshot(season, week, trade, rosters, users, players_by_id))

        messages.append(message)
        posted_count += 1
        snapshots_written += 1

    return HandlerResult(
        messages=messages,
        posted_count=posted_count,
        skipped_count=skipped_count,
        snapshots_written=snapshots_written,
    )
