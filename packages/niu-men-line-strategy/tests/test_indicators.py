import math

import pandas as pd
import pytest

from niu_men_line_strategy.indicators import (
    cost_line_proxy,
    niu_men_lines,
    simple_atr,
    true_range,
)


def _sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [9.0, 10.0, 10.5, 12.5],
            "high": [10.0, 12.0, 11.0, 14.0],
            "low": [8.0, 9.0, 10.0, 12.0],
            "close": [9.0, 11.0, 10.0, 13.0],
            "volume": [100.0, 200.0, 100.0, 300.0],
            "amount": [900.0, 2200.0, 1000.0, 3900.0],
        }
    )


def test_true_range_matches_transcribed_formula() -> None:
    tr = true_range(_sample())
    assert tr.tolist() == [2.0, 3.0, 1.0, 4.0]


def test_atr_is_simple_moving_average_not_wilder() -> None:
    atr = simple_atr(_sample(), period=2)
    assert math.isnan(atr.iloc[0])
    assert atr.iloc[1:].tolist() == [2.5, 2.0, 2.5]


def test_niu_men_lines_use_previous_window_high() -> None:
    lines = niu_men_lines(
        _sample(),
        high_lookback=2,
        atr_period=2,
        smx_period=2,
    )
    assert math.isnan(lines.loc[1, "previous_high"])
    assert lines.loc[2, "previous_high"] == 12.0
    assert lines.loc[2, "nml"] == 13.0
    assert lines.loc[2, "qrl"] == 14.0
    assert lines.loc[3, "nml"] == 13.25
    assert lines.loc[3, "qrl"] == 14.5


def test_preopen_variant_lags_only_atr_component() -> None:
    lines = niu_men_lines(
        _sample(),
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        atr_lag=1,
    )
    assert lines.loc[2, "previous_high"] == 12.0
    assert lines.loc[2, "nml"] == 13.25  # 12 + 0.5 * ATR_1(2.5)


def test_stock_cost_proxy_uses_explicit_amount_scale() -> None:
    data = _sample()
    proxy = cost_line_proxy(
        data,
        window=2,
        asset_class="stock",
        amount_scale=0.01,
    )
    expected = (900.0 + 2200.0) / (100.0 + 200.0) * 0.01
    assert proxy.iloc[1] == expected


def test_stock_cost_proxy_refuses_to_guess_without_amount() -> None:
    data = _sample().drop(columns=["amount"])
    with pytest.raises(ValueError, match="amount"):
        cost_line_proxy(data, window=2, asset_class="stock")


def test_index_cost_proxy_uses_close_volume_proxy() -> None:
    data = _sample()
    proxy = cost_line_proxy(data, window=2, asset_class="index")
    expected = (9.0 * 100.0 + 11.0 * 200.0) / 300.0
    assert proxy.iloc[1] == expected
