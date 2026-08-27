from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Market(StrEnum):
    CN = "CN"
    HK = "HK"
    US = "US"


@dataclass(frozen=True, slots=True)
class Instrument:
    market: Market
    symbol: str
    provider_symbol: str
    currency: str
    timezone: str


_CN_PREFIX = re.compile(r"^(?P<exchange>sh|sz|bj)[.?]?(?P<code>\d{6})$", re.I)
_CN_SUFFIX = re.compile(r"^(?P<code>\d{6})\.(?P<exchange>SH|SZ|BJ)$", re.I)
_HK_PREFIX = re.compile(r"^hk[.:]?(?P<code>\d{5})$", re.I)
_HK_SUFFIX = re.compile(r"^(?P<code>\d{5})\.HK$", re.I)
_US_CANONICAL = re.compile(r"^us:(?P<ticker>[A-Z][A-Z0-9.-]{0,14})$", re.I)
_US_SUFFIX = re.compile(r"^(?P<ticker>[A-Z][A-Z0-9.-]{0,14})\.US$", re.I)
_US_BARE = re.compile(r"^(?P<ticker>[A-Z][A-Z0-9.-]{0,14})$", re.I)

_MARKET_METADATA = {
    Market.CN: ("CNY", "Asia/Shanghai"),
    Market.HK: ("HKD", "Asia/Hong_Kong"),
    Market.US: ("USD", "America/New_York"),
}


def _coerce_market(value: Market | str | None) -> Market | None:
    if value is None or isinstance(value, Market):
        return value
    try:
        return Market(value.strip().upper())
    except ValueError as exc:
        raise ValueError(f"invalid market: {value!r}") from exc


def _instrument(market: Market, symbol: str, provider_symbol: str) -> Instrument:
    currency, timezone = _MARKET_METADATA[market]
    return Instrument(
        market=market,
        symbol=symbol,
        provider_symbol=provider_symbol,
        currency=currency,
        timezone=timezone,
    )


def parse_instrument(raw: str, *, market: Market | str | None = None) -> Instrument:
    value = raw.strip()
    requested_market = _coerce_market(market)

    prefix_match = _CN_PREFIX.fullmatch(value)
    suffix_match = _CN_SUFFIX.fullmatch(value)
    if prefix_match or suffix_match:
        match = prefix_match or suffix_match
        assert match is not None
        if requested_market not in (None, Market.CN):
            raise ValueError(f"symbol {raw!r} does not belong to market {requested_market}")
        exchange = match.group("exchange").lower()
        code = match.group("code")
        return _instrument(Market.CN, f"{exchange}{code}", code)

    hk_match = _HK_PREFIX.fullmatch(value) or _HK_SUFFIX.fullmatch(value)
    if hk_match:
        if requested_market not in (None, Market.HK):
            raise ValueError(f"symbol {raw!r} does not belong to market {requested_market}")
        code = hk_match.group("code")
        return _instrument(Market.HK, f"hk{code}", code)

    us_match = _US_CANONICAL.fullmatch(value) or _US_SUFFIX.fullmatch(value)
    if us_match:
        if requested_market not in (None, Market.US):
            raise ValueError(f"symbol {raw!r} does not belong to market {requested_market}")
        ticker = us_match.group("ticker").upper()
        return _instrument(Market.US, f"us:{ticker}", ticker)

    if requested_market is Market.US:
        bare_match = _US_BARE.fullmatch(value)
        if bare_match:
            ticker = bare_match.group("ticker").upper()
            return _instrument(Market.US, f"us:{ticker}", ticker)

    raise ValueError(f"invalid symbol: {raw!r}")


def normalize_symbol(raw: str) -> str:
    return parse_instrument(raw).symbol
