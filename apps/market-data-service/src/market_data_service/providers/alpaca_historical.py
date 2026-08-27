from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any

from alpaca.data.enums import Adjustment
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from ..config import AlpacaConfig
from ..contracts import Bar, BarTimeframe
from ..symbols import Market, parse_instrument
from .alpaca import resolve_data_feed

_TIMEFRAMES = {
    BarTimeframe.DAY_1: TimeFrame.Day,
    BarTimeframe.MINUTE_1: TimeFrame.Minute,
}


class AlpacaHistoricalProvider:
    def __init__(
        self,
        config: AlpacaConfig,
        *,
        client: Any | None = None,
        request_factory: Callable[..., Any] = StockBarsRequest,
    ) -> None:
        self.config = config
        self._client = client or StockHistoricalDataClient(config.api_key, config.secret_key)
        self._request_factory = request_factory

    async def fetch_bars(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        timeframe: BarTimeframe,
    ) -> list[Bar]:
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError("start must be timezone-aware")
        if end.tzinfo is None or end.utcoffset() is None:
            raise ValueError("end must be timezone-aware")
        if start >= end:
            raise ValueError("start must be before end")

        try:
            instrument = parse_instrument(symbol, market=Market.US)
        except ValueError as exc:
            raise ValueError(f"Alpaca historical provider only supports US symbols: {symbol!r}") from exc

        normalized_timeframe = BarTimeframe(timeframe)
        request = self._request_factory(
            symbol_or_symbols=instrument.provider_symbol,
            timeframe=_TIMEFRAMES[normalized_timeframe],
            start=start,
            end=end,
            adjustment=Adjustment.ALL,
            feed=resolve_data_feed(self.config.feed),
        )
        response = await asyncio.to_thread(self._client.get_stock_bars, request)
        try:
            source_bars = response[instrument.provider_symbol]
        except KeyError:
            return []

        source = f"alpaca:{self.config.feed}"
        return [
            Bar(
                symbol=instrument.symbol,
                timeframe=normalized_timeframe,
                timestamp=source_bar.timestamp,
                open=float(source_bar.open),
                high=float(source_bar.high),
                low=float(source_bar.low),
                close=float(source_bar.close),
                volume=float(source_bar.volume),
                source=source,
            )
            for source_bar in source_bars
        ]
