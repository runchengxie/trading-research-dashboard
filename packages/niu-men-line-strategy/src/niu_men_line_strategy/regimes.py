from __future__ import annotations

import pandas as pd


def _require_columns(data: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def simple_return_regime(
    data: pd.DataFrame,
    *,
    lookback: int = 63,
    close_column: str = "close",
) -> pd.Series:
    """Return a deliberately simple close-to-close trend score.

    The score is the trailing ``lookback``-bar return known at bar ``t`` close::

        close_t / close_(t-lookback) - 1

    Positive values represent an upward price regime for long-only NML research.
    This is a low-complexity comparator for future A1-style regime models, not an
    implementation or approximation of the report's AR(1)-GARCH(1,1) TSI model.
    Because the score uses bar ``t`` close, any signal gated by it may execute no
    earlier than bar ``t+1`` open.
    """

    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if not close_column:
        raise ValueError("close_column must be non-empty")
    _require_columns(data, (close_column,))

    close = data[close_column]
    return (close / close.shift(lookback) - 1.0).rename("price_regime")
