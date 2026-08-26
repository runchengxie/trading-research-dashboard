from __future__ import annotations

import importlib.util
import json

import pandas as pd
import pytest

from niu_men_line_strategy.portfolio_adapter import (
    build_portfolio_replay_inputs,
)


def _signals() -> pd.DataFrame:
    index = pd.to_datetime(
        [
            "2026-01-02",
            "2026-01-05",
            "2026-01-06",
            "2026-01-07",
            "2026-01-08",
            "2026-01-09",
            "2026-01-12",
        ]
    )
    return pd.DataFrame(
        {
            "open": [10.0, 10.5, 11.0, 10.8, 11.2, 11.5, 11.8],
            "high": [10.2, 10.7, 11.2, 11.0, 11.4, 11.7, 12.0],
            "low": [9.8, 10.3, 10.8, 10.6, 11.0, 11.3, 11.6],
            "close": [10.1, 10.6, 11.1, 10.9, 11.3, 11.6, 11.9],
            "atr": [0.5] * len(index),
            "entry_signal": [True, False, False, False, True, False, False],
            "exit_signal": [False, False, True, False, False, False, False],
            "tradable": [True] * len(index),
            "up_limit": [11.0] * len(index),
            "down_limit": [9.0] * len(index),
        },
        index=index,
    )


def test_build_portfolio_replay_inputs_preserves_signal_timing_and_final_liquidation() -> None:
    inputs = build_portfolio_replay_inputs(_signals(), "600000.SH", weight=0.4)

    assert list(inputs.positions.columns) == [
        "rebalance_date",
        "entry_date",
        "symbol",
        "weight",
        "side",
        "signal",
    ]
    assert inputs.positions.to_dict(orient="records") == [
        {
            "rebalance_date": pd.Timestamp("2026-01-02"),
            "entry_date": pd.Timestamp("2026-01-05"),
            "symbol": "600000.SH",
            "weight": 0.4,
            "side": "long",
            "signal": "entry_signal",
        },
        {
            "rebalance_date": pd.Timestamp("2026-01-08"),
            "entry_date": pd.Timestamp("2026-01-09"),
            "symbol": "600000.SH",
            "weight": 0.4,
            "side": "long",
            "signal": "entry_signal",
        },
    ]
    assert inputs.periods.to_dict(orient="records") == [
        {
            "rebalance_date": pd.Timestamp("2026-01-02"),
            "entry_date": pd.Timestamp("2026-01-05"),
            "exit_date": pd.Timestamp("2026-01-07"),
            "planned_exit_date": pd.Timestamp("2026-01-07"),
            "entry_signal_date": pd.Timestamp("2026-01-02"),
            "exit_signal_date": pd.Timestamp("2026-01-06"),
            "exit_reason": "exit_signal",
        },
        {
            "rebalance_date": pd.Timestamp("2026-01-08"),
            "entry_date": pd.Timestamp("2026-01-09"),
            "exit_date": pd.Timestamp("2026-01-12"),
            "planned_exit_date": pd.Timestamp("2026-01-12"),
            "entry_signal_date": pd.Timestamp("2026-01-08"),
            "exit_signal_date": pd.NaT,
            "exit_reason": "end_of_data",
        },
    ]

    assert inputs.pricing[["trade_date", "symbol", "close", "entry_price", "exit_price"]].to_dict(
        orient="records"
    ) == [
        {
            "trade_date": pd.Timestamp("2026-01-02"),
            "symbol": "600000.SH",
            "close": 10.1,
            "entry_price": 10.0,
            "exit_price": 10.0,
        },
        {
            "trade_date": pd.Timestamp("2026-01-05"),
            "symbol": "600000.SH",
            "close": 10.6,
            "entry_price": 10.5,
            "exit_price": 10.5,
        },
        {
            "trade_date": pd.Timestamp("2026-01-06"),
            "symbol": "600000.SH",
            "close": 11.1,
            "entry_price": 11.0,
            "exit_price": 11.0,
        },
        {
            "trade_date": pd.Timestamp("2026-01-07"),
            "symbol": "600000.SH",
            "close": 10.9,
            "entry_price": 10.8,
            "exit_price": 10.8,
        },
        {
            "trade_date": pd.Timestamp("2026-01-08"),
            "symbol": "600000.SH",
            "close": 11.3,
            "entry_price": 11.2,
            "exit_price": 11.2,
        },
        {
            "trade_date": pd.Timestamp("2026-01-09"),
            "symbol": "600000.SH",
            "close": 11.6,
            "entry_price": 11.5,
            "exit_price": 11.5,
        },
        {
            "trade_date": pd.Timestamp("2026-01-12"),
            "symbol": "600000.SH",
            "close": 11.9,
            "entry_price": 11.8,
            "exit_price": 11.9,
        },
    ]
    assert inputs.pricing["tradable"].tolist() == [True] * 7
    assert inputs.pricing["up_limit"].tolist() == [11.0] * 7
    assert inputs.pricing["down_limit"].tolist() == [9.0] * 7


