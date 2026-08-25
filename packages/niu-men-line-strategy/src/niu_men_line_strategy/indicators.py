from __future__ import annotations

from typing import Literal

import pandas as pd

AssetClass = Literal["stock", "etf", "index", "futures", "commodity"]
_ALLOWED_ASSET_CLASSES = {"stock", "etf", "index", "futures", "commodity"}


def _require_columns(data: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def true_range(data: pd.DataFrame) -> pd.Series:
    """Return the transcribed true range series.

    TR_t = max(H_t-L_t, |H_t-C_{t-1}|, |L_t-C_{t-1}|)
    """

    _require_columns(data, ("high", "low", "close"))
    previous_close = data["close"].shift(1)
    components = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return components.max(axis=1).rename("tr")


def simple_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Return ATR as a simple moving average of true range.

    This intentionally matches ``MA(TR1, M)`` from the source material and
    is not Wilder/RMA ATR.
    """

    if period <= 0:
        raise ValueError("period must be positive")
    return true_range(data).rolling(period, min_periods=period).mean().rename("atr")


def niu_men_lines(
    data: pd.DataFrame,
    *,
    high_lookback: int = 20,
    atr_period: int = 14,
    nml_atr_multiple: float = 0.5,
    qrl_atr_multiple: float = 1.0,
    smx_period: int = 10,
    atr_lag: int = 0,
) -> pd.DataFrame:
    """Compute the transcribed NML/QRL lines and the 10-bar moving average.

    ``atr_lag=0`` reproduces the close-known source formula. ``atr_lag=1``
    creates a pre-open research variant whose ATR component is known before
    the current bar starts.
    """

    _require_columns(data, ("high", "low", "close"))
    if high_lookback <= 0 or atr_period <= 0 or smx_period <= 0:
        raise ValueError("lookback periods must be positive")
    if atr_lag < 0:
        raise ValueError("atr_lag cannot be negative")

    previous_high = (
        data["high"]
        .rolling(high_lookback, min_periods=high_lookback)
        .max()
        .shift(1)
        .rename("previous_high")
    )
    atr = simple_atr(data, atr_period)
    atr_for_line = atr.shift(atr_lag) if atr_lag else atr
    nml = (previous_high + nml_atr_multiple * atr_for_line).rename("nml")
    qrl = (previous_high + qrl_atr_multiple * atr_for_line).rename("qrl")
    smx = data["close"].rolling(smx_period, min_periods=smx_period).mean().rename("smx")
    return pd.concat([previous_high, atr, nml, qrl, smx], axis=1)


def cost_line_proxy(
    data: pd.DataFrame,
    *,
    window: int,
    asset_class: AssetClass,
    amount_scale: float = 1.0,
) -> pd.Series:
    """Compute a rolling volume-weighted price proxy.

    Stocks/ETFs require an explicit ``amount`` column and use rolling amount
    divided by rolling volume, with ``amount_scale`` handling vendor units.
    Indices/futures/commodities use the documented ``close * volume`` proxy.
    The result is deliberately called a proxy, not institutional cost.
    """

    if window <= 0:
        raise ValueError("window must be positive")
    if asset_class not in _ALLOWED_ASSET_CLASSES:
        raise ValueError(f"unsupported asset_class: {asset_class}")
    _require_columns(data, ("close", "volume"))

    denominator = data["volume"].rolling(window, min_periods=window).sum()
    if asset_class in {"stock", "etf"}:
        _require_columns(data, ("amount",))
        numerator = data["amount"].rolling(window, min_periods=window).sum()
        result = numerator / denominator * amount_scale
    else:
        numerator = (
            (data["close"] * data["volume"]).rolling(window, min_periods=window).sum()
        )
        result = numerator / denominator

    return result.where(denominator != 0).rename(f"cost_proxy_{window}")
