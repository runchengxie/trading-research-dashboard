"""Frozen-parameter rolling out-of-sample evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .backtest import BacktestConfig, BacktestResult, run_backtest
from .signals import StrategyConfig, build_signals


@dataclass(frozen=True)
class WalkForwardConfig:
    train_bars: int = 252 * 3
    test_bars: int = 252
    step_bars: int = 252


@dataclass(frozen=True)
class WalkForwardFold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


@dataclass(frozen=True)
class WalkForwardResult:
    folds: tuple[WalkForwardFold, ...]
    results: tuple[BacktestResult, ...]


def walk_forward_folds(
    dates: pd.DatetimeIndex, config: WalkForwardConfig | None = None
) -> tuple[WalkForwardFold, ...]:
    """Build rolling, non-overlapping test folds with a prior training window."""

    config = config or WalkForwardConfig()
    if min(config.train_bars, config.test_bars, config.step_bars) <= 0:
        raise ValueError("walk-forward bar counts must be positive")
    if not dates.is_monotonic_increasing or dates.has_duplicates:
        raise ValueError("dates must be unique and ascending")
    folds: list[WalkForwardFold] = []
    test_start = config.train_bars
    while test_start + config.test_bars <= len(dates):
        folds.append(
            WalkForwardFold(
                train_start=dates[test_start - config.train_bars],
                train_end=dates[test_start - 1],
                test_start=dates[test_start],
                test_end=dates[test_start + config.test_bars - 1],
            )
        )
        test_start += config.step_bars
    return tuple(folds)


def run_walk_forward(
    data: pd.DataFrame,
    *,
    strategy_config: StrategyConfig | None = None,
    backtest_config: BacktestConfig | None = None,
    walk_forward_config: WalkForwardConfig | None = None,
) -> WalkForwardResult:
    """Evaluate frozen strategy parameters over independent out-of-sample folds.

    Signals are calculated on the complete history so rolling indicators have
    their proper pre-test warm-up. Each fold starts flat; a decision made before
    its first OOS close is intentionally excluded rather than leaked in.
    """

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("data index must be a DatetimeIndex")
    folds = walk_forward_folds(data.index, walk_forward_config)
    signals = build_signals(data, strategy_config)
    results = []
    for fold in folds:
        oos_signals = signals.loc[fold.test_start : fold.test_end]
        results.append(run_backtest(oos_signals, backtest_config))
    return WalkForwardResult(folds=folds, results=tuple(results))
