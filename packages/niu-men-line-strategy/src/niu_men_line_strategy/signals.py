from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .indicators import niu_men_lines


@dataclass(frozen=True)
class StrategyConfig:
    high_lookback: int = 20
    atr_period: int = 14
    nml_atr_multiple: float = 0.5
    qrl_atr_multiple: float = 1.0
    smx_period: int = 10
    reset_bars: int = 5

    enable_red_three_soldiers: bool = True
    soldier_body_atr_fraction: float = 0.5

    enable_long_upper_shadow: bool = True
    upper_shadow_fraction: float = 0.4
    volume_spike_ratio: float = 1.5
    volume_lookback: int = 20

    enable_sector_retreat: bool = False
    sector_fast_period: int = 20
    sector_slow_period: int = 60

    enable_market_volume_divergence: bool = False
    market_dry_ratio: float = 0.8
    asset_spike_ratio: float = 1.5
    market_volume_lookback: int = 20

    enable_regime_gate: bool = False
    minimum_regime_score: float = 0.0


def _require_columns(data: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")


def _red_three_soldiers(data: pd.DataFrame, atr: pd.Series, config: StrategyConfig) -> pd.Series:
    bullish = data["close"] > data["open"]
    rising_close = data["close"].diff() > 0
    body_large = (data["close"] - data["open"]).abs() >= (
        config.soldier_body_atr_fraction * atr
    )

    three_bullish = bullish.rolling(3, min_periods=3).sum().eq(3)
    three_large = body_large.rolling(3, min_periods=3).sum().eq(3)
    two_rises = rising_close.rolling(2, min_periods=2).sum().eq(2)
    # The source says the three bars occur before the NML touch bar.
    return (three_bullish & three_large & two_rises).shift(1, fill_value=False)


def _long_upper_shadow_with_volume(data: pd.DataFrame, config: StrategyConfig) -> pd.Series:
    upper_shadow = data["high"] - data[["open", "close"]].max(axis=1)
    bar_range = (data["high"] - data["low"]).replace(0, pd.NA)
    upper_shadow_ratio = upper_shadow / bar_range
    previous_average_volume = (
        data["volume"]
        .shift(1)
        .rolling(config.volume_lookback, min_periods=config.volume_lookback)
        .mean()
    )
    volume_ratio = data["volume"] / previous_average_volume
    return (upper_shadow_ratio >= config.upper_shadow_fraction) & (
        volume_ratio >= config.volume_spike_ratio
    )


def _sector_retreat(data: pd.DataFrame, config: StrategyConfig) -> pd.Series:
    _require_columns(data, ("sector_close",))
    fast = data["sector_close"].rolling(
        config.sector_fast_period, min_periods=config.sector_fast_period
    ).mean()
    slow = data["sector_close"].rolling(
        config.sector_slow_period, min_periods=config.sector_slow_period
    ).mean()
    return (data["sector_close"] < fast) & (fast < slow)


def _market_volume_divergence(data: pd.DataFrame, config: StrategyConfig) -> pd.Series:
    _require_columns(data, ("market_volume",))
    market_average = (
        data["market_volume"]
        .shift(1)
        .rolling(
            config.market_volume_lookback,
            min_periods=config.market_volume_lookback,
        )
        .mean()
    )
    asset_average = (
        data["volume"]
        .shift(1)
        .rolling(
            config.market_volume_lookback,
            min_periods=config.market_volume_lookback,
        )
        .mean()
    )
    market_ratio = data["market_volume"] / market_average
    asset_ratio = data["volume"] / asset_average
    return (market_ratio <= config.market_dry_ratio) & (
        asset_ratio >= config.asset_spike_ratio
    )


def _regime_block(data: pd.DataFrame, config: StrategyConfig) -> pd.Series:
    _require_columns(data, ("macro_regime", "industry_regime"))
    return (data["macro_regime"] <= config.minimum_regime_score) | (
        data["industry_regime"] <= config.minimum_regime_score
    )


def build_signals(data: pd.DataFrame, config: StrategyConfig | None = None) -> pd.DataFrame:
    """Build a close-confirmed, next-open executable baseline signal set.

    The transcribed ``+ATR`` formula is treated as an upward breakout threshold.
    A baseline entry requires a close crossing above NML after ``reset_bars``
    consecutive prior closes below NML. This is an explicit research
    interpretation of the source conflict, not a claim that the transcript's
    separate "pullback" wording is correct.
    """

    config = config or StrategyConfig()
    _require_columns(data, ("open", "high", "low", "close", "volume"))
    if config.reset_bars <= 0:
        raise ValueError("reset_bars must be positive")

    indicators = niu_men_lines(
        data,
        high_lookback=config.high_lookback,
        atr_period=config.atr_period,
        nml_atr_multiple=config.nml_atr_multiple,
        qrl_atr_multiple=config.qrl_atr_multiple,
        smx_period=config.smx_period,
    )
    result = pd.concat([data.copy(), indicators], axis=1)

    below_nml = result["close"] < result["nml"]
    armed = (
        below_nml.shift(1)
        .rolling(config.reset_bars, min_periods=config.reset_bars)
        .sum()
        .eq(config.reset_bars)
    )
    crossing = (result["close"] >= result["nml"]) & (
        result["close"].shift(1) < result["nml"].shift(1)
    )

    result["filter_red_three_soldiers"] = (
        _red_three_soldiers(result, result["atr"], config)
        if config.enable_red_three_soldiers
        else False
    )
    result["filter_long_upper_shadow"] = (
        _long_upper_shadow_with_volume(result, config)
        if config.enable_long_upper_shadow
        else False
    )
    result["filter_sector_retreat"] = (
        _sector_retreat(result, config) if config.enable_sector_retreat else False
    )
    result["filter_market_volume_divergence"] = (
        _market_volume_divergence(result, config)
        if config.enable_market_volume_divergence
        else False
    )
    result["filter_regime"] = (
        _regime_block(result, config) if config.enable_regime_gate else False
    )

    filter_columns = [
        "filter_red_three_soldiers",
        "filter_long_upper_shadow",
        "filter_sector_retreat",
        "filter_market_volume_divergence",
        "filter_regime",
    ]
    blocked = result[filter_columns].fillna(False).any(axis=1)
    result["armed"] = armed.fillna(False)
    result["raw_entry_signal"] = crossing.fillna(False)
    result["entry_signal"] = (crossing & armed & ~blocked).fillna(False)
    result["exit_signal"] = (result["close"] < result["smx"]).fillna(False)
    return result
