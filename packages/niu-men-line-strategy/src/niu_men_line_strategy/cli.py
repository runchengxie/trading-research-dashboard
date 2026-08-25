from __future__ import annotations

import argparse
import json
from dataclasses import asdict

import pandas as pd

from .backtest import BacktestConfig, run_backtest
from .signals import StrategyConfig, build_signals


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Niu Men Line research baseline on an OHLCV CSV."
    )
    parser.add_argument("csv", help="CSV with date, open, high, low, close, volume columns")
    parser.add_argument("--date-column", default="date")
    parser.add_argument("--initial-cash", type=float, default=1_000_000.0)
    parser.add_argument("--commission-bps", type=float, default=0.0)
    parser.add_argument("--slippage-bps", type=float, default=0.0)
    parser.add_argument("--lot-size", type=float, default=1.0)
    parser.add_argument("--disable-price-volume-filters", action="store_true")
    parser.add_argument("--json-out", help="Optional path for a JSON summary")
    return parser


def main() -> None:
    args = _parser().parse_args()
    data = pd.read_csv(args.csv)
    if args.date_column in data.columns:
        data[args.date_column] = pd.to_datetime(data[args.date_column])
        data = data.set_index(args.date_column)

    strategy = StrategyConfig(
        enable_red_three_soldiers=not args.disable_price_volume_filters,
        enable_long_upper_shadow=not args.disable_price_volume_filters,
    )
    signals = build_signals(data, strategy)
    backtest_config = BacktestConfig(
        initial_cash=args.initial_cash,
        commission_bps=args.commission_bps,
        slippage_bps=args.slippage_bps,
        lot_size=args.lot_size,
    )
    result = run_backtest(signals, backtest_config)

    payload = {
        "strategy_config": asdict(strategy),
        "backtest_config": asdict(backtest_config),
        "metrics": result.metrics,
        "trades": [asdict(trade) for trade in result.trades],
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    print(rendered)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")


if __name__ == "__main__":
    main()
