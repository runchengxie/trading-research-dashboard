import asyncio
import json
from datetime import UTC, datetime, timedelta

import market_data_service.redis_state as redis_state


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expiries: dict[str, int | None] = {}

    async def get(self, name: str):
        return self.values.get(name)

    async def set(self, name: str, value: str, *, ex: int | None = None):
        self.values[name] = value
        self.expiries[name] = ex
        return True

    async def publish(self, channel: str, message: str):
        return 0

    def pubsub(self):
        raise AssertionError("pubsub is not used by heartbeat tests")


def test_redis_state_exposes_collector_heartbeat_contract() -> None:
    assert hasattr(redis_state, "CollectorHeartbeat")


def test_collector_heartbeat_roundtrips_with_finite_ttl() -> None:
    async def scenario() -> None:
        CollectorHeartbeat = redis_state.CollectorHeartbeat
        RedisQuoteStore = redis_state.RedisQuoteStore
        now = datetime(2026, 8, 27, 2, 10, tzinfo=UTC)
        heartbeat = CollectorHeartbeat(
            loop_at=now,
            last_success_at=now - timedelta(seconds=1),
            success_count=3,
            failure_count=1,
        )
        redis = FakeRedis()
        store = RedisQuoteStore(redis, heartbeat_ttl_seconds=30)

        await store.write_heartbeat(heartbeat)

        assert redis.expiries[redis_state.HEARTBEAT_KEY] == 30
        payload = json.loads(redis.values[redis_state.HEARTBEAT_KEY])
        assert payload == {
            "loopAt": "2026-08-27T02:10:00.000000Z",
            "lastSuccessAt": "2026-08-27T02:09:59.000000Z",
            "successCount": 3,
            "failureCount": 1,
        }
        assert await store.get_heartbeat() == heartbeat

    asyncio.run(scenario())


def test_missing_heartbeat_returns_none_and_last_success_may_be_null() -> None:
    async def scenario() -> None:
        CollectorHeartbeat = redis_state.CollectorHeartbeat
        RedisQuoteStore = redis_state.RedisQuoteStore
        redis = FakeRedis()
        store = RedisQuoteStore(redis, heartbeat_ttl_seconds=45)
        assert await store.get_heartbeat() is None

        heartbeat = CollectorHeartbeat(
            loop_at=datetime(2026, 8, 27, 2, 10, tzinfo=UTC),
            last_success_at=None,
            success_count=0,
            failure_count=2,
        )
        await store.write_heartbeat(heartbeat)
        restored = await store.get_heartbeat()

        assert restored is not None
        assert restored.last_success_at is None
        assert redis.expiries[redis_state.HEARTBEAT_KEY] == 45

    asyncio.run(scenario())
