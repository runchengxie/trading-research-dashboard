"""Research implementation of the Niu Men Line strategy."""

from .backtest import (
    BacktestConfig,
    BacktestResult,
    Trade,
    run_backtest,
    run_buy_and_hold,
)
from .data import load_tushare_daily_clean
from .context import (
    attach_industry_asof,
    attach_market_context,
    attach_point_in_time_eligibility,
    load_industry_changes,
    load_market_context,
    load_point_in_time_universe,
)
from .indicators import cost_line_proxy, niu_men_lines, simple_atr, true_range
from .signals import StrategyConfig, build_signals
from .walk_forward import WalkForwardConfig, run_walk_forward, walk_forward_folds

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "StrategyConfig",
    "Trade",
    "build_signals",
    "attach_industry_asof",
    "attach_market_context",
    "attach_point_in_time_eligibility",
    "cost_line_proxy",
    "load_tushare_daily_clean",
    "load_industry_changes",
    "load_market_context",
    "load_point_in_time_universe",
    "niu_men_lines",
    "run_backtest",
    "run_buy_and_hold",
    "simple_atr",
    "true_range",
    "WalkForwardConfig",
    "run_walk_forward",
    "walk_forward_folds",
]
