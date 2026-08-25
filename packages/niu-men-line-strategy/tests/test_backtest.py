import math

import pandas as pd

from niu_men_line_strategy.backtest import (
    BacktestConfig,
    run_backtest,
    run_buy_and_hold,
)


def _manual_signals(
    *,
    opens: list[float],
    highs: list[float],
    lows: list[float],
    closes: list[float],
    entries: list[bool],
    exits: list[bool],
    atr: float = 2.0,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "atr": [atr] * len(opens),
            "entry_signal": entries,
            "exit_signal": exits,
        },
        index=pd.date_range("2026-01-01", periods=len(opens), freq="D"),
    )


def test_close_signal_executes_at_next_open() -> None:
    signals = _manual_signals(
        opens=[100.0, 101.0, 110.0, 120.0],
        highs=[101.0, 103.0, 114.0, 121.0],
        lows=[99.0, 100.0, 109.0, 119.0],
        closes=[100.0, 102.0, 112.0, 120.0],
        entries=[False, True, False, False],
        exits=[False, False, True, False],
    )
    result = run_backtest(
        signals,
        BacktestConfig(initial_cash=100_000.0, lot_size=1.0),
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_time == signals.index[2]
    assert trade.entry_price == 110.0
    assert trade.exit_time == signals.index[3]
    assert trade.exit_price == 120.0
    assert trade.exit_reason == "smx_exit"
    # 15% weight cap is tighter than the 1% / 2ATR risk budget here.
    assert trade.units == 136.0


def test_gap_through_stop_fills_at_worse_open() -> None:
    signals = _manual_signals(
        opens=[100.0, 100.0, 90.0],
        highs=[101.0, 103.0, 92.0],
        lows=[99.0, 97.0, 89.0],
        closes=[100.0, 102.0, 91.0],
        entries=[True, False, False],
        exits=[False, False, False],
    )
    result = run_backtest(
        signals,
        BacktestConfig(initial_cash=100_000.0, lot_size=1.0),
    )

    trade = result.trades[0]
    assert trade.entry_price == 100.0
    assert trade.exit_reason == "protective_stop"
    assert trade.exit_price == 90.0  # stop was 96, but the market gapped below it
    assert trade.pnl < 0


def test_risk_budget_can_be_tighter_than_position_cap() -> None:
    signals = _manual_signals(
        opens=[100.0, 100.0, 110.0],
        highs=[101.0, 101.0, 111.0],
        lows=[99.0, 99.0, 109.0],
        closes=[100.0, 100.0, 110.0],
        entries=[True, False, False],
        exits=[False, False, False],
        atr=10.0,
    )
    result = run_backtest(
        signals,
        BacktestConfig(initial_cash=100_000.0, lot_size=1.0),
    )

    trade = result.trades[0]
    # 1% risk budget / (2 * ATR=20) = 50 units, below 15% weight cap (150).
    assert trade.units == 50.0


def test_transaction_costs_are_reflected_in_pnl_and_equity() -> None:
    signals = _manual_signals(
        opens=[100.0, 100.0, 110.0],
        highs=[101.0, 105.0, 111.0],
        lows=[99.0, 99.0, 109.0],
        closes=[100.0, 105.0, 110.0],
        entries=[True, False, False],
        exits=[False, True, False],
    )
    result = run_backtest(
        signals,
        BacktestConfig(
            initial_cash=100_000.0,
            commission_bps=10.0,
            slippage_bps=0.0,
            lot_size=1.0,
        ),
    )

    trade = result.trades[0]
    gross = (110.0 - 100.0) * trade.units
    assert trade.pnl < gross
    assert math.isclose(
        result.metrics["final_equity"],
        100_000.0 + trade.pnl,
        rel_tol=1e-12,
    )
    assert result.metrics["max_drawdown"] <= 0.0


def test_buy_and_hold_invests_full_cash_and_applies_costs() -> None:
    data = pd.DataFrame(
        {"open": [100.0, 105.0, 110.0], "close": [101.0, 108.0, 110.0]},
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )
    result = run_buy_and_hold(
        data, BacktestConfig(initial_cash=10_000.0, commission_bps=10.0, lot_size=1.0)
    )
    assert result.trades[0].units == 99.0
    assert result.trades[0].entry_price == 100.0
    assert result.metrics["final_equity"] < 10_000.0 + 99.0 * 10.0


def test_entry_at_upper_limit_is_cancelled() -> None:
    signals = _manual_signals(
        opens=[100.0, 110.0, 110.0],
        highs=[101.0, 110.0, 111.0],
        lows=[99.0, 110.0, 109.0],
        closes=[100.0, 110.0, 110.0],
        entries=[True, False, False],
        exits=[False, False, False],
    )
    signals["up_limit"] = [float("nan"), 110.0, 121.0]
    result = run_backtest(signals, BacktestConfig(initial_cash=100_000.0))
    assert not result.trades
    assert result.metrics["blocked_entry_count"] == 1.0
