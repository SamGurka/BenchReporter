"""Common handler result objects."""

from __future__ import annotations

from dataclasses import dataclass, field

from sleeper_discord_bot.messages.bot_message import BotMessage


@dataclass(frozen=True)
class HandlerResult:
    messages: list[BotMessage] = field(default_factory=list)
    posted_count: int = 0
    skipped_count: int = 0
    snapshots_written: int = 0
