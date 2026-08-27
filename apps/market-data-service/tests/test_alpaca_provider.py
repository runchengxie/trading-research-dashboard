from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from market_data_service.config import AlpacaConfig
from market_data_service.contracts import QuoteStatus
from market_data_service.providers.alpaca import (
    AlpacaStockProvider,
    quote_from_trade,
    resolve_data_feed,
)


def _trade():
    return SimpleNamespace(
        symbol="AAPL",
        price=201.25,
        timestamp=datetime(2026, 8, 26, 20, 1, tzinfo=UTC),
    )


def test_quote_from_trade_normalizes_alpaca_symbol() -> None:
    quote = quote_from_trade(_trade())

    assert quote.symbol == "us:AAPL"
    assert quote.price == 201.25
    assert quote.source == "alpaca"
    assert quote.status is QuoteStatus.LIVE


@pytest.mark.parametrize("raw", ["iex", "IEX", "sip", "delayed_sip"])
def test_resolve_data_feed_accepts_supported_feeds(raw: str) -> None:
    feed = resolve_data_feed(raw)
    assert feed.value.lower() == raw.lower()


def test_resolve_data_feed_rejects_unknown_feed() -> None:
    with pytest.raises(ValueError, match="ALPACA_DATA_FEED"):
        resolve_data_feed("boats")


def test_provider_marks_delayed_sip_quotes_delayed() -> None:
    provider = AlpacaStockProvider(
        AlpacaConfig(
            api_key="key-id",
            secret_key="secret",
            feed="delayed_sip",
            symbols=("us:AAPL",),
        ),
        stream_factory=lambda *args, **kwargs: SimpleNamespace(),
    )

    quote = quote_from_trade(_trade(), status=provider.quote_status)

    assert provider.quote_status is QuoteStatus.DELAYED
    assert quote.status is QuoteStatus.DELAYED


def test_provider_enables_stream_data_timeout() -> None:
    calls = {}

    def fake_stream_factory(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return SimpleNamespace()

    config = AlpacaConfig(
        api_key="key-id",
        secret_key="secret",
        feed="iex",
        symbols=("us:AAPL",),
    )
    provider = AlpacaStockProvider(config, stream_factory=fake_stream_factory)

    provider.create_stream()

    assert calls["args"] == ("key-id", "secret")
    assert calls["kwargs"]["feed"].value == "iex"
    assert calls["kwargs"]["data_timeout"] == 60
