import asyncio
import json
from datetime import UTC, datetime

import pytest

from market_data_service.contracts import Quote
from market_data_service.redis_state import QUOTE_CHANNEL, RedisQuoteStore


class FakePubSub:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = messages
        self.subscribed: list[str] = []
        self.unsubscribed: list[str] = []
        self.closed = False

    async def subscribe(self, channel: str) -> None:
        self.subscribed.append(channel)

    async def unsubscribe(self, channel: str) -> None:
        self.unsubscribed.append(channel)

    async def aclose(self) -> None:
        self.closed = True

    async def listen(self):
        for message in self.messages:
            yield message


class FakeRedis:
    def __init__(self, messages: list[dict] | None = None) -> None:
        self.published: list[tuple[str, str]] = []
        self.pubsub_instance = FakePubSub(messages or [])

    async def get(self, name: str):
        return None

    async def set(self, name: str, value: str, *, ex: int | None = None):
        return True

    async def publish(self, channel: str, message: str):
        self.published.append((channel, message))
        return 1

    def pubsub(self):
        return self.pubsub_instance


def encoded_quote(symbol: str, price: float) -> str:
    canonical = symbol.removesuffix(".US")
    return json.dumps(
        {
            "schemaVersion": "trading_research.live_quote.v1",
            "symbol": f"us:{canonical}",
            "price": price,
            "timestamp": "2026-08-27T02:00:00.000000Z",
            "source": "alpaca",
            "status": "live",
        }
    )


def test_publish_quote_uses_fixed_channel_and_canonical_payload() -> None:
    async def scenario() -> None:
        redis = FakeRedis()
        store = RedisQuoteStore(redis)
        quote = Quote("AAPL.US", 202.5, datetime(2026, 8, 27, 2, 0, tzinfo=UTC), "alpaca")

        await store.publish_quote(quote)

        assert len(redis.published) == 1
        channel, message = redis.published[0]
        assert channel == QUOTE_CHANNEL
        assert json.loads(message)["symbol"] == "us:AAPL"

    asyncio.run(scenario())


def test_quote_subscription_closes_pubsub_when_subscribe_fails() -> None:
    class FailingSubscribePubSub(FakePubSub):
        async def subscribe(self, channel: str) -> None:
            raise RuntimeError("subscribe failed")

    async def scenario() -> None:
        redis = FakeRedis()
        redis.pubsub_instance = FailingSubscribePubSub([])
        store = RedisQuoteStore(redis)

        with pytest.raises(RuntimeError, match="subscribe failed"):
            async with store.subscribe_quotes(["AAPL.US"]):
                pass

        assert redis.pubsub_instance.closed is True

    asyncio.run(scenario())


def test_quote_subscription_closes_pubsub_when_unsubscribe_fails() -> None:
    class FailingUnsubscribePubSub(FakePubSub):
        async def unsubscribe(self, channel: str) -> None:
            self.unsubscribed.append(channel)
            raise RuntimeError("unsubscribe failed")

    async def scenario() -> None:
        redis = FakeRedis()
        redis.pubsub_instance = FailingUnsubscribePubSub([])
        store = RedisQuoteStore(redis)

        with pytest.raises(RuntimeError, match="unsubscribe failed"):
            async with store.subscribe_quotes(["AAPL.US"]):
                pass

        assert redis.pubsub_instance.unsubscribed == [QUOTE_CHANNEL]
        assert redis.pubsub_instance.closed is True

    asyncio.run(scenario())


def test_quote_subscription_filters_symbols_and_closes_pubsub() -> None:
    async def scenario() -> None:
        messages = [
            {"type": "subscribe", "data": 1},
            {"type": "message", "data": encoded_quote("MSFT.US", 410.0)},
            {"type": "message", "data": encoded_quote("AAPL.US", 202.5)},
        ]
        redis = FakeRedis(messages)
        store = RedisQuoteStore(redis)

        received = []
        async with store.subscribe_quotes(["AAPL.US"]) as subscription:
            async for quote in subscription:
                received.append(quote)
                break

        assert [quote.symbol for quote in received] == ["us:AAPL"]
        assert redis.pubsub_instance.subscribed == [QUOTE_CHANNEL]
        assert redis.pubsub_instance.unsubscribed == [QUOTE_CHANNEL]
        assert redis.pubsub_instance.closed is True

    asyncio.run(scenario())
