from __future__ import annotations

import os
from dataclasses import dataclass

from .symbols import Market, normalize_symbol, parse_instrument


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


@dataclass(frozen=True, slots=True)
class AlpacaConfig:
    api_key: str
    secret_key: str
    feed: str = "iex"
    symbols: tuple[str, ...] = (
        "us:AAPL",
        "us:MSFT",
        "us:NVDA",
        "us:TSLA",
    )

    @classmethod
    def from_env(cls) -> AlpacaConfig:
        api_key = os.getenv("APCA_API_KEY_ID", "").strip()
        secret_key = os.getenv("APCA_API_SECRET_KEY", "").strip()
        if not api_key or not secret_key:
            raise ValueError("Alpaca credentials are required")

        feed = os.getenv("ALPACA_DATA_FEED", "iex").strip().lower()
        if feed not in {"iex", "sip", "delayed_sip"}:
            raise ValueError("ALPACA_DATA_FEED must be one of: iex, sip, delayed_sip")

        raw_symbols = os.getenv("MARKET_DATA_SYMBOLS", "AAPL.US,MSFT.US,NVDA.US,TSLA.US")
        instruments = [
            parse_instrument(value.strip())
            for value in raw_symbols.split(",")
            if value.strip()
        ]
        if not instruments or any(instrument.market is not Market.US for instrument in instruments):
            raise ValueError("Alpaca MARKET_DATA_SYMBOLS must contain only US symbols")

        return cls(
            api_key=api_key,
            secret_key=secret_key,
            feed=feed,
            symbols=tuple(instrument.symbol for instrument in instruments),
        )
