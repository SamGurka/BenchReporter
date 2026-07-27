from sleeper_discord_bot.clients.storage import InMemoryStorage, weekly_key


def test_put_if_absent_only_writes_once():
    storage = InMemoryStorage()

    assert storage.put_if_absent("TXN", "abc", {"posted_at": "now"})
    assert not storage.put_if_absent("TXN", "abc", {"posted_at": "later"})

    assert storage.get("TXN", "abc")["posted_at"] == "now"


def test_exists_supports_dedupe_records():
    storage = InMemoryStorage()

    storage.put_if_absent("RSS", "item-1")

    assert storage.exists("RSS", "item-1")
    assert not storage.exists("RSS", "item-2")


def test_weekly_flags_are_marked_independently():
    storage = InMemoryStorage()

    storage.mark_weekly_flag("2025", 16, "roundup_posted")
    storage.mark_weekly_flag("2025", 16, "team_snapshots_written")

    weekly = storage.get_weekly_flags("2025", 16)

    assert weekly["pk"] == "WEEK"
    assert weekly["sk"] == "2025-16"
    assert weekly["roundup_posted"] is True
    assert weekly["team_snapshots_written"] is True
    assert "free_agents_posted" not in weekly


def test_get_weekly_flags_returns_default_shape_when_missing():
    storage = InMemoryStorage()

    assert storage.get_weekly_flags("2025", 1) == {"pk": "WEEK", "sk": "2025-01"}


def test_put_snapshot_requires_pk_and_sk():
    storage = InMemoryStorage()

    try:
        storage.put_snapshot({"pk": "TEAM#1"})
    except ValueError as exc:
        assert "pk and sk" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_put_snapshot_stores_team_week_record():
    storage = InMemoryStorage()
    snapshot = {
        "pk": "TEAM#1",
        "sk": "WEEK#2025#16",
        "points_for": 123.4,
    }

    storage.put_snapshot(snapshot)
    snapshot["points_for"] = 0

    assert storage.get("TEAM#1", "WEEK#2025#16")["points_for"] == 123.4


def test_put_snapshot_stores_trade_record():
    storage = InMemoryStorage()

    storage.put_snapshot({"pk": "TRADE#abc", "sk": "META", "week": 1})

    assert storage.get("TRADE#abc", "META")["week"] == 1


def test_players_cache_round_trip_is_copied():
    storage = InMemoryStorage()
    players = {"123": {"name": "Player Name"}}

    storage.set_players_cache(players, fetched_at="2026-01-01T00:00:00Z")
    players["123"]["name"] = "Mutated"

    cache = storage.get_players_cache()

    assert cache["fetched_at"] == "2026-01-01T00:00:00Z"
    assert cache["data"]["123"]["name"] == "Player Name"


def test_weekly_key_formats_week_with_two_digits():
    assert weekly_key("2025", 3) == ("WEEK", "2025-03")
