"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping


def _bool_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class AppConfig:
    sleeper_league_id: str
    season: str | None = None
    sleeper_base_url: str = "https://api.sleeper.app/v1"
    sleeper_stats_base_url: str = "https://api.sleeper.com/stats/nfl"
    rss_feed_url: str = ""
    dry_run: bool = True
    discord_bot_token: str = ""
    channel_ids: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "AppConfig":
        env = env or os.environ
        return cls(
            sleeper_league_id=env.get("SLEEPER_LEAGUE_ID", ""),
            season=env.get("SEASON") or None,
            sleeper_base_url=env.get("SLEEPER_BASE_URL", cls.sleeper_base_url),
            sleeper_stats_base_url=env.get("SLEEPER_STATS_BASE_URL", cls.sleeper_stats_base_url),
            rss_feed_url=env.get("RSS_FEED_URL", ""),
            dry_run=_bool_env(env.get("DRY_RUN"), default=True),
            discord_bot_token=env.get("DISCORD_BOT_TOKEN", ""),
            channel_ids={
                "espn_news_feed": env.get("DISCORD_CHANNEL_ESPN_NEWS_FEED", ""),
                "standout_free_agents": env.get("DISCORD_CHANNEL_STANDOUT_FREE_AGENTS", ""),
                "last_week_tldr": env.get("DISCORD_CHANNEL_LAST_WEEK_TLDR", ""),
                "trade_block": env.get("DISCORD_CHANNEL_TRADE_BLOCK", ""),
                "season_awards": env.get("DISCORD_CHANNEL_SEASON_AWARDS", ""),
            },
        )

    def require_league_id(self) -> str:
        if not self.sleeper_league_id:
            raise ValueError("SLEEPER_LEAGUE_ID is required.")
        return self.sleeper_league_id
