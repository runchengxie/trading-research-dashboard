from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Protocol, Self

from .contracts import Quote, QuoteStatus
from .freshness import classify_freshness
from .state import QuoteState
from .symbols import normalize_symbol

QUOTE_KEY_PREFIX = "trading-research:live:v1:quote:"
HEARTBEAT_KEY = "trading-research:live:v1:collector:heartbeat"
QUOTE_CHANNEL = "trading-research:live:v1:quotes"

_PUT_QUOTE_IF_NOT_OLDER_SCRIPT = """
local current = redis.call("GET", KEYS[1])
if current then
    local payload = cjson.decode(current)
    local current_timestamp = payload["timestamp"]
    if type(current_timestamp) ~= "string" then
        return redis.error_reply("invalid existing live quote timestamp")
    end
    if ARGV[2] < current_timestamp then
        return 0
    end
end
redis.call("SET", KEYS[1], ARGV[1])
return 1
"""


class AsyncRedisPubSub(Protocol):
    async def subscribe(self, channel: str) -> Any: ...

    async def unsubscribe(self, channel: str) -> Any: ...

    async def aclose(self) -> Any: ...

    def listen(self) -> AsyncIterator[dict[str, Any]]: ...


class AsyncRedisClient(Protocol):
    async def get(self, name: str) -> Any: ...

    async def set(self, name: str, value: str, *, ex: int | None = None) -> Any: ...

    async def publish(self, channel: str, message: str) -> Any: ...

    async def eval(self, script: str, numkeys: int, *keys_and_args: str) -> Any: ...

    def pubsub(self) -> AsyncRedisPubSub: ...


@dataclass(frozen=True, slots=True)
class CollectorHeartbeat:
    loop_at: datetime
    last_success_at: datetime | None
    success_count: int
    failure_count: int

    def __post_init__(self) -> None:
        if self.loop_at.tzinfo is None or self.loop_at.utcoffset() is None:
            raise ValueError("loop_at must be timezone-aware")
        if self.last_success_at is not None and (
            self.last_success_at.tzinfo is None or self.last_success_at.utcoffset() is None
        ):
            raise ValueError("last_success_at must be timezone-aware")
        if self.success_count < 0:
            raise ValueError("success_count must not be negative")
        if self.failure_count < 0:
            raise ValueError("failure_count must not be negative")


def quote_key(symbol: str) -> str:
    return f"{QUOTE_KEY_PREFIX}{normalize_symbol(symbol)}"


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timestamp string")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return timestamp


def _quote_payload(quote: Quote) -> dict[str, object]:
    return {
        "schemaVersion": "trading_research.live_quote.v1",
        "symbol": quote.symbol,
        "price": quote.price,
        "timestamp": _timestamp_text(quote.timestamp),
        "source": quote.source,
        "status": quote.status.value,
    }


def _encode_quote(quote: Quote) -> str:
    return json.dumps(_quote_payload(quote), ensure_ascii=False, separators=(",", ":"))


