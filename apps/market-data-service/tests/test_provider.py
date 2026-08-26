import inspect

from market_data_service.provider import MarketDataProvider


def test_provider_protocol_defines_async_quote_fetch() -> None:
    method = MarketDataProvider.fetch_quote
    assert inspect.iscoroutinefunction(method)
