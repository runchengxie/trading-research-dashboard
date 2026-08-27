from __future__ import annotations

from typing import Any, Protocol

QUOTE_KEY_PREFIX = "trading-research:live:v1:quote:"
HEARTBEAT_KEY = "trading-research:live:v1:collector:heartbeat"
QUOTE_CHANNEL = "trading-research:live:v1:quotes"


class AsyncRedisClient(Protocol):
    async def get(self, name: str) -> Any: ...

    async def set(self, name: str, value: str, *, ex: int | None = None) -> Any: ...

    async def publish(self, channel: str, message: str) -> Any: ...

    def pubsub(self) -> Any: ...
