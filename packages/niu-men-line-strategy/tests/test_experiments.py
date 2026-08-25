import pandas as pd
import pytest

from niu_men_line_strategy.experiments import run_standard_experiments


def _sample() -> pd.DataFrame:
    close = pd.Series([100.0 + i for i in range(80)])
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000.0,
        }
    )


def test_standard_experiments_include_simple_trend_gate_comparator() -> None:
    results = run_standard_experiments(_sample(), simple_trend_lookback=5)

    assert list(results) == [
        "nml_baseline",
        "nml_no_price_volume_filters",
        "simple_20_day_breakout",
        "nml_simple_trend_gate",
        "buy_and_hold",
    ]


def test_standard_experiments_reject_non_positive_trend_lookback() -> None:
    with pytest.raises(ValueError, match="simple_trend_lookback must be positive"):
        run_standard_experiments(_sample(), simple_trend_lookback=0)
