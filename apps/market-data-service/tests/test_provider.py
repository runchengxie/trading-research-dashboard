import inspect

import market_data_service.provider as providers
from market_data_service.provider import MarketDataProvider


def test_provider_protocol_defines_async_quote_fetch() -> None:
    method = MarketDataProvider.fetch_quote
    assert inspect.iscoroutinefunction(method)


def test_historical_provider_protocol_defines_async_bar_fetch() -> None:
    assert hasattr(providers, "HistoricalMarketDataProvider")
    method = providers.HistoricalMarketDataProvider.fetch_bars
    assert inspect.iscoroutinefunction(method)
