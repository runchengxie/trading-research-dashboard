import asyncio
import importlib.util
import json
from datetime import UTC, datetime, timedelta

from market_data_service.contracts import Freshness, Quote


def test_redis_state_module_is_available() -> None:
    assert importlib.util.find_spec("market_data_service.redis_state") is not None


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.expiries: dict[str, int | None] = {}
        self.published: list[tuple[str, str]] = []

    async def get(self, name: str):
        return self.values.get(name)

    async def set(self, name: str, value: str, *, ex: int | None = None):
        self.values[name] = value
        self.expiries[name] = ex
        return True

    async def publish(self, channel: str, message: str):
        self.published.append((channel, message))
        return 1

    def pubsub(self):
        raise AssertionError("pubsub is not used by latest-state tests")


def test_redis_quote_store_roundtrips_normalized_quote_and_recomputes_freshness() -> None:
    from market_data_service.redis_state import RedisQuoteStore, quote_key

    async def scenario() -> None:
        now = datetime(2026, 8, 27, 2, 0, tzinfo=UTC)
        redis = FakeRedis()
        store = RedisQuoteStore(redis, max_age_seconds=15)
        quote = Quote("AAPL.US", 201.25, now - timedelta(seconds=5), "alpaca")

        accepted = await store.put_quote(quote)

        assert accepted is True
        raw = json.loads(redis.values[quote_key("us:AAPL")])
        assert raw["symbol"] == "us:AAPL"
        assert raw["timestamp"] == "2026-08-27T01:59:55.000000Z"
        assert raw["status"] == "live"
        assert redis.expiries[quote_key("us:AAPL")] is None

        current = await store.get_quote("AAPL.US", now=now)
        stale = await store.get_quote("us:AAPL", now=now + timedelta(seconds=20))

        assert current is not None
        assert current.quote.price == 201.25
        assert current.freshness is Freshness.CURRENT
        assert stale is not None
        assert stale.freshness is Freshness.STALE

    asyncio.run(scenario())


def test_redis_quote_store_rejects_older_quotes_and_accepts_equal_timestamp_corrections() -> None:
    from market_data_service.redis_state import RedisQuoteStore

    async def scenario() -> None:
        timestamp = datetime(2026, 8, 27, 2, 0, tzinfo=UTC)
        redis = FakeRedis()
        store = RedisQuoteStore(redis, max_age_seconds=15)

        assert await store.put_quote(Quote("AAPL.US", 200.0, timestamp, "alpaca")) is True
        assert (
            await store.put_quote(
                Quote("AAPL.US", 199.0, timestamp - timedelta(microseconds=1), "alpaca")
            )
            is False
        )
        assert await store.put_quote(Quote("AAPL.US", 202.0, timestamp, "alpaca")) is True

        state = await store.get_quote("AAPL.US", now=timestamp)
        assert state is not None
        assert state.quote.price == 202.0

    asyncio.run(scenario())


def test_redis_quote_store_returns_none_for_missing_symbol() -> None:
    from market_data_service.redis_state import RedisQuoteStore

    async def scenario() -> None:
        store = RedisQuoteStore(FakeRedis(), max_age_seconds=15)
        assert await store.get_quote("MSFT.US") is None

    asyncio.run(scenario())
