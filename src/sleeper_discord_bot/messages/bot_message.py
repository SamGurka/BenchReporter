"""Structured bot message objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BotMessage:
    feature: str
    channel_key: str
    title: str
    content: str
