"""Delivery adapters for structured bot messages."""

from __future__ import annotations

from dataclasses import dataclass, field

from sleeper_discord_bot.clients.discord import DiscordClient, DiscordSendResult
from sleeper_discord_bot.messages.bot_message import BotMessage


class ConsoleDelivery:
    def __init__(self) -> None:
        self.messages: list[BotMessage] = []

    def send(self, message: BotMessage) -> None:
        self.messages.append(message)
        print(f"[{message.channel_key}] {message.title}")
        print(message.content)


@dataclass
class DiscordDelivery:
    client: DiscordClient
    channel_ids: dict[str, str]
    sent: list[DiscordSendResult] = field(default_factory=list)

    def send(self, message: BotMessage) -> None:
        channel_id = self.channel_ids.get(message.channel_key)
        if not channel_id:
            raise ValueError(f"No Discord channel configured for {message.channel_key}.")
        self.sent.append(self.client.send_message(channel_id, message.content))
