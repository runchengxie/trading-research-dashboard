import asyncio
import importlib.util
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.timeframe import TimeFrame

import market_data_service.providers.alpaca_historical as historical
from market_data_service.config import AlpacaConfig
from market_data_service.contracts import BarTimeframe


def test_alpaca_historical_provider_module_is_available() -> None:
    assert importlib.util.find_spec("market_data_service.providers.alpaca_historical") is not None
    assert hasattr(historical, "AlpacaHistoricalProvider")


class FakeBarSet:
    def __init__(self, bars_by_symbol):
        self._bars_by_symbol = bars_by_symbol

    def __getitem__(self, symbol):
        return self._bars_by_symbol[symbol]


class FakeHistoricalClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def get_stock_bars(self, request):
        self.requests.append(request)
        return self.response


def _config(feed: str = "iex") -> AlpacaConfig:
    return AlpacaConfig(
        api_key="key-id",
        secret_key="secret",
        feed=feed,
        symbols=("us:AAPL",),
    )


def _request_factory(calls):
    def factory(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(**kwargs)

    return factory


def test_daily_bars_map_alpaca_request_and_canonical_contract() -> None:
    async def scenario() -> None:
        calls = []
        source_bar = SimpleNamespace(
            symbol="AAPL",
            timestamp=datetime(2026, 8, 26, 4, 0, tzinfo=UTC),
            open=225.0,
            high=229.5,
            low=224.0,
            close=228.0,
            volume=52_000_000,
        )
        client = FakeHistoricalClient(FakeBarSet({"AAPL": [source_bar]}))
        provider = historical.AlpacaHistoricalProvider(
            _config(), client=client, request_factory=_request_factory(calls)
        )
        start = datetime(2026, 8, 1, tzinfo=UTC)
        end = datetime(2026, 8, 27, tzinfo=UTC)

        bars = await provider.fetch_bars("AAPL.US", start=start, end=end, timeframe=BarTimeframe.DAY_1)

        assert len(calls) == 1
        request = calls[0]
        assert request["symbol_or_symbols"] == "AAPL"
        assert request["timeframe"].value == TimeFrame.Day.value
        assert request["feed"] == DataFeed.IEX
        assert request["adjustment"] == Adjustment.ALL
        assert request["start"] == start
        assert request["end"] == end
        assert len(bars) == 1
        assert bars[0].symbol == "us:AAPL"
        assert bars[0].timeframe is BarTimeframe.DAY_1
        assert bars[0].close == 228.0
        assert bars[0].volume == 52_000_000
        assert bars[0].source == "alpaca:iex"

    asyncio.run(scenario())


def test_minute_bars_use_minute_timeframe_and_selected_feed() -> None:
    async def scenario() -> None:
        calls = []
        source_bar = SimpleNamespace(
            symbol="MSFT",
            timestamp=datetime(2026, 8, 26, 14, 31, tzinfo=UTC),
            open=501.0,
            high=501.5,
            low=500.5,
            close=501.25,
            volume=12_345,
        )
        client = FakeHistoricalClient(FakeBarSet({"MSFT": [source_bar]}))
        provider = historical.AlpacaHistoricalProvider(
            _config("sip"), client=client, request_factory=_request_factory(calls)
        )

        bars = await provider.fetch_bars(
            "MSFT.US",
            start=datetime(2026, 8, 26, 13, 30, tzinfo=UTC),
            end=datetime(2026, 8, 26, 20, 0, tzinfo=UTC),
            timeframe=BarTimeframe.MINUTE_1,
        )

        assert calls[0]["timeframe"].value == TimeFrame.Minute.value
        assert calls[0]["feed"] == DataFeed.SIP
        assert bars[0].timeframe is BarTimeframe.MINUTE_1
        assert bars[0].source == "alpaca:sip"

    asyncio.run(scenario())


def test_historical_provider_rejects_non_us_symbols_and_invalid_windows() -> None:
    provider = historical.AlpacaHistoricalProvider(
        _config(), client=FakeHistoricalClient(FakeBarSet({})), request_factory=lambda **kwargs: kwargs
    )
    start = datetime(2026, 8, 27, tzinfo=UTC)

    with pytest.raises(ValueError, match="US"):
        asyncio.run(
            provider.fetch_bars(
                "sz300246",
                start=start,
                end=datetime(2026, 8, 28, tzinfo=UTC),
                timeframe=BarTimeframe.DAY_1,
            )
        )
    with pytest.raises(ValueError, match="start.*end"):
        asyncio.run(
            provider.fetch_bars(
                "AAPL.US",
                start=start,
                end=start,
                timeframe=BarTimeframe.DAY_1,
            )
        )


def test_historical_provider_returns_empty_list_for_empty_alpaca_result() -> None:
    class EmptyBarSet:
        def __getitem__(self, symbol):
            raise KeyError(symbol)

    async def scenario() -> None:
        provider = historical.AlpacaHistoricalProvider(
            _config(), client=FakeHistoricalClient(EmptyBarSet()), request_factory=lambda **kwargs: kwargs
        )
        bars = await provider.fetch_bars(
            "AAPL.US",
            start=datetime(2026, 8, 1, tzinfo=UTC),
            end=datetime(2026, 8, 27, tzinfo=UTC),
            timeframe=BarTimeframe.DAY_1,
        )
        assert bars == []

    asyncio.run(scenario())
