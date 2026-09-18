"""Small structured logging helpers for Lambda jobs."""

from __future__ import annotations

import json
from typing import Any

from sleeper_discord_bot.handlers.results import HandlerResult


def log_job_result(*, job: str, season: str | None, dry_run: bool, result: HandlerResult) -> None:
    print(
        json.dumps(
            {
                "event": "job_result",
                "job": job,
                "season": season,
                "dry_run": dry_run,
                "posted": result.posted_count,
                "skipped": result.skipped_count,
                "snapshots_written": result.snapshots_written,
            },
            sort_keys=True,
        )
    )
