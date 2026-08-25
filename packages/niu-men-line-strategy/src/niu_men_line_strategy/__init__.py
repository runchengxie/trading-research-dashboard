"""Research implementation of the Niu Men Line strategy."""

from .backtest import (
    BacktestConfig,
    BacktestResult,
    Trade,
    run_backtest,
    run_buy_and_hold,
)
from .context import (
    attach_industry_asof,
    attach_industry_etf_context,
    attach_market_context,
    attach_point_in_time_eligibility,
    load_industry_changes,
    load_industry_etf_context,
    load_market_context,
    load_point_in_time_universe,
)
from .data import load_tushare_daily_clean
from .indicators import cost_line_proxy, niu_men_lines, simple_atr, true_range
from .industry_mapping import (
    classify_benchmark,
    classify_sw_industry,
    sw_mapping_confidence,
)
from .portfolio import (
    PortfolioResult,
    PortfolioTrade,
    run_equal_weight_buy_and_hold,
    run_portfolio_backtest,
)
from .regimes import simple_return_regime
from .signals import StrategyConfig, build_signals
from .validation import ValidationReport, validate_research_inputs
from .walk_forward import WalkForwardConfig, run_walk_forward, walk_forward_folds

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "PortfolioResult",
    "PortfolioTrade",
    "StrategyConfig",
    "Trade",
    "ValidationReport",
    "WalkForwardConfig",
    "attach_industry_asof",
    "attach_industry_etf_context",
    "attach_market_context",
    "attach_point_in_time_eligibility",
    "build_signals",
    "classify_benchmark",
    "classify_sw_industry",
    "cost_line_proxy",
    "load_industry_changes",
    "load_industry_etf_context",
    "load_market_context",
    "load_point_in_time_universe",
    "load_tushare_daily_clean",
    "niu_men_lines",
    "run_backtest",
    "run_buy_and_hold",
    "run_equal_weight_buy_and_hold",
    "run_portfolio_backtest",
    "run_walk_forward",
    "simple_atr",
    "simple_return_regime",
    "sw_mapping_confidence",
    "true_range",
    "validate_research_inputs",
    "walk_forward_folds",
]
