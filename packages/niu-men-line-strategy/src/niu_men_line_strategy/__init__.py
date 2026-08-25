"""Research implementation of the Niu Men Line strategy."""

from .backtest import (
    BacktestConfig,
    BacktestResult,
    Trade,
    run_backtest,
    run_buy_and_hold,
)
from .data import load_tushare_daily_clean
from .indicators import cost_line_proxy, niu_men_lines, simple_atr, true_range
from .signals import StrategyConfig, build_signals

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "StrategyConfig",
    "Trade",
    "build_signals",
    "cost_line_proxy",
    "load_tushare_daily_clean",
    "niu_men_lines",
    "run_backtest",
    "run_buy_and_hold",
    "simple_atr",
    "true_range",
]
