import pandas as pd

from niu_men_line_strategy.context import (
    attach_industry_asof,
    attach_point_in_time_eligibility,
)


def test_pit_snapshot_becomes_eligible_on_following_bar() -> None:
    data = pd.DataFrame(index=pd.date_range("2024-01-31", periods=3, freq="D"))
    universe = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-31"]),
            "symbol": ["000001.SZ"],
            "selected": [1],
            "liq_metric": [1.0],
        }
    )
    result = attach_point_in_time_eligibility(
        data, symbol="000001.SZ", universe=universe
    )
    assert result["pit_eligible"].tolist() == [False, True, True]


def test_industry_mapping_respects_end_date() -> None:
    data = pd.DataFrame(index=pd.date_range("2024-01-01", periods=3, freq="D"))
    changes = pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "effective_date": pd.to_datetime(["2024-01-01"]),
            "end_date": pd.to_datetime(["2024-01-02"]),
            "industry_code": ["801010.SI"],
            "industry_name": ["农林牧渔"],
        }
    )
    result = attach_industry_asof(data, symbol="000001.SZ", industry_changes=changes)
    assert result["industry_code"].iloc[:2].tolist() == ["801010.SI", "801010.SI"]
    assert pd.isna(result["industry_code"].iloc[2])
