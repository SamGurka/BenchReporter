from __future__ import annotations

from typing import Any

import pytest

from sleeper_discord_bot.clients.discord import DISCORD_MESSAGE_LIMIT, DiscordClient


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self.payload = payload

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)


def test_dry_run_returns_message_without_http_call():
    session = FakeSession([])
    client = DiscordClient(bot_token="token", dry_run=True, session=session)

    result = client.send_message("channel-1", "hello")

    assert result.dry_run is True
    assert result.channel_id == "channel-1"
    assert result.content == "hello"
    assert session.calls == []


def test_send_message_posts_to_discord_api():
    session = FakeSession([FakeResponse(200, {"id": "message-1"})])
    client = DiscordClient(bot_token="token", session=session, timeout_sec=7)

    result = client.send_message("channel-1", "hello")

    assert result.dry_run is False
    assert result.status_code == 200
    assert result.message_id == "message-1"
    assert session.calls == [
        {
            "url": "https://discord.com/api/v10/channels/channel-1/messages",
            "headers": {
                "Authorization": "Bot token",
                "Content-Type": "application/json",
                "User-Agent": "sleeper-discord-bot",
            },
            "json": {"content": "hello"},
            "timeout": 7,
        }
    ]


def test_send_message_retries_once_after_rate_limit():
    sleeps: list[float] = []
    session = FakeSession(
        [
            FakeResponse(429, {"retry_after": 0.25}),
            FakeResponse(200, {"id": "message-2"}),
        ]
    )
    client = DiscordClient(bot_token="token", session=session, sleep=sleeps.append)

    result = client.send_message("channel-1", "hello")

    assert result.message_id == "message-2"
    assert len(session.calls) == 2
    assert sleeps == [0.25]


def test_send_message_rejects_content_over_discord_limit():
    client = DiscordClient(bot_token="token", dry_run=True)

    with pytest.raises(ValueError, match="exceeds"):
        client.send_message("channel-1", "x" * (DISCORD_MESSAGE_LIMIT + 1))
