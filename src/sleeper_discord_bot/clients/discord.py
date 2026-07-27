"""Discord REST client for message sends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

import requests


DISCORD_MESSAGE_LIMIT = 2000


class HttpSession(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> Any: ...


@dataclass(frozen=True)
class DiscordSendResult:
    channel_id: str
    content: str
    dry_run: bool
    status_code: int | None = None
    message_id: str | None = None


class DiscordClient:
    def __init__(
        self,
        *,
        bot_token: str,
        dry_run: bool = False,
        base_url: str = "https://discord.com/api/v10",
        timeout_sec: int = 20,
        session: HttpSession | None = None,
        sleep: Callable[[float], None] | None = None,
    ) -> None:
        self.bot_token = bot_token
        self.dry_run = dry_run
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.session = session or requests
        self.sleep = sleep

    def send_message(self, channel_id: str, content: str) -> DiscordSendResult:
        if len(content) > DISCORD_MESSAGE_LIMIT:
            raise ValueError(f"Discord message content exceeds {DISCORD_MESSAGE_LIMIT} characters.")

        if self.dry_run:
            return DiscordSendResult(
                channel_id=channel_id,
                content=content,
                dry_run=True,
            )

        response = self._post_message(channel_id, content)
        if response.status_code == 429:
            retry_after = self._retry_after_seconds(response)
            if self.sleep is not None and retry_after > 0:
                self.sleep(retry_after)
            response = self._post_message(channel_id, content)

        response.raise_for_status()
        data = response.json()
        return DiscordSendResult(
            channel_id=channel_id,
            content=content,
            dry_run=False,
            status_code=response.status_code,
            message_id=data.get("id"),
        )

    def _post_message(self, channel_id: str, content: str) -> Any:
        return self.session.post(
            f"{self.base_url}/channels/{channel_id}/messages",
            headers={
                "Authorization": f"Bot {self.bot_token}",
                "Content-Type": "application/json",
                "User-Agent": "sleeper-discord-bot",
            },
            json={"content": content},
            timeout=self.timeout_sec,
        )

    @staticmethod
    def _retry_after_seconds(response: Any) -> float:
        try:
            data = response.json()
        except ValueError:
            return 0.0
        return float(data.get("retry_after") or 0.0)
