from fastapi.testclient import TestClient
from urllib.parse import urlsplit

from sleeper_discord_bot.clients.discord import DiscordClient
from sleeper_discord_bot.clients.sleeper import SleeperClient
from sleeper_discord_bot.clients.storage import InMemoryStorage
from sleeper_discord_bot.delivery import DiscordDelivery
from sleeper_discord_bot.handlers.weekly_roundup import run_weekly_roundup
from sleeper_discord_bot.clients import sleeper as sleeper_module
from tests.support.mock_sleeper_api import create_mock_sleeper_app


def test_mock_api_serves_core_league_routes():
    client = TestClient(create_mock_sleeper_app())

    assert client.get("/league/sample_league").json()["league_id"] == "sample_league"
    assert len(client.get("/league/sample_league/users").json()) == 15
    assert len(client.get("/league/sample_league/rosters").json()) == 12
    state = client.get("/state/nfl").json()
    assert state["previous_season"] == "2025"
    assert state["season_type"] == "off"
    assert "4881" in client.get("/players/nfl").json()


def test_mock_api_serves_week_routes():
    client = TestClient(create_mock_sleeper_app())

    assert len(client.get("/league/sample_league/matchups/1").json()) == 12
    assert len(client.get("/league/sample_league/transactions/1").json()) == 29
    assert len(client.get("/stats/nfl/2025/1?season_type=regular").json()) == 331
    assert len(client.get("/projections/nfl/2025/1?season_type=regular").json()) == 331


def test_mock_api_returns_404_for_missing_week():
    client = TestClient(create_mock_sleeper_app())

    response = client.get("/league/sample_league/matchups/2")

    assert response.status_code == 404


def test_weekly_handler_uses_mock_sleeper_api_and_dry_run_delivery(monkeypatch):
    mock_api = TestClient(create_mock_sleeper_app())
    monkeypatch.setattr(
        sleeper_module.requests,
        "get",
        lambda url, timeout: mock_api.get(f"{urlsplit(url).path}?{urlsplit(url).query}"),
    )
    sleeper = SleeperClient(base_url="https://mock.test", stats_base_url="https://mock.test/stats/nfl")
    delivery = DiscordDelivery(DiscordClient(bot_token="test", dry_run=True), {"last_week_tldr": "channel"})

    result = run_weekly_roundup(
        sleeper=sleeper, storage=InMemoryStorage(), league_id="sample_league", season="2025", week=16,
        prior_weeks=[1, 3, 10], send_message=delivery.send,
    )

    assert result.posted_count == 1
    assert delivery.sent[0].dry_run is True
