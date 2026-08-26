import json

import pandas as pd
import pytest

from niu_men_line_strategy.backtest import BacktestConfig
from niu_men_line_strategy.experiments import (
    experiment_metrics_table,
    main,
    run_standard_experiments,
)


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


def test_standard_experiments_use_explicit_backtest_config() -> None:
    config = BacktestConfig(initial_cash=123_000.0)

    results = run_standard_experiments(_sample(), config, simple_trend_lookback=5)

    assert results["nml_baseline"].metrics["final_equity"] == 123_000.0
    assert results["buy_and_hold"].trades[0].entry_price == 99.8


def test_experiment_metrics_table_preserves_result_order_and_metrics() -> None:
    results = run_standard_experiments(_sample(), simple_trend_lookback=5)

    table = experiment_metrics_table(results)

    assert table.index.tolist() == list(results)
    assert table.columns.tolist() == list(results["nml_baseline"].metrics)
    assert table.loc["buy_and_hold", "trade_count"] == 1.0


def test_experiments_main_loads_data_and_writes_serialized_report(
    tmp_path, monkeypatch, capsys
) -> None:
    root = tmp_path / "daily-clean"
    data_dir = root / "data"
    data_dir.mkdir(parents=True)
    close = pd.Series([100.0 + i for i in range(80)])
    pd.DataFrame(
        {
            "trade_date": pd.date_range("2024-01-01", periods=len(close), freq="D")
            .strftime("%Y%m%d")
            .tolist(),
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "adj_open": close - 0.1,
            "adj_high": close + 0.6,
            "adj_low": close - 0.6,
            "adj_close": close + 0.1,
            "vol": 1_000.0,
            "amount": 100_000.0,
        }
    ).to_parquet(data_dir / "600519.SH.parquet", index=False)
    json_path = tmp_path / "experiments.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "niu-men-experiments",
            "600519.SH",
            "--daily-clean-root",
            str(root),
            "--unadjusted",
            "--initial-cash",
            "200000",
            "--commission-bps",
            "2",
            "--slippage-bps",
            "3",
            "--lot-size",
            "10",
            "--atr-lag",
            "1",
            "--simple-trend-lookback",
            "5",
            "--json-out",
            str(json_path),
        ],
    )

    main()

    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload == saved
    assert payload["symbol"] == "600519.SH"
    assert payload["adjusted_ohlc"] is False
    assert payload["atr_lag"] == 1
    assert payload["simple_trend_lookback"] == 5
    assert payload["bars"] == 80
    assert payload["backtest_config"]["lot_size"] == 10.0
