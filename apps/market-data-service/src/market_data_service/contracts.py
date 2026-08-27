from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .symbols import normalize_symbol


class QuoteStatus(StrEnum):
    LIVE = "live"
    DELAYED = "delayed"


class Freshness(StrEnum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class BarTimeframe(StrEnum):
    DAY_1 = "1d"
    MINUTE_1 = "1m"


@dataclass(frozen=True, slots=True)
class Quote:
    symbol: str
    price: float
    timestamp: datetime
    source: str
    status: QuoteStatus = QuoteStatus.LIVE

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if not self.source.strip():
            raise ValueError("source must not be empty")


@dataclass(frozen=True, slots=True)
class Bar:
    symbol: str
    timeframe: BarTimeframe
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    source: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", normalize_symbol(self.symbol))
        object.__setattr__(self, "timeframe", BarTimeframe(self.timeframe))
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        prices = (self.open, self.high, self.low, self.close)
        if any(price <= 0 for price in prices):
            raise ValueError("bar prices must be positive")
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("bar high must be greater than or equal to OHLC values")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("bar low must be less than or equal to OHLC values")
        if self.volume < 0:
            raise ValueError("bar volume must not be negative")
        if not self.source.strip():
            raise ValueError("source must not be empty")
