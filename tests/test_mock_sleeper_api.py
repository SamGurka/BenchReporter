from fastapi.testclient import TestClient

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


def test_mock_api_returns_404_for_missing_week():
    client = TestClient(create_mock_sleeper_app())

    response = client.get("/league/sample_league/matchups/2")

    assert response.status_code == 404