def _decode_quote(raw: str | bytes) -> Quote:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("live quote payload must be an object")
        if payload.get("schemaVersion") != "trading_research.live_quote.v1":
            raise ValueError("unsupported live quote schemaVersion")
        return Quote(
            symbol=str(payload["symbol"]),
            price=float(payload["price"]),
            timestamp=_parse_timestamp(payload["timestamp"], field="timestamp"),
            source=str(payload["source"]),
            status=QuoteStatus(str(payload["status"])),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid Redis live quote payload") from exc


def _encode_heartbeat(heartbeat: CollectorHeartbeat) -> str:
    return json.dumps(
        {
            "loopAt": _timestamp_text(heartbeat.loop_at),
            "lastSuccessAt": (
                _timestamp_text(heartbeat.last_success_at)
                if heartbeat.last_success_at is not None
                else None
            ),
            "successCount": heartbeat.success_count,
            "failureCount": heartbeat.failure_count,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _decode_heartbeat(raw: str | bytes) -> CollectorHeartbeat:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("heartbeat payload must be an object")
        last_success_raw = payload["lastSuccessAt"]
        last_success_at = (
            None
            if last_success_raw is None
            else _parse_timestamp(last_success_raw, field="lastSuccessAt")
        )
        return CollectorHeartbeat(
            loop_at=_parse_timestamp(payload["loopAt"], field="loopAt"),
            last_success_at=last_success_at,
            success_count=int(payload["successCount"]),
            failure_count=int(payload["failureCount"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid Redis collector heartbeat payload") from exc


class RedisQuoteSubscription:
    def __init__(self, client: AsyncRedisClient, symbols: Sequence[str]) -> None:
        normalized = frozenset(normalize_symbol(symbol) for symbol in symbols)
        if not normalized:
            raise ValueError("at least one symbol is required")
        self._client = client
        self._symbols = normalized
        self._pubsub: AsyncRedisPubSub | None = None

    async def __aenter__(self) -> Self:
        pubsub = self._client.pubsub()
        try:
            await pubsub.subscribe(QUOTE_CHANNEL)
        except BaseException:
            await pubsub.aclose()
            raise
        self._pubsub = pubsub
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pubsub = self._pubsub
        self._pubsub = None
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(QUOTE_CHANNEL)
            finally:
                await pubsub.aclose()

    async def __aiter__(self) -> AsyncIterator[Quote]:
        pubsub = self._pubsub
        if pubsub is None:
            raise RuntimeError("quote subscription must be entered before iteration")
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if not isinstance(raw, (str, bytes)):
                continue
            try:
                quote = _decode_quote(raw)
            except ValueError:
                continue
            if quote.symbol in self._symbols:
                yield quote


class RedisQuoteStore:
    def __init__(
        self,
        client: AsyncRedisClient,
        *,
        max_age_seconds: float = 15,
        heartbeat_ttl_seconds: int = 30,
    ) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        if heartbeat_ttl_seconds <= 0:
            raise ValueError("heartbeat_ttl_seconds must be positive")
        self._client = client
        self._max_age_seconds = max_age_seconds
        self._heartbeat_ttl_seconds = heartbeat_ttl_seconds

    async def get_quote(
        self,
        symbol: str,
        *,
        now: datetime | None = None,
    ) -> QuoteState | None:
        raw = await self._client.get(quote_key(symbol))
        if raw is None:
            return None
        quote = _decode_quote(raw)
        observed_at = now or datetime.now(UTC)
        freshness = classify_freshness(
            quote.timestamp,
            now=observed_at,
            max_age=self._max_age_seconds,
        )
        return QuoteState(quote=quote, freshness=freshness)

    async def get_quotes(
        self,
        symbols: Sequence[str],
        *,
        now: datetime | None = None,
    ) -> list[QuoteState]:
        observed_at = now or datetime.now(UTC)
        states: list[QuoteState] = []
        for symbol in dict.fromkeys(symbols):
            state = await self.get_quote(symbol, now=observed_at)
            if state is not None:
                states.append(state)
        return states

    async def put_quote(self, quote: Quote) -> bool:
        accepted = await self._client.eval(
            _PUT_QUOTE_IF_NOT_OLDER_SCRIPT,
            1,
            quote_key(quote.symbol),
            _encode_quote(quote),
            _timestamp_text(quote.timestamp),
        )
        return bool(accepted)

    async def publish_quote(self, quote: Quote) -> None:
        await self._client.publish(QUOTE_CHANNEL, _encode_quote(quote))

    def subscribe_quotes(self, symbols: Sequence[str]) -> RedisQuoteSubscription:
        return RedisQuoteSubscription(self._client, symbols)

    async def write_heartbeat(self, heartbeat: CollectorHeartbeat) -> None:
        await self._client.set(
            HEARTBEAT_KEY,
            _encode_heartbeat(heartbeat),
            ex=self._heartbeat_ttl_seconds,
        )

    async def get_heartbeat(self) -> CollectorHeartbeat | None:
        raw = await self._client.get(HEARTBEAT_KEY)
        if raw is None:
            return None
        return _decode_heartbeat(raw)
