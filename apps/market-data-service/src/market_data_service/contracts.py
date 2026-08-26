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
