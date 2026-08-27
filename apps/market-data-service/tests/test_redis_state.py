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

    async def eval(self, script: str, numkeys: int, *keys_and_args):
        assert numkeys == 1
        name, value, timestamp = keys_and_args
        current_raw = self.values.get(name)
        if current_raw is not None:
            current = json.loads(current_raw)
            if timestamp < current["timestamp"]:
                return 0
        self.values[name] = value
        self.expiries[name] = None
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


def test_concurrent_quote_writes_never_replace_a_newer_quote_with_an_older_one() -> None:
    from market_data_service.redis_state import RedisQuoteStore

    class RacingRedis(FakeRedis):
        def __init__(self) -> None:
            super().__init__()
            self._read_count = 0
            self._both_read = asyncio.Event()
            self._eval_lock = asyncio.Lock()

        async def get(self, name: str):
            current = self.values.get(name)
            self._read_count += 1
            if self._read_count >= 2:
                self._both_read.set()
            await self._both_read.wait()
            return current

        async def set(self, name: str, value: str, *, ex: int | None = None):
            if json.loads(value)["price"] == 199.0:
                await asyncio.sleep(0.01)
            return await super().set(name, value, ex=ex)

        async def eval(self, script: str, numkeys: int, *keys_and_args):
            async with self._eval_lock:
                return await super().eval(script, numkeys, *keys_and_args)

    async def scenario() -> None:
        redis = RacingRedis()
        store = RedisQuoteStore(redis)
        timestamp = datetime(2026, 8, 27, 2, 0, tzinfo=UTC)
        newer = Quote("AAPL.US", 202.0, timestamp, "alpaca")
        older = Quote("AAPL.US", 199.0, timestamp - timedelta(microseconds=1), "alpaca")

        await asyncio.gather(store.put_quote(newer), store.put_quote(older))
        redis._both_read.set()

        state = await store.get_quote("AAPL.US", now=timestamp)
        assert state is not None
        assert state.quote.price == 202.0
        assert state.quote.timestamp == timestamp

    asyncio.run(scenario())


def test_redis_quote_store_returns_none_for_missing_symbol() -> None:
    from market_data_service.redis_state import RedisQuoteStore

    async def scenario() -> None:
        store = RedisQuoteStore(FakeRedis(), max_age_seconds=15)
        assert await store.get_quote("MSFT.US") is None

    asyncio.run(scenario())
