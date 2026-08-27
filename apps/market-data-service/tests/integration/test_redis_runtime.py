import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest
import redis.asyncio as redis

from market_data_service.contracts import Quote
from market_data_service.redis_state import (
    CollectorHeartbeat,
    RedisQuoteStore,
    SyncRedisQuoteStore,
)

REDIS_URL = os.getenv("REDIS_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not REDIS_URL, reason="REDIS_URL is required"),
]


def test_real_redis_runtime_roundtrip_and_pubsub() -> None:
    assert REDIS_URL is not None

    async def scenario() -> None:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        await client.flushdb()
        try:
            store = RedisQuoteStore(client, max_age_seconds=15)
            timestamp = datetime.now(UTC).replace(microsecond=0)
            quote = Quote("AAPL.US", 201.25, timestamp, "integration")

            assert await store.put_quote(quote) is True
            assert await store.put_quote(
                Quote("AAPL.US", 199.0, timestamp - timedelta(seconds=1), "integration")
            ) is False
            state = await store.get_quote("AAPL.US", now=timestamp)
            assert state is not None
            assert state.quote.price == 201.25

            heartbeat = CollectorHeartbeat(timestamp, timestamp, 1, 0)
            await store.write_heartbeat(heartbeat)
            assert await store.get_heartbeat() == heartbeat

            received = asyncio.create_task(_receive_quote(store))
            await asyncio.sleep(0.05)
            await store.publish_quote(Quote("AAPL.US", 202.0, timestamp, "integration"))
            published = await asyncio.wait_for(received, timeout=2)
            assert published.price == 202.0
        finally:
            await client.flushdb()
            await client.aclose()

    asyncio.run(scenario())


async def _receive_quote(store: RedisQuoteStore) -> Quote:
    async with store.subscribe_quotes(["AAPL.US"]) as subscription:
        async for quote in subscription:
            return quote
    raise AssertionError("subscription ended before receiving a quote")


def test_real_sync_collector_sink_writes_to_redis() -> None:
    assert REDIS_URL is not None

    async def scenario() -> None:
        async_client = redis.from_url(REDIS_URL, decode_responses=True)
        await async_client.flushdb()
        sync_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        try:
            sink = SyncRedisQuoteStore(sync_client)
            timestamp = datetime.now(UTC).replace(microsecond=0)
            assert sink.put_quote(Quote("MSFT.US", 410.0, timestamp, "integration")) is True
            store = RedisQuoteStore(async_client)
            state = await store.get_quote("MSFT.US", now=timestamp)
            assert state is not None
            assert state.quote.price == 410.0
        finally:
            sync_client.close()
            await async_client.flushdb()
            await async_client.aclose()

    asyncio.run(scenario())
