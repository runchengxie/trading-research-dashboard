from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Protocol

from .contracts import Quote, QuoteStatus
from .freshness import classify_freshness
from .state import QuoteState
from .symbols import normalize_symbol

QUOTE_KEY_PREFIX = "trading-research:live:v1:quote:"
HEARTBEAT_KEY = "trading-research:live:v1:collector:heartbeat"
QUOTE_CHANNEL = "trading-research:live:v1:quotes"


class AsyncRedisClient(Protocol):
    async def get(self, name: str) -> Any: ...

    async def set(self, name: str, value: str, *, ex: int | None = None) -> Any: ...

    async def publish(self, channel: str, message: str) -> Any: ...

    def pubsub(self) -> Any: ...


def quote_key(symbol: str) -> str:
    return f"{QUOTE_KEY_PREFIX}{normalize_symbol(symbol)}"


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


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
        if payload.get("schemaVersion") != "trading_research.live_quote.v1":
            raise ValueError("unsupported live quote schemaVersion")
        timestamp = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00"))
        return Quote(
            symbol=str(payload["symbol"]),
            price=float(payload["price"]),
            timestamp=timestamp,
            source=str(payload["source"]),
            status=QuoteStatus(str(payload["status"])),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid Redis live quote payload") from exc


class RedisQuoteStore:
    def __init__(self, client: AsyncRedisClient, *, max_age_seconds: float = 15) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        self._client = client
        self._max_age_seconds = max_age_seconds

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
        key = quote_key(quote.symbol)
        current_raw = await self._client.get(key)
        if current_raw is not None:
            current = _decode_quote(current_raw)
            if quote.timestamp.astimezone(UTC) < current.timestamp.astimezone(UTC):
                return False
        await self._client.set(key, _encode_quote(quote), ex=None)
        return True
