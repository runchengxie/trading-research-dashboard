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
