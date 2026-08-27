from pathlib import Path

import pandas as pd

from trading_research.strategies import rbreaker_data


def test_load_or_download_data_reads_normalized_local_csv(tmp_path: Path) -> None:
    path = tmp_path / "300246_20260810_20260810.csv"
    pd.DataFrame(
        {
            "时间": ["2026-08-10 09:30:00"],
            "开盘": [10.0],
            "最高": [10.2],
            "最低": [9.9],
            "收盘": [10.1],
            "成交量": [1000],
        }
    ).to_csv(path, index=False, encoding="utf-8-sig")

    result = rbreaker_data.load_or_download_data(
        "300246", "20260810", "20260810", tmp_path
    )

    assert list(result["时间"]) == [pd.Timestamp("2026-08-10 09:30:00")]


def test_load_or_download_data_returns_empty_frame_for_malformed_csv(tmp_path: Path) -> None:
    path = tmp_path / "300246_20260810_20260810.csv"
    path.write_text("unexpected\nvalue\n", encoding="utf-8")

    result = rbreaker_data.load_or_download_data(
        "300246", "20260810", "20260810", tmp_path
    )

    assert result.empty
