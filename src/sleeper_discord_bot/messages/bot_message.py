"""Structured bot message objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BotMessage:
    feature: str
    channel_key: str
    title: str
    content: str


def split_content(content: str, limit: int = 2000) -> list[str]:
    """Split Discord content at line boundaries, never exceeding its limit."""
    chunks: list[str] = []
    current = ""
    for line in content.splitlines():
        pieces = [line[index:index + limit] for index in range(0, max(len(line), 1), limit)]
        for piece in pieces:
            candidate = piece if not current else f"{current}\n{piece}"
            if len(candidate) > limit:
                chunks.append(current)
                current = piece
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks or [""]
