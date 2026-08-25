import pandas as pd

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
