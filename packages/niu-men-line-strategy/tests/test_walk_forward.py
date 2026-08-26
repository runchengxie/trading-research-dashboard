import pandas as pd
import pytest

from niu_men_line_strategy.signals import StrategyConfig
from niu_men_line_strategy.walk_forward import (
    WalkForwardConfig,
    run_walk_forward,
    walk_forward_folds,
)


def test_walk_forward_folds_are_rolling_and_disjoint() -> None:
    dates = pd.date_range("2020-01-01", periods=12, freq="D")
    folds = walk_forward_folds(dates, WalkForwardConfig(train_bars=4, test_bars=3, step_bars=3))
    assert [
        (fold.train_start, fold.train_end, fold.test_start, fold.test_end) for fold in folds
    ] == [
        (dates[0], dates[3], dates[4], dates[6]),
        (dates[3], dates[6], dates[7], dates[9]),
    ]


def test_walk_forward_folds_reject_non_positive_windows() -> None:
    dates = pd.date_range("2020-01-01", periods=5, freq="D")

    with pytest.raises(ValueError, match="bar counts must be positive"):
        walk_forward_folds(dates, WalkForwardConfig(train_bars=0, test_bars=2, step_bars=1))


def test_walk_forward_folds_reject_unsorted_or_duplicate_dates() -> None:
    with pytest.raises(ValueError, match="unique and ascending"):
        walk_forward_folds(
            pd.to_datetime(["2020-01-02", "2020-01-01"]),
            WalkForwardConfig(train_bars=1, test_bars=1, step_bars=1),
        )

    with pytest.raises(ValueError, match="unique and ascending"):
        walk_forward_folds(
            pd.to_datetime(["2020-01-01", "2020-01-01"]),
            WalkForwardConfig(train_bars=1, test_bars=1, step_bars=1),
        )


def test_walk_forward_folds_return_empty_when_no_complete_test_window() -> None:
    dates = pd.date_range("2020-01-01", periods=5, freq="D")

    assert (
        walk_forward_folds(dates, WalkForwardConfig(train_bars=4, test_bars=2, step_bars=1)) == ()
    )


def test_run_walk_forward_returns_one_backtest_per_oos_fold() -> None:
    close = pd.Series([100.0 + i for i in range(12)])
    data = pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000.0,
        },
        index=pd.date_range("2020-01-01", periods=12, freq="D"),
    )
    strategy = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        reset_bars=1,
        enable_red_three_soldiers=False,
        enable_long_upper_shadow=False,
    )
    walk_forward = WalkForwardConfig(train_bars=4, test_bars=3, step_bars=3)

    result = run_walk_forward(
        data,
        strategy_config=strategy,
        walk_forward_config=walk_forward,
    )

    assert len(result.folds) == 2
    assert len(result.results) == 2
    assert result.results[0].equity_curve.index.tolist() == data.index[4:7].tolist()
    assert result.results[1].equity_curve.index.tolist() == data.index[7:10].tolist()


def test_run_walk_forward_requires_datetime_index() -> None:
    with pytest.raises(TypeError, match="DatetimeIndex"):
        run_walk_forward(pd.DataFrame({"close": [1.0]}))
