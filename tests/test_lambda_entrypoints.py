from __future__ import annotations

from sleeper_discord_bot.handlers.results import HandlerResult
from sleeper_discord_bot.handlers import trade_watch, weekly_roundup


def _lambda_env(monkeypatch) -> None:
    monkeypatch.setenv("SSM_PARAMETER_PREFIX", "/benchreporter/test")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "test-state")
    monkeypatch.setenv("DRY_RUN", "true")


def test_weekly_roundup_lambda_wires_ssm_storage_and_dry_run_delivery(monkeypatch):
    _lambda_env(monkeypatch)
    monkeypatch.setattr(
        weekly_roundup,
        "_ssm_values",
        lambda prefix: {
            f"{prefix}/discord-bot-token": "token",
            f"{prefix}/discord-channel-last-week-tldr": "channel",
            f"{prefix}/sleeper-league-id": "league",
        },
    )
    monkeypatch.setattr(weekly_roundup, "DynamoDBStorage", lambda table_name: ("storage", table_name))
    monkeypatch.setattr(weekly_roundup, "SleeperClient", lambda **kwargs: ("sleeper", kwargs))
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return HandlerResult(posted_count=1, skipped_count=2, snapshots_written=10)

    monkeypatch.setattr(weekly_roundup, "run_weekly_roundup", fake_run)

    result = weekly_roundup.lambda_handler({}, None)

    assert result == {"posted": 1, "skipped": 2, "snapshots_written": 10}
    assert captured["league_id"] == "league"
    assert captured["season"] is None
    assert captured["week"] is None
    assert captured["storage"] == ("storage", "test-state")
    assert captured["sleeper"][0] == "sleeper"


def test_trade_watch_lambda_enforces_in_season_polling(monkeypatch):
    _lambda_env(monkeypatch)
    monkeypatch.setattr(
        trade_watch,
        "_ssm_values",
        lambda prefix: {
            f"{prefix}/discord-bot-token": "token",
            f"{prefix}/discord-channel-trade-block": "channel",
            f"{prefix}/sleeper-league-id": "league",
        },
    )
    monkeypatch.setattr(trade_watch, "DynamoDBStorage", lambda table_name: ("storage", table_name))
    monkeypatch.setattr(trade_watch, "SleeperClient", lambda **kwargs: ("sleeper", kwargs))
    captured = {}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return HandlerResult(posted_count=3, skipped_count=4, snapshots_written=3)

    monkeypatch.setattr(trade_watch, "run_trade_watch", fake_run)

    result = trade_watch.lambda_handler({}, None)

    assert result == {"posted": 3, "skipped": 4, "snapshots_written": 3}
    assert captured["league_id"] == "league"
    assert captured["in_season_only"] is True
    assert captured["storage"] == ("storage", "test-state")
