import pandas as pd
import pytest

from niu_men_line_strategy.context import (
    attach_industry_etf_context,
    load_industry_etf_context,
)


def _context() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": ["20240102", "20240103"],
            "industry_code": ["bank", "bank"],
            "sector_close": [100.0, 101.0],
            "sector_ma20": [99.0, 100.0],
            "sector_ma60": [98.0, 99.0],
            "sector_strong": [True, True],
        }
    )


def test_load_and_attach_industry_etf_context(tmp_path):
    path = tmp_path / "context.parquet"
    _context().to_parquet(path, index=False)
    context = load_industry_etf_context(path)
    bars = pd.DataFrame({"close": [10.0, 11.0]}, index=pd.to_datetime(["2024-01-02", "2024-01-03"]))
    result = attach_industry_etf_context(bars, industry_code="bank", industry_context=context)
    assert result["sector_close"].tolist() == [100.0, 101.0]
    assert result["industry_regime"].tolist() == [True, True]


def test_context_rejects_duplicate_date_industry(tmp_path):
    path = tmp_path / "context.parquet"
    data = pd.concat([_context(), _context().iloc[[0]]], ignore_index=True)
    data.to_parquet(path, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        load_industry_etf_context(path)


def test_context_preserves_warmup_missing_regime(tmp_path):
    path = tmp_path / "context.parquet"
    data = _context()
    data["sector_strong"] = data["sector_strong"].astype("boolean")
    data.loc[0, "sector_strong"] = pd.NA
    data.to_parquet(path, index=False)
    context = load_industry_etf_context(path)
    assert pd.isna(context.loc[0, "sector_strong"])


def test_load_industry_etf_context_rejects_missing_columns_and_non_boolean_values(tmp_path):
    missing_path = tmp_path / "missing.parquet"
    pd.DataFrame({"trade_date": ["20240102"]}).to_parquet(missing_path, index=False)
    with pytest.raises(ValueError, match="industry ETF context is missing columns"):
        load_industry_etf_context(missing_path)

    invalid_path = tmp_path / "invalid.parquet"
    invalid = _context()
    invalid["sector_strong"] = ["yes", "no"]
    invalid.to_parquet(invalid_path, index=False)
    with pytest.raises(ValueError, match="sector_strong must be boolean"):
        load_industry_etf_context(invalid_path)


def test_attach_industry_etf_context_requires_datetime_index() -> None:
    with pytest.raises(TypeError, match="DatetimeIndex"):
        attach_industry_etf_context(
            pd.DataFrame(index=[0]),
            industry_code="bank",
            industry_context=pd.DataFrame(
                columns=[
                    "trade_date",
                    "industry_code",
                    "sector_close",
                    "sector_ma20",
                    "sector_ma60",
                    "sector_strong",
                ]
            ),
        )
