from __future__ import annotations

import pytest

from trading_research.agent_portfolio import (
    PaperPortfolioState,
    Position,
    simulate_rebalance,
)


def test_first_run_allocates_cash_and_records_buy_trades() -> None:
    state = simulate_rebalance(
        None,
        {"SPY": 0.5, "CASH": 0.5},
        {"SPY": 100.0},
        "2026-09-01",
        100_000.0,
        0.001,
        0.8,
        0.1,
    )
    assert state.equity == pytest.approx(99_950.0)
    assert state.positions["SPY"].market_value == pytest.approx(50_000.0)
    assert state.cash == pytest.approx(49_950.0)
    assert len(state.trades) == 1


def test_rebalance_sells_and_buys_using_current_equity() -> None:
    previous = PaperPortfolioState(
        as_of="2026-09-01",
        initial_equity=100_000.0,
        equity=100_000.0,
        cash=50_000.0,
        positions={"SPY": Position(symbol="SPY", shares=500, price=100.0, market_value=50_000.0)},
        history=(),
        trades=(),
    )
    state = simulate_rebalance(
        previous,
        {"QQQ": 0.4, "CASH": 0.6},
        {"SPY": 110.0, "QQQ": 200.0},
        "2026-09-02",
        100_000.0,
        0.001,
        0.8,
        0.1,
    )
    assert "SPY" not in state.positions
    assert state.positions["QQQ"].market_value > 0


def test_missing_price_rejects_the_rebalance() -> None:
    with pytest.raises(ValueError, match="prices must not be empty"):
        simulate_rebalance(
            None,
            {"SPY": 0.8, "CASH": 0.2},
            {},
            "2026-09-01",
            100_000.0,
            0.0,
            0.8,
            0.1,
        )


def test_zero_share_adjustment_is_not_recorded_as_trade() -> None:
    state = simulate_rebalance(
        None,
        {"SPY": 0.000001, "CASH": 0.999999},
        {"SPY": 100.0},
        "2026-09-01",
        100_000.0,
        0.001,
        0.8,
        0.1,
    )
    assert state.trades == ()
    assert state.positions == {}


def test_rebalance_rejects_duplicate_or_older_dates() -> None:
    previous = PaperPortfolioState(
        as_of="2026-09-01",
        initial_equity=100_000.0,
        equity=100_000.0,
        cash=100_000.0,
        positions={},
        history=(),
        trades=(),
    )
    with pytest.raises(ValueError, match="after previous"):
        simulate_rebalance(
            previous,
            {"CASH": 1.0},
            {"SPY": 100.0},
            "2026-09-01",
            100_000.0,
            0.0,
            0.8,
            0.1,
        )
