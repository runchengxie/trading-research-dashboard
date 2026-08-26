from __future__ import annotations

import os
from dataclasses import dataclass

from .symbols import normalize_symbol


@dataclass(frozen=True, slots=True)
class ServiceConfig:
    quote_max_age_seconds: int = 15
    symbols: tuple[str, ...] = ("sz300246",)

    @classmethod
    def from_env(cls) -> ServiceConfig:
        raw_symbols = os.getenv("MARKET_DATA_SYMBOLS", "sz300246")
        symbols = tuple(normalize_symbol(value) for value in raw_symbols.split(",") if value.strip())
        if not symbols:
            raise ValueError("MARKET_DATA_SYMBOLS must contain at least one symbol")
        max_age = int(os.getenv("MARKET_DATA_QUOTE_MAX_AGE_SECONDS", "15"))
        if max_age <= 0:
            raise ValueError("MARKET_DATA_QUOTE_MAX_AGE_SECONDS must be positive")
        return cls(quote_max_age_seconds=max_age, symbols=symbols)