def test_portfolio_replay_payload_is_stable_and_json_serializable() -> None:
    inputs = build_portfolio_replay_inputs(_signals(), "600000.SH")

    payload = inputs.to_payload()

    assert json.dumps(payload, sort_keys=True) == json.dumps(
        {
            "periods": [
                {
                    "entry_date": "2026-01-05",
                    "entry_signal_date": "2026-01-02",
                    "exit_date": "2026-01-07",
                    "exit_reason": "exit_signal",
                    "exit_signal_date": "2026-01-06",
                    "planned_exit_date": "2026-01-07",
                    "rebalance_date": "2026-01-02",
                },
                {
                    "entry_date": "2026-01-09",
                    "entry_signal_date": "2026-01-08",
                    "exit_date": "2026-01-12",
                    "exit_reason": "end_of_data",
                    "exit_signal_date": None,
                    "planned_exit_date": "2026-01-12",
                    "rebalance_date": "2026-01-08",
                },
            ],
            "positions": [
                {
                    "entry_date": "2026-01-05",
                    "rebalance_date": "2026-01-02",
                    "side": "long",
                    "signal": "entry_signal",
                    "symbol": "600000.SH",
                    "weight": 1.0,
                },
                {
                    "entry_date": "2026-01-09",
                    "rebalance_date": "2026-01-08",
                    "side": "long",
                    "signal": "entry_signal",
                    "symbol": "600000.SH",
                    "weight": 1.0,
                },
            ],
            "pricing": [
                {
                    "close": 10.1,
                    "down_limit": 9.0,
                    "entry_price": 10.0,
                    "exit_price": 10.0,
                    "symbol": "600000.SH",
                    "trade_date": "2026-01-02",
                    "tradable": True,
                    "up_limit": 11.0,
                },
                {
                    "close": 10.6,
                    "down_limit": 9.0,
                    "entry_price": 10.5,
                    "exit_price": 10.5,
                    "symbol": "600000.SH",
                    "trade_date": "2026-01-05",
                    "tradable": True,
                    "up_limit": 11.0,
                },
                {
                    "close": 11.1,
                    "down_limit": 9.0,
                    "entry_price": 11.0,
                    "exit_price": 11.0,
                    "symbol": "600000.SH",
                    "trade_date": "2026-01-06",
                    "tradable": True,
                    "up_limit": 11.0,
                },
                {
                    "close": 10.9,
                    "down_limit": 9.0,
                    "entry_price": 10.8,
                    "exit_price": 10.8,
                    "symbol": "600000.SH",
                    "trade_date": "2026-01-07",
                    "tradable": True,
                    "up_limit": 11.0,
                },
                {
                    "close": 11.3,
                    "down_limit": 9.0,
                    "entry_price": 11.2,
                    "exit_price": 11.2,
                    "symbol": "600000.SH",
                    "trade_date": "2026-01-08",
                    "tradable": True,
                    "up_limit": 11.0,
                },
                {
                    "close": 11.6,
                    "down_limit": 9.0,
                    "entry_price": 11.5,
                    "exit_price": 11.5,
                    "symbol": "600000.SH",
                    "trade_date": "2026-01-09",
                    "tradable": True,
                    "up_limit": 11.0,
                },
                {
                    "close": 11.9,
                    "down_limit": 9.0,
                    "entry_price": 11.8,
                    "exit_price": 11.9,
                    "symbol": "600000.SH",
                    "trade_date": "2026-01-12",
                    "tradable": True,
                    "up_limit": 11.0,
                },
            ],
        },
        sort_keys=True,
    )


def test_portfolio_replay_adapter_rejects_invalid_inputs() -> None:
    signals = _signals()

    with pytest.raises(ValueError, match="missing required columns: entry_signal"):
        build_portfolio_replay_inputs(signals.drop(columns="entry_signal"), "600000.SH")
    with pytest.raises(ValueError, match="symbol must not be empty"):
        build_portfolio_replay_inputs(signals, " ")
    with pytest.raises(ValueError, match="weight must be finite and positive"):
        build_portfolio_replay_inputs(signals, "600000.SH", weight=0.0)
    with pytest.raises(ValueError, match="index must be unique and monotonic"):
        build_portfolio_replay_inputs(signals.iloc[::-1], "600000.SH")


def test_portfolio_backtester_optional_integration() -> None:
    if importlib.util.find_spec("portfolio_backtester") is None:
        pytest.skip("portfolio-backtester is not installed in this environment")
    import portfolio_backtester

    inputs = build_portfolio_replay_inputs(_signals(), "600000.SH")

    result = portfolio_backtester.run_position_backtest(
        positions=inputs.positions,
        pricing=inputs.pricing,
        periods=inputs.periods,
        config=portfolio_backtester.PositionBacktestConfig(
            price_col="close",
            entry_price_col="entry_price",
            exit_price_col="exit_price",
        ),
    )

    assert result.summary["periods"] == 2
