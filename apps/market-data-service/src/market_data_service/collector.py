from __future__ import annotations

import threading
from collections.abc import Awaitable
from datetime import UTC, datetime
from inspect import isawaitable
from typing import Any, Protocol

from .contracts import QuoteStatus
from .providers.alpaca import quote_from_trade
from .redis_state import CollectorHeartbeat
from .state import QuoteStore


class StockStream(Protocol):
    def subscribe_trades(self, handler, *symbols: str) -> None: ...

    def run(self) -> None: ...

    def stop(self) -> None: ...


class StreamingProvider(Protocol):
    @property
    def provider_symbols(self) -> tuple[str, ...]: ...

    @property
    def quote_status(self) -> QuoteStatus: ...

    def create_stream(self) -> StockStream: ...


class QuoteSink(Protocol):
    def put_quote(self, quote: Any) -> Any: ...


class HeartbeatSink(Protocol):
    def write_heartbeat(self, heartbeat: CollectorHeartbeat): ...


class AlpacaCollector:
    def __init__(
        self,
        provider: StreamingProvider,
        store: QuoteSink | QuoteStore,
        *,
        heartbeat_sink: HeartbeatSink | None = None,
    ) -> None:
        self._provider = provider
        self._store: Any = store
        self._stream: StockStream | None = None
        self._thread: threading.Thread | None = None
        self._heartbeat_sink = heartbeat_sink
        self._success_count = 0
        self._failure_count = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        stream = self._provider.create_stream()

        async def handle_trade(trade) -> None:
            quote = quote_from_trade(trade, status=self._provider.quote_status)
            try:
                result = self._store.put_quote(quote) if hasattr(self._store, "put_quote") else self._store.put(quote)
                if isinstance(result, Awaitable) or isawaitable(result):
                    await result
                self._success_count += 1
            except Exception:
                self._failure_count += 1
                raise
            finally:
                if self._heartbeat_sink is not None:
                    self._heartbeat_sink.write_heartbeat(
                        CollectorHeartbeat(
                            loop_at=datetime.now(UTC),
                            last_success_at=datetime.now(UTC) if self._success_count else None,
                            success_count=self._success_count,
                            failure_count=self._failure_count,
                        )
                    )

        stream.subscribe_trades(handle_trade, *self._provider.provider_symbols)
        self._stream = stream
        self._thread = threading.Thread(
            target=stream.run,
            name="alpaca-stock-data-stream",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        stream = self._stream
        thread = self._thread
        if stream is not None:
            stream.stop()
        if thread is not None and thread.is_alive():
            thread.join(timeout=5)
        self._stream = None
        self._thread = None
