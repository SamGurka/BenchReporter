from decimal import Decimal

from sleeper_discord_bot.clients.storage import DynamoDBStorage


class ConditionalWriteFailed(Exception):
    response = {"Error": {"Code": "ConditionalCheckFailedException"}}


class FakeTable:
    def __init__(self):
        self.items = {}

    def put_item(self, *, Item, ConditionExpression=None):
        key = (Item["pk"], Item["sk"])
        if ConditionExpression and key in self.items:
            raise ConditionalWriteFailed()
        self.items[key] = Item

    def get_item(self, *, Key):
        item = self.items.get((Key["pk"], Key["sk"]))
        return {"Item": item} if item else {}

    def delete_item(self, *, Key):
        self.items.pop((Key["pk"], Key["sk"]), None)


def test_dynamodb_storage_uses_conditional_write_for_dedupe_and_converts_floats():
    table = FakeTable()
    storage = DynamoDBStorage("bot-state", table=table)

    assert storage.put_if_absent("RSS", "item-1", {"score": 12.5})
    assert not storage.put_if_absent("RSS", "item-1", {"score": 20.0})

    assert table.items[("RSS", "item-1")]["score"] == Decimal("12.5")
    assert storage.get("RSS", "item-1") == {"pk": "RSS", "sk": "item-1", "score": 12.5}


def test_dynamodb_player_cache_chunks_large_directories_under_the_item_limit():
    table = FakeTable()
    storage = DynamoDBStorage("bot-state", table=table)
    directory = {str(index): {"name": "Player " + "x" * 1_000, "position": "WR"} for index in range(500)}

    storage.set_players_cache(directory, fetched_at="2026-09-18T00:00:00+00:00")

    metadata = storage.get("PLAYERS_CACHE", "latest")
    assert metadata["chunk_count"] > 1
    assert storage.get_players_cache() == {**metadata, "data": directory}
