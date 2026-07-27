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


def test_dynamodb_storage_uses_conditional_write_for_dedupe_and_converts_floats():
    table = FakeTable()
    storage = DynamoDBStorage("bot-state", table=table)

    assert storage.put_if_absent("RSS", "item-1", {"score": 12.5})
    assert not storage.put_if_absent("RSS", "item-1", {"score": 20.0})

    assert table.items[("RSS", "item-1")]["score"] == Decimal("12.5")
    assert storage.get("RSS", "item-1") == {"pk": "RSS", "sk": "item-1", "score": 12.5}
