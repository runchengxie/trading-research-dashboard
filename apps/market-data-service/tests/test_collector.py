import threading
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


def test_collector_records_failed_store_write_in_heartbeat() -> None:
    class FailingStore:
        def put_quote(self, quote) -> None:
            del quote
            raise ConnectionError("store unavailable")

    class HeartbeatRecorder:
        def __init__(self) -> None:
            self.values = []

        def write_heartbeat(self, heartbeat) -> None:
            self.values.append(heartbeat)

    stream = FakeStream()
    heartbeat = HeartbeatRecorder()
    collector = AlpacaCollector(
        FakeProvider(stream), FailingStore(), heartbeat_sink=heartbeat
    )
    collector.start()

    trade = SimpleNamespace(symbol="AAPL", price=201.25, timestamp=datetime.now(UTC))
    assert stream.handler is not None
    try:
        __import__("asyncio").run(stream.handler(trade))
    except ConnectionError:
        pass

    assert len(heartbeat.values) == 1
    assert heartbeat.values[0].success_count == 0
    assert heartbeat.values[0].failure_count == 1
    collector.stop()


def test_collector_can_start_again_after_stop() -> None:
    stream = FakeStream()
    collector = AlpacaCollector(FakeProvider(stream), QuoteStore())

    collector.start()
    collector.stop()
    collector.start()
    collector.stop()

    assert stream.run_calls == 2
    assert stream.stop_calls == 2


def test_collector_reconnects_after_stream_failure() -> None:
    first = FakeStream()
    second = FakeStream()
    second_stopped = threading.Event()

    def run_first() -> None:
        first.run_calls += 1
        raise ConnectionError("provider disconnected")

    def run_second() -> None:
        second.run_calls += 1
        second_stopped.wait(timeout=1)

    first.run = run_first
    second.run = run_second

    class ReconnectingProvider(FakeProvider):
        def __init__(self) -> None:
            self.streams = iter((first, second))

        def create_stream(self) -> FakeStream:
            return next(self.streams)

    original_stop = second.stop

    def stop_second() -> None:
        original_stop()
        second_stopped.set()

    second.stop = stop_second
    collector = AlpacaCollector(
        ReconnectingProvider(), QuoteStore(), reconnect_delay_seconds=0
    )

    collector.start()
    for _ in range(100):
        if second.run_calls:
            break
        time.sleep(0.001)

    assert first.run_calls == 1
    assert second.run_calls == 1
    assert second.symbols == ("AAPL", "MSFT")
    collector.stop()
