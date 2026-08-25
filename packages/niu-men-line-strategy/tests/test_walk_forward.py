import pandas as pd

from niu_men_line_strategy.walk_forward import WalkForwardConfig, walk_forward_folds


def test_walk_forward_folds_are_rolling_and_disjoint() -> None:
    dates = pd.date_range("2020-01-01", periods=12, freq="D")
    folds = walk_forward_folds(dates, WalkForwardConfig(train_bars=4, test_bars=3, step_bars=3))
    assert [
        (fold.train_start, fold.train_end, fold.test_start, fold.test_end) for fold in folds
    ] == [
        (dates[0], dates[3], dates[4], dates[6]),
        (dates[3], dates[6], dates[7], dates[9]),
    ]
