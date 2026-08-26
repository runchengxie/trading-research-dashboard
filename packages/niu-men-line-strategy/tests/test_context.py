import pandas as pd
import pytest

from niu_men_line_strategy.context import (
    attach_industry_asof,
    attach_market_context,
    attach_point_in_time_eligibility,
    load_industry_changes,
    load_market_context,
    load_point_in_time_universe,
)


def test_load_point_in_time_universe_sorts_rows_and_parses_dates(tmp_path) -> None:
    path = tmp_path / "universe.csv"
    pd.DataFrame(
        {
            "trade_date": ["20240201", "20240131"],
            "symbol": ["000002.SZ", "000001.SZ"],
            "liq_metric": [2.0, 1.0],
            "selected": [0, 1],
        }
    ).to_csv(path, index=False)

    result = load_point_in_time_universe(path)

    assert result["trade_date"].tolist() == list(pd.to_datetime(["2024-01-31", "2024-02-01"]))
    assert result["symbol"].tolist() == ["000001.SZ", "000002.SZ"]


def test_load_point_in_time_universe_rejects_missing_columns(tmp_path) -> None:
    path = tmp_path / "universe.csv"
    pd.DataFrame({"trade_date": ["20240131"], "symbol": ["000001.SZ"], "liq_metric": [1.0]}).to_csv(
        path, index=False
    )

    with pytest.raises(ValueError, match="universe is missing columns: selected"):
        load_point_in_time_universe(path)


def test_load_point_in_time_universe_rejects_duplicates_and_invalid_selection(tmp_path) -> None:
    duplicate_path = tmp_path / "duplicate.csv"
    duplicate = pd.DataFrame(
        {
            "trade_date": ["20240131", "20240131"],
            "symbol": ["000001.SZ", "000001.SZ"],
            "liq_metric": [1.0, 2.0],
            "selected": [1, 0],
        }
    )
    duplicate.to_csv(duplicate_path, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        load_point_in_time_universe(duplicate_path)

    invalid_path = tmp_path / "invalid-selection.csv"
    invalid = duplicate.iloc[[0]].copy()
    invalid["selected"] = 2
    invalid.to_csv(invalid_path, index=False)
    with pytest.raises(ValueError, match="selected must contain only 0 or 1"):
        load_point_in_time_universe(invalid_path)


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
    result = attach_point_in_time_eligibility(data, symbol="000001.SZ", universe=universe)
    assert result["pit_eligible"].tolist() == [False, True, True]


def test_pit_eligibility_is_false_without_a_selected_snapshot() -> None:
    data = pd.DataFrame(index=pd.date_range("2024-01-31", periods=2, freq="D"))
    universe = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2024-01-31"]),
            "symbol": ["000001.SZ"],
            "selected": [0],
            "liq_metric": [1.0],
        }
    )

    result = attach_point_in_time_eligibility(data, symbol="000001.SZ", universe=universe)

    assert result["pit_eligible"].tolist() == [False, False]


def test_pit_eligibility_requires_datetime_index() -> None:
    with pytest.raises(TypeError, match="DatetimeIndex"):
        attach_point_in_time_eligibility(
            pd.DataFrame(index=[0]),
            symbol="000001.SZ",
            universe=pd.DataFrame(columns=["trade_date", "symbol", "selected"]),
        )


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


def test_load_industry_changes_sorts_rows_and_parses_open_end_intervals(tmp_path) -> None:
    path = tmp_path / "industry.parquet"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000001.SZ"],
            "effective_date": ["20240201", "20240101"],
            "end_date": [None, "20240131"],
            "industry_code": ["bank", "farm"],
            "industry_name": ["银行", "农林牧渔"],
        }
    ).to_parquet(path, index=False)

    result = load_industry_changes(path)

    assert result["effective_date"].tolist() == list(pd.to_datetime(["2024-01-01", "2024-02-01"]))
    assert pd.isna(result.loc[1, "end_date"])


def test_load_industry_changes_rejects_missing_columns_and_overlaps(tmp_path) -> None:
    missing_path = tmp_path / "missing.parquet"
    pd.DataFrame({"symbol": ["000001.SZ"]}).to_parquet(missing_path, index=False)
    with pytest.raises(ValueError, match="industry changes are missing columns"):
        load_industry_changes(missing_path)

    overlap_path = tmp_path / "overlap.parquet"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000001.SZ"],
            "effective_date": ["20240101", "20240115"],
            "end_date": ["20240131", None],
            "industry_code": ["farm", "bank"],
            "industry_name": ["农林牧渔", "银行"],
        }
    ).to_parquet(overlap_path, index=False)
    with pytest.raises(ValueError, match="overlapping"):
        load_industry_changes(overlap_path)


def test_industry_mapping_requires_datetime_index() -> None:
    with pytest.raises(TypeError, match="DatetimeIndex"):
        attach_industry_asof(
            pd.DataFrame(index=[0]),
            symbol="000001.SZ",
            industry_changes=pd.DataFrame(
                columns=[
                    "symbol",
                    "effective_date",
                    "end_date",
                    "industry_code",
                    "industry_name",
                ]
            ),
        )


def test_load_market_context_filters_index_and_renames_columns(tmp_path) -> None:
    path = tmp_path / "market.parquet"
    pd.DataFrame(
        {
            "ts_code": ["000300.SH", "000905.SH", "000300.SH"],
            "trade_date": ["20240103", "20240102", "20240102"],
            "close": [101.0, 999.0, 100.0],
            "vol": [11.0, 99.0, 10.0],
        }
    ).to_parquet(path, index=False)

    result = load_market_context(path, index_code="000300.SH")

    assert result.index.tolist() == list(pd.to_datetime(["2024-01-02", "2024-01-03"]))
    assert result["market_close"].tolist() == [100.0, 101.0]
    assert result["market_volume"].tolist() == [10.0, 11.0]


def test_load_market_context_rejects_missing_columns_and_absent_index(tmp_path) -> None:
    missing_path = tmp_path / "missing.parquet"
    pd.DataFrame({"ts_code": ["000300.SH"]}).to_parquet(missing_path, index=False)
    with pytest.raises(ValueError, match="market index data is missing columns"):
        load_market_context(missing_path, index_code="000300.SH")

    absent_path = tmp_path / "absent.parquet"
    pd.DataFrame(
        {
            "ts_code": ["000905.SH"],
            "trade_date": ["20240102"],
            "close": [100.0],
            "vol": [10.0],
        }
    ).to_parquet(absent_path, index=False)
    with pytest.raises(ValueError, match=r"000300\.SH is absent"):
        load_market_context(absent_path, index_code="000300.SH")


def test_attach_market_context_left_joins_without_filling_missing_dates() -> None:
    data = pd.DataFrame({"close": [10.0, 11.0]}, index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    market = pd.DataFrame(
        {"market_close": [100.0], "market_volume": [10.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )

    result = attach_market_context(data, market)

    assert result.loc["2024-01-02", "market_close"] == 100.0
    assert pd.isna(result.loc["2024-01-03", "market_close"])
    assert pd.isna(result.loc["2024-01-03", "market_volume"])


def test_attach_market_context_requires_datetime_index() -> None:
    with pytest.raises(TypeError, match="DatetimeIndex"):
        attach_market_context(pd.DataFrame(index=[0]), pd.DataFrame())
