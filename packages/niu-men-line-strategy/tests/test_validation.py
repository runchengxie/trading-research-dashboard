import pandas as pd

from niu_men_line_strategy.validation import validate_research_inputs


def test_validate_research_inputs_reports_join_and_market_gaps(tmp_path) -> None:
    daily = tmp_path / "daily" / "data"
    daily.mkdir(parents=True)
    pd.DataFrame({"x": [1]}).to_parquet(daily / "000001.SZ.parquet")
    universe = tmp_path / "universe.csv"
    pd.DataFrame(
        {
            "trade_date": [20240131, 20240131],
            "symbol": ["000001.SZ", "000002.SZ"],
            "liq_metric": [1, 1],
            "selected": [1, 1],
        }
    ).to_csv(universe, index=False)
    industry = tmp_path / "industry.parquet"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ"],
            "effective_date": [20200101],
            "end_date": [None],
            "industry_code": ["801010.SI"],
            "industry_name": ["农林牧渔"],
        }
    ).to_parquet(industry, index=False)
    market = tmp_path / "market.parquet"
    pd.DataFrame(
        {
            "ts_code": ["000906.SH"],
            "trade_date": [20240130],
            "close": [1.0],
            "vol": [1.0],
        }
    ).to_parquet(market, index=False)
    report = validate_research_inputs(
        daily_clean_root=daily.parent,
        universe_path=universe,
        industry_changes_path=industry,
        market_index_path=market,
    )
    assert report.universe_file_coverage == 0.5
    assert report.industry_coverage == 0.5
    assert len(report.warnings) == 3
