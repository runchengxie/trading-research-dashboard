from __future__ import annotations

from collections.abc import Callable
from typing import Any

from alpaca.data.enums import DataFeed
from alpaca.data.live import StockDataStream

from ..config import AlpacaConfig
from ..contracts import Quote, QuoteStatus
from ..symbols import Market, parse_instrument

_SUPPORTED_FEEDS = {
    "iex": DataFeed.IEX,
    "sip": DataFeed.SIP,
    "delayed_sip": DataFeed.DELAYED_SIP,
}


def resolve_data_feed(raw: str) -> DataFeed:
    key = raw.strip().lower()
    try:
        return _SUPPORTED_FEEDS[key]
    except KeyError as exc:
        raise ValueError("ALPACA_DATA_FEED must be one of: iex, sip, delayed_sip") from exc


def quote_from_trade(trade: Any, *, status: QuoteStatus = QuoteStatus.LIVE) -> Quote:
    instrument = parse_instrument(str(trade.symbol), market=Market.US)
    return Quote(
        symbol=instrument.symbol,
        price=float(trade.price),
        timestamp=trade.timestamp,
        source="alpaca",
        status=status,
    )


class AlpacaStockProvider:
    def __init__(
        self,
        config: AlpacaConfig,
        *,
        stream_factory: Callable[..., StockDataStream] = StockDataStream,
    ) -> None:
        self.config = config
        self._stream_factory = stream_factory

    def create_stream(self) -> StockDataStream:
        return self._stream_factory(
            self.config.api_key,
            self.config.secret_key,
            feed=resolve_data_feed(self.config.feed),
            data_timeout=60,
        )

    @property
    def quote_status(self) -> QuoteStatus:
        return QuoteStatus.DELAYED if self.config.feed == "delayed_sip" else QuoteStatus.LIVE

    @property
    def provider_symbols(self) -> tuple[str, ...]:
        return tuple(
            parse_instrument(symbol).provider_symbol
            for symbol in self.config.symbols
        )
