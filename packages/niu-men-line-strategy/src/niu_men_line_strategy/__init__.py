"""Research implementation of the Niu Men Line strategy."""

from .backtest import BacktestConfig, BacktestResult, Trade, run_backtest
from .indicators import cost_line_proxy, niu_men_lines, simple_atr, true_range
from .signals import StrategyConfig, build_signals

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "StrategyConfig",
    "Trade",
    "build_signals",
    "cost_line_proxy",
    "niu_men_lines",
    "run_backtest",
    "simple_atr",
    "true_range",
]
