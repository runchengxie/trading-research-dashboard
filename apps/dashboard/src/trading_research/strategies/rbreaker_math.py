"""Pure R-Breaker level calculations."""

from __future__ import annotations


def calculate_levels(
    high: float,
    low: float,
    close: float,
    *,
    f1: float,
    f2: float,
    f3: float,
) -> tuple[float, float, float, float, float, float]:
    """Calculate setup, entry and breakout levels from the previous session."""
    if high <= low:
        raise ValueError("high must be greater than low")
    sell_setup = high + f1 * (close - low)
    buy_setup = low - f1 * (high - close)
    sell_entry = ((1 + f2) / 2) * (high + close) - f2 * low
    buy_entry = ((1 + f2) / 2) * (low + close) - f2 * high
    buy_break = sell_setup + f3 * (sell_setup - buy_setup)
    sell_break = buy_setup - f3 * (sell_setup - buy_setup)
    return sell_setup, buy_setup, sell_entry, buy_entry, buy_break, sell_break
