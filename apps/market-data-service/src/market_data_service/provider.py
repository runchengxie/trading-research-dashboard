from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .contracts import Bar, BarTimeframe, Quote


class MarketDataProvider(Protocol):
    async def fetch_quote(self, symbol: str, *, as_of: datetime | None = None) -> Quote:
        """Return one quote for a normalized symbol."""


class HistoricalMarketDataProvider(Protocol):
    async def fetch_bars(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        timeframe: BarTimeframe,
    ) -> list[Bar]:
        """Return normalized historical bars for one symbol and timeframe."""
