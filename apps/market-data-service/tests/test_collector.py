import time
from datetime import UTC, datetime
from types import SimpleNamespace

from market_data_service.collector import AlpacaCollector
from market_data_service.contracts import Freshness, QuoteStatus
from market_data_service.state import QuoteStore


class FakeStream:
    def __init__(self) -> None:
        self.handler = None
        self.symbols = ()
        self.run_calls = 0
        self.stop_calls = 0

    def subscribe_trades(self, handler, *symbols) -> None:
        self.handler = handler
        self.symbols = symbols

    def run(self) -> None:
        self.run_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


class FakeProvider:
    provider_symbols = ("AAPL", "MSFT")
    quote_status = QuoteStatus.LIVE

    def __init__(self, stream: FakeStream) -> None:
        self.stream = stream

    def create_stream(self) -> FakeStream:
        return self.stream


def test_collector_uses_one_stream_and_writes_trade_to_store() -> None:
    stream = FakeStream()
    store = QuoteStore(max_age_seconds=15)
    collector = AlpacaCollector(FakeProvider(stream), store)

    collector.start()
    for _ in range(100):
        if stream.run_calls:
            break
        time.sleep(0.001)
    assert stream.symbols == ("AAPL", "MSFT")
    assert stream.run_calls == 1

    trade = SimpleNamespace(
        symbol="AAPL",
        price=201.25,
        timestamp=datetime.now(UTC),
    )
    assert stream.handler is not None
    __import__("asyncio").run(stream.handler(trade))

    state = store.get("AAPL.US")
    assert state is not None
    assert state.quote.price == 201.25
    assert state.quote.status is QuoteStatus.LIVE
    assert state.freshness is Freshness.CURRENT

    collector.stop()
    assert stream.stop_calls == 1
