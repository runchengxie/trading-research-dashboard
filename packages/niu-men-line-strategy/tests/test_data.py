import pandas as pd
import pytest

from niu_men_line_strategy.data import load_tushare_daily_clean


def test_daily_clean_loader_maps_adjusted_ohlcv_and_filters_suspension(
    tmp_path,
) -> None:
    root = tmp_path / "daily_clean"
    data_dir = root / "data"
    data_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "trade_date": [20240103, 20240102, 20240104],
            "open": [10.0, 9.0, 11.0],
            "high": [11.0, 10.0, 12.0],
            "low": [9.0, 8.0, 10.0],
            "close": [10.5, 9.5, 11.5],
            "adj_open": [20.0, 18.0, 22.0],
            "adj_high": [22.0, 20.0, 24.0],
            "adj_low": [18.0, 16.0, 20.0],
            "adj_close": [21.0, 19.0, 23.0],
            "vol": [100.0, 200.0, 300.0],
            "amount": [1000.0, 2000.0, 3000.0],
            "is_suspended": [False, False, True],
            "up_limit": [11.0, 10.0, 12.0],
            "down_limit": [9.0, 8.0, 10.0],
        }
    ).to_parquet(data_dir / "000001.SZ.parquet", index=False)
    result = load_tushare_daily_clean(root, "000001.SZ")
    assert result.index.tolist() == list(pd.to_datetime(["2024-01-02", "2024-01-03"]))
    assert result.loc["2024-01-02", "open"] == 18.0
    assert result.loc["2024-01-03", "amount"] == 1000.0
    assert result.loc["2024-01-02", "up_limit"] == 20.0


def _raw_daily_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": [20240102, 20240103],
            "open": [10.0, 11.0],
            "high": [11.0, 12.0],
            "low": [9.0, 10.0],
            "close": [10.5, 11.5],
            "vol": [100.0, 110.0],
            "amount": [1000.0, 1200.0],
        }
    )


def test_daily_clean_loader_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="daily-clean file not found"):
        load_tushare_daily_clean(tmp_path, "000001.SZ")


def test_daily_clean_loader_rejects_missing_required_columns(tmp_path) -> None:
    data_dir = tmp_path / "daily" / "data"
    data_dir.mkdir(parents=True)
    _raw_daily_frame().drop(columns=["amount"]).to_parquet(
        data_dir / "000001.SZ.parquet", index=False
    )

    with pytest.raises(ValueError, match="daily-clean asset missing columns: amount"):
        load_tushare_daily_clean(tmp_path / "daily", "000001.SZ", adjusted=False)


def test_daily_clean_loader_rejects_missing_adjusted_ohlc(tmp_path) -> None:
    data_dir = tmp_path / "daily" / "data"
    data_dir.mkdir(parents=True)
    _raw_daily_frame().to_parquet(data_dir / "000001.SZ.parquet", index=False)

    with pytest.raises(ValueError, match="lacks adjusted OHLC columns"):
        load_tushare_daily_clean(tmp_path / "daily", "000001.SZ")


def test_daily_clean_loader_rejects_insufficient_usable_bars(tmp_path) -> None:
    data_dir = tmp_path / "daily" / "data"
    data_dir.mkdir(parents=True)
    data = _raw_daily_frame()
    data["is_suspended"] = True
    data.to_parquet(data_dir / "000001.SZ.parquet", index=False)

    with pytest.raises(ValueError, match="insufficient usable bars"):
        load_tushare_daily_clean(tmp_path / "daily", "000001.SZ", adjusted=False)


def test_daily_clean_loader_deduplicates_trade_dates_using_last_row(tmp_path) -> None:
    data_dir = tmp_path / "daily" / "data"
    data_dir.mkdir(parents=True)
    first = _raw_daily_frame().iloc[[0]].copy()
    replacement = first.copy()
    replacement["close"] = 12.0
    data = pd.concat([first, replacement, _raw_daily_frame().iloc[[1]]], ignore_index=True)
    data.to_parquet(data_dir / "000001.SZ.parquet", index=False)

    result = load_tushare_daily_clean(tmp_path / "daily", "000001.SZ", adjusted=False)

    assert len(result) == 2
    assert result.loc["2024-01-02", "close"] == 12.0
