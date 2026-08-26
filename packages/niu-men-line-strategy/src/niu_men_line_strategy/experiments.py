from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .backtest import BacktestConfig, BacktestResult, run_backtest, run_buy_and_hold
from .data import load_tushare_daily_clean
from .regimes import simple_return_regime
from .signals import StrategyConfig, build_signals


def run_standard_experiments(
    data: pd.DataFrame,
    backtest_config: BacktestConfig | None = None,
    *,
    atr_lag: int = 0,
    simple_trend_lookback: int = 63,
) -> dict[str, BacktestResult]:
    """Run preregistered single-asset baseline comparisons on identical bars."""

    if simple_trend_lookback <= 0:
        raise ValueError("simple_trend_lookback must be positive")

    backtest_config = backtest_config or BacktestConfig()
    variants = {
        "nml_baseline": StrategyConfig(atr_lag=atr_lag),
        "nml_no_price_volume_filters": StrategyConfig(
            atr_lag=atr_lag,
            enable_red_three_soldiers=False,
            enable_long_upper_shadow=False,
        ),
        "simple_20_day_breakout": StrategyConfig(
            nml_atr_multiple=0.0,
            atr_lag=atr_lag,
            reset_bars=1,
            enable_red_three_soldiers=False,
            enable_long_upper_shadow=False,
        ),
    }
    results = {
        name: run_backtest(build_signals(data, config), backtest_config)
        for name, config in variants.items()
    }

    trend_data = data.copy()
    trend_data["price_regime"] = simple_return_regime(data, lookback=simple_trend_lookback)
    results["nml_simple_trend_gate"] = run_backtest(
        build_signals(
            trend_data,
            StrategyConfig(
                atr_lag=atr_lag,
                enable_price_regime_gate=True,
            ),
        ),
        backtest_config,
    )
    results["buy_and_hold"] = run_buy_and_hold(data, backtest_config)
    return results


def experiment_metrics_table(results: dict[str, BacktestResult]) -> pd.DataFrame:
    """Return a consistently ordered performance table for serialisation/reporting."""
    return pd.DataFrame({name: result.metrics for name, result in results.items()}).T


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Niu Men Line baseline comparisons on a daily-clean symbol."
    )
    parser.add_argument("symbol", help="TuShare symbol, e.g. 600519.SH")
    parser.add_argument(
        "--daily-clean-root",
        required=True,
        help="Path to a_share_all_daily_clean_latest (or a versioned equivalent)",
    )
    parser.add_argument("--unadjusted", action="store_true")
    parser.add_argument("--initial-cash", type=float, default=1_000_000.0)
    parser.add_argument("--commission-bps", type=float, default=5.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--lot-size", type=float, default=100.0)
    parser.add_argument("--atr-lag", type=int, default=0)
    parser.add_argument(
        "--simple-trend-lookback",
        type=int,
        default=63,
        help="Trailing close-return lookback used by the simple price-regime comparator.",
    )
    parser.add_argument("--json-out", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    data = load_tushare_daily_clean(
        args.daily_clean_root, args.symbol, adjusted=not args.unadjusted
    )
    config = BacktestConfig(
        initial_cash=args.initial_cash,
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        lot_size=args.lot_size,
    )
    results = run_standard_experiments(
        data,
        config,
        atr_lag=args.atr_lag,
        simple_trend_lookback=args.simple_trend_lookback,
    )
    table = experiment_metrics_table(results)
    payload = {
        "symbol": args.symbol,
        "adjusted_ohlc": not args.unadjusted,
        "atr_lag": args.atr_lag,
        "simple_trend_lookback": args.simple_trend_lookback,
        "bars": len(data),
        "start": str(data.index[0].date()),
        "end": str(data.index[-1].date()),
        "backtest_config": asdict(config),
        "metrics": table.to_dict(orient="index"),
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=True)
    print(rendered)
    if args.json_out:
        args.json_out.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
