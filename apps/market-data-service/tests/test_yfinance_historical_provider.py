from datetime import UTC, datetime

import pytest

from market_data_service.contracts import BarTimeframe
from market_data_service.providers.yfinance_historical import YFinanceHistoricalProvider


class _FakeHistory:
    def __init__(self, rows):
        self.rows = rows

    def history(self, **kwargs):
        self.kwargs = kwargs
        return self.rows


def test_yfinance_maps_minute_history_to_canonical_bars() -> None:
    history = _FakeHistory(
        [
            {
                "timestamp": datetime(2026, 8, 27, 14, 30, tzinfo=UTC),
                "Open": 200,
                "High": 202,
                "Low": 199,
                "Close": 201,
                "Volume": 1000,
            }
        ]
    )
    provider = YFinanceHistoricalProvider(ticker_factory=lambda symbol: history)

    bars = asyncio_run(provider.fetch_bars(
        "AAPL.US",
        start=datetime(2026, 8, 27, tzinfo=UTC),
        end=datetime(2026, 8, 28, tzinfo=UTC),
        timeframe=BarTimeframe.MINUTE_1,
    ))

    assert bars[0].symbol == "us:AAPL"
    assert bars[0].timeframe is BarTimeframe.MINUTE_1
    assert bars[0].source == "yfinance"
    assert history.kwargs["interval"] == "1m"
    assert history.kwargs["auto_adjust"] is False


def test_yfinance_rejects_non_us_symbols() -> None:
    provider = YFinanceHistoricalProvider(ticker_factory=lambda symbol: _FakeHistory([]))

    with pytest.raises(ValueError, match="only supports US symbols"):
        asyncio_run(provider.fetch_bars(
            "600519.SH",
            start=datetime(2026, 8, 27, tzinfo=UTC),
            end=datetime(2026, 8, 28, tzinfo=UTC),
            timeframe=BarTimeframe.DAY_1,
        ))


def asyncio_run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
