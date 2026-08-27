from __future__ import annotations

import threading
from typing import Protocol

from .contracts import QuoteStatus
from .providers.alpaca import quote_from_trade
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


class AlpacaCollector:
    def __init__(self, provider: StreamingProvider, store: QuoteStore) -> None:
        self._provider = provider
        self._store = store
        self._stream: StockStream | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        stream = self._provider.create_stream()

        async def handle_trade(trade) -> None:
            self._store.put(quote_from_trade(trade, status=self._provider.quote_status))

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
