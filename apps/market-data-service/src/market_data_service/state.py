from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .contracts import Freshness, Quote
from .freshness import classify_freshness
from .symbols import normalize_symbol


@dataclass(frozen=True, slots=True)
class QuoteState:
    quote: Quote
    freshness: Freshness


class QuoteStore:
    def __init__(self, *, max_age_seconds: float = 15) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        self._max_age_seconds = max_age_seconds
        self._quotes: dict[str, Quote] = {}

    def put(self, quote: Quote) -> None:
        self._quotes[quote.symbol] = quote

    def get(self, symbol: str, *, now: datetime | None = None) -> QuoteState | None:
        quote = self._quotes.get(normalize_symbol(symbol))
        if quote is None:
            return None
        observed_at = now or datetime.now(UTC)
        freshness = classify_freshness(
            quote.timestamp,
            now=observed_at,
            max_age=self._max_age_seconds,
        )
        return QuoteState(quote=quote, freshness=freshness)
