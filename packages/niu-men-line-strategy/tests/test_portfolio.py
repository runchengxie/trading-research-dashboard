import pandas as pd

from niu_men_line_strategy.backtest import BacktestConfig
from niu_men_line_strategy.portfolio import (
    run_equal_weight_buy_and_hold,
    run_portfolio_backtest,
)


def _frame(entries: list[bool], exits: list[bool]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0],
            "high": [101.0, 102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0, 102.0],
            "close": [100.0, 101.0, 102.0, 103.0],
            "atr": [2.0] * 4,
            "entry_signal": entries,
            "exit_signal": exits,
        },
        index=pd.date_range("2026-01-01", periods=4, freq="D"),
    )


def test_portfolio_uses_shared_cash_and_next_open_execution() -> None:
    frames = {
        "A": _frame([True, False, False, False], [False, False, True, False]),
        "B": _frame([False, True, False, False], [False, False, False, False]),
    }
    result = run_portfolio_backtest(
        frames,
        BacktestConfig(initial_cash=100_000.0, lot_size=1.0),
    )

    assert {trade.symbol for trade in result.trades} == {"A", "B"}
    assert result.trades[0].entry_time == pd.Timestamp("2026-01-02")
    assert result.metrics["position_count_max"] <= 2.0
    assert result.metrics["turnover"] > 0.0


def test_portfolio_blocks_limit_up_entry() -> None:
    frame = _frame([True, False, False, False], [False, False, False, False])
    frame["up_limit"] = [float("nan"), 101.0, float("nan"), float("nan")]

    result = run_portfolio_backtest(
        {"A": frame},
        BacktestConfig(initial_cash=100_000.0, lot_size=1.0),
    )

    assert not result.trades
    assert result.metrics["blocked_entry_count"] == 1.0


def test_equal_weight_buy_and_hold_has_one_trade_per_entry() -> None:
    result = run_equal_weight_buy_and_hold(
        {"A": _frame([False] * 4, [False] * 4)},
        BacktestConfig(initial_cash=100_000.0, lot_size=1.0),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "end_of_data"
    assert result.metrics["trade_count"] == 1.0
    assert result.equity_curve.iloc[0]["position_count"] == 1.0
    assert result.equity_curve.iloc[-1]["equity"] > result.equity_curve.iloc[0]["equity"]
