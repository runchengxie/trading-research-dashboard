from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ..contracts import Bar, BarTimeframe
from ..symbols import Market, parse_instrument

_INTERVALS = {
    BarTimeframe.DAY_1: "1d",
    BarTimeframe.MINUTE_1: "1m",
}


def _default_ticker_factory(symbol: str) -> Any:
    import yfinance as yf

    return yf.Ticker(symbol)


def _as_timezone(timestamp: Any, timezone: str) -> datetime:
    value = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
    if not isinstance(value, datetime):
        raise ValueError("yfinance returned a non-datetime bar timestamp")
    target = ZoneInfo(timezone)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=target)
    return value.astimezone(target)


def _rows(history: Any) -> Iterable[tuple[Any, Any]]:
    if hasattr(history, "iterrows"):
        return history.iterrows()
    return ((row["timestamp"], row) for row in history)


class YFinanceHistoricalProvider:
    """Provider for keyless US historical daily and recent minute bars."""

    def __init__(self, *, ticker_factory: Callable[[str], Any] = _default_ticker_factory) -> None:
        self._ticker_factory = ticker_factory

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
            raise ValueError(f"yfinance historical provider only supports US symbols: {symbol!r}") from exc

        normalized_timeframe = BarTimeframe(timeframe)
        ticker = self._ticker_factory(instrument.provider_symbol)
        history = await asyncio.to_thread(
            ticker.history,
            start=start,
            end=end,
            interval=_INTERVALS[normalized_timeframe],
            auto_adjust=False,
            actions=False,
            prepost=False,
        )
        bars: list[Bar] = []
        for timestamp, row in _rows(history):
            bars.append(
                Bar(
                    symbol=instrument.symbol,
                    timeframe=normalized_timeframe,
                    timestamp=_as_timezone(timestamp, instrument.timezone),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                    source="yfinance",
                )
            )
        return bars
