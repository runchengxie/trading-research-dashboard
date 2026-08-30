from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from trading_research.scripts.build_contextual_history import build_history


def _stock() -> dict:
    start = date(2026, 7, 20)
    daily = []
    for offset in range(30):
        current = start + timedelta(days=offset)
        daily.append(
            {
                "date": current.isoformat(),
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "close": 10.0 + offset * 0.01,
                "volume": 1000,
            }
        )
    return {
        "code": "sz300246",
        "name": "宝莱特",
        "market": "CN",
        "timezone": "Asia/Shanghai",
        "lastTradeDay": "2026-08-28",
        "daily": daily,
        "indicators": {"atr20": 0.5},
        "levels": [],
    }


def test_build_history_reconstructs_point_in_time_intraday_dates() -> None:
    def fetcher(_code: str, data_date: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "time": ["09:30:00", "09:31:00", "09:32:00", "09:33:00", "09:34:00", "09:35:00"],
                "price": [10.0, 10.1, 10.2, 10.15, 10.05, 10.0],
                "volume": [100, 100, 100, 100, 100, 100],
            }
        )

    snapshots = build_history(
        {"stocks": [_stock()]}, sessions=2, codes=["sz300246"], fetch_intraday=fetcher
    )

    assert [snapshot["dataDate"] for snapshot in snapshots] == ["2026-08-17", "2026-08-18"]
    assert all(snapshot["contexts"][0]["dataDate"] == snapshot["dataDate"] for snapshot in snapshots)
    assert all(
        row["time"].startswith(snapshot["dataDate"])
        for snapshot in snapshots
        for row in snapshot["setupEvents"]
    )
