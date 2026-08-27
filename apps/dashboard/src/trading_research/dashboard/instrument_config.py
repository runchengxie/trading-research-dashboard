"""Dashboard instrument configuration and explicit ticker resolution."""

from __future__ import annotations

from collections.abc import Mapping

from trading_research.dashboard.config import STOCK_CONFIG
from trading_research.data import market_compat as data_sources


def vwap_deviation_override(config: Mapping[str, object]) -> float | None:
    value = config.get("vwap_dev_k")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("vwap_dev_k must be a number")
    result = float(value)
    if result <= 0:
        raise ValueError("vwap_dev_k must be positive")
    return result


def _dynamic_us_config(code: str) -> dict[str, object]:
    profile = data_sources.market_profile("US")
    ticker = code.strip().upper()
    if ticker.startswith("US:"):
        ticker = ticker[3:]
    elif ticker.endswith(".US"):
        ticker = ticker[:-3]
    return {
        "name": ticker,
        "market": profile.market,
        "instrument_type": "stock",
        "currency": profile.currency,
        "timezone": profile.timezone,
    }


def resolve_stock_config(
    codes=None,
    *,
    configured: Mapping[str, dict[str, object]] | None = None,
) -> dict[str, dict[str, object]]:
    """Return configured instruments, adding explicit US tickers when requested."""
    config_items = dict(configured or STOCK_CONFIG)
    if not codes:
        return config_items
    resolved: dict[str, dict[str, object]] = {}
    for raw_code in codes:
        code = raw_code.strip()
        if not code:
            continue
        if code in config_items:
            resolved[code] = config_items[code]
            continue
        try:
            market = data_sources.infer_market(code)
        except ValueError:
            continue
        if market == "US":
            resolved[code] = _dynamic_us_config(code)
    return resolved
