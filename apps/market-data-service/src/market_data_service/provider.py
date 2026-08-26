from __future__ import annotations

from datetime import datetime
from typing import Protocol

from .contracts import Quote


class MarketDataProvider(Protocol):
    async def fetch_quote(self, symbol: str, *, as_of: datetime | None = None) -> Quote:
        """Return one quote for a normalized symbol."""
