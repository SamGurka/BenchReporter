from pathlib import Path

import pytest
import requests

from sleeper_discord_bot.clients.rss import RssClient


SAMPLE_FEED_PATH = Path(__file__).parent / "data" / "sample_news_feed.xml"


class FakeResponse:
    def __init__(self, content: bytes, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.raise_for_status_called = False

    def raise_for_status(self) -> None:
        self.raise_for_status_called = True
        if self.error:
            raise self.error


class FakeSession:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def get(self, url: str, *, timeout: int, headers: dict[str, str]) -> FakeResponse:
        self.calls.append({"url": url, "timeout": timeout, "headers": headers})
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def test_parses_static_sample_feed_and_sends_identifying_user_agent():
    response = FakeResponse(SAMPLE_FEED_PATH.read_bytes())
    session = FakeSession(response)

    items = RssClient(session=session, timeout_sec=12).items("https://example.test/feed.xml")

    assert [item.title for item in items] == ["Newer injury update", "Older roster update"]
    assert all(item.source == "Example Fantasy Feed" for item in items)
    assert response.raise_for_status_called
    assert session.calls == [
        {
            "url": "https://example.test/feed.xml",
            "timeout": 12,
            "headers": {"User-Agent": "BenchReporter/0.1 (+https://github.com/Nexather/BenchReporter)"},
        }
    ]


def test_requires_feed_url_before_making_a_request():
    session = FakeSession()

    with pytest.raises(ValueError, match="RSS_FEED_URL is required"):
        RssClient(session=session).items("")

    assert session.calls == []


def test_propagates_http_errors():
    response = FakeResponse(b"", requests.HTTPError("503 Service Unavailable"))

    with pytest.raises(requests.HTTPError, match="503"):
        RssClient(session=FakeSession(response)).items("https://example.test/feed.xml")

    assert response.raise_for_status_called


def test_propagates_network_errors():
    session = FakeSession(error=requests.ConnectionError("connection refused"))

    with pytest.raises(requests.ConnectionError, match="connection refused"):
        RssClient(session=session).items("https://example.test/feed.xml")


def test_rejects_unparseable_feed_without_entries():
    response = FakeResponse(b"\xff\x00")

    with pytest.raises(ValueError, match="Unable to parse RSS/Atom feed"):
        RssClient(session=FakeSession(response)).items("https://example.test/feed.xml")
