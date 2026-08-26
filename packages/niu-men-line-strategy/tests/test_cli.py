import json
import sys

import pandas as pd

from niu_men_line_strategy.cli import main


def _write_ohlcv_csv(path, *, date_column: str = "date", rows: int = 25) -> None:
    close = pd.Series([100.0 + i for i in range(rows)])
    pd.DataFrame(
        {
            date_column: pd.date_range("2024-01-01", periods=rows, freq="D"),
            "open": close - 0.2,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000.0,
        }
    ).to_csv(path, index=False)


def test_cli_main_parses_dates_and_writes_json_summary(tmp_path, monkeypatch, capsys) -> None:
    csv_path = tmp_path / "bars.csv"
    json_path = tmp_path / "summary.json"
    _write_ohlcv_csv(csv_path, date_column="session")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "niu-men-backtest",
            str(csv_path),
            "--date-column",
            "session",
            "--initial-cash",
            "250000",
            "--commission-bps",
            "3",
            "--slippage-bps",
            "4",
            "--lot-size",
            "100",
            "--atr-lag",
            "1",
            "--disable-price-volume-filters",
            "--json-out",
            str(json_path),
        ],
    )

    main()

    stdout_payload = json.loads(capsys.readouterr().out)
    file_payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert stdout_payload == file_payload
    assert stdout_payload["strategy_config"]["atr_lag"] == 1
    assert stdout_payload["strategy_config"]["enable_red_three_soldiers"] is False
    assert stdout_payload["strategy_config"]["enable_long_upper_shadow"] is False
    assert stdout_payload["backtest_config"] == {
        "initial_cash": 250000.0,
        "max_position_weight": 0.15,
        "risk_fraction": 0.01,
        "stop_atr_multiple": 2.0,
        "commission_bps": 3.0,
        "slippage_bps": 4.0,
        "lot_size": 100.0,
        "annualization": 252,
    }
    assert stdout_payload["trades"] == []


def test_cli_main_accepts_csv_without_date_column(tmp_path, monkeypatch, capsys) -> None:
    csv_path = tmp_path / "bars.csv"
    pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.0, 101.0],
            "volume": [1_000.0, 1_000.0],
        }
    ).to_csv(csv_path, index=False)
    monkeypatch.setattr(sys, "argv", ["niu-men-backtest", str(csv_path)])

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["strategy_config"]["atr_lag"] == 0
    assert payload["backtest_config"]["initial_cash"] == 1_000_000.0
    assert payload["trades"] == []
